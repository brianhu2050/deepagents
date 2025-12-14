# Filesystem Middleware Prompts 解析

该文档详细分析了 `FilesystemMiddleware` 中定义的两个核心系统提示（System Prompts），它们共同指导 LLM 如何与文件系统及沙箱环境进行交互。

## 1. `FILESYSTEM_SYSTEM_PROMPT`

### 1.1. Prompt原文

```
## Filesystem Tools `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`

You have access to a filesystem which you can interact with using these tools.
All file paths must start with a /.

- ls: list files in a directory (requires absolute path)
- read_file: read a file from the filesystem
- write_file: write to a file in the filesystem
- edit_file: edit a file in the filesystem
- glob: find files matching a pattern (e.g., "**/*.py")
- grep: search for text within files
```

### 1.2. 目的与作用

这个 Prompt 是 `FilesystemMiddleware` 的**基础指令集**。它的核心目的是告知 LLM：

1.  **能力宣告**: “你现在拥有了操作文件系统的能力”。
2.  **工具列表**: 明确列出所有可用的基本文件操作工具名称，便于模型进行工具选择。
3.  **核心规则**: 强调一个至关重要的规则——**“所有文件路径必须以 `/` 开头”**。这强制模型使用绝对路径，避免了因当前工作目录不确定而导致的路径混乱问题，是保证操作稳定性的关键。
4.  **简要说明**: 为每个工具提供一句话的简短描述，帮助模型理解其基本用途。

### 1.3. 注入机制

-   此 Prompt 在 `FilesystemMiddleware` 的 `wrap_model_call` 方法中被处理。
-   它是**无条件注入**的。只要 `FilesystemMiddleware` 被激活，这个 Prompt 就会作为基础能力的一部分，被追加到发送给 LLM 的最终系统提示中。

---

## 2. `EXECUTION_SYSTEM_PROMPT`

### 2.1. Prompt原文

```
## Execute Tool `execute`

You have access to an `execute` tool for running shell commands in a sandboxed environment.
Use this tool to run commands, scripts, tests, builds, and other shell operations.

- execute: run a shell command in the sandbox (returns output and exit code)
```

### 2.2. 目的与作用

这个 Prompt 是**条件性**的、**增强能力**的指令集。它的目的是告知 LLM，除了基本的文件操作外，它还拥有一个更高级、更强大的能力：

1.  **能力宣告**: “你拥有了一个可以在沙箱环境中执行任意 Shell 命令的 `execute` 工具”。
2.  **用途指导**: 明确指出该工具适用于运行脚本、测试、构建等更复杂的命令行任务。
3.  **功能概述**: 简单说明 `execute` 工具的作用和返回值（输出+退出码）。

### 2.3. 注入机制

`EXECUTION_SYSTEM_PROMPT` 的注入机制是**动态和条件性**的，这是其设计的精髓所在：

1.  **前置检查**: 在 `wrap_model_call` 方法中，代码会首先检查当前激活的后端（Backend）是否实现了 `SandboxBackendProtocol` 接口（通过 `_supports_execution` 函数）。
2.  **条件注入**:
    -   **如果**后端**支持**命令执行，`EXECUTION_SYSTEM_PROMPT` 就会被追加到最终的系统提示中。同时，`execute` 工具本身也会被提供给 LLM。
    -   **如果**后端**不支持**命令执行，这个 Prompt **不会**被注入，并且 `execute` 工具也会从工具列表中被**过滤掉**。

这种机制确保了 LLM 的“认知”与环境的“实际能力”严格保持一致，防止模型产生“幻觉”，去尝试调用一个当前环境下根本不存在或无法使用的工具。
