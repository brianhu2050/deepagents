# 🚀🧠 Deep Agents CLI

The [deepagents](https://github.com/langchain-ai/deepagents) CLI is an open source coding assistant that runs in your terminal, similar to Claude Code.

**Key Features:**
- **Built-in Tools**: File operations (read, write, edit, glob, grep), shell commands, web search, and subagent delegation
- **Customizable Skills**: Add domain-specific capabilities through a progressive disclosure skill system
- **Persistent Memory**: Agent remembers your preferences, coding style, and project context across sessions
- **Project-Aware**: Automatically detects project roots and loads project-specific configurations 

<img src="cli-banner.jpg" alt="deep agent" width="100%"/>

## 🚀 Quickstart

`deepagents-cli` is a Python package that can be installed via pip or uv.

**Install via pip:**
```bash
pip install deepagents-cli
```

**Or using uv (recommended):**
```bash
# Create a virtual environment
uv venv

# Install the package
uv pip install deepagents-cli
```

**Run the agent in your terminal:**
```bash
deepagents
```

**Get help:**
```bash
deepagents help
```

**Common options:**
```bash
# Use a specific agent configuration
deepagents --agent mybot

# Auto-approve tool usage (skip human-in-the-loop prompts)
deepagents --auto-approve

# Execute code in a remote sandbox
deepagents --sandbox modal        # or runloop, daytona
deepagents --sandbox-id dbx_123   # reuse existing sandbox
```

Type naturally as you would in a chat interface. The agent will use its built-in tools, skills, and memory to help you with tasks. 

## Built-in Tools

The agent comes with the following built-in tools (always available without configuration):

| Tool | Description |
|------|-------------|
| `ls` | List files and directories |
| `read_file` | Read contents of a file |
| `write_file` | Create or overwrite a file |
| `edit_file` | Make targeted edits to existing files |
| `glob` | Find files matching a pattern (e.g., `**/*.py`) |
| `grep` | Search for text patterns across files |
| `shell` | Execute shell commands (local mode) |
| `execute` | Execute commands in remote sandbox (sandbox mode) |
| `web_search` | Search the web using Tavily API |
| `fetch_url` | Fetch and convert web pages to markdown |
| `task` | Delegate work to subagents for parallel execution |
| `write_todos` | Create and manage task lists for complex work |

> [!WARNING]
> **Human-in-the-Loop (HITL) Approval Required**
>
> Potentially destructive operations require user approval before execution:
> - **File operations**: `write_file`, `edit_file`
> - **Command execution**: `shell`, `execute`
> - **External requests**: `web_search`, `fetch_url`
> - **Delegation**: `task` (subagents)
>
> Each operation will prompt for approval showing the action details. Use `--auto-approve` to skip prompts:
> ```bash
> deepagents --auto-approve
> ``` 

## Agent Configuration

Each agent has its own configuration directory at `~/.deepagents/<agent_name>/`, with default `agent`.

```bash
# List all configured agents
deepagents list

# Create a new agent
deepagents create <agent_name>
```

## Customization 

There are two primary ways to customize any agent: **memory** and **skills**. 

Each agent has its own global configuration directory at `~/.deepagents/<agent_name>/`:

```
~/.deepagents/<agent_name>/
  ├── agent.md              # Auto-loaded global personality/style
  └── skills/               # Auto-loaded agent-specific skills
      ├── web-research/
      │   └── SKILL.md
      └── langgraph-docs/
          └── SKILL.md
```

Projects can extend the global configuration with project-specific instructions and skills:

```
my-project/
  ├── .git/
  └── .deepagents/
      ├── agent.md          # Project-specific instructions
      └── skills/           # Project-specific skills
          └── custom-tool/
              └── SKILL.md
```

The CLI automatically detects project roots (via `.git`) and loads:
- Project-specific `agent.md` from `[project-root]/.deepagents/agent.md`
- Project-specific skills from `[project-root]/.deepagents/skills/`

Both global and project configurations are loaded together, allowing you to:
- Keep general coding style/preferences in global agent.md
- Add project-specific context, conventions, or guidelines in project agent.md
- Share project-specific skills with your team (committed to version control)
- Override global skills with project-specific versions (when skill names match)

### agent.md files

`agent.md` files provide persistent memory that is always loaded at session start. Both global and project-level `agent.md` files are loaded together and injected into the system prompt.

**Global `agent.md`** (`~/.deepagents/agent/agent.md`) 
  - Your personality, style, and universal coding preferences
  - General tone and communication style
  - Universal coding preferences (formatting, type hints, etc.)
  - Tool usage patterns that apply everywhere
  - Workflows and methodologies that don't change per-project

**Project `agent.md`** (`.deepagents/agent.md` in project root) 
  - Project-specific context and conventions
  - Project architecture and design patterns
  - Coding conventions specific to this codebase
  - Testing strategies and deployment processes
  - Team guidelines and project structure

**How it works (AgentMemoryMiddleware):**
- Loads both files at startup and injects into system prompt as `<user_memory>` and `<project_memory>`
- Appends [memory management instructions](deepagents_cli/agent_memory.py#L44-L158) on when/how to update memory files

**When the agent updates memory:**
- IMMEDIATELY when you describe how it should behave
- IMMEDIATELY when you give feedback on its work
- When you explicitly ask it to remember something
- When patterns or preferences emerge from your interactions

The agent uses `edit_file` to update memories when learning preferences or receiving feedback.

### Project memory files

Beyond `agent.md`, you can create additional memory files in `.deepagents/` for structured project knowledge. These work similarly to [Anthropic's Memory Tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool). The agent receives [detailed instructions](deepagents_cli/agent_memory.py#L123-L158) on when to read and update these files.

**How it works:**
1. Create markdown files in `[project-root]/.deepagents/` (e.g., `api-design.md`, `architecture.md`, `deployment.md`)
2. The agent checks these files when relevant to a task (not auto-loaded into every prompt)
3. The agent uses `write_file` or `edit_file` to create/update memory files when learning project patterns

**Example workflow:**
```bash
# Agent discovers deployment pattern and saves it
.deepagents/
├── agent.md           # Always loaded (personality + conventions)
├── architecture.md    # Loaded on-demand (system design)
└── deployment.md      # Loaded on-demand (deploy procedures)
```

**When the agent reads memory files:**
- At the start of new sessions (checks what files exist)
- Before answering questions about project-specific topics
- When you reference past work or patterns
- When performing tasks that match saved knowledge domains

**Benefits:**
- **Persistent learning**: Agent remembers project patterns across sessions
- **Team collaboration**: Share project knowledge through version control
- **Contextual retrieval**: Load only relevant memory when needed (reduces token usage)
- **Structured knowledge**: Organize information by domain (APIs, architecture, deployment, etc.)

### Skills

Skills are reusable agent capabilities that provide specialized workflows and domain knowledge. Example skills are provided in the `examples/skills/` directory:

- **web-research** - Structured web research workflow with planning, parallel delegation, and synthesis
- **langgraph-docs** - LangGraph documentation lookup and guidance

To use an example skill globally with the default agent, just copy them to the agent's skills global or project-level skills directory:

```bash
mkdir -p ~/.deepagents/agent/skills
cp -r examples/skills/web-research ~/.deepagents/agent/skills/
```

To manage skills: 

```bash
# List all skills (global + project)
deepagents skills list

# List only project skills
deepagents skills list --project

# Create a new global skill from template
deepagents skills create my-skill

# Create a new project skill
deepagents skills create my-tool --project

# View detailed information about a skill
deepagents skills info web-research

# View info for a project skill only
deepagents skills info my-tool --project
```

To use skills (e.g., the langgraph-docs skill), just type a request relevant to a skill and the skill will be used automatically.

```bash
$ deepagents 
$ "create a agent.py script that implements a LangGraph agent" 
```

Skills follow Anthropic's [progressive disclosure pattern](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) - the agent knows skills exist but only reads full instructions when needed.

The CLI supports two modes for this:

1.  **Default Mode (`SkillsMiddleware`)**: At startup, the agent scans all `SKILL.md` files and injects their `name` and `description` into the system prompt. The agent knows the skills exist, but must use `read_file` to access the full instructions.
2.  **Lazy Loading Mode (`SkillActivationMiddleware`)**: This is a more advanced pattern. Not only are the instructions progressively disclosed, but the tools associated with a skill only become available *after* the agent has used `read_file` on the corresponding `SKILL.md`.

### Lazy Loading of Tools

When using the `SkillActivationMiddleware`, you can bundle tools with your skills that are loaded dynamically at runtime.

**How it works:**

1.  **Add a `tools` key** to your `SKILL.md`'s YAML frontmatter. This key should contain a list of Python import strings for your tools.
2.  When the agent uses the `read_file` tool to read this `SKILL.md` file, the `SkillActivationMiddleware` intercepts the action.
3.  It parses the `tools` list, dynamically imports the tools, and adds them to the agent's set of available tools for all subsequent calls.

This encourages the agent to develop a more realistic workflow of "learning" about a skill before it can use its associated capabilities.

For security, tools can only be loaded from the `deepagents_cli.skills.contrib` namespace.

**Example:**

Let's say you have a tool in `libs/deepagents-cli/deepagents_cli/skills/contrib/system.py`:

```python
# libs/deepagents-cli/deepagents_cli/skills/contrib/system.py
from datetime import datetime
from langchain_core.tools import tool

@tool
def get_current_datetime(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Returns the current date and time."""
    return datetime.now().strftime(format)
```

You can create a skill that makes this tool available to the agent *after* it has been read:

**`~/.deepagents/agent/skills/system-info/SKILL.md`**:

```yaml
---
name: system-info
description: Provides tools to get system information, like the current date and time.
tools:
  - "deepagents_cli.skills.contrib.system.get_current_datetime"
---

# System Information Skill

This skill provides the `get_current_datetime` tool.
```

**Agent's Workflow:**

1.  Agent starts. The `get_current_datetime` tool is **not** available.
2.  User asks for the time. The agent, seeing the `system-info` skill in its prompt, knows it should investigate.
3.  The agent calls `read_file` on `~/.deepagents/agent/skills/system-info/SKILL.md`.
4.  The `SkillActivationMiddleware` loads the `get_current_datetime` tool into the agent's context.
5.  The agent can now successfully call `get_current_datetime` to fulfill the user's request.

## Development

### Running Tests

To run the test suite:

```bash
uv sync --all-groups

make test
```

### Running During Development

```bash
# From libs/deepagents-cli directory
uv run deepagents

# Or install in editable mode
uv pip install -e .
deepagents
```

### Modifying the CLI

- **UI changes** → Edit `ui.py` or `input.py`
- **Add new tools** → Edit `tools.py`
- **Change execution flow** → Edit `execution.py`
- **Add commands** → Edit `commands.py`
- **Agent configuration** → Edit `agent.py`
- **Skills system** → Edit `skills/` modules
- **Constants/colors** → Edit `config.py`
