# 架构深度解析: 中间件 (Middleware)

`deepagents` 框架的**中间件（Middleware）**是其模块化、可组合架构的核心。中间件允许开发者通过注入自定义逻辑来扩展和修改智能体（Agent）的核心行为，而无需修改智能体本身。它们就像是围绕着智能体核心的一系列“插件”或“装饰器”，每个都负责一个特定的功能。

## 1. 核心理念：面向切面编程 (AOP)

中间件架构是面向切面编程思想的体现。它将那些横跨多个功能点的“横切关注点”（Cross-Cutting Concerns）从主业务逻辑中分离出来，封装到独立的模块中。

在 `deepagents` 中，这些关注点包括：
-   **状态管理**: 如何加载、保存和管理记忆？(`AgentMemoryMiddleware`)
-   **能力扩展**: 如何动态地为 Agent 添加新知识或技能？(`SkillsMiddleware`)
-   **上下文注入**: 如何在模型调用前动态修改系统提示？(几乎所有中间件)
-   **鲁棒性与修复**: 如何保证数据流的完整性和一致性？(`PatchToolCallsMiddleware`)
-   **人机交互**: 如何在特定点暂停以寻求人类批准？(`HumanInTheLoopMiddleware`)

## 2. 中间件生命周期钩子 (Lifecycle Hooks)

中间件通过实现 `AgentMiddleware` 基类中定义的一系列“钩子”（Hook）方法来将其逻辑注入到 Agent 的生命周期中。Agent 的执行流程在关键节点会检查并调用当前所有已注册中间件的相应钩子方法。

![Middleware Architecture](module-architecture-middleware.svg)
*(上图的 SVG 文件将更新以反映更详细的流程)*

主要的生命周期钩子包括：

-   **`before_agent(state, runtime)`**:
    -   **触发时机**: 在 Agent 的主运行循环开始，但在执行任何核心逻辑（如图的构建、模型调用）**之前**。
    -   **主要用途**:
        -   **状态初始化/填充**: 从外部源（如文件系统）加载数据并填充到 `AgentState` 中。例如，`SkillsMiddleware` 在此阶段加载技能元数据。
        -   **状态校验/修复**: 检查和清理当前状态，确保其一致性。`PatchToolCallsMiddleware` 在此阶段修复悬空的工具调用。
    -   **返回值**: 可以返回一个字典来更新或覆写 `AgentState`。

-   **`wrap_model_call(request, handler)`**:
    -   **触发时机**: 在 Agent 即将调用 LLM **之前**。
    -   **主要用途**:
        -   **动态 Prompt 构建**: 这是最常用的功能。中间件可以检查当前状态，然后动态地修改、追加或完全替换将要发送给 LLM 的系统提示（`system_prompt`）。`FilesystemMiddleware`, `SubAgentMiddleware`, `SkillsMiddleware` 都利用此钩子来告知 LLM 它们所提供的能力和用法。
        -   **动态工具过滤**: 可以根据当前状态或后端能力，动态地从工具列表（`tools`）中添加或删除工具。例如，`FilesystemMiddleware` 会检查后端是否支持 `execute`，如果不支持，则会在此阶段过滤掉 `execute` 工具。
    -   **工作方式**: 它是一个“包装器”。`request` 参数是即将发送给模型的请求，`handler` 是一个函数，代表了调用链中的下一个环节（最终是实际的 LLM 调用）。你可以在调用 `handler(modified_request)` 前后执行你的逻辑。

-   **`wrap_tool_call(request, handler)`**:
    -   **触发时机**: 在 Agent 即将执行一个工具调用（Tool Call）**之前**。
    -   **主要用途**:
        -   **输入修改**: 修改传递给工具的参数。
        -   **输出拦截与处理**: 在工具执行**之后**，拦截其返回结果（`ToolMessage`），并进行处理。`FilesystemMiddleware` 利用这个钩子来检查工具输出是否过大，如果过大，则将其存入文件并返回引导消息。
    -   **工作方式**: 与 `wrap_model_call` 类似，是一个包装器。

## 3. 现有核心中间件协同工作流程

当一个 `deepagents` 智能体被创建并运行时，其注册的中间件会形成一个调用链，协同工作。

1.  **循环开始**: `agent.stream()` 被调用。
2.  **`before_agent` 阶段**:
    -   `PatchToolCallsMiddleware` 首先运行，清理 `messages` 列表。
    -   `SkillsMiddleware` 接着运行，扫描文件系统，将最新的技能元数据写入 `state['skills_metadata']`。
    -   `AgentMemoryMiddleware` (假设存在) 可能会运行，从 `agent.md` 文件中加载记忆内容到 `state['memory']`。
3.  **准备模型调用**: Agent 的核心逻辑（LangGraph）构建好 `ModelRequest`，准备调用 LLM。
4.  **`wrap_model_call` 阶段 (调用链)**:
    -   请求首先进入 `SkillsMiddleware`，它从 `state` 中读取技能列表，格式化后追加到 `system_prompt`。
    -   然后请求流经 `SubAgentMiddleware`，它将关于如何使用 `task` 工具的详细指南追加到已被修改的 `system_prompt` 后。
    -   接着请求流经 `FilesystemMiddleware`，它检查后端能力，追加文件系统和（可能的）命令执行的指南到 `system_prompt`，并可能过滤掉 `execute` 工具。
    -   ... 其他中间件 ...
    -   最终，这个被层层“装饰”和丰富的 `ModelRequest` 被 `handler` 发送给 LLM。
5.  **LLM 响应与工具调用**:
    -   LLM 返回一个包含 `tool_calls` 的 `AIMessage`。
6.  **`wrap_tool_call` 阶段**:
    -   当 Agent 准备执行工具时，请求进入 `wrap_tool_call` 链。
    -   (假设) `HumanInTheLoopMiddleware` 可能会拦截一个名为 `execute` 的工具调用，暂停执行并等待用户批准。
    -   工具执行完毕后，`FilesystemMiddleware` 可能会拦截其巨大的输出结果，并将其替换为一个引导消息。
7.  **状态更新**:
    -   `AIMessage` 和最终的 `ToolMessage` 被合并回 `AgentState`。
8.  **循环结束**，等待下一次触发。

通过这种方式，`deepagents` 框架将复杂的功能逻辑分解到各个独立的中间件中，并通过一个定义良好的生命周期将它们串联起来，实现了高度的模块化和可维护性。
