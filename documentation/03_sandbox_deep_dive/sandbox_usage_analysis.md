# 深度解析: Sandbox 的使用与集成流程

前序文档详细分析了 `BaseSandbox` 及其子类的**内部实现**。本文档将聚焦于一个更实际的问题：**一个具体的 Sandbox 子类（如 `DaytonaBackend`）是如何在 `deepagents-cli` 应用中被选择、实例化，并最终集成到 Agent 的工作流程中的？**

我们将通过追踪从命令行参数到中间件注入的完整路径来回答这个问题。

## 1. 命令行参数：用户意图的起点

-   **文件**: `main.py`
-   **函数**: `parse_args()`

一切始于用户在终端输入的命令。`main.py` 中的 `parse_args` 函数定义了与沙箱相关的命令行参数：

-   `--sandbox <choice>`: 这是最关键的参数，它允许用户从一个预定义的列表中选择要使用的沙箱环境。`choices=["none", "modal", "daytona", "runloop"]`。默认值为 `"none"`，即本地模式。
-   `--sandbox-id <id>`: 允许用户连接到一个**已存在**的、指定 ID 的沙箱实例，而不是每次都创建一个新的。
-   `--sandbox-setup <path>`: 指定一个初始化脚本的路径，该脚本会在新的沙箱环境创建后立即在其中执行，用于安装依赖、克隆仓库等准备工作。

当用户执行 `deepagents --sandbox=daytona` 时，`parse_args` 会返回一个包含 `sandbox='daytona'` 的 `args` 对象。

## 2. 主函数 `main()`: 沙箱生命周期的管理者

-   **文件**: `main.py`
-   **函数**: `main()`

`main` 函数接收到 `args` 对象后，会进入沙箱处理逻辑：

```python
# main.py -> main()
if sandbox_type != "none":
    try:
        with create_sandbox(sandbox_type, ...) as sandbox_backend:
            # ... 运行 Agent 会话 ...
    except Exception as e:
        # ... 错误处理 ...
else:
    # ... 运行本地模式的 Agent 会话 ...
```

这里的关键是 **`create_sandbox()`** 工厂函数和 `with` 语句。

## 3. 工厂模式: `create_sandbox()` 的职责

-   **文件**: `integrations/sandbox_factory.py`
-   **函数**: `create_sandbox()`

`create_sandbox` 是一个**工厂函数**，同时也是一个**上下文管理器**。它根据传入的 `sandbox_type` 字符串，负责实例化对应的 Backend 类并管理其生命周期。

-   **职责**:
    1.  **动态导入**: 它会懒加载（lazy-import）所需的依赖（如 `daytona` 客户端），避免即使用户不使用某个沙箱，也需要安装其所有依赖。
    2.  **实例化 Client**: 调用特定平台的客户端库来创建一个沙箱会话（例如，`daytona_client.create_sandbox(...)`）。
    3.  **实例化 Backend**: 将上一步创建的平台客户端实例，注入到对应 Backend 类的构造函数中（例如，`DaytonaBackend(sandbox=daytona_sandbox_client)`）。
    4.  **执行初始化脚本**: 如果用户提供了 `--sandbox-setup`，它会在新创建的沙箱中执行该脚本。
    5.  **生命周期管理**:
        -   `__enter__` (with 语句进入时): 返回创建好的 Backend 实例 (`DaytonaBackend(...)`)。
        -   `__exit__` (with 语句退出时): 负责执行清理工作，例如销毁远程的沙箱实例，除非用户提供了 `--sandbox-id` 来复用。

## 4. 注入 `_run_agent_session()`

-   **文件**: `main.py`
-   **函数**: `main()` -> `_run_agent_session()`

`create_sandbox` 上下文管理器返回的 `sandbox_backend` 实例，被直接传递给了 `_run_agent_session` 函数。

```python
# main.py -> main()
with create_sandbox(...) as sandbox_backend:
    await _run_agent_session(
        ...,
        sandbox_backend=sandbox_backend,  # 注入实例
        sandbox_type=sandbox_type,
    )
```

## 5. Agent 的最终组装: `create_cli_agent()`

-   **文件**: `agent.py`
-   **函数**: `_run_agent_session()` -> `create_cli_agent()`

`create_cli_agent` 是完成沙箱集成的最后一步，也是最关键的一步。

```python
# agent.py -> create_cli_agent()

# ...
if sandbox is None:
    # ========== LOCAL MODE ==========
    composite_backend = CompositeBackend(
        default=FilesystemBackend(),
        ...
    )
    # ... 添加 ShellMiddleware ...
else:
    # ========== REMOTE SANDBOX MODE ==========
    composite_backend = CompositeBackend(
        default=sandbox,  # 将传入的沙箱实例设为默认后端
        ...
    )
    # 注意: 在沙箱模式下，不添加 ShellMiddleware

# ...
agent = create_deep_agent(
    ...
    backend=composite_backend,  # 将配置好的后端注入 Agent
    middleware=agent_middleware,
    ...
)
```

-   **核心逻辑**:
    1.  函数接收 `sandbox_backend` 参数（此时是 `DaytonaBackend` 的一个实例），并将其命名为 `sandbox`。
    2.  进入 `REMOTE SANDBOX MODE` 分支。
    3.  一个 `CompositeBackend` 被创建，并将 `sandbox` 实例（即 `DaytonaBackend` 实例）设置为其**默认后端**。这意味着，所有未被特别路由的文件或执行请求，都将默认由 `DaytonaBackend` 处理。
    4.  **重要的是**，在此模式下，`ShellMiddleware` **不会**被添加到中间件栈中。因为本地 shell 执行能力在这种模式下是不需要（也不安全）的，所有的命令执行都应该通过 `execute` 工具交由沙箱处理。
    5.  最后，这个配置了 `DaytonaBackend` 的 `composite_backend` 实例，在调用 `create_deep_agent()` 时，被传递给了 `FilesystemMiddleware`（`create_deep_agent` 内部会处理这个传递）。

## 6. 运行时动态激活

如《Sandbox 整体实现机制》文档所述，一旦 `FilesystemMiddleware` 内部持有了 `DaytonaBackend` 实例，它的 `wrap_model_call` 方法就会在运行时检测到 `self.backend` 是 `SandboxBackendProtocol` 的一个实例，从而动态地向 LLM 宣告 `execute` 工具的存在和用法。

至此，从一个简单的命令行参数 `--sandbox=daytona` 开始，`DaytonaBackend` 已经通过工厂模式、依赖注入，被成功地集成为了 Agent 执行其操作的默认后端，并动态激活了 Agent 的远程命令执行能力。
