# Antigravity Retrospective Skill (`retrospective`) v0.2.1

A post-session retrospective framework for **Antigravity** AI coding agents. 

Run `/retro` or `/retrospective` at the end of any session or workspace project to analyze what happened, measure tool performance and context waste, track git commit stats, attribute subagent contributions, identify friction signals, and generate concrete proposals to improve your agent rules, skills, and workflows.

---

## Table of Contents

- [Overview & Purpose](#overview--purpose)
- [Key Features](#key-features)
- [How It Works (Under the Hood)](#how-it-works-under-the-hood)
- [Architecture & Package Anatomy](#architecture--package-anatomy)
- [Installation Guide](#installation-guide)
  - [Global Installation (Recommended)](#global-installation-recommended)
  - [Project-Local Installation](#project-local-installation)
  - [Multi-Machine Deployment](#multi-machine-deployment)
- [Usage & Command Reference](#usage--command-reference)
  - [In-Session Usage](#in-session-usage)
  - [Command Line (CLI) Reference](#command-line-cli-reference)
- [Understanding the Retrospective Report (`RETRO.md`)](#understanding-the-retrospective-report-retromd)
- [Privacy & Security](#privacy--security)

---

## Overview & Purpose

As AI coding agents work through complex projects, they execute tens or hundreds of steps—reading files, running bash commands, spawning subagents, and reacting to user feedback. Over long sessions, identifying where context was wasted, why errors occurred, or which subagent dispatches were effective can be difficult.

The **Antigravity Retrospective Skill** automates this post-session reflection. It scans your local Antigravity session storage (`conversations/*.db` and `brain/<UUID>/`), extracts complete step-by-step trajectory telemetry, and synthesizes a comprehensive post-project retrospective report (`./RETRO.md`).

---

## Key Features

- 🔍 **2-Pass Hierarchy-Aware Session Discovery**:
  - **Pass 1**: Discovers all root conversations matching the workspace path via SQLite database blobs and transcript metadata.
  - **Pass 2**: Traces child subagent worktrees (`brain/<ROOT_ID>/.system_generated/worktrees/...`) to resolve 100% of subagent sessions with zero false positives.
- ⚡ **Tool Waste & Context Inflation Detection**:
  - Identifies oversized tool outputs (>20KB) fetched during file reads or command executions.
  - Calculates total byte volume and flags unreferenced context inflation to optimize token efficiency.
- 📊 **Git Commit & Code Delta Tracking**:
  - Correlates session timestamps with `git log` and `git diff --stat`.
  - Captures total commits created, modified files, line insertions (`+`), and line deletions (`-`).
- 🤖 **Subagent Attribution Breakdown**:
  - Attributes step counts, tool call distributions, duration, and file changes per subagent role across dispatches.
- 💡 **Automated Rule & Skill Improvement Proposals**:
  - Analyzes friction signals (execution errors, shell syntax failures, user redirects).
  - Automatically maps error patterns to structured, copy-pasteable rule proposals for `.gemini/GEMINI.md` or skill files.
- 📝 **Rich Standalone Exporter (`./RETRO.md`)**:
  - Generates a complete, multi-section Markdown report featuring executive summaries, step-by-step turn timelines, friction logs, waste metrics, and rule tables.

---

## How It Works (Under the Hood)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Local Antigravity Storage                         │
├─────────────────────────────────────┬───────────────────────────────────┤
│  SQLite DBs                         │  Brain Trajectories               │
│  conversations/*.db                 │  brain/<UUID>/                    │
└──────────────────┬──────────────────┴─────────────────┬─────────────────┘
                   │                                    │
                   ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                extract_antigravity_session.py (Pass 1 & 2)              │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Match Root Conversations by Workspace Path                           │
│ 2. Trace Subagent Worktrees (brain/<ROOT_ID>/worktrees/...)             │
│ 3. Extract JSON Telemetry: Arcs, Friction, Tools, Waste, Subagents      │
│ 4. Fetch Git Activity: Commits, Diff Stats (+ins / -del)                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      AI Agent Synthesis / Exporter                       │
├─────────────────────────────────────────────────────────────────────────┤
│ Analyzes extracted telemetry, classifies friction, synthesizes deep     │
│ narratives following references/retro_template.md, and writes RETRO.md. │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           ./RETRO.md Report                             │
└─────────────────────────────────────────────────────────────────────────┘
```

1. **Database & Brain Inspection**: Antigravity logs every step, tool call, thinking trace, and user request to `transcript.jsonl` inside a UUID directory in `brain/<UUID>/`. Workspace metadata is stored in SQLite databases in `conversations/*.db`.
2. **Telemetry Extraction**: The Python script `extract_antigravity_session.py` scans these files using standard library modules (`sqlite3`, `json`, `glob`, `re`, `subprocess`).
3. **Synthesis & Export**: The data is formatted into structured JSON and compiled into a rich `./RETRO.md` file.

---

## Architecture & Package Anatomy

```
retrospective-skill/
├── SKILL.md                 # Main skill specification & AI workflow instructions
├── install.sh               # One-click installation script (copies to ~/.gemini/config/skills/)
├── README.md                # Package documentation & reference manual
├── .gitignore               # Configured ignore rules (excludes RETRO.md, tarballs, cache)
├── scripts/
│   └── extract_antigravity_session.py # Portable Python telemetry & discovery engine
├── references/
│   └── retro_template.md    # Standardized markdown retro report format
└── examples/
    └── sample-retro.md      # Sample retrospective output report
```

---

## Installation Guide

### Global Installation (Recommended)

To make the `/retro` slash command available across all your Antigravity workspaces on a machine:

```bash
./install.sh
```

This copies the skill package to `~/.gemini/config/skills/retrospective/`.

### Project-Local Installation

To install the skill specifically inside a single project workspace:

```bash
mkdir -p ~/.gemini/config/skills/retrospective
cp -r * ~/.gemini/config/skills/retrospective/
```

### Multi-Machine Deployment

You can archive and copy the skill folder or tarball to another workstation:

```bash
# Extract and install on target machine
tar -xzvf retrospective-skill.tar.gz -C ~/.gemini/config/skills/retrospective/
```

---

## Usage & Command Reference

### In-Session Usage

Inside any Antigravity chat session:

```
/retro
```
*or*
```
/retrospective
```

The agent will execute `extract_antigravity_session.py`, analyze your session telemetry, present key findings, and save `./RETRO.md`.

---

### Command Line (CLI) Reference

You can also run the Python extraction engine directly from your terminal:

```bash
# 1. Analyze current workspace, track git activity, and export report to ./RETRO.md
python3 scripts/extract_antigravity_session.py --workspace . --git --export ./RETRO.md

# 2. Print chronological list of first user requests across all workspace sessions
python3 scripts/extract_antigravity_session.py --workspace . --print-requests

# 3. Analyze a specific session UUID with git diff statistics
python3 scripts/extract_antigravity_session.py --session <SESSION-UUID> --git

# 4. Output compact JSON summary without full turn-by-turn arc
python3 scripts/extract_antigravity_session.py --workspace . --summary

# 5. Export retrospective report to a custom file path
python3 scripts/extract_antigravity_session.py --workspace . --export /path/to/custom_report.md
```

#### CLI Flag Summary

| Flag | Argument | Description |
|---|---|---|
| `--workspace` | `<PATH>` | Target workspace directory path (defaults to current working directory). |
| `--session` | `<UUID>` | Target specific conversation UUID for inspection. |
| `--git` | *(None)* | Include git commit logs and diff metrics (`+ins / -del`). |
| `--export` | `[PATH]` | Export complete retrospective report to markdown file (defaults to `./RETRO.md`). |
| `--print-requests` | *(None)* | Print user request history across all workspace sessions. |
| `--summary` | *(None)* | Omit turn-by-turn conversation arc from JSON output. |
| `--metadata-only` | *(None)* | Return basic session metadata only (`session_id`, `created_at`, `total_steps`). |

---

## Understanding the Retrospective Report (`RETRO.md`)

A generated `./RETRO.md` includes the following sections:

1. **Executive Summary**: High-level overview of total sessions, step count, files modified, tool calls, and subagent dispatches.
2. **Key Metrics Table**: Aggregated metrics including steps, tool count, subagents, modified files, friction signals, git commits, and line deltas.
3. **Conversation Arc & Session Timeline**: Chronological turn-by-turn narrative of user requests, assistant plans, tool calls, and subagent dispatches for every session.
4. **Tool Efficiency & Context Inflation (Waste Metrics)**: List of oversized tool payloads (>20KB) and total bytes fetched per session.
5. **Modified Files**: Complete list of files created or edited during the session.
6. **Friction Points & Root Cause Analysis**: Detailed step-by-step breakdown of execution errors, failed commands, user redirects, and snippets.
7. **Automated Rule & Skill Improvement Proposals**: Actionable recommendations table mapping friction steps to proposed `.gemini/GEMINI.md` rule updates.

---

## Privacy & Security

- **Local Processing**: `extract_antigravity_session.py` runs entirely on your local machine using standard Python library modules (`sqlite3`, `json`, `glob`). No external API calls are made by the extraction script.
- **Git Safety**: Generated session reports (`RETRO.md`), tarball archives (`*.tar.gz`), and Python cache folders (`__pycache__/`) are included in `.gitignore` to prevent accidental check-ins of session logs or local user paths.
- **Dynamic Path Resolution**: No hardcoded usernames or absolute home paths exist in the codebase. All path resolvers use `os.path.expanduser("~")` or environment variables (`ANTIGRAVITY_HOME`).

---

*Antigravity Retrospective Skill v0.2.1*
