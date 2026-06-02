# okpdf 中文说明

okpdf 是一个本地优先、面向 AI Agent 的开源 PDF 基础设施项目。它不是一个单点 PDF 小工具，也不只是 PDF RAG，而是一套可以被 CLI、MCP、REST、TypeScript/Node SDK 和未来云端服务共同调用的 PDF 操作、组合、验证和证据交付层。

## 一分钟开始

```bash
git clone git@github.com:tover0314-w/okpdf.git
cd okpdf
python scripts/setup_dev.py
python scripts/doctor.py
python scripts/smoke.py
```

如果 smoke 通过，你已经可以生成、检查、编辑和验证 PDF：

```bash
okpdf create text "你好，okpdf" -o .agentpdf-out/hello.pdf --json
okpdf inspect .agentpdf-out/hello.pdf --json
okpdf watermark .agentpdf-out/hello.pdf --text "DRAFT" -o .agentpdf-out/draft.pdf --json
okpdf page-numbers .agentpdf-out/draft.pdf -o .agentpdf-out/numbered.pdf --json
okpdf validate .agentpdf-out/numbered.pdf --json
okpdf render-check .agentpdf-out/numbered.pdf --pages 1 --json
okpdf blank-page-check .agentpdf-out/numbered.pdf --pages all --json
```

`agentpdf` 命令仍然保留兼容，但推荐新用户使用品牌一致的 `okpdf` 命令。

## 当前已经可用

- 本地 CLI：`okpdf`
- 本地 MCP server：`okpdf serve --mcp`
- 本地 REST API：`okpdf serve --api`
- TypeScript/Node SDK：`packages/agentpdf-node`
- PDF inspect、merge、split、extract/remove/reorder/rotate pages、insert blank pages
- 图片/Text/Markdown 转 PDF
- PDF render、text extraction、metadata read/update/remove
- 文本水印、页码叠加、生成 PDF 验证
- Lite parse、Document IR、本地 RAG ingest/query 和页码引用
- 标准 `ToolResult` JSON、artifact manifest、warnings、next recommended tools
- 产品方向已经扩展到 context packet、target PDF profile、source graph、composition IR、PDF patch transaction、evidence coverage、多模态上下文转多样式 PDF

## Node.js / TypeScript

```bash
okpdf serve --api
node packages/agentpdf-node/dist/src/cli.js tools
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o .agentpdf-out/node.pdf
node packages/agentpdf-node/dist/src/cli.js watermark .agentpdf-out/node.pdf --text DRAFT -o .agentpdf-out/node-draft.pdf
```

SDK 示例：

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient();
const result = await client.createMarkdownPdf({
  markdown: "# 报告\n\n- 本地优先\n- Agent 可调用",
  outputPath: ".agentpdf-out/report.pdf",
});

await client.addPageNumbers({
  inputPath: ".agentpdf-out/report.pdf",
  outputPath: ".agentpdf-out/report-numbered.pdf",
});

await client.ragIngest({
  inputPath: ".agentpdf-out/report-numbered.pdf",
  indexPath: ".agentpdf-out/report.index.json",
});

console.log(result.status);
```

## 设计原则

- 本地优先：不启用云服务、不提供 API key 也能工作。
- Agent 优先：工具输出结构化 JSON，而不是只返回 `success: true`。
- 证据优先：生成内容、引用、修改和验证都应该能追溯来源。
- Python core + TypeScript SDK：PDF 处理集中在 Python，本地 Node/Web/Agent 走同一套工具结果。
- 云边界清晰：收费、托管、AI 高级能力不混进 OSS core。
- 依赖安全：默认核心避免 GPL/AGPL 依赖。
- 生成即验证：每个生成 PDF 都返回 artifact 和 validation report。
- 集大成式借鉴：参考 pypdf、qpdf、pdfcpu、pdfplumber、OCRmyPDF、Docling、Marker、Stirling-PDF 等项目的架构和产品面，但不直接复制实现代码。

## 下一步方向

- Docker / self-hosted 一键启动。
- 更完整的 PDF 工具覆盖：压缩、裁剪、表单、安全、diff、redaction verification。
- 更强输出验证：空白页检测、渲染检查、视觉 diff。
- 更强 Document IR：段落、表格、bbox、Markdown/JSON export。
- Context packet、target PDF profile、source graph、composition IR、artifact lineage、patch manifest。
- 图片、视频、文档、代码、数据、网络链接、现有 PDF 到学习 PDF、简历 PDF、论文 PDF、报告、证据包、演示文稿式 PDF 的工作流。
- 云端高级能力边界：OCR、agentic parse、多模态处理、批处理、长期 artifact graph、企业审计。
