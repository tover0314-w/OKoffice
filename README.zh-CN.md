# AgentPDF Infra 中文说明

AgentPDF Infra 是一个面向 AI Agent 的开源 PDF 基础设施项目。目标不是做一个小型 PDF MCP 工具，而是打造：

> iLovePDF / PDF24 的全量 PDF 工具能力 + LlamaParse / LiteParse / Docling 的文档理解能力 + Firecrawl 式开源导流和云端商业化。

本 ZIP 是给 Codex 使用的开发 harness，包含完整项目文档、工具全集、MCP/API schema、开源治理、测试验收、路线图和任务卡。

首版先开发开源项目部分：

- 本地 MCP Server
- CLI
- 本地 REST API
- Python SDK 基础
- PDF 工具全集 manifest
- 基础确定性 PDF 操作
- Lite parse / 本地 RAG demo
- Document IR
- 输出验证与 artifact manifest
- Docker 自托管
- 精美 README、文档、示例和开源规范

云端部分未来可以收费：高级 OCR、agentic parse、AI 创建/修改/翻译、托管 RAG index、批处理、高并发、长期存储、审计日志、团队管理、SSO、zero retention、VPC/on-prem 等。

建议 Codex 从 `AGENTS.md` 和 `docs/00_START_HERE_FOR_CODEX.md` 开始。
