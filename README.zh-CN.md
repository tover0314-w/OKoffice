# okpdf 中文说明

okpdf 是一个本地优先、面向 AI Agent 的开源 PDF 基础设施项目。目标不是只做一个小型 PDF MCP 工具，而是提供一套可以被 CLI、MCP、REST、TypeScript/Node SDK 和未来云端服务共同调用的 PDF 工具层。

## 一分钟开始

```bash
git clone git@github.com:tover0314-w/okpdf.git
cd okpdf
python scripts/setup_dev.py
python scripts/doctor.py
python scripts/smoke.py
```

如果 smoke 通过，你已经可以生成、检查和抽取 PDF：

```bash
okpdf create text "你好，okpdf" -o .agentpdf-out/hello.pdf --json
okpdf inspect .agentpdf-out/hello.pdf --json
okpdf extract-text .agentpdf-out/hello.pdf --json
```

`agentpdf` 命令仍然保留兼容，但推荐新用户使用品牌一致的 `okpdf` 命令。

## 当前已经可用

- 本地 CLI：`okpdf`
- 本地 MCP server：`okpdf serve --mcp`
- 本地 REST API：`okpdf serve --api`
- TypeScript/Node SDK：`packages/agentpdf-node`
- PDF inspect、merge、split、extract/remove/rotate pages
- PDF render、text extraction、metadata read/update/remove
- Markdown/Text to PDF
- 标准 `ToolResult` JSON、artifact manifest、输出 PDF 验证

## Node.js / TypeScript

```bash
okpdf serve --api
node packages/agentpdf-node/dist/src/cli.js tools
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o .agentpdf-out/node.pdf
```

SDK 示例：

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient();
const result = await client.createMarkdownPdf({
  markdown: "# 报告\n\n- 本地优先\n- Agent 可调用",
  outputPath: ".agentpdf-out/report.pdf",
});
```

## 设计原则

- 本地优先：不开云服务、不放 API key 也能工作。
- Agent 优先：工具输出结构化 JSON，而不是只有 `success: true`。
- Python core + TypeScript SDK：PDF 处理集中在 Python，本地/Node/Web/Agent 都走同一套工具结果。
- 云边界清晰：收费、托管、AI 高级能力不混进 OSS core。
- 依赖安全：默认核心避免 GPL/AGPL 依赖。

## 下一步方向

- Lite parse 和本地 RAG demo。
- Docker / self-hosted 一键启动。
- 更完整的 PDF 工具覆盖：水印、页码、压缩、表单、安全、diff。
- 更强输出验证：空白页检测、渲染检查、视觉 diff。
