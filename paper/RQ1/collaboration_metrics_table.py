import math
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from paper.RQ1.collaboration_common import build_author_bip_map, build_collaboration_metrics_rows


TABLE_COLUMNS = [
    ("author", "Author"),
    ("clusterId", "Cluster"),
    ("clusterSize", "Cluster Size"),
    ("rawDegree", "Degree"),
    ("weightedDegree", "Weighted Degree"),
    ("normalizedDegree", "Normalized Degree"),
    ("eigenvector", "Eigenvector Centrality"),
    ("weightedEigenvector", "Weighted Eigenvector"),
]

LATEX_TOP_N = 5
LATEX_HEADER_WRAP_WIDTH = 14

LATEX_TABLE_HEADERS = [
    "Author",
    "BIPs",
    "Degree",
    "W. Degree",
    "Eigenvector Centrality",
    "W. Eigenvector",
]


def _excel_column_name(index: int) -> str:
    name = ""
    value = index + 1
    while value:
        value, remainder = divmod(value - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _cell_xml(cell_ref: str, value) -> str:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return f'<c r="{cell_ref}"><v>{value}</v></c>'

    text = escape("" if value is None else str(value))
    return f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'


def _sheet_xml(headers: list[str], rows: list[list]) -> str:
    all_rows = [headers] + rows
    max_column = _excel_column_name(len(headers) - 1)
    dimension = f"A1:{max_column}{len(all_rows)}"

    row_xml = []
    for row_index, row in enumerate(all_rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            cell_ref = f"{_excel_column_name(column_index)}{row_index}"
            cells.append(_cell_xml(cell_ref, value))
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        '</worksheet>'
    )


def _write_xlsx(headers: list[str], rows: list[list], output_path: Path, sheet_name: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets>'
        f'<sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/>'
        '</sheets>'
        '</workbook>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )

    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as workbook_zip:
        workbook_zip.writestr("[Content_Types].xml", content_types_xml)
        workbook_zip.writestr("_rels/.rels", root_rels_xml)
        workbook_zip.writestr("xl/workbook.xml", workbook_xml)
        workbook_zip.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        workbook_zip.writestr("xl/worksheets/sheet1.xml", _sheet_xml(headers, rows))


def _latex_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("$", r"\$")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\textasciitilde{}")
        .replace("^", r"\textasciicircum{}")
    )


def _format_float(value: float) -> str:
    if not math.isfinite(value):
        return "0.000"
    return f"{value:.3f}"


def _latex_header_cell(title: str, max_line_length: int = LATEX_HEADER_WRAP_WIDTH) -> str:
    wrapped_lines = []
    for line in str(title).splitlines() or [""]:
        wrapped_lines.extend(
            textwrap.wrap(
                line.strip(),
                width=max_line_length,
                break_long_words=False,
                break_on_hyphens=False,
            )
            or [line.strip()]
        )

    escaped_lines = [_latex_escape(line) for line in wrapped_lines if line]
    if len(escaped_lines) <= 1:
        return rf"\textbf{{{escaped_lines[0] if escaped_lines else ''}}}"

    return r"\shortstack[c]{" + r" \\ ".join(
        rf"\textbf{{{line}}}" for line in escaped_lines
    ) + "}"


def export_collaboration_metrics_latex_table(
    authorship_payload: dict,
    network_data: dict,
    output_path: Path,
    top_n: int = LATEX_TOP_N,
    header_wrap_width: int = LATEX_HEADER_WRAP_WIDTH,
) -> None:
    metrics_rows = build_collaboration_metrics_rows(
        authorship_payload.get("collaboration_network", {}),
        authorship_payload.get("collaboration_centrality", []),
    )
    author_bip_map = build_author_bip_map(network_data)

    top_rows = sorted(
        metrics_rows,
        key=lambda row: (-int(row.get("weightedDegree", 0) or 0), str(row.get("author", ""))),
    )[:top_n]

    body_lines = []
    for row in top_rows:
        author = str(row.get("author", ""))
        body_lines.append(
            "        "
            + " & ".join(
                [
                    _latex_escape(author),
                    str(len(author_bip_map.get(author, []))),
                    str(int(row.get("rawDegree", 0) or 0)),
                    str(int(row.get("weightedDegree", 0) or 0)),
                    _format_float(float(row.get("eigenvector", 0) or 0)),
                    _format_float(float(row.get("weightedEigenvector", 0) or 0)),
                ]
            )
            + r" \\"
        )

    header_line = " & ".join(
        _latex_header_cell(title, max_line_length=header_wrap_width)
        for title in LATEX_TABLE_HEADERS
    ) + r" \\"

    latex_table = "\n".join(
        [
            r"    \begin{tabular}{lccccc}",
            r"    \toprule",
            f"    {header_line}",
            r"    \midrule",
            *body_lines,
            r"    \bottomrule",
            r"    \end{tabular}",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex_table, encoding="utf-8")


def export_collaboration_metrics_table(
    authorship_payload: dict,
    output_path: Path,
) -> None:
    metrics_rows = build_collaboration_metrics_rows(
        authorship_payload.get("collaboration_network", {}),
        authorship_payload.get("collaboration_centrality", []),
    )

    headers = [header for _, header in TABLE_COLUMNS]
    rows = [
        [row.get(field) for field, _ in TABLE_COLUMNS]
        for row in metrics_rows
    ]
    _write_xlsx(headers, rows, output_path, sheet_name="Collaboration Metrics")
