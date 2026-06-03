import zipfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from agentpdf.conversion.local import (
    docx_to_pdf,
    pdf_to_docx,
    pdf_to_html,
    pdf_to_pptx,
    pdf_to_xlsx,
    pptx_to_pdf,
    url_to_pdf,
    xlsx_to_pdf,
)
from agentpdf.forms.local import create_form_pdf, import_form_data_pdf, validate_form_pdf
from agentpdf.ocr_scan.local import (
    despeckle_pdf,
    multilingual_ocr_pdf,
    ocr_pdf,
    remove_existing_ocr_pdf,
    searchable_pdf,
    scan_to_pdf,
)
from agentpdf.optimize.local import subset_fonts_pdf, to_pdfa_pdf
from agentpdf.security.local import (
    decrypt_authorized_pdf,
    encrypt_pdf,
    malware_scan_pdf,
    protect_pdf,
    sign_pdf,
    unlock_authorized_pdf,
    verify_signature_pdf,
)


def test_office_url_and_pdf_conversion_tools_write_local_artifacts(tmp_path: Path) -> None:
    pdf = tmp_path / "source.pdf"
    html = tmp_path / "source.html"
    docx = tmp_path / "source.docx"
    pptx = tmp_path / "source.pptx"
    xlsx = tmp_path / "source.xlsx"
    _write_text_pdf(pdf, ["Quarterly revenue was 15%."])
    html.write_text("<h1>AgentPDF</h1><p>URL conversion body.</p>", encoding="utf-8")
    _write_minimal_docx(docx, ["DOCX heading", "DOCX body"])
    _write_minimal_pptx(pptx, ["Slide one", "Slide two"])
    _write_minimal_xlsx(xlsx, [["metric", "value"], ["latency", "42"]])

    url_pdf = url_to_pdf(html.as_uri(), tmp_path / "url.pdf", allow_file_urls=True)
    docx_pdf = docx_to_pdf(docx, tmp_path / "docx.pdf")
    pptx_pdf = pptx_to_pdf(pptx, tmp_path / "pptx.pdf")
    xlsx_pdf = xlsx_to_pdf(xlsx, tmp_path / "xlsx.pdf")
    html_result = pdf_to_html(pdf, tmp_path / "out.html")
    docx_result = pdf_to_docx(pdf, tmp_path / "out.docx")
    pptx_result = pdf_to_pptx(pdf, tmp_path / "out.pptx")
    xlsx_result = pdf_to_xlsx(pdf, tmp_path / "out.xlsx")

    assert url_pdf.tool == "pdf.convert.url_to_pdf"
    assert docx_pdf.tool == "pdf.convert.docx_to_pdf"
    assert pptx_pdf.tool == "pdf.convert.pptx_to_pdf"
    assert xlsx_pdf.tool == "pdf.convert.xlsx_to_pdf"
    assert html_result.tool == "pdf.convert.pdf_to_html"
    assert "Quarterly revenue" in (tmp_path / "out.html").read_text(encoding="utf-8")
    assert docx_result.tool == "pdf.convert.pdf_to_docx"
    assert zipfile.is_zipfile(tmp_path / "out.docx")
    assert pptx_result.tool == "pdf.convert.pdf_to_pptx"
    assert zipfile.is_zipfile(tmp_path / "out.pptx")
    assert xlsx_result.tool == "pdf.convert.pdf_to_xlsx"
    assert zipfile.is_zipfile(tmp_path / "out.xlsx")


def test_pdfa_font_form_security_and_ocr_tools(tmp_path: Path) -> None:
    pdf = tmp_path / "source.pdf"
    image = tmp_path / "scan.png"
    _write_text_pdf(pdf, ["Name:", "Signed content"])
    Image.new("RGB", (80, 40), color=(245, 245, 245)).save(image)

    subset = subset_fonts_pdf(pdf, tmp_path / "subset.pdf")
    pdfa = to_pdfa_pdf(pdf, tmp_path / "pdfa.pdf")
    form = create_form_pdf(
        tmp_path / "form.pdf",
        [{"name": "name", "label": "Name", "required": True}],
    )
    filled = import_form_data_pdf(form.artifacts[0].path, {"name": "Ada"}, tmp_path / "filled.pdf")
    valid = validate_form_pdf(filled.artifacts[0].path, required_fields=["name"])
    protected = protect_pdf(pdf, tmp_path / "protected.pdf", password="secret")
    encrypted = encrypt_pdf(pdf, tmp_path / "encrypted.pdf", password="secret")
    unlocked = unlock_authorized_pdf(protected.artifacts[0].path, tmp_path / "unlocked.pdf", password="secret")
    decrypted = decrypt_authorized_pdf(
        encrypted.artifacts[0].path,
        tmp_path / "decrypted.pdf",
        password="secret",
    )
    signature = sign_pdf(pdf, tmp_path / "signature.json", secret="local-secret")
    verified = verify_signature_pdf(pdf, signature.artifacts[0].path, secret="local-secret")
    scan = malware_scan_pdf(pdf)
    scan_pdf = scan_to_pdf([image], tmp_path / "scan.pdf")
    despeckled = despeckle_pdf(scan_pdf.artifacts[0].path, tmp_path / "despeckled.pdf")
    no_ocr = remove_existing_ocr_pdf(scan_pdf.artifacts[0].path, tmp_path / "no-ocr.pdf")
    multilingual = multilingual_ocr_pdf(
        scan_pdf.artifacts[0].path,
        tmp_path / "multi-ocr.pdf",
        languages=["eng", "chi_sim"],
    )

    assert subset.tool == "pdf.optimize.subset_fonts"
    assert pdfa.tool == "pdf.optimize.to_pdfa"
    assert form.tool == "pdf.forms.create"
    assert filled.tool == "pdf.forms.import_data"
    assert valid.tool == "pdf.forms.validate"
    assert valid.usage["missing_required_fields"] == []
    assert protected.tool == "pdf.security.protect"
    assert PdfReader(protected.artifacts[0].path).is_encrypted is True
    assert encrypted.tool == "pdf.security.encrypt"
    assert unlocked.tool == "pdf.security.unlock_authorized"
    assert decrypted.tool == "pdf.security.decrypt_authorized"
    assert signature.tool == "pdf.security.sign"
    assert verified.tool == "pdf.security.verify_signature"
    assert verified.usage["signature_valid"] is True
    assert scan.tool == "pdf.security.malware_scan"
    assert scan.usage["suspicious_count"] == 0
    assert scan_pdf.tool == "pdf.ocr_scan.scan_to_pdf"
    assert despeckled.tool == "pdf.ocr_scan.despeckle"
    assert no_ocr.tool == "pdf.ocr_scan.remove_existing_ocr"
    assert multilingual.tool == "pdf.ocr_scan.multilingual_ocr"


def test_ocr_pdf_returns_text_regions_from_local_engine(monkeypatch, tmp_path: Path) -> None:
    image = tmp_path / "scan.png"
    Image.new("RGB", (160, 80), color=(255, 255, 255)).save(image)

    monkeypatch.setattr("agentpdf.ocr_scan.local._run_tesseract_tsv", _fake_tesseract_tsv)

    result = ocr_pdf(image, languages=["eng"])

    assert result.status == "succeeded"
    assert result.tool == "pdf.ocr_scan.ocr"
    assert result.usage["input_kind"] == "image"
    assert result.usage["languages"] == ["eng"]
    assert result.usage["engine"] == "tesseract"
    assert result.usage["text"] == "Hello OCR"
    assert result.usage["region_count"] == 2
    page = result.usage["pages"][0]
    assert page["page_number"] == 1
    assert page["text"] == "Hello OCR"
    assert page["regions"][0]["text"] == "Hello"
    assert page["regions"][0]["image_bbox"] == [10, 20, 50, 32]
    assert page["regions"][0]["confidence"] == 96.0


def test_searchable_pdf_writes_ocr_text_layer(monkeypatch, tmp_path: Path) -> None:
    image = tmp_path / "scan.png"
    image_pdf = tmp_path / "scan.pdf"
    output = tmp_path / "searchable.pdf"
    Image.new("RGB", (160, 80), color=(255, 255, 255)).save(image)
    scan_to_pdf([image], image_pdf)
    monkeypatch.setattr("agentpdf.ocr_scan.local._run_tesseract_tsv", _fake_tesseract_tsv)

    result = searchable_pdf(image_pdf, output_path=output, languages=["eng"])

    assert result.status == "succeeded"
    assert result.tool == "pdf.ocr_scan.searchable_pdf"
    assert result.artifacts[0].path == output
    assert result.validation is not None
    assert result.validation.status == "passed"
    assert result.usage["ocr"]["text"] == "Hello OCR"
    assert "Hello" in (PdfReader(output).pages[0].extract_text() or "")


def test_ocr_pdf_reports_missing_engine(monkeypatch, tmp_path: Path) -> None:
    from agentpdf.tools.runner import run_ocr

    image = tmp_path / "scan.png"
    Image.new("RGB", (160, 80), color=(255, 255, 255)).save(image)
    monkeypatch.setattr("shutil.which", lambda _engine: None)

    result = run_ocr(image, languages=["eng"], engine="missing-ocr")

    assert result.status == "failed"
    assert result.tool == "pdf.ocr_scan.ocr"
    assert result.error is not None
    assert result.error.code == "dependency_missing"
    assert "missing-ocr" in result.error.message


def _fake_tesseract_tsv(
    image_path: Path,
    languages: list[str],
    engine: str,
    psm: int,
) -> str:
    assert image_path.exists()
    assert languages == ["eng"]
    assert engine == "tesseract"
    assert psm == 6
    return (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\t10\t20\t40\t12\t96\tHello\n"
        "5\t1\t1\t1\t1\t2\t56\t20\t28\t12\t91\tOCR\n"
    )


def _write_text_pdf(path: Path, lines: list[str]) -> None:
    document = canvas.Canvas(str(path))
    y = 740
    for line in lines:
        document.drawString(72, y, line)
        y -= 20
    document.showPage()
    document.save()


def _write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>" for paragraph in paragraphs)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("_rels/.rels", "<Relationships />")
        archive.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body>{body}</w:body></w:document>",
        )


def _write_minimal_pptx(path: Path, slide_texts: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("_rels/.rels", "<Relationships />")
        for index, text in enumerate(slide_texts, start=1):
            archive.writestr(
                f"ppt/slides/slide{index}.xml",
                f'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                f'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                f"<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r>"
                f"</a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>",
            )


def _write_minimal_xlsx(path: Path, rows: list[list[str]]) -> None:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_xlsx_column(column_index)}{row_index}"
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{value}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("_rels/.rels", "<Relationships />")
        archive.writestr("xl/workbook.xml", "<workbook />")
        archive.writestr(
            "xl/worksheets/sheet1.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{''.join(row_xml)}</sheetData></worksheet>",
        )


def _xlsx_column(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name
