from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent.parent
MARKDOWN_PATH = ROOT / 'docs' / 'paper_draft.md'
OUTPUT_PATH = ROOT / 'papers' / 'qec_repetition_code_article.pdf'


def build_story():
    stylesheet = getSampleStyleSheet()
    body = ParagraphStyle(
        'BodyText',
        parent=stylesheet['BodyText'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        spaceBefore=6,
        spaceAfter=6,
        alignment=1,
    )
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=stylesheet['Title'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        alignment=1,
        spaceAfter=18,
    )
    heading2 = ParagraphStyle(
        'CustomHeading2',
        parent=stylesheet['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        spaceBefore=12,
        spaceAfter=6,
    )
    heading3 = ParagraphStyle(
        'CustomHeading3',
        parent=stylesheet['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=14,
        spaceBefore=10,
        spaceAfter=4,
    )
    list_style = ParagraphStyle(
        'ListText',
        parent=body,
        leftIndent=18,
        firstLineIndent=0,
        bulletIndent=12,
    )

    story = []
    text = MARKDOWN_PATH.read_text(encoding='utf-8')
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            story.append(Spacer(1, 6))
            continue

        if line.startswith('# '):
            story.append(Paragraph(line[2:], title_style))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], heading2))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:], heading3))
        elif line.startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
            story.append(Paragraph(line, list_style))
        elif line.startswith('- '):
            story.append(Paragraph(line[2:], list_style))
        elif line.startswith('$$') or line.startswith('$'):
            story.append(Paragraph(line, body))
        else:
            story.append(Paragraph(line, body))
    return story


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=letter,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
    )
    doc.build(build_story())
    print(f'PDF generated: {OUTPUT_PATH}')
    print(f'Bytes: {OUTPUT_PATH.stat().st_size}')


if __name__ == '__main__':
    main()
