import csv
import re
import time
import zipfile
from html import escape
from pathlib import Path


OUTPUT_COLUMNS = ["번호", "개별 평점", "리뷰 내용"]
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'


def save_detail_review_outputs(summary, reviews, base_dir, timestamp=None):
    timestamp = timestamp or _current_timestamp()
    safe_product_name = _safe_filename(summary.product_name)
    file_stem = f"{timestamp}-{safe_product_name}"
    output_dir = Path(base_dir) / file_stem
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_path = output_dir / f"{file_stem}.txt"
    csv_path = output_dir / f"{file_stem}.csv"
    xlsx_path = output_dir / f"{file_stem}.xlsx"

    _write_txt(txt_path, reviews)
    _write_csv(csv_path, reviews)
    _write_xlsx(xlsx_path, reviews)

    return {
        "output_dir": str(output_dir),
        "txt": str(txt_path),
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
    }


def _write_txt(path, reviews):
    lines = ["\t".join(OUTPUT_COLUMNS)]
    for number, review in enumerate(reviews, start=1):
        lines.append(f"{number}\t{_empty_if_none(review.rating)}\t{review.content}")

    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path, reviews):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for number, review in enumerate(reviews, start=1):
            writer.writerow(_review_row(number, review))


def _write_xlsx(path, reviews):
    rows = [OUTPUT_COLUMNS]
    rows.extend(
        [_review_row(number, review)[column] for column in OUTPUT_COLUMNS]
        for number, review in enumerate(reviews, start=1)
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", _xlsx_content_types())
        workbook.writestr("_rels/.rels", _xlsx_root_rels())
        workbook.writestr("xl/workbook.xml", _xlsx_workbook())
        workbook.writestr("xl/_rels/workbook.xml.rels", _xlsx_workbook_rels())
        workbook.writestr("xl/worksheets/sheet1.xml", _xlsx_sheet(rows))
        workbook.writestr("xl/styles.xml", _xlsx_styles())


def _review_row(number, review):
    return {
        "번호": number,
        "개별 평점": _empty_if_none(review.rating),
        "리뷰 내용": review.content,
    }


def _xlsx_sheet(rows):
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            cell_ref = f"{_column_name(column_index)}{row_index}"
            cells.append(
                f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
            )
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def _column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _xlsx_content_types():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )


def _xlsx_root_rels():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )


def _xlsx_workbook():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="reviews" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )


def _xlsx_workbook_rels():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>'
    )


def _xlsx_styles():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '</styleSheet>'
    )


def _safe_filename(value, max_length=80):
    cleaned = re.sub(INVALID_FILENAME_CHARS, " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_length].rstrip() or "naver-shopping-reviews"


def _current_timestamp():
    now = time.localtime()
    return "%04d-%02d-%02d-%02d-%02d-%02d" % (
        now.tm_year,
        now.tm_mon,
        now.tm_mday,
        now.tm_hour,
        now.tm_min,
        now.tm_sec,
    )


def _empty_if_none(value):
    return "" if value is None else value
