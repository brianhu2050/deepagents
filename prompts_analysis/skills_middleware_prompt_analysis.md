# Skills Middleware Prompt 解析

`SkillsMiddleware` 通过一个精心设计的、动态填充的系统提示（System Prompt），向 LLM 引入了“技能”（Skills）的概念。这个 Prompt 的核心是实现一种名为**“渐进式披露”（Progressive Disclosure）**的交互模式，既能让模型感知到自身能力的扩展，又不会在初期就用大量无关信息淹没其上下文窗口。

## 1. `SKILLS_SYSTEM_PROMPT`

### 1.1. Prompt 模板原文

```
## Skills System

You have access to a skills library that provides specialized capabilities and domain knowledge.

{skills_locations}

**Available Skills:**

{skills_list}

**How to Use Skills (Progressive Disclosure):**

Skills follow a **progressive disclosure** pattern - you know they exist (name + description above), but you only read the full instructions when needed:

1. **Recognize when a skill applies**: Check if the user's task matches any skill's description
2. **Read the skill's full instructions**: The skill list above shows the exact path to use with read_file
3. **Follow the skill's instructions**: SKILL.md contains step-by-step workflows, best practices, and examples
4. **Access supporting files**: Skills may include Python scripts, configs, or reference docs - use absolute paths

**When to Use Skills:**
- When the user's request matches a skill's domain (e.g., "research X" → web-research skill)
- When you need specialized knowledge or structured workflows
- When a skill provides proven patterns for complex tasks

**Skills are Self-Documenting:**
- Each SKILL.md tells you exactly what the skill does and how to use it
- The skill list above shows the full path for each skill's SKILL.md file

**Executing Skill Scripts:**
Skills may contain Python scripts or other executable files. Always use absolute paths from the skill list.

**Example Workflow:**
...
```

### 1.2. 目的与作用

这个 Prompt 的主要目的不是提供一个可以直接使用的工具，而是向 LLM **传授一套使用“技能”的思维框架和工作流程**。

-   **能力宣告**: “你拥有了一个技能库”，这是一种比“工具”更高层次、更侧重于“知识和流程”的能力。
-   **“渐进式披露”核心思想**: 这是整个 Prompt 的灵魂。它明确告诉模型：
    1.  你首先会看到一个技能的**摘要列表**（名称+描述）。
    2.  你**不需要**立刻知道每个技能的全部细节。
    3.  当你判断某个任务与某个技能相关时，你的**下一步行动**是使用你已有的 `read_file` 工具去**读取**该技能的 `SKILL.md` 文件。
    4.  `SKILL.md` 文件中包含了完成任务所需的所有详细步骤、指令和最佳实践。
-   **决策指导**: 提供了清晰的“何时使用技能”的决策指南，帮助模型建立正确的判断标准。
-   **自文档化**: 强调了技能是“自文档化”的，进一步强化了“需要时再去读取”的心智模型。
-   **工作流示例**: 提供了一个完整的示例，演示了从“识别需求 -> 匹配技能 -> 读取技能 -> 执行技能”的完整闭环。

### 1.3. 动态占位符

这个 Prompt 是一个模板，包含两个动态填充的占位符：

-   **`{skills_locations}`**:
    -   **填充内容**: 由 `_format_skills_locations` 方法生成。它会显示用户技能库（`~/.deepagents/...`）和项目技能库（`./.deepagents/...`）的路径。
    -   **作用**: 告知模型技能的来源，并明确指出项目技能会覆盖同名的用户技能，这有助于模型在遇到冲突时理解优先级。
-   **`{skills_list}`**:
    -   **填充内容**: 由 `_format_skills_list` 方法生成。该方法会遍历所有从文件系统中加载的技能元数据 (`skills_metadata`)，并生成一个格式化的列表。
    -   **格式**: 每个技能条目都包含：
        -   技能名称（`name`）和描述（`description`）。
        -   一个**明确的、可直接复制使用的指令**：`→ Read \`{skill['path']}\` for full instructions`。这至关重要，因为它直接将“读取技能”这个抽象概念转化为了一个具体的、模型可以立即执行的 `read_file` 工具调用。
    -   **作用**: 这是“渐进式披露”的第一步，即“披露摘要”。

### 1.4. 注入机制

1.  **加载技能**: 在 `before_agent` 钩子中，`SkillsMiddleware` 会调用 `list_skills` 函数，扫描指定的目录，解析所有 `SKILL.md` 文件的元数据（YAML frontmatter），并将结果存入 `state['skills_metadata']`。这个过程在每个交互轮次开始时都会执行，以确保能动态加载新添加或修改的技能。
2.  **动态生成**: 在 `wrap_model_call` 钩子中，中间件从 `state` 中读取 `skills_metadata`。
3.  **格式化与注入**: 调用 `_format_skills_locations` 和 `_format_skills_list` 方法填充 `SKILLS_SYSTEM_PROMPT` 模板，生成最终的技能系统提示。
4.  **追加提示**: 将这个最终生成的、包含所有当前可用技能列表的 Prompt 文本，追加到主智能体的系统提示之后。

这个机制确保了 LLM 在每次决策时，都能看到最新、最完整的可用技能列表，并始终被提醒应遵循“渐进式披露”的原则来使用它们。
