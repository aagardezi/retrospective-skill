# Antigravity Retrospective Skill (`retrospective` v0.2.0)

Session retrospective skill for Antigravity AI coding agents. Run `/retro` or `/retrospective` at the end of any session or workspace project to analyze what happened, identify friction points, measure tool/subagent performance, detect context inflation/tool waste, track git commit stats, and generate concrete proposals to improve your skills, rules, and workflows.

Automatically generates `./RETRO.md` upon execution.

## Package Structure

```
retrospective-skill/
├── SKILL.md                 # Main agent skill definition & workflow
├── install.sh               # One-click installation script
├── scripts/
│   └── extract_antigravity_session.py # Portable v0.2.0 Python transcript & database parser
├── references/
│   └── retro_template.md    # Standardized markdown retro report format
└── examples/
    └── sample-retro.md      # Sample retrospective output
```

## How to Install on Another Machine / Workspace

### Option 1: Global Install (Recommended)
Copy or clone this repository folder to any machine and run:

```bash
./install.sh
```

This copies the skill to `~/.gemini/config/skills/retrospective/`, making `/retro` available across all your Antigravity projects.

### Option 2: Project-Local Install
Copy the skill files into your project's `.gemini/skills/retrospective/` folder:

```bash
mkdir -p ~/.gemini/config/skills/retrospective
cp -r * ~/.gemini/config/skills/retrospective/
```

## Usage

In any Antigravity chat session:

```
/retro
```

or

```
/retrospective
```

You can also run the Python extraction script manually from the command line:

```bash
# Analyze sessions and auto-export report to ./RETRO.md
python3 scripts/extract_antigravity_session.py --workspace . --git --export ./RETRO.md

# Print user requests directly for workspace history
python3 scripts/extract_antigravity_session.py --workspace . --print-requests

# Analyze a specific session UUID
python3 scripts/extract_antigravity_session.py --session <session-id> --git
```

## Requirements
- Python 3.8+ (stdlib only, zero external dependencies)
- Works on Linux & macOS
