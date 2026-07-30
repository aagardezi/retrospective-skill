---
name: retrospective
description: Analyze Antigravity session conversations in a workspace to produce a structured retrospective — identifying goals, conversation arcs, friction points, tool efficiency, context waste, git commits, subagent performance, and actionable rule proposals. Automatically exports ./RETRO.md. Use when the user says /retro, /retrospective, "retro", "retrospective", "session review", "analyze session", or when wrapping up a session to capture lessons.
metadata:
  author: agent
  version: "0.2.1"
---

# Retrospective Skill for Antigravity (v0.2.1)

Run a retrospective on your current Antigravity workspace session(s): analyze what happened, what worked, what didn't, measure context/tool waste, track git commit impact, and propose concrete improvements to agent rules, skills, prompts, or workflows.

Automatically generates a rich, detailed `./RETRO.md` report upon completion.

---

## Step 1: Extract Session Data

Session transcripts and database records live in local Antigravity session storage. Always use the extraction script to process these files to avoid token overhead.

### Run Extraction

Execute the Python extraction script to extract structured JSON and generate initial `./RETRO.md`:

```bash
python3 scripts/extract_antigravity_session.py --workspace . --git --export ./RETRO.md
```

To extract full conversation arcs for a specific session ID:

```bash
python3 scripts/extract_antigravity_session.py --session <session-id> --git
```

The script outputs JSON containing:
- `workspace`: Target workspace path.
- `sessions_count`: Number of matched sessions (including 2-Pass Hierarchy subagents).
- `git_metrics`: Commits created during session, insertions (+), deletions (-), and diff stats.
- `sessions`: List of parsed sessions, including:
  - `session_id`, `created_at`, `updated_at`, `duration_seconds`, `total_steps`.
  - `tools_used`: Counts per tool name.
  - `tool_waste`: Total bytes fetched and oversized output details (>20KB).
  - `subagents`: List of subagent dispatches with roles and prompts.
  - `files_read_count` / `files_written_count` and list of written files.
  - `friction_signals`: Detected user corrections, error steps, and keyword triggers.
  - `rule_proposals`: Auto-generated rule/skill patch recommendations based on friction signals.
  - `conversation_arc`: Step-by-step timeline of user requests and assistant responses.

---

## Step 2: Read the Conversation Arc & Synthesize Deep Retrospective

Read the extracted JSON data to trace the session narrative in detail:
1. **User Request & Intent**: What did the user actually ask for at each turn?
2. **Pivots & Course Changes**: How did the approach evolve? Did the agent change plans mid-stream?
3. **Friction Points & Root Causes**: Trace every error or user redirect to its underlying root cause and operational impact.
4. **What Worked Well**: Highlight first-try accomplishments, effective tool usage, and productive subagent dispatches.

---

## Step 3: Write Rich Retrospective Report (`./RETRO.md`)

Synthesize a comprehensive, deep retrospective report following `references/retro_template.md` and write it directly to `./RETRO.md` using `write_to_file`:

```markdown
# Session Retrospective Report - [Project/Workspace Name]

**Date**: YYYY-MM-DD
**Workspace**: `/path/to/project`
**Sessions Analyzed**: N
**Total Duration**: X minutes
**Files Modified**: M

## Executive Summary
Detailed multi-paragraph overview of session objectives, accomplishments, and major deliverables.

## Key Metrics
| Metric | Value |
|---|---|
| Total Session Steps | N |
| Tool Invocations | T |
| Subagents Spawned | S |
| Files Written / Edited | M |
| Friction Signals Flagged | F |
| Git Commits Created | C |
| Git Line Delta | +X / -Y |

## Conversation Arc & Major Milestones
Detailed timeline of user prompts, key plan evolutions, subagent dispatches, and completions.

## What Worked Well
- First-try successes
- Efficient subagent dispatches
- High-value tool usage

## Friction Points & Root Cause Analysis
### 1. [Friction Title]
- **Observed Signal**: What went wrong or caused user redirect
- **Root Cause**: Underlying technical or prompt failure
- **Impact**: Time/context impact

## Tool Efficiency & Context Inflation (Waste Metrics)
- Oversized tool outputs (>20KB) and context inflation details.

## Automated Rule & Skill Improvement Proposals
| Area | Proposed Action | Rationale | Trigger Step |
|---|---|---|---|
```

---

## Step 4: Interactive Walkthrough

Walk through the proposed improvements with the user:
- Present the newly generated `./RETRO.md` file link.
- Highlight rule or skill updates that can prevent observed friction in future sessions.
- Offer to write or apply approved rule changes directly to `.gemini/GEMINI.md` or skill files.
