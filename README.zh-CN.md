# okoffice 中文说明

> 本地优先、面向 agent 的 Office 基础设施：Word、Excel、PowerPoint、PDF、Bundle、CLI、MCP、REST 和 SDK 工作流。

语言：[English](README.md) | [中文说明](README.zh-CN.md) | [翻译维护说明](docs/i18n/README.md)

okoffice 的目标不是继续做一个 PDF 工具箱，而是做一层 agent-native Office infra。它让 coding agent 和本地自动化系统能够可靠地检查、抽取、创建、编辑、验证、引用和打包 Word 文档、Excel 工作簿、PowerPoint 演示文稿、PDF 和证据型 artifact。

历史上的 `agentpdf` / `okpdf` / `pdf.*` 现在是兼容层。它们仍然有用，但不再是产品边界。

## 产品主循环

```text
多个来源文件
  -> source graph
  -> 证据抽取
  -> workbook/model
  -> Word report + PowerPoint deck + PDF packet
  -> validation
  -> okoffice bundle
```

旗舰场景：

```text
多个 Word/PDF 来源 -> 可审计 Excel 工作簿 -> 漂亮的 PowerPoint -> 高管 memo -> PDF handout -> 审计 bundle
```

## 为什么值得关注

- 本地优先：默认不需要托管 URL、付费 API key 或云依赖。
- Agent 优先：工具返回统一 ToolResult，包含 artifact、validation、warning、usage 和 next recommended tools。
- 不止 RAG：RAG 只是证据能力之一，核心是跨 Office artifact 的抽取、建模、创作、验证和打包。
- 原生结构：保留 Word 段落/表格/批注、Excel 单元格/公式/图表、PPT 幻灯片/shape/notes、PDF 页码/bbox。
- 安全边界清楚：不默认执行宏，不默认把文件发到云端，不静默修改输入文件。
- 商业化边界清楚：OSS 做本地确定性工具，云端卖 worker、连接器、批处理、持久化和企业治理。

## 目标工具面

| 领域 | 示例工具 |
|---|---|
| Inspect | `office.inspect.file`, `word.inspect.document`, `sheet.inspect.workbook`, `deck.inspect.presentation`, `pdf.inspect.document` |
| Extract | `word.extract.tables`, `sheet.extract.formulas`, `deck.extract.notes`, `office.extract.schema` |
| Create | `word.create.report`, `sheet.create.evidence_workbook`, `deck.create.presentation`, `pdf.create.handout` |
| Patch | `office.patch.plan`, `word.patch.apply`, `sheet.patch.apply`, `deck.patch.apply` |
| Validate | `word.validation.document`, `sheet.validation.formulas`, `deck.validation.presentation`, `deck.validation.contact_sheet`, `pdf.validation.render_check` |
| Workflow | `office.workflow.docset_to_sheet`, `office.workflow.sheet_to_deck`, `office.workflow.board_pack` |
| Bundle | `office.bundle.export`, `office.bundle.verify` |

当前 machine manifest 有 **264** 个公开工具名：包括 okoffice beta 工具波次，以及保留的 `pdf.*` 和 agent setup 兼容层。

## 当前能跑什么

当前可运行实现主要是 PDF 兼容域：

- CLI：`okpdf`
- Python 包：`agentpdf`
- TypeScript 包：`@okpdf/agentpdf-node`
- 工具命名空间：`pdf.*` 和 `agent.setup.*`

兼容 quickstart：

```bash
python scripts/setup_dev.py
python scripts/doctor.py
python scripts/smoke.py
okpdf tools list --json
okpdf inspect tests/fixtures/simple.pdf --json
okpdf serve --mcp --safe-root .
okpdf serve --api
```

## okoffice 目标命令

这些命令代表产品方向，实际实现会按计划逐步补齐：

```bash
okoffice tools list --json
okoffice inspect report.docx --json
okoffice inspect model.xlsx --json
okoffice inspect deck.pptx --json
okoffice workflow docset-to-sheet sources/*.docx sources/*.pdf -o .okoffice-out/evidence.xlsx --json
okoffice workflow sheet-to-deck .okoffice-out/evidence.xlsx -o .okoffice-out/board-deck.pptx --json
okoffice workflow board-pack --file sources/report.docx --file sources/context.pdf --schema examples/schemas/vendor-renewal.json --out-dir .okoffice-out/board-pack --include-pdf-handout --json
okoffice bundle verify .okoffice-out/board-pack.okoffice.zip --json
```

## 下一步实现顺序

1. 增加 `okoffice` CLI alias，同时保留 `okpdf`。
2. 增加 okoffice manifest / namespace skeleton。
3. 增加 Office IR 和 source locator schemas。
4. 实现 DOCX/XLSX/PPTX inspect。
5. 实现 Word/Excel/PPT validation。
6. 实现 `docset_to_sheet`。
7. 实现 `sheet_to_deck`。
8. 实现 `board_pack`。
9. 把 OfficeCLI、LibreOffice、OCR、formula engine、AI provider 做成可选 worker。

## 重点文档

- [产品策略](docs/37_OKOFFICE_PRODUCT_STRATEGY.md)
- [工具分类](docs/38_OKOFFICE_TOOL_TAXONOMY.md)
- [云端商业化](docs/39_OKOFFICE_CLOUD_BUSINESS.md)
- [Agent infra](docs/40_OKOFFICE_AGENT_INFRA.md)
- [实施计划](docs/41_OKOFFICE_IMPLEMENTATION_PLAN.md)
- [PDF 兼容层](docs/42_LEGACY_PDF_COMPATIBILITY.md)
- [Office PRD](docs/36_OKOFFICE_AGENT_NATIVE_OFFICE_INFRA_PRD.md)

## 开发

```bash
python scripts/setup_dev.py
pytest -q
npm test --workspace @okpdf/agentpdf-node
ruff check src tests scripts
```

本地开发当前不需要任何云服务。

## License

Apache-2.0。详见 [LICENSE](LICENSE)。
