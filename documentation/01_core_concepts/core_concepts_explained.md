# Deep Agents 核心概念解析

本文档旨在清晰、直接地解答关于 `deepagents` 框架中一些最核心概念的疑问，包括中间件的生命周期钩子以及关键中间件的职责划分。

---

## 1. `before_agent` vs `wrap_model_call`

这两个方法都是中间件（Middleware）架构中的核心生命周期钩子，但它们的**触发时机、设计目的和典型用途**完全不同。

### 1.1. `before_agent(self, state, runtime)`

-   **触发时机**:
    在 Agent 的一个**完整运行循环（run）开始时**，但在 LangGraph 图（Graph）开始执行其任何内部逻辑（如调用模型、执行工具）**之前**。对于一个多步骤的任务，它可能只在最开始被调用一次或几次（取决于图的结构），而不是在每次模型调用前都调用。

-   **核心职责**:
    **“准备工作台”——即准备和校验 `AgentState`**。它的主要任务是在 Agent 开始“思考”（调用 LLM）之前，确保状态（State）是最新、最准确和最完整的。

-   **典型用途**:
    1.  **从外部加载数据到状态 (Loading data into state)**:
        -   **示例**: `SkillsMiddleware` 在此阶段扫描文件系统中的 `SKILL.md` 文件，解析它们的元数据，并将这个技能列表**写入** `state['skills_metadata']`。
        -   **示例**: `AgentMemoryMiddleware` 在此阶段读取 `agent.md` 文件，并将用户记忆和项目记忆**写入** `state['memory']`。
    2.  **校验和修复状态 (Validating and patching state)**:
        -   **示例**: `PatchToolCallsMiddleware` 在此阶段**读取** `state['messages']`，检查是否存在悬空的（即没有对应 `ToolMessage` 的）`tool_calls`，并注入“已取消”的 `ToolMessage` 来修复状态的逻辑一致性。

-   **数据流**:
    **单向**。`外部世界 -> AgentState`，或者 `AgentState -> (修复后的) AgentState`。它不直接与 LLM 的 Prompt 交互。

### 1.2. `wrap_model_call(self, request, handler)`

-   **触发时机**:
    在 Agent 运行过程中的**每一次 LLM 模型调用即将发生时**。如果一个任务需要三次 LLM 调用，那么这个钩子就会被触发三次。

-   **核心职责**:
    **“准备给国王的奏折”——即构建和修改发送给 LLM 的 `ModelRequest`**。它的主要任务是拦截即将发给 LLM 的请求，并根据当前的 `AgentState` 动态地修改它，尤其是修改**系统提示（System Prompt）**和**工具列表（Tools）**。

-   **典型用途**:
    1.  **动态注入系统提示 (Dynamically injecting system prompts)**:
        -   **示例**: `SkillsMiddleware` **读取** `state['skills_metadata']`，将其格式化成一个用户可读的技能列表，然后将这个列表**追加**到 `request.system_prompt` 中，从而告诉 LLM 它当前有哪些技能可用。
        -   **示例**: `SubAgentMiddleware` 将关于如何以及何时使用 `task` 工具的详细指南和示例，**追加**到 `request.system_prompt` 中。
    2.  **动态过滤工具 (Dynamically filtering tools)**:
        -   **示例**: `FilesystemMiddleware` 检查其后端（Backend）是否支持沙箱协议。如果不支持，它会从 `request.tools` 列表中**移除** `execute` 工具，确保 LLM 不会产生调用一个不可用工具的“幻觉”。

-   **数据流**:
    **双向包装器**。它接收原始的 `ModelRequest`，返回一个修改后的 `ModelRequest` 给 `handler`（调用链的下一环）。它直接塑造了 LLM 的“世界观”和“可用能力”。

### **总结对比**

| 特性 | `before_agent` | `wrap_model_call` |
| :--- | :--- | :--- |
| **时机** | Agent 运行循环开始时 | 每次 LLM 调用前 |
| **目的** | 准备/校验**状态 (State)** | 准备/修改给**模型 (Model)** 的请求 |
| **主要操作对象** | `AgentState` | `ModelRequest` (尤其是 `system_prompt`) |
| **核心动词** | 加载 (Load), 填充 (Populate), 修复 (Patch) | 注入 (Inject), 追加 (Append), 过滤 (Filter) |
| **示例** | 加载技能列表到 state | 将 state 中的技能列表注入 prompt |

---

## 2. 三大核心中间件的职责

`SubAgentMiddleware`, `SkillsMiddleware`, 和 `FilesystemMiddleware` 是 `deepagents` 的三大支柱性中间件，它们各自负责一个正交（Orthogonal）的能力维度。

### 2.1. `FilesystemMiddleware`

-   **核心职责**: **提供与“世界”交互的基础 I/O 和执行能力**。
-   **一句话总结**: 它是 Agent 的**“手和脚”**。
-   **具体功能**:
    1.  **提供基础工具**: 向 Agent 暴露一套标准的文件操作工具 (`ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`) 和一个（可选的）命令执行工具 (`execute`)。
    2.  **抽象后端**: 将这些工具的**具体实现**与工具本身解耦。工具的调用最终会被委派给一个可配置的后端（Backend），这个后端可能是本地文件系统、内存，或者一个远程的沙箱（Sandbox）。
    3.  **动态能力宣告**: 通过 `wrap_model_call`，它会检查后端的能力，并动态地告诉 LLM 它当前是否拥有 `execute` 的能力。
    4.  **大结果处理**: 通过 `wrap_tool_call`，自动拦截过大的工具输出，将其存入文件并返回引导消息，防止上下文窗口溢出。

### 2.2. `SkillsMiddleware`

-   **核心职责**: **为 Agent 提供可复用的、结构化的“知识”和“工作流程”**。
-   **一句话总结**: 它是 Agent 的**“知识库”或“操作手册”**。
-   **具体功能**:
    1.  **技能发现**: 通过 `before_agent`，从文件系统（`SKILL.md` 文件）中动态发现和加载所有可用的技能元数据。
    2.  **能力宣告 (摘要)**: 通过 `wrap_model_call`，将所有已发现技能的**名称和描述**注入到系统提示中。
    3.  **实现渐进式披露 (Progressive Disclosure)**: 它**不**直接提供工具。相反，它教会 LLM 一个**模式**：当任务与某个技能相关时，使用 `FilesystemMiddleware` 提供的 `read_file` 工具去**读取**该技能的详细说明文档，然后再按照文档中的步骤去操作。
    4.  **知识/流程封装**: “技能”本身（`SKILL.md` 的内容）封装了完成特定任务（如“进行网页研究”）的最佳实践、思考链或固定的操作流程。

### 2.3. `SubAgentMiddleware`

-   **核心职责**: **提供任务分解、委派和并发执行的能力**。
-   **一句话总结**: 它是 Agent 的**“项目管理和委派能力”**。
-   **具体功能**:
    1.  **提供 `task` 工具**: 只向 Agent 暴露一个名为 `task` 的特殊工具。
    2.  **子代理管理**: 在内部管理一个或多个“子 Agent”。这些子 Agent 可以拥有与主 Agent 不同的 Prompt、工具集和中间件。
    3.  **任务隔离**: 当 `task` 工具被调用时，它会在一个**隔离的上下文**中启动一个子 Agent 来执行指定的任务描述，主 Agent 的消息历史不会被泄露过去。
    4.  **并发与效率**: 通过 `wrap_model_call` 中的详细 Prompt，它强烈地**鼓励**主 Agent（作为“协调者”）在面对可以并行处理的多个独立任务时，一次性发起多个并行的 `task` 工具调用，以最大限度地提高执行效率。

### **协同关系**

这三者协同工作，形成了一个强大的能力矩阵：
-   主 Agent 通过 `SubAgentMiddleware` 学会了将一个复杂任务（如“为我的项目A写单元测试”）分解并委派出去。
-   它调用 `task(description="为项目A写单元测试", ...)`。
-   子 Agent 在隔离的环境中启动。它通过 `SkillsMiddleware` 看到有一个名为 "python-unit-testing" 的技能。
-   子 Agent 遵循“渐进式披露”原则，使用 `FilesystemMiddleware` 提供的 `read_file` 工具读取了 `python-unit-testing/SKILL.md` 的内容。
-   `SKILL.md` 指导它：“首先，使用 `glob` 找到所有 `_test.py` 文件...然后，使用 `execute` 运行 `pytest`...”。
-   子 Agent 于是使用 `FilesystemMiddleware` 提供的 `glob` 和 `execute` 工具来完成任务。
-   最终，子 Agent 将测试结果返回给主 Agent，任务完成。
