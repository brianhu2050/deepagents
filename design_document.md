### **第一部分：`CompositeBackend` 的使用与数据分离存储**

`CompositeBackend` 是 `deepagents` 框架中一个强大的功能，它扮演着一个“路由”或“分发器”的角色，允许您将不同的文件路径前缀（prefix）映射到不同的后端存储实现上。这使得您可以灵活地将数据隔离存储，例如，一部分数据存储在安全、隔离的沙盒环境中，而另一部分则持久化到物理文件系统。

**工作原理:**

`CompositeBackend` 接受一个 `default` 后端和一系列 `routes`。当对一个文件路径执行操作（如读、写、列出文件）时：

1.  `CompositeBackend` 会检查该路径是否匹配 `routes` 中定义的某个前缀。
2.  它会优先匹配**最长的前缀**。
3.  如果找到匹配的路由，它会将请求转发给该路由对应的后端处理。在转发时，路径的前缀会被剥离。
4.  如果没有找到匹配的路由，请求将被发送到 `default` 后端进行处理。
5.  对于代码执行 (`execute`) 等非路径特定的操作，请求总是由 `default` 后端处理，该后端必须是一个支持代码执行的沙盒环境。

**如何实现沙盒与文件系统的分离存储：**

假设我们希望将所有临时文件、代码和执行结果存储在沙盒中（路径如 `/workspace/`, `/tmp/`），同时将需要持久化的关键数据（如从 API 拉取的数据）存储在主机的文件系统上（挂载到虚拟路径 `/data/`）。

可以按如下方式进行配置：

```python
from deepagents.backends.composite import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.sandbox import SandboxBackend # 这是一个支持代码执行的沙盒后端

# 1. 为持久化数据创建 FilesystemBackend
#    - root_dir: 指向主机上的一个真实目录，例如 /var/myapp/data
#    - virtual_mode=True: 确保所有路径操作都被安全地限制在该目录内
persistent_storage = FilesystemBackend(root_dir="/var/myapp/data", virtual_mode=True)

# 2. 为代码执行和临时文件创建 SandboxBackend
#    这个后端提供了一个隔离的运行时环境
sandbox_environment = SandboxBackend()

# 3. 创建 CompositeBackend 并定义路由规则
#    - default: 所有未匹配到路由的请求都将进入沙盒环境
#    - routes: 定义一个路由规则，将所有以 "/data/" 开头的虚拟路径请求，转发给 persistent_storage
composite_backend = CompositeBackend(
    default=sandbox_environment,
    routes={
        "/data/": persistent_storage,
    }
)

# 使用示例
# 这个操作将在 SandboxBackend 中执行
composite_backend.write("/workspace/script.py", "print('hello world')")
composite_backend.execute("python /workspace/script.py")

# 这个操作将被路由到 FilesystemBackend，并将文件真实地写入到 /var/myapp/data/metrics.csv
composite_backend.write("/data/metrics.csv", "timestamp,value\n1672531200,100")
```

通过这种方式，Agent 可以无缝地与两种存储后端交互，将业务逻辑（数据处理）与数据存储（持久化）清晰地分离开来。

---

### **第二、三、四部分：线上故障诊断 Data+AI 项目完整方案**

这是一个基于 `deepagents` 实现的、企业级的线上故障自动诊断系统的完整设计方案。

#### **核心理念**

我们将构建一个由“**Orchestrator Agent (调度器Agent)**”领导的、多个“**Sub-Agent (子Agent)**”协作的 Multi-Agent 系统。每个 Sub-Agent 都是特定领域的专家，拥有自己独特的 **Skills (技能)**，它们协同工作，完成从数据拉取到最终诊断报告生成的完整流程。

#### **系统架构图**

请参考同目录下 `architecture.svg` 文件。

#### **Agent 与 Skill 设计**

**1. Orchestrator Agent (调度器Agent)**

*   **职责**: 作为系统的总指挥，负责理解初始的故障告警信息，制定诊断计划，依次调用合适的 Sub-Agent，并最终整合所有信息，生成一份简洁明了的故障诊断报告。
*   **Skills**:
    *   `plan_investigation(alert: dict) -> list[dict]`: 根据告警信息（如服务名、错误信息、时间戳），生成一个包含多个步骤的调查计划。例如：`[{'agent': 'DataRetriever', 'task': 'Fetch CPU metrics for service X'}, {'agent': 'DataAnalyzer', 'task': 'Analyze CPU metrics for anomalies'}]`。
    *   `delegate_task(agent_name: str, task_description: str) -> dict`: 调用指定的 Sub-Agent 来执行一项具体任务，并获取执行结果。
    *   `synthesize_report(findings: list[dict]) -> str`: 汇总所有 Sub-Agent 的发现，生成一份人类可读的 Markdown 格式的诊断报告，指出可能的原因和建议。

**2. Data Retriever Sub-Agent (数据拉取子Agent)**

*   **职责**: 作为数据专家，负责从各种监控和日志系统中拉取原始数据。所有拉取到的数据都将被存储到持久化的文件系统 (`/data/`) 中，以便后续的 Agent 使用。
*   **Skills**:
    *   `fetch_metrics(query: str, start_time: str, end_time: str, output_path: str) -> str`:
        *   功能: 连接到监控系统（如 Prometheus, InfluxDB）的 API，执行查询语句（如 PromQL）。
        *   实现: 内部使用 `requests` 或其他 HTTP 客户端库。
        *   输出: 将查询结果格式化为 CSV，并使用 `write(output_path, ...)` 存储到 `/data/` 目录下。返回成功信息或错误。
    *   `fetch_logs(service_name: str, query_filter: str, start_time: str, end_time: str, output_path: str) -> str`:
        *   功能: 连接到日志聚合系统（如 ELK, Loki）的 API，根据服务名和关键词进行查询。
        *   输出: 将日志数据保存为纯文本或 JSON Lines 格式，存储到 `/data/` 目录下。

**3. Data Analyzer Sub-Agent (数据分析子Agent)**

*   **职责**: 作为数据分析专家，负责对拉取到的原始数据进行深度分析，以发现异常模式和关键指标。它在沙盒环境中执行分析脚本，确保安全和环境隔离。
*   **Skills**:
    *   `perform_statistical_analysis(input_path: str, output_path: str) -> str`:
        *   功能: 读取 `/data/` 中的指标数据（CSV），计算关键的描述性统计数据（如均值、P95/P99分位数、标准差），并将结果保存为 JSON 文件到 `/data/`。
        *   实现: 在沙盒中动态生成并执行一个 Python 脚本，该脚本使用 `pandas` 和 `numpy` 库进行计算。例如：`execute("python /workspace/stats.py --input /data/metrics.csv --output /data/stats.json")`。
    *   `detect_timeseries_anomalies(input_path: str, output_path: str) -> str`:
        *   功能: 使用时序异常检测算法（如基于移动平均线、孤立森林等）来识别指标数据中的突变点或异常波动。
        *   实现: 执行一个使用 `scipy`, `scikit-learn` 等库的 Python 分析脚本。将发现的异常点（时间戳和数值）保存为 JSON 文件。
    *   `extract_log_patterns(input_path: str, keywords: list[str], output_path: str) -> str`:
        *   功能: 扫描 `/data/` 中的日志文件，统计 `FATAL`, `ERROR`, `Exception` 等关键词的出现频率，或使用正则表达式匹配特定的错误模式。
        *   实现: 执行一个 Python 脚本，对日志文件进行逐行分析和统计。

**4. Data Visualizer Sub-Agent (数据可视化子Agent)**

*   **职责**: 作为可视化专家，将复杂的分析结果转化为直观的图表，帮助人类更快地理解问题。
*   **Skills**:
    *   `plot_timeseries_chart(input_path: str, title: str, output_path: str) -> str`:
        *   功能: 读取指标数据和分析出的异常点，生成带有异常标记的时间序列折线图。
        *   实现: 在沙盒中执行一个使用 `matplotlib` 或 `plotly` 的 Python 脚本，将生成的图表保存为图片（如 PNG）到 `/data/` 目录。
    *   `plot_barchart_from_json(input_path: str, title: str, output_path: str) -> str`:
        *   功能: 读取统计分析的结果（如日志关键词频率），并生成一个柱状图进行对比。
        *   实现: 类似于上一个技能，执行一个 Python 脚本来生成图表。

#### **如何确保方案可落地 (Production-Ready)**

1.  **配置化与模板化**: 将 API 地址、认证信息、监控查询语句（PromQL/SQL）等配置外置，存储在如 `/config/settings.yml` 文件中。查询语句可以使用模板，由 Agent 在运行时填充参数（如服务名、时间）。
2.  **错误处理与重试**: 每个 Skill 的实现都必须包含健壮的错误处理逻辑。例如，API 请求失败时应有重试机制；文件不存在或格式错误时应能向 Orchestrator Agent 报告清晰的错误。
3.  **安全与隔离**: 严格使用 `CompositeBackend` 将数据处理限制在沙盒内。对于生产环境，`SandboxBackend` 最好基于 Docker 或 `firejail` 等容器技术实现，以提供文件系统、网络和进程级别的强隔离。
4.  **可观测性 (Observability)**: 为每个 Agent 和 Skill 的执行过程添加详细的日志。记录每个决策的原因、执行的命令、输入和输出，便于事后审计和调试。
5.  **知识库与反馈循环 (Advanced)**:
    *   **知识库**: 建立一个向量数据库，存储历史故障的诊断报告。当新故障出现时，Orchestrator Agent 可以先查询知识库，寻找相似的历史案例，从而加快诊断速度。
    *   **反馈循环**: 在诊断报告结束后，提供一个接口让运维人员可以对报告的准确性进行评分（“有用”或“无用”）。这个反馈可以用来微调（Fine-tune）Orchestrator Agent 的大语言模型，使其未来的决策更精准。

这套方案不仅充分利用了 `deepagents` 的灵活性和可扩展性，而且在设计上考虑了生产环境的实际需求，具备很强的可落地性。