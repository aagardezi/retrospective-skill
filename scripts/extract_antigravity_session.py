#!/usr/bin/env python3
"""
extract_antigravity_session.py - v0.2.1 Session data extraction and retrospective engine for Antigravity.

Scans Antigravity conversation databases (~/.gemini/jetski/conversations/*.db) and brain transcripts
(~/.gemini/jetski/brain/<UUID>/.system_generated/logs/transcript.jsonl) to extract:
- 2-Pass Hierarchy-Aware session discovery (root sessions + subagent worktrees).
- Rich Conversation Arc & User Prompts Timeline.
- Tool Waste & Context Inflation Metrics (identifying unused tool outputs >20KB).
- Git Activity Tracking (commits, insertions, deletions, diff stats during session timeframe).
- Subagent Attribution & Performance Metrics.
- Automated Rule & Skill Improvement Proposals based on friction signals.
- Comprehensive Markdown Retrospective Auto-Export (./RETRO.md).

Fully portable across workspaces and user environments.
"""

import os
import sys
import json
import sqlite3
import glob
import re
import subprocess
import argparse
from datetime import datetime

# Resolve Antigravity data root directory
def get_antigravity_dir():
    env_dir = os.environ.get("ANTIGRAVITY_HOME") or os.environ.get("JETSKI_HOME")
    if env_dir and os.path.exists(env_dir):
        return env_dir
    
    candidates = [
        os.path.expanduser("~/.gemini/jetski"),
        os.path.expanduser("~/.antigravity/jetski"),
        os.path.expanduser("~/.config/antigravity")
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]

GEMINI_DIR = get_antigravity_dir()
CONVERSATIONS_DIR = os.path.join(GEMINI_DIR, "conversations")
BRAIN_DIR = os.path.join(GEMINI_DIR, "brain")

FRICTION_KEYWORDS = [
    "wrong", "error", "failed", "failure", "fix", "don't", "stop",
    "instead", "invalid", "re-do", "incorrect", "bug", "undo", "redo",
    "broken", "unexpected", "issue", "missing"
]


def find_conversations_for_workspace(workspace_path):
    """
    Robust 2-Pass Discovery:
    Pass 1: Find Root Conversations via DB blobs & Brain transcript metadata (<user_information>).
    Pass 2: Trace Subagent Worktrees (brain/<ROOT_ID>/.system_generated/worktrees/...) to resolve child sessions.
    """
    norm_target = os.path.abspath(workspace_path)
    
    root_convs = set()
    all_db_files = glob.glob(os.path.join(CONVERSATIONS_DIR, "*.db")) if os.path.exists(CONVERSATIONS_DIR) else []
    
    # --- Pass 1: Find Root Sessions ---
    for db_path in all_db_files:
        conv_id = os.path.basename(db_path).replace(".db", "")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trajectory_metadata_blob';")
            if cursor.fetchone():
                cursor.execute("SELECT data FROM trajectory_metadata_blob")
                row = cursor.fetchone()
                if row and row[0]:
                    blob_str = row[0].decode("utf-8", errors="ignore")
                    if norm_target in blob_str:
                        root_convs.add(conv_id)
            conn.close()
        except Exception:
            pass

    # Check orphaned brain transcripts missing DB entries or for user_information URI tag
    if os.path.exists(BRAIN_DIR):
        for conv_id in os.listdir(BRAIN_DIR):
            if conv_id in root_convs:
                continue
            tpath = os.path.join(BRAIN_DIR, conv_id, ".system_generated", "logs", "transcript.jsonl")
            if os.path.exists(tpath):
                try:
                    with open(tpath, "r", encoding="utf-8") as f:
                        for line in f:
                            if "<user_information>" in line and norm_target in line:
                                root_convs.add(conv_id)
                                break
                except Exception:
                    pass

    # --- Pass 2: Resolve Subagent Sessions via Hierarchy Tracing ---
    matched_convs = set(root_convs)
    if root_convs:
        for db_path in all_db_files:
            conv_id = os.path.basename(db_path).replace(".db", "")
            if conv_id in matched_convs:
                continue
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trajectory_metadata_blob';")
                if cursor.fetchone():
                    cursor.execute("SELECT data FROM trajectory_metadata_blob")
                    row = cursor.fetchone()
                    if row and row[0]:
                        blob_str = row[0].decode("utf-8", errors="ignore")
                        for root_id in root_convs:
                            if root_id in blob_str and ".system_generated/worktrees" in blob_str:
                                matched_convs.add(conv_id)
                                break
                conn.close()
            except Exception:
                pass

    return sorted(list(matched_convs))


def get_git_activity(workspace_path, start_iso=None, end_iso=None):
    """Fetch git commit logs and diff metrics for the session timeframe."""
    git_info = {
        "commits": [],
        "files_changed": 0,
        "insertions": 0,
        "deletions": 0
    }
    if not os.path.exists(os.path.join(workspace_path, ".git")):
        return git_info

    try:
        # Run git log
        cmd = ["git", "log", "-n", "10", "--pretty=format:%h|%an|%s|%cd", "--date=iso"]
        if start_iso:
            cmd.extend(["--since", start_iso])
        if end_iso:
            cmd.extend(["--until", end_iso])

        res = subprocess.run(cmd, cwd=workspace_path, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.strip().split("\n"):
                parts = line.split("|")
                if len(parts) >= 4:
                    git_info["commits"].append({
                        "hash": parts[0],
                        "author": parts[1],
                        "subject": parts[2],
                        "date": parts[3]
                    })

        # Run git diff stat
        diff_cmd = ["git", "diff", "--stat", "HEAD~5", "HEAD"] if git_info["commits"] else ["git", "diff", "--stat"]
        res_diff = subprocess.run(diff_cmd, cwd=workspace_path, capture_output=True, text=True)
        if res_diff.returncode == 0 and res_diff.stdout.strip():
            stat_line = res_diff.stdout.strip().split("\n")[-1]
            # e.g., " 3 files changed, 45 insertions(+), 12 deletions(-)"
            fc = re.search(r'(\d+)\s+file', stat_line)
            ins = re.search(r'(\d+)\s+insertion', stat_line)
            dels = re.search(r'(\d+)\s+deletion', stat_line)

            if fc:
                git_info["files_changed"] = int(fc.group(1))
            if ins:
                git_info["insertions"] = int(ins.group(1))
            if dels:
                git_info["deletions"] = int(dels.group(1))

    except Exception:
        pass

    return git_info


def parse_transcript(conv_id, summary_only=False, metadata_only=False):
    """Parse transcript.jsonl for a single conversation ID."""
    tpath = os.path.join(BRAIN_DIR, conv_id, ".system_generated", "logs", "transcript.jsonl")
    full_tpath = os.path.join(BRAIN_DIR, conv_id, ".system_generated", "logs", "transcript_full.jsonl")

    target_path = tpath if os.path.exists(tpath) else (full_tpath if os.path.exists(full_tpath) else None)

    if not target_path:
        return None

    steps = []
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    steps.append(json.loads(line))
    except Exception:
        return None

    if not steps:
        return None

    first_step = steps[0]
    last_step = steps[-1]

    created_at = first_step.get("created_at", "")
    updated_at = last_step.get("created_at", "")

    # Calculate duration
    duration_seconds = 0
    try:
        t0 = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        duration_seconds = int((t1 - t0).total_seconds())
    except Exception:
        pass

    # Find first user request
    first_request = ""
    for step in steps:
        stype = step.get("type", "")
        source = step.get("source", "")
        content = step.get("content", "")
        if stype == "USER_INPUT" or source == "USER_EXPLICIT":
            clean_text = content
            if "<USER_REQUEST>" in clean_text:
                match = re.search(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', clean_text, re.DOTALL)
                if match:
                    clean_text = match.group(1)
            first_request = clean_text.strip().replace("\n", " ")
            if first_request:
                break

    if metadata_only:
        return {
            "session_id": conv_id,
            "created_at": created_at,
            "updated_at": updated_at,
            "duration_seconds": duration_seconds,
            "total_steps": len(steps),
            "first_request": first_request[:200]
        }

    tools_used = {}
    tool_result_sizes = {}
    subagents = []
    files_read = set()
    files_written = set()
    friction_signals = []
    conversation_arc = []
    oversized_outputs = []
    rule_proposals = []

    for idx, step in enumerate(steps):
        step_idx = step.get("step_index", idx)
        source = step.get("source", "")
        stype = step.get("type", "")
        content = step.get("content", "")

        # Tool calls count
        tool_calls = step.get("tool_calls", [])
        for tc in tool_calls:
            tname = tc.get("name", "unknown")
            tools_used[tname] = tools_used.get(tname, 0) + 1

            # Extract subagents
            if tname == "invoke_subagent":
                args = tc.get("args", {})
                subs = args.get("Subagents", [])
                if isinstance(subs, str):
                    try:
                        subs = json.loads(subs)
                    except Exception:
                        subs = []
                for sub in subs:
                    subagents.append({
                        "role": sub.get("Role", ""),
                        "type": sub.get("TypeName", ""),
                        "prompt": sub.get("Prompt", "")[:150]
                    })

            # Extract file interactions
            if tname in ["view_file", "read_file"]:
                fpath = tc.get("args", {}).get("AbsolutePath") or tc.get("args", {}).get("TargetFile")
                if fpath:
                    files_read.add(str(fpath).strip('"\''))
            elif tname in ["write_to_file", "replace_file_content", "multi_replace_file_content"]:
                fpath = tc.get("args", {}).get("TargetFile")
                if fpath:
                    files_written.add(str(fpath).strip('"\''))

        # Track output sizes & detect oversized waste (>20KB)
        if content:
            content_len = len(content)
            tool_result_sizes[stype] = tool_result_sizes.get(stype, 0) + content_len
            if content_len > 20000 and stype not in ["CONVERSATION_HISTORY", "CHECKPOINT"]:
                oversized_outputs.append({
                    "step": step_idx,
                    "type": stype,
                    "size_bytes": content_len,
                    "kb": round(content_len / 1024, 1)
                })

        # Extract conversation arc
        if stype == "USER_INPUT" or source == "USER_EXPLICIT":
            clean_text = content
            if "<USER_REQUEST>" in clean_text:
                match = re.search(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', clean_text, re.DOTALL)
                if match:
                    clean_text = match.group(1)

            conversation_arc.append({
                "step": step_idx,
                "role": "user",
                "text": clean_text[:500]
            })

            # Check for user friction signals
            clean_lower = clean_text.lower()
            for kw in FRICTION_KEYWORDS:
                if f" {kw} " in f" {clean_lower} " or clean_lower.startswith(kw):
                    friction_signals.append({
                        "step": step_idx,
                        "type": "user_feedback",
                        "keyword": kw,
                        "snippet": clean_text[:200]
                    })
                    break

        elif stype == "PLANNER_RESPONSE":
            thinking = step.get("thinking", "")
            snippet = thinking[:200] if thinking else "Planner tool execution"
            conversation_arc.append({
                "step": step_idx,
                "role": "assistant",
                "tools": [tc.get("name") for tc in tool_calls],
                "snippet": snippet
            })

        # Detect error/friction steps and generate proposals
        status = step.get("status", "")
        if status == "ERROR" or "error" in content.lower() or "exception" in content.lower():
            if stype not in ["CONVERSATION_HISTORY", "CHECKPOINT"]:
                friction_signals.append({
                    "step": step_idx,
                    "type": "execution_error",
                    "snippet": content[:200]
                })

                # Rule proposals generator
                if "syntax error" in content.lower():
                    rule_proposals.append({
                        "area": "Command Execution",
                        "proposal": "Avoid unescaped special characters or quotes in bash -c string parameters.",
                        "trigger_step": step_idx
                    })
                elif "no such file" in content.lower() or "not found" in content.lower():
                    rule_proposals.append({
                        "area": "File System",
                        "proposal": "Verify target directory and file existence before executing file commands.",
                        "trigger_step": step_idx
                    })

    total_tool_bytes = sum(tool_result_sizes.values())
    wasted_tool_bytes = sum(item["size_bytes"] for item in oversized_outputs)

    result = {
        "session_id": conv_id,
        "created_at": created_at,
        "updated_at": updated_at,
        "duration_seconds": duration_seconds,
        "total_steps": len(steps),
        "first_request": first_request[:200],
        "tools_used": tools_used,
        "tool_result_total_bytes": total_tool_bytes,
        "tool_waste": {
            "total_tool_bytes": total_tool_bytes,
            "oversized_outputs_count": len(oversized_outputs),
            "wasted_bytes": wasted_tool_bytes,
            "wasted_kb": round(wasted_tool_bytes / 1024, 1),
            "oversized_details": oversized_outputs
        },
        "subagents": subagents,
        "files_read_count": len(files_read),
        "files_written_count": len(files_written),
        "files_written": list(files_written),
        "friction_signals_count": len(friction_signals),
        "friction_signals": friction_signals,
        "rule_proposals": rule_proposals
    }

    if not summary_only:
        result["conversation_arc"] = conversation_arc

    return result


def export_markdown_retro(data, export_path):
    """Generate a rich, detailed retrospective markdown report including full conversation arcs, friction, subagents, and git activity."""
    workspace = data.get("workspace", "Current Workspace")
    sessions_count = data.get("sessions_count", 0)
    sessions = data.get("sessions", [])
    git_metrics = data.get("git_metrics", {})

    total_duration = sum(s.get("duration_seconds", 0) for s in sessions)
    total_steps = sum(s.get("total_steps", 0) for s in sessions)
    all_files_written = sorted(list(set(f for s in sessions for f in s.get("files_written", []))))
    total_friction = sum(s.get("friction_signals_count", 0) for s in sessions)
    total_subagents = sum(len(s.get("subagents", [])) for s in sessions)
    total_tool_calls = sum(sum(s.get("tools_used", {}).values()) for s in sessions)

    min_sec = f"{total_duration // 60}m {total_duration % 60}s"

    lines = [
        f"# Session Retrospective Report - {os.path.basename(workspace)}",
        "",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d')}",
        f"**Workspace**: `{workspace}`",
        f"**Sessions Analyzed**: {sessions_count}",
        f"**Total Duration**: {min_sec}",
        f"**Files Modified**: {len(all_files_written)}",
        "",
        "---",
        "",
        "## Executive Summary",
        f"Retrospective analysis across {sessions_count} session(s) in workspace `{os.path.basename(workspace)}`. The session(s) completed a total of {total_steps} execution steps, made {len(all_files_written)} file modifications, dispatched {total_subagents} subagent tasks, and executed {total_tool_calls} tool calls.",
        "",
        "---",
        "",
        "## Key Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total Session Steps | {total_steps} |",
        f"| Tool Invocations | {total_tool_calls} |",
        f"| Subagents Spawned | {total_subagents} |",
        f"| Files Written / Edited | {len(all_files_written)} |",
        f"| Friction Signals Flagged | {total_friction} |",
        f"| Git Commits Created | {len(git_metrics.get('commits', []))} |",
        f"| Git Line Delta | +{git_metrics.get('insertions', 0)} / -{git_metrics.get('deletions', 0)} |",
        "",
        "---",
        "",
        "## Conversation Arc & Session Timeline",
        ""
    ]

    # Detailed Timeline for each session
    for s_idx, s in enumerate(sessions, 1):
        sid = s.get("session_id", "")[:8]
        created = s.get("created_at", "")[:16]
        req = s.get("first_request", "No prompt recorded")
        steps_cnt = s.get("total_steps", 0)

        lines.append(f"### Session {s_idx}: `{sid}` ({created}, {steps_cnt} steps)")
        lines.append(f"- **Initial Request / Goal**: {req}")
        
        # Subagents in this session
        subs = s.get("subagents", [])
        if subs:
            lines.append("- **Subagents Spawned**:")
            for sub in subs:
                lines.append(f"  - **{sub.get('role')}** (`{sub.get('type')}`): {sub.get('prompt')}")
        
        # Timeline Arc
        arc = s.get("conversation_arc", [])
        if arc:
            lines.append("- **Key Steps & Turns**:")
            for turn in arc:
                role = turn.get("role", "").upper()
                step_num = turn.get("step", 0)
                if role == "USER":
                    lines.append(f"  - **Step {step_num} [USER]**: {turn.get('text', '').strip()}")
                elif role == "ASSISTANT":
                    tools = ", ".join(turn.get("tools", []))
                    snippet = turn.get("snippet", "").strip()
                    lines.append(f"  - **Step {step_num} [ASSISTANT]** (Tools: {tools or 'none'}): {snippet}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Tool Efficiency & Context Inflation (Waste Metrics)",
        ""
    ])
    for s in sessions:
        tw = s.get("tool_waste", {})
        sid = s.get("session_id", "")[:8]
        lines.append(f"- **Session `{sid}`**: {tw.get('total_tool_bytes', 0)} total bytes fetched | **{tw.get('wasted_kb', 0)} KB** in oversized outputs (>20KB).")
        for det in tw.get("oversized_details", []):
            lines.append(f"  - Step {det['step']} ({det['type']}): {det['kb']} KB payload")

    lines.extend([
        "",
        "---",
        "",
        "## Modified Files",
        ""
    ])
    if all_files_written:
        for fpath in all_files_written:
            lines.append(f"- `{fpath}`")
    else:
        lines.append("- No files modified.")

    lines.extend([
        "",
        "---",
        "",
        "## Friction Points & Root Cause Analysis",
        ""
    ])
    friction_found = False
    for s in sessions:
        sid = s.get("session_id", "")[:8]
        for f_sig in s.get("friction_signals", []):
            friction_found = True
            lines.append(f"### Friction at Step {f_sig['step']} (Session `{sid}`, Type: {f_sig['type']})")
            lines.append(f"```")
            lines.append(f"{f_sig['snippet'].strip()}")
            lines.append(f"```")
            lines.append(f"- **Analysis**: Execution flag or user correction triggered at this turn.")
            lines.append("")

    if not friction_found:
        lines.append("- No critical friction signals or user redirects recorded.")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Automated Rule & Skill Improvement Proposals",
        "",
        "| Area | Proposal | Trigger Step |",
        "|---|---|---|",
    ])
    proposals_found = False
    for s in sessions:
        for prop in s.get("rule_proposals", []):
            proposals_found = True
            lines.append(f"| **{prop['area']}** | {prop['proposal']} | Step {prop['trigger_step']} |")

    if not proposals_found:
        lines.append("| **General** | All tool calls executed within standard error thresholds. | N/A |")

    lines.extend([
        "",
        "---",
        "*Report automatically generated by Antigravity Retrospective Skill v0.2.1.*"
    ])

    report_content = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)
    with open(export_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return export_path


def main():
    parser = argparse.ArgumentParser(description="v0.2.1 Extract session data for Antigravity retrospectives.")
    parser.add_argument("--workspace", type=str, help="Path to workspace directory")
    parser.add_argument("--session", type=str, help="Specific conversation UUID")
    parser.add_argument("--summary", action="store_true", help="Output compact summary without full arc")
    parser.add_argument("--metadata-only", action="store_true", help="Output metadata only")
    parser.add_argument("--print-requests", action="store_true", help="Print user requests for matching sessions directly")
    parser.add_argument("--git", action="store_true", help="Include git commit and diff metrics")
    parser.add_argument("--export", type=str, nargs="?", const="./RETRO.md", help="Export retrospective report to markdown file (defaults to ./RETRO.md)")

    args = parser.parse_args()

    if not args.workspace and not args.session:
        args.workspace = os.getcwd()

    target_convs = []

    if args.session:
        target_convs = [args.session]
    elif args.workspace:
        target_convs = find_conversations_for_workspace(args.workspace)

    if not target_convs:
        print(json.dumps({
            "error": "No conversations found matching target.",
            "workspace": args.workspace,
            "session": args.session,
            "antigravity_dir": GEMINI_DIR
        }, indent=2))
        sys.exit(1)

    sessions_data = []
    for conv_id in target_convs:
        parsed = parse_transcript(conv_id, summary_only=args.summary, metadata_only=args.metadata_only)
        if parsed:
            sessions_data.append(parsed)

    # Sort chronologically
    sessions_data.sort(key=lambda s: s.get("created_at", ""))

    git_metrics = {}
    if args.git and args.workspace:
        start_t = sessions_data[0].get("created_at") if sessions_data else None
        end_t = sessions_data[-1].get("updated_at") if sessions_data else None
        git_metrics = get_git_activity(args.workspace, start_t, end_t)

    if args.print_requests:
        print(f"=== User Requests for Workspace ({args.workspace}) ===")
        for s in sessions_data:
            sid = s.get("session_id", "")[:8]
            created = s.get("created_at", "")[:16]
            steps_cnt = s.get("total_steps", 0)
            req = s.get("first_request", "N/A")
            print(f"[{sid}] ({created}, steps: {steps_cnt}) -> {req}")
        return

    output = {
        "workspace": os.path.abspath(args.workspace) if args.workspace else None,
        "sessions_count": len(sessions_data),
        "sessions": sessions_data,
        "git_metrics": git_metrics
    }

    if args.export:
        export_file = export_markdown_retro(output, args.export)
        output["exported_to"] = os.path.abspath(export_file)
        print(f"Retrospective report successfully exported to: {os.path.abspath(export_file)}")

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
