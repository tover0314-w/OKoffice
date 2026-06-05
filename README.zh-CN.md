# OKoffice 中文说明

> 面向 agent 的 Office 基础设施：把 Word、Excel、PowerPoint、PDF 和审计型文档工作流变成可调用、可验证、可组合的本地工具层。

语言入口：[English](README.md) | [中文](README.zh-CN.md) | [翻译维护说明](docs/i18n/README.md)

OKoffice 是给 coding agent、自动化系统和开发者使用的开源 Office infra。它不只是做文件转换，而是让 agent 能够结构化地检查、抽取、创建、编辑、验证、引用和打包 Office artifact。

历史上的 `agentpdf` / `okpdf` / `pdf.*` 现在是 OKoffice 里的 PDF 兼容层。兼容层会继续保留，但新产品边界是 `office.*`、`word.*`、`sheet.*`、`deck.*` 和跨格式 workflow。

## 为什么做 OKoffice

- **Agent-first 输出**：工具统一返回 `ToolResult` JSON，包含 artifacts、validation、warnings、usage 和 next recommended tools。
- **原生定位信息**：保留 Word 段落/表格/批注、Excel 单元格/公式/图表、PPT 幻灯片/shape/notes、PDF 页码/bbox 等 source refs。
- **本地优先**：CLI、MCP、REST、SDK 默认本地可跑，不依赖云账号。
- **验证是基础能力**：生成和编辑后的 artifact 应该带有渲染、安全、质量和 source-map 证据。
- **Taste-driven deck**：PPT 生成目标路线应先进入可检查的 HTML slide preview，再经过审美/布局验证后导出 PPTX。
- **云端边界清晰**：OSS 做确定性本地工具；云端未来做托管 worker、连接器、批处理、持久化和企业治理。

## 快速开始

```bash
git clone git@github.com:tover0314-w/OKoffice.git
cd OKoffice

python scripts/setup_dev.py
okoffice version
okoffice tools show word.extract.tables --json
pytest tests/unit/test_office_table_extract.py -q
```

当前可试用的本地入口：

```bash
okoffice inspect path/to/report.docx --json
okoffice word inspect path/to/report.docx --json
okoffice word extract-tables path/to/report.docx --json
okoffice sheet inspect path/to/model.xlsx --json
okoffice sheet read path/to/model.xlsx --max-rows 100 --json
okoffice sheet profile path/to/model.xlsx --json
okoffice sheet extract-tables path/to/model.xlsx --json
okoffice sheet create-evidence-workbook records.json -o .okoffice-out/evidence.xlsx --json
okoffice sheet write-workbook records.json -o .okoffice-out/model.xlsx --json
okoffice sheet validate .okoffice-out/model.xlsx --json
okoffice sheet validate-formulas .okoffice-out/model.xlsx --json
okoffice deck inspect path/to/deck.pptx --json
okoffice deck compose-plan .okoffice-out/evidence.xlsx -o .okoffice-out/deck.plan.json --title "Board Review" --json
okoffice deck create-presentation .okoffice-out/deck.plan.json -o .okoffice-out/board-review.pptx --json
okoffice deck create-from-outline outline.json -o .okoffice-out/board-review.pptx --json
okoffice deck validate .okoffice-out/board-review.pptx --json
okoffice context build --file path/to/report.docx --file path/to/model.xlsx -o .okoffice-out/context.packet.json --json
okoffice extract schema .okoffice-out/context.packet.json --schema examples/schemas/vendor-renewal.json -o .okoffice-out/evidence.json --json
okoffice validate package path/to/report.docx --json
okoffice workflow extract-to-sheet --context-packet .okoffice-out/context.packet.json -o .okoffice-out/evidence.xlsx --json
okoffice workflow extract-to-sheet path/to/report.docx path/to/model.xlsx -o .okoffice-out/evidence.xlsx --json
okoffice workflow sheet-to-deck .okoffice-out/evidence.xlsx -o .okoffice-out/board-review.pptx --title "Board Review" --json
okoffice workflow board-pack .okoffice-out/evidence.xlsx .okoffice-out/board-review.pptx -o .okoffice-out/board-pack.zip --title "Board Review" --json
okoffice bundle verify .okoffice-out/board-pack.zip --json

okpdf inspect tests/fixtures/simple.pdf --json
okpdf serve --mcp --safe-root .
okpdf serve --api
```

Deck 说明：当前 OSS beta 可以从 deck plan 直接创建确定性的可编辑 PPTX。OKoffice 目标路线是 taste-driven、HTML-first：

```text
deck.compose.plan -> deck.render.html -> deck.validation.html_preview
-> deck.validation.contact_sheet -> deck.export.pptx -> deck.validate.presentation
```

详见 [Taste-Driven HTML-First Deck Pipeline](docs/43_TASTE_DRIVEN_DECK_PIPELINE.md)。

## 当前状态

| 模块 | 状态 | 说明 |
|---|---:|---|
| `okoffice` CLI | beta | 已有 target manifest、plan、inspect、context build、表格抽取、workflow 和 bundle 入口。 |
| `office.inspect.file` | beta | 检测 DOCX/XLSX/PPTX/PDF/text，并返回安全元数据。 |
| `office.context.build_packet` | beta | 从 Office 兼容文件构建本地 context packet 和 source graph；可下钻到 Word 表格、Excel 工作表/区域/公式、PowerPoint 幻灯片节点。 |
| `office.extract.schema` | beta | 从 context packet 抽取 schema-shaped evidence JSON，保留 source refs、coverage 和缺失字段 warnings。 |
| `office.validation.package` | beta | 本地校验 OOXML/PDF package baseline、危险 ZIP entry、macro 标记和外部关系，不执行嵌入代码。 |
| `word.inspect.document` | beta | 读取 DOCX 结构、标题、表格、批注、样式和安全标记。 |
| `word.extract.tables` | beta | 把 DOCX 表格抽取成带 source refs 的 rows/cells。 |
| `sheet.inspect.workbook` | beta | 读取 workbook sheets、dimension、公式、表、图表、外链和安全标记。 |
| `sheet.read.workbook` | beta | 把 workbook rows、cells、公式和 source refs 读成有界的 agent JSON。 |
| `sheet.profile.data` | beta | 分析 headers、数据类型、缺失单元格、公式和 source coverage。 |
| `sheet.extract.tables` | beta | 抽取工作表表格，保留 sheet、row、column、cell refs。 |
| `sheet.write.workbook` | beta | 把 source-mapped records 写成本地 XLSX，并保留 provenance sheet。 |
| `sheet.validate.workbook` | beta | 校验 XLSX 结构、非空 sheet、外链、安全标记和 SourceRefs 就绪状态。 |
| `deck.inspect.presentation` | beta | 读取 PPTX 幻灯片、notes、layout、theme、media 和 chart 信息。 |
| `deck.compose.plan` | beta | 从 evidence workbook 生成带 source refs 的 Composition IR 和 outline JSON，不直接写 HTML 或 PPTX。 |
| `deck.create.presentation` | beta | 当前本地 writer 从 outline/plan 创建 PPTX；目标路线会编排 HTML preview 验证后再导出 PPTX。 |
| `deck.create.from_outline` | beta | 低层 outline-to-PPTX writer，用于兼容和 fallback。 |
| `deck.validate.presentation` | beta | 校验 PPTX 结构、空白页、placeholder 泄漏、安全标记和 source-map 就绪状态。 |
| `office.workflow.extract_to_sheet` | beta | 从 DOCX/XLSX 表格或 OKoffice context packet source graph 生成带 source refs 的 XLSX evidence workbook。 |
| `office.workflow.sheet_to_deck` | beta | 当前本地路线分析 evidence workbook 并创建 PPTX；目标路线会加入 HTML preview/contact-sheet gates。 |
| `office.workflow.board_pack` | beta | 创建本地 ZIP board pack，包含 artifacts、manifest、validation report 和交付元数据。 |
| `office.bundle.verify` | beta | 校验 board pack ZIP 的 manifest、validation report、artifact 成员、大小和 SHA-256。 |
| `pdf.*` 兼容层 | stable/beta | 完整 manifest 当前覆盖 270 个本地 PDF、Office 和 agent setup 工具，继续通过 `okpdf`、MCP、REST、SDK 可用。 |

## 产品主循环

```text
多来源文件
  -> inspect / extract
  -> source graph
  -> evidence workbook
  -> Word report + PowerPoint deck + PDF packet
  -> validation
  -> portable OKoffice bundle
```

旗舰场景：

```text
多个 Word/PDF 来源 -> 可审计 Excel 工作簿 -> 漂亮的 PowerPoint -> 高管 memo -> PDF handout -> audit bundle
```

## 工具面

| 领域 | 示例工具 |
|---|---|
| Inspect | `office.inspect.file`, `word.inspect.document`, `sheet.inspect.workbook`, `deck.inspect.presentation`, `pdf.inspect.document` |
| Extract | `word.extract.tables`, `sheet.read.workbook`, `sheet.profile.data`, `sheet.extract.tables`, `deck.extract.notes`, `pdf.convert.pdf_to_text` |
| Create | `word.write.document`, `sheet.create.evidence_workbook`, `sheet.write.workbook`, `deck.compose.plan`, `deck.render.html`, `deck.export.pptx`, `deck.create.presentation`, `pdf.convert.markdown_to_pdf` |
| Patch | `office.patch.plan`, `word.edit.patch`, `sheet.edit.patch`, `deck.edit.patch`, `pdf.patch.apply` |
| Validate | `office.validation.run`, `word.validation.document`, `sheet.validate.workbook`, `sheet.validation.formulas`, `deck.validate.presentation`, `pdf.validation.render_check` |
| Evidence | `office.context.build_packet`, `office.evidence.coverage`, `office.source_map.create` |
| Workflow | `office.workflow.extract_to_sheet`, `office.workflow.sheet_to_deck`, `office.workflow.board_pack`, `pdf.workflow.run` |
| Bundle | `office.bundle.export`, `office.bundle.verify`, `pdf.artifacts.export_bundle` |
| Agents | `agent.setup.codex`, `agent.setup.claude_code`, `agent.setup.openclaw`，未来会增加 `office.agent.setup.*` aliases |

## 文档地图

- [产品策略](docs/37_OKOFFICE_PRODUCT_STRATEGY.md)
- [Agent-native Office PRD](docs/36_OKOFFICE_AGENT_NATIVE_OFFICE_INFRA_PRD.md)
- [工具分类](docs/38_OKOFFICE_TOOL_TAXONOMY.md)
- [Taste-driven HTML-first deck pipeline](docs/43_TASTE_DRIVEN_DECK_PIPELINE.md)
- [Agent 基础设施](docs/40_OKOFFICE_AGENT_INFRA.md)
- [实施计划](docs/41_OKOFFICE_IMPLEMENTATION_PLAN.md)
- [PDF 兼容层](docs/42_LEGACY_PDF_COMPATIBILITY.md)
- [架构](docs/03_ARCHITECTURE.md)
- [Office IR 和 source locators](docs/11_DOCUMENT_IR_SPEC.md)
- [云端商业化边界](docs/39_OKOFFICE_CLOUD_BUSINESS.md)
- [仓库卫生](docs/REPOSITORY_HYGIENE.md)

## 开发

```bash
python scripts/setup_dev.py
python scripts/doctor.py
pytest -q
npm --workspace @okpdf/agentpdf-node test
ruff check src tests scripts
```

贡献规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题不要发公开 issue，请看 [SECURITY.md](SECURITY.md)。

## License

Apache-2.0。详见 [LICENSE](LICENSE)。
