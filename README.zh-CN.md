# okpdf 中文说明

> 本地优先、面向 AI Agent 的 PDF 基础设施：CLI、MCP、REST、本地工作流和 TypeScript/Node SDK。

语言： [English](README.md) · [中文说明](README.zh-CN.md) · [翻译维护说明](docs/i18n/README.md)

okpdf 正在构建一套开源的 agent-native PDF 基础设施。它不是单点 PDF 小工具，而是一层统一的工具面：检查、组织、渲染、提取、创建、组合、补丁、验证，并把结果以结构化 JSON、artifact、validation、warning 和下一步建议的形式返回给本地 agent。

公开 CLI 命令是 `okpdf`。兼容命令 `agentpdf` 仍然可用。TypeScript/Node 包位于 `packages/agentpdf-node`，包名是 `@okpdf/agentpdf-node`。

## 为什么值得关注

- 完整工具地图：当前 227 个公开工具名已经可通过 CLI、MCP、REST 和 manifest 发现。
- 本地优先：默认不需要托管服务 URL、付费 API key 或云依赖。
- Agent 优先输出：工具返回统一 `ToolResult`，包含 artifacts、validation、warnings、usage 和 next recommended tools。
- 不止 RAG：方向覆盖 context packet、target PDF profile、source graph、composition IR、PDF patch transaction、evidence coverage 和多模态 context-to-PDF 工作流。
- 多接口一致：CLI、MCP、REST 和 Node SDK 调用同一套工具层。
- PDF 安全优先：显式路径、不静默修改输入、拒绝路径穿越、元数据移除、生成 PDF 验证。
- 许可证安全：默认核心依赖避免 GPL/AGPL。

## 当前可用能力

| 能力族 | 说明 | 接口 |
|---|---|---|
| Inspect | 文档和页面级事实、文本/图像/渲染证据 | CLI, MCP, REST, Node.js |
| Organize | merge、split、extract/remove/reorder/rotate pages、插入空白页 | CLI, MCP, REST |
| Optimize | 压缩、可解析 PDF repair/rewrite | CLI, MCP, REST, Node.js |
| Convert | 图片/Markdown/Text 转 PDF，渲染页面，提取文本和内嵌图片 | CLI, MCP, REST, Node.js |
| Create Agent | 模板、style pack、context report、validation、coverage、本地 artifact bundle | CLI, MCP, REST, Node.js |
| Context / Compose | context packet、target PDF profile、source graph、composition IR、context-backed PDF | CLI, MCP, REST, Node.js |
| Evidence / Patch | 证据覆盖报告、结构化 append transaction、补丁预览/应用/验证 | CLI, MCP, REST, Node.js |
| Metadata | read、update、remove | CLI, MCP, REST |
| Validation | page count、render check、blank page check | CLI, MCP, REST |
| AI-lite | 本地 Document IR parse、PDF-to-JSON/Markdown、本地 RAG ingest/query/citation | CLI, MCP, REST |
| Workflow | 本地 agent workflow 规划、执行、报告 | CLI, MCP, REST, Node.js |

规划中的能力包括 crop/resize、forms、attachments、更丰富的 repair diagnostics、table parsing、visual diff 和 redaction verification。

## 一分钟开始

```bash
git clone git@github.com:tover0314-w/okpdf.git
cd okpdf
python scripts/setup_dev.py
python scripts/doctor.py
python scripts/smoke.py
okpdf tools list
okpdf create text "Hello from okpdf" -o .agentpdf-out/hello.pdf --json
```

常用命令：

```bash
okpdf inspect tests/fixtures/simple.pdf --json
okpdf merge tests/fixtures/simple.pdf tests/fixtures/two_pages.pdf -o .agentpdf-out/merged.pdf --json
okpdf render tests/fixtures/simple.pdf --pages 1 --format png --out-dir .agentpdf-out/renders --json
okpdf create markdown examples/sample-documents/business_report.md -o .agentpdf-out/report.pdf --json
okpdf validate .agentpdf-out/report.pdf --json
okpdf serve --api
okpdf serve --mcp --safe-root .
```

## Docker

```bash
docker build -t okpdf/local:dev .
docker run --rm -p 7331:7331 -v "$PWD:/workspace" okpdf/local:dev
curl http://127.0.0.1:7331/healthz
```

也可以使用：

```bash
docker compose up --build
```

镜像默认以非 root 用户运行，默认关闭云端/model 调用，暴露与 MCP 和 Node SDK 共用的本地 REST API。

## TypeScript / Node.js

先启动本地 REST API：

```bash
okpdf serve --api
```

然后从 Node 调用：

```bash
npm install
npm run build:node
node packages/agentpdf-node/dist/src/cli.js tools
node packages/agentpdf-node/dist/src/cli.js create-text --text "Hello Node" -o .agentpdf-out/node.pdf
```

SDK 示例：

```ts
import { AgentPDFClient } from "@okpdf/agentpdf-node";

const client = new AgentPDFClient({ baseUrl: "http://127.0.0.1:7331" });
const result = await client.createMarkdownPdf({
  markdown: "# Agent Report\n\n- Local first\n- MCP ready",
  outputPath: ".agentpdf-out/report.pdf",
  stylePack: "business_report_modern",
});

console.log(result.status);
console.log(result.artifacts[0]?.path);
```

## MCP 和 REST

运行本地 stdio MCP server：

```bash
okpdf serve --mcp --safe-root .
```

生成 Claude Code 项目配置：

```bash
okpdf agent setup claude-code -o .mcp.json --json
```

运行本地 HTTP API：

```bash
okpdf serve --api
```

REST 示例：

```bash
curl -X POST http://127.0.0.1:7331/v1/tools/pdf.inspect.document/run \
  -H 'Content-Type: application/json' \
  -d '{"path": "tests/fixtures/simple.pdf"}'
```

## ToolResult 合约

每个公开工具都返回统一结构：

```json
{
  "job_id": "job_...",
  "status": "succeeded",
  "tool": "pdf.organize.merge",
  "artifacts": [],
  "validation": {},
  "warnings": [],
  "usage": {},
  "next_recommended_tools": []
}
```

生成 PDF 会附带 artifact metadata 和 validation checks，例如可解析性、页数、renderability 和 blank page 检查。

## 仓库规范

应该提交：

- 源代码、schemas、tests、fixtures、docs、examples。
- 小型、许可安全、可复现的 baseline 生成样例。
- 能解释来源和再生成命令的示例资产。

不应该提交：

- `.agentpdf-out/` 下的本地输出。
- `node_modules/`、`.venv/`、`dist/`、`build/`、cache、log、coverage。
- `.env`、token、私有 URL、个人 MCP 配置。
- 随手生成的大 PDF、数据库、临时压缩包、本地 benchmark 产物。

如果确实需要提交生成 PDF，请放在 `examples/generated/`，同时保留 README 说明来源、用途和再生成命令。

完整规则见 [docs/REPOSITORY_HYGIENE.md](docs/REPOSITORY_HYGIENE.md)。

## 开发

```bash
python scripts/setup_dev.py
pytest -q
npm --workspace @okpdf/agentpdf-node test
ruff check src tests scripts
```

本地开发不需要云服务。

## 贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)、[SECURITY.md](SECURITY.md)、[community/DEPENDENCY_POLICY.md](community/DEPENDENCY_POLICY.md) 和 [docs/i18n/README.md](docs/i18n/README.md)。

新增公开功能时，请同步更新：

- CLI 示例。
- MCP 示例。
- REST 示例。
- 预期输出示例。
- 错误示例。
- 限制说明。
- 依赖和许可证说明。
- 相关翻译入口，至少保证 README 链接和核心术语不失真。

## 许可证

Apache-2.0。见 [LICENSE](LICENSE)。
