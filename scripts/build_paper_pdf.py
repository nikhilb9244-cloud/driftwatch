"""Typeset the rendered paper without composing or changing its scientific prose.

Requires reportlab. Font files are supplied explicitly so the same build works
with any locally licensed Unicode serif family on Windows or Linux.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
INLINE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*")


def inline(text, base):
    text = text.translate(str.maketrans({"\u2011": "-", "\u2013": "-", "\u2014": "-"}))
    out, start = [], 0
    for match in INLINE.finditer(text):
        out.append(html.escape(text[start : match.start()]))
        label, link, code, bold = match.groups()
        if link is not None:
            destination = urljoin(base, link)
            out.append(
                f'<link href="{html.escape(destination, quote=True)}" color="#244f6c">{html.escape(label)}</link>'
            )
        elif code is not None:
            # Long evidence hashes may wrap without altering their extracted text.
            out.append(f'<font size="8">{html.escape(code)}</font>')
        else:
            out.append(f"<b>{html.escape(bold)}</b>")
        start = match.end()
    out.append(html.escape(text[start:]))
    return "".join(out)


def build(source, output, font_dir):
    for name, filename in (("Paper", "times.ttf"), ("Paper-Bold", "timesbd.ttf"), ("Paper-Italic", "timesi.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
    pdfmetrics.registerFontFamily(
        "Paper", normal="Paper", bold="Paper-Bold", italic="Paper-Italic", boldItalic="Paper-Bold"
    )
    metadata = json.loads((ROOT / "docs/publication-metadata.json").read_text(encoding="utf-8"))
    base = f"https://github.com/nikhilb9244-cloud/driftwatch/blob/{metadata['release_tag']}/docs/"
    width, height = A4
    margin = 43
    available = width - 2 * margin
    styles = {
        "body": ParagraphStyle("body", fontName="Paper", fontSize=10.4, leading=14, spaceAfter=8, alignment=TA_LEFT),
        "title": ParagraphStyle(
            "title", fontName="Paper-Bold", fontSize=19, leading=22, spaceAfter=13, keepWithNext=True
        ),
        "heading": ParagraphStyle(
            "heading", fontName="Paper-Bold", fontSize=13, leading=16, spaceBefore=12, spaceAfter=7, keepWithNext=True
        ),
        "reference": ParagraphStyle(
            "reference", fontName="Paper", fontSize=9.4, leading=12.2, spaceAfter=6, leftIndent=10, firstLineIndent=-10
        ),
        "cell": ParagraphStyle("cell", fontName="Paper", fontSize=8.1, leading=10.2, spaceAfter=0),
        "cell_head": ParagraphStyle("cell_head", fontName="Paper-Bold", fontSize=8.1, leading=10.2, spaceAfter=0),
    }
    text = source.read_text(encoding="utf-8")
    story = []
    for block in re.split(r"\n\s*\n", text.strip()):
        if block.startswith("# "):
            story.append(Paragraph(inline(block[2:], base), styles["title"]))
        elif block.startswith("## "):
            story.append(Paragraph(inline(block[3:], base), styles["heading"]))
        elif block.startswith("| "):
            lines = block.splitlines()
            rows = [[part.strip() for part in row.strip().strip("|").split("|")] for row in lines]
            rows.pop(1)  # Markdown separator, not a data row.
            count = len(rows[0])
            if rows[0][0] == "Band":
                weights = [0.13, 0.17, 0.22, 0.24, 0.24]
            elif rows[0][0] == "Element-set age h":
                weights = [0.115, 0.13, 0.145, 0.13, 0.13, 0.08, 0.13, 0.14]
            elif rows[0][0] == "Boundary":
                weights = [0.22, 0.35, 0.43]
            else:
                weights = [1 / count] * count
            assert len(weights) == count, rows[0]
            widths = [available * x / sum(weights) for x in weights]
            cells = [
                [Paragraph(inline(cell, base), styles["cell_head" if i == 0 else "cell"]) for cell in row]
                for i, row in enumerate(rows)
            ]
            table = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf0")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f8f8")]),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#70828c")),
                        ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.HexColor("#b1bdc3")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.extend([table, Spacer(1, 9)])
        elif block.startswith("- "):
            for item in block.split("\n- "):
                story.append(Paragraph(inline(item.removeprefix("- "), base), styles["reference"]))
        else:
            story.append(Paragraph(inline(block.replace("\n", " "), base), styles["body"]))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#c6cdd1"))
        canvas.line(margin, 35, width - margin, 35)
        canvas.setFont("Paper", 8)
        canvas.setFillColor(colors.HexColor("#53616a"))
        canvas.drawString(margin, 23, f"{metadata['author']} | {metadata['release_tag']}")
        canvas.drawRightString(width - margin, 23, str(doc.page))
        canvas.restoreState()

    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=41,
        bottomMargin=49,
        title=text.splitlines()[0][2:],
        author=metadata["author"],
        pageCompression=1,
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(
        json.dumps(
            {
                "pdf": str(output),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "docs/paper.md")
    parser.add_argument("--output", type=Path, default=ROOT / "output/pdf/paper-2026-09-v2.pdf")
    parser.add_argument("--font-dir", type=Path, default=Path("C:/Windows/Fonts"))
    args = parser.parse_args()
    build(args.source, args.output, args.font_dir)
