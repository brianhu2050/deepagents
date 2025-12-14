# 深度解析: 上下文的分层披露机制 (Context Layered Disclosure)

`deepagents` 框架的一个核心设计哲学是**上下文的分层披露**（也称“渐进式披露”）。这是一种先进的 Prompt Engineering 和 Agent 设计模式，旨在通过在恰当的时机、以恰当的方式向 LLM 提供恰当数量的信息，来最大化其效率、准确性和处理复杂任务的能力，同时最小化 Token 消耗和“上下文噪音”。

本文档将深入剖析这一机制的实现原理，并关联具体的代码流程，阐明其与工具（Tool）和后端（Backend）的关系。

---

## 1. 问题的根源: 有限的上下文窗口

LLM 的“注意力”（上下文窗口）是有限且宝贵的资源。如果在一开始就将所有可能用到的信息（所有工具的详细用法、所有文件的内容、所有技能的完整步骤）全部塞给 LLM，会导致几个严重问题：
-   **Token 浪费**: 大部分信息在当前步骤中都是无用的，白白消耗了成本。
-   **性能下降**: 上下文越长，模型的推理速度越慢。
-   **注意力分散 (Lost in the Middle)**: 在极长的上下文中，模型可能会忽略或忘记中间部分的关键信息。
-   **灵活性差**: 无法动态适应变化的环境（例如，在会话中途添加了一个新技能）。

分层披露机制就是为了解决这些问题而设计的。

## 2. 实现原理：一个三层信息披露模型

`deepagents` 主要通过 `SkillsMiddleware` 和 `FilesystemMiddleware` 的协同工作来实现这一机制。整个流程可以被看作一个三层的信息金字塔。

### **第一层: “存在性”披露 (Existence Disclosure)**

-   **目标**: 告诉 LLM **“有什么”**，但不告诉它具体**“怎么做”**。
-   **实现**:
    1.  **技能发现**: 在每个任务循环开始时，`SkillsMiddleware` 的 **`before_agent()`** 方法被调用。它会触发 **`skills.load.list_skills()`** 函数。
    2.  **加载元数据**: `list_skills()` 扫描文件系统中的 `SKILL.md` 文件，但它**不读取文件的全部内容**。它只解析每个文件头部的 YAML Frontmatter，提取出技能的 `name` 和 `description`。
    3.  **状态填充**: 这个技能元数据列表被写入 `AgentState['skills_metadata']`。
    4.  **Prompt 注入**: 在模型调用前，`SkillsMiddleware` 的 **`wrap_model_call()`** 方法被触发。它读取 `state['skills_metadata']`，将其格式化成一个摘要列表，并注入到系统提示中。
-   **LLM 看到的例子**:
    ```
    **Available Skills:**
    - **web-research**: A skill for conducting web research.
      → Read `~/.deepagents/skills/web-research/SKILL.md` for instructions.
    - **code-review**: A skill for reviewing code.
      → Read `~/.deepagents/skills/code-review/SKILL.md` for instructions.
    ```
-   **代码关联**:
    -   `SkillsMiddleware.before_agent()`: 负责发现。
    -   `skills.load.list_skills()`: 负责加载摘要。
    -   `SkillsMiddleware.wrap_model_call()`: 负责注入摘要。

### **第二层: “细节”披露 (Details Disclosure)**

-   **目标**: 当 LLM 认为某个摘要信息与当前任务相关时，它**主动发起请求**来获取完整的细节。
-   **实现**:
    1.  **LLM 决策**: LLM 分析任务（例如，用户说“帮我研究一下... B”），并将其与第一层披露的技能描述进行匹配。它判断 `web-research` 技能是相关的。
    2.  **主动请求**: LLM 遵循第一层信息中给出的明确指令 (`→ Read ...`)，生成一个**工具调用（Tool Call）**。
    3.  **工具执行**: 这个工具调用 `read_file(path="~/.deepagents/skills/web-research/SKILL.md")` 被 `FilesystemMiddleware` 捕获并执行。
-   **LLM 看到的例子**:
    LLM 的内心活动：“任务是研究，我有一个叫 `web-research` 的技能，它的描述和任务匹配。现在，我需要调用 `read_file` 工具来读取它的详细说明。”
    *LLM 生成 Tool Call: `read_file(...)`*
-   **代码关联**:
    -   `FilesystemMiddleware`: 提供 `read_file` 工具。
    -   `read_file` 工具内部调用 `self.backend.read()` 来执行读取。

### **第三层: “执行”披露 (Execution Disclosure)**

-   **目标**: LLM 获取到完整的细节（`SKILL.md` 的全部内容），并根据其中的指令执行具体的操作。
-   **实现**:
    1.  **接收细节**: `read_file` 的结果（`SKILL.md` 的内容）作为一个 `ToolMessage` 返回给 LLM。
    2.  **遵循指令**: `SKILL.md` 的内容本身就是一个详细的 Prompt 或操作手册，它会指导 LLM 下一步应该做什么。例如，它可能会说：“第一步，使用 `web_search` 工具搜索关键词... 第二步，使用 `write_file` 工具将结果保存到 `research_summary.md`...”。
    3.  **执行具体工具**: LLM 根据这些新获得的指令，生成新的工具调用（如 `web_search`, `write_file`）。
-   **LLM 看到的例子**:
    *LLM 接收到 `ToolMessage`，内容是 `web-research/SKILL.md` 的全部 Markdown 文本。*
    LLM 的内心活动：“好的，我已经知道如何进行网页研究了。现在我将按照手册的第一步，调用 `web_search` 工具。”
    *LLM 生成 Tool Call: `web_search(...)`*
-   **代码关联**:
    -   `web_search` (来自 `main.py` 的工具)
    -   `write_file` (来自 `FilesystemMiddleware`)

通过这三层递进，Agent 只在绝对必要时才加载和处理详细信息，极大地优化了上下文的使用。

---

## 2. 澄清 Tool 与 Backend 的关系: 桥梁与实现

在 `deepagents` 框架中，**Tool 是“桥梁”，Backend 是“具体实现”**。这种分离是实现沙箱（Sandbox）和多环境支持的关键。

-   **Tool (The Bridge - “桥梁”)**:
    -   **角色**: 作为暴露给 LLM 的**接口**。它定义了一个操作的名称、参数和描述。
    -   **代码**: `read_file` 工具的定义在 `FilesystemMiddleware` 中 (`_read_file_tool_generator`)。
    -   **职责**:
        1.  **面向 LLM**: 向 LLM “宣告”一个能力的存在。
        2.  **安全校验**: 在执行前对输入进行验证（例如，`_validate_path` 防止路径遍历）。
        3.  **委派 (Delegate)**: **它自身不包含任何执行逻辑**。它的唯一工作就是将经过验证的请求，调用 `self.backend` 实例上的相应方法。
    -   **伪代码**:
        ```python
        class FilesystemMiddleware:
            def __init__(self, backend: BackendProtocol):
                self.backend = backend  # 接收一个具体的后端实例

            def read_file_tool(self, path: str):
                validated_path = _validate_path(path)
                # 将执行工作完全委派给后端
                return self.backend.read(validated_path)
        ```

-   **Backend (The Implementation - “具体实现”)**:
    -   **角色**: 作为操作的**实际执行者**。它实现了 `BackendProtocol` 或 `SandboxBackendProtocol` 定义的接口。
    -   **代码**: `StateBackend`, `FilesystemBackend`, `DaytonaBackend` 等。
    -   **职责**: 包含完成操作的具体逻辑。
    -   **示例**:
        -   **`FilesystemBackend.read(path)`**: 内部会调用 `Path(path).read_text()` 来从**本地磁盘**读取文件。
        -   **`DaytonaBackend.read(path)`**: 内部会调用 `self.execute(f"cat {path}")`，将一个 `cat` 命令发送到**远程的 Daytona 沙箱**中执行。
        -   **`StateBackend.read(path)`**: 内部会从 `AgentState['files']` 这个**内存中的字典**里查找并返回内容。

### **总结关系**

当 LLM 调用 `read_file` 时：
1.  `FilesystemMiddleware` 捕获该调用。
2.  `read_file` 工具函数被执行。
3.  它调用被注入的 `self.backend` 实例的 `.read()` 方法。
4.  **具体执行哪一个 `.read()` 的逻辑（本地、远程还是内存），完全取决于在创建 Agent 时给 `FilesystemMiddleware` 注入的是哪一个 Backend 实例**。

这种设计使得 `FilesystemMiddleware` 及其工具集保持了高度的通用性，而将所有与环境相关的具体实现细节都隔离在了 Backend 层，实现了彻底的解耦。
