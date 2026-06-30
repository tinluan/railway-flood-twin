import re
import os
import sys
from markdown import markdown
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Suppress headers/footers on cover page
        if self._pageNumber == 1:
            self.restoreState()
            return
            
        # Draw header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1A365D"))
        self.drawString(54, 755, "SNCF Ligne 400 — Digital Twin Research")
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 747, 558, 747)
        
        # Draw footer
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Confidential — SNCF Réseau & Master's Thesis partners")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def parse_markdown_to_story(md_path, figures_dir, styles):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Clean frontmatter / cover lines
    lines = content.split('\n')
    story = []
    
    # Custom cover page
    story.append(Spacer(1, 100))
    story.append(Paragraph("Master's Thesis Report", ParagraphStyle('SubTitleDoc', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#4A5568"), spaceAfter=15)))
    story.append(Paragraph("Railway Flood-Risk Digital Twin for the SNCF Tartaiguille Corridor", ParagraphStyle('TitleDoc', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=24, textColor=colors.HexColor("#1A365D"), leading=28, spaceAfter=20)))
    story.append(Paragraph("Validation, Architecture & Scientific Calibration", ParagraphStyle('SubTitle2Doc', parent=styles['Normal'], fontName='Helvetica', fontSize=16, textColor=colors.HexColor("#2B6CB0"), spaceAfter=50)))
    
    story.append(Paragraph("<b>Authors:</b> Szilvia PALASTI • Amal MAIZI • Trong-Tin TRAN<br/><b>Date:</b> June 2026<br/><b>Institution:</b> SNCF Réseau & Partner Universities", ParagraphStyle('AuthorBlock', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=16, textColor=colors.HexColor("#2D3748"))))
    story.append(PageBreak())

    # Regular parsing logic (simplified Markdown parser for ReportLab flowables)
    in_code_block = False
    code_text = []
    in_table = False
    table_rows = []

    # Simple inline tags clean up
    def clean_text(t):
        t = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', t)
        t = re.sub(r'\*(.*?)\*', r'<i>\1</i>', t)
        t = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', t)
        t = re.sub(r'\$(.*?)\$', r'<i>\1</i>', t) # simple math italicization
        t = t.replace('&', '&amp;').replace('< ', '&lt; ').replace(' >', ' &gt;')
        return t

    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip header metadata lines
        if i < 12 and (line.startswith('>') or line.strip() == '---' or line.startswith('#')):
            i += 1
            continue

        # Code blocks / Mermaid
        if line.strip().startswith('```'):
            if in_code_block:
                in_code_block = False
                code_content = '\n'.join(code_text)
                
                # Check if this is a mermaid block
                is_mermaid = False
                if len(story) > 0 and hasattr(story[-1], 'text') and 'mermaid' in story[-1].text:
                    is_mermaid = True
                # Alternatively look at the entry header (sometimes it's marked or handled before)
                # We can also detect if code starts with graph TD, pie title, gantt etc.
                first_line = code_text[0].strip() if code_text else ""
                if first_line.startswith("graph ") or first_line.startswith("pie ") or first_line.startswith("gantt"):
                    is_mermaid = True
                
                if is_mermaid:
                    # Generate a diagram PNG using Kroki
                    import urllib.parse
                    import requests
                    import base64
                    import zlib
                    
                    try:
                        # Compress mermaid code using zlib for Kroki GET/POST
                        # Kroki format is base64_utf8(zlib_compress(text))
                        compressed = zlib.compress(code_content.encode('utf-8'), 9)
                        encoded = base64.urlsafe_b64encode(compressed).decode('ascii')
                        kroki_url = f"https://kroki.io/mermaid/png/{encoded}"
                        
                        # Fetch the compiled diagram PNG
                        response = requests.get(kroki_url, timeout=15)
                        if response.status_code == 200:
                            # Save to temp file
                            temp_dir = os.path.dirname(md_path)
                            diagram_filename = f"diagram_temp_{i}.png"
                            diagram_path = os.path.join(temp_dir, diagram_filename)
                            with open(diagram_path, 'wb') as df:
                                df.write(response.content)
                            
                            # Render image in story
                            img = Image(diagram_path)
                            aspect = img.imageHeight / img.imageWidth
                            
                            # Keep within bounds of letter size printable area (width: ~500 max, height: ~650 max)
                            max_width = 400
                            max_height = 500
                            
                            width = max_width
                            height = max_width * aspect
                            
                            if height > max_height:
                                height = max_height
                                width = max_height / aspect
                                
                            img.drawWidth = width
                            img.drawHeight = height
                            story.append(img)
                            story.append(Spacer(1, 10))
                        else:
                            raise Exception(f"Kroki returned status {response.status_code}")
                    except Exception as ex:
                        print(f"Error rendering mermaid: {ex}")
                        # Fallback to plain text code representation
                        formatted_code = "<br/>".join([clean_text(l) for l in code_text])
                        story.append(Paragraph(f"<font face='Courier'>{formatted_code}</font>", styles['Code']))
                        story.append(Spacer(1, 10))
                else:
                    formatted_code = "<br/>".join([clean_text(l) for l in code_text])
                    story.append(Paragraph(f"<font face='Courier'>{formatted_code}</font>", styles['Code']))
                    story.append(Spacer(1, 10))
                
                code_text = []
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_text.append(line)
            i += 1
            continue

        # Tables
        if '|' in line:
            if not in_table:
                in_table = True
                table_rows = []
            
            # Skip separator line (e.g. |---|---|)
            if re.match(r'^[\s|:-]+$', line):
                i += 1
                continue
                
            parts = [clean_text(p.strip()) for p in line.split('|')[1:-1]]
            table_rows.append(parts)
            i += 1
            continue
        else:
            if in_table:
                in_table = False
                # Convert rows to ReportLab Table
                if table_rows:
                    formatted_rows = []
                    # Header style vs Body style
                    for idx, row in enumerate(table_rows):
                        style_to_use = ParagraphStyle('TableHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white) if idx == 0 else ParagraphStyle('TableBody', parent=styles['Normal'], fontSize=8, leading=10)
                        formatted_rows.append([Paragraph(cell, style_to_use) for cell in row])
                    
                    col_widths = [504 / len(table_rows[0])] * len(table_rows[0])
                    t = Table(formatted_rows, colWidths=col_widths)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ]))
                    story.append(t)
                    story.append(Spacer(1, 12))
                table_rows = []

        # Headings
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            title_text = clean_text(line.lstrip('#').strip())
            if level == 1:
                story.append(Spacer(1, 15))
                story.append(Paragraph(title_text, styles['Heading1']))
                story.append(Spacer(1, 10))
            elif level == 2:
                story.append(Spacer(1, 12))
                story.append(Paragraph(title_text, styles['Heading2']))
                story.append(Spacer(1, 8))
            else:
                story.append(Spacer(1, 10))
                story.append(Paragraph(title_text, styles['Heading3']))
                story.append(Spacer(1, 6))
            i += 1
            continue

        # Figures (Markdown image link)
        img_match = re.match(r'^!\[(.*?)\]\((.*?)\)', line.strip())
        if img_match:
            caption = img_match.group(1)
            rel_path = img_match.group(2)
            # Resolve relative path
            abs_path = os.path.abspath(os.path.join(os.path.dirname(md_path), rel_path))
            
            if os.path.exists(abs_path):
                # Scale image nicely to fit page width (max 400 width)
                try:
                    img = Image(abs_path)
                    aspect = img.imageHeight / img.imageWidth
                    img.drawWidth = 400
                    img.drawHeight = 400 * aspect
                    
                    caption_style = ParagraphStyle('Caption', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, leading=10, textColor=colors.HexColor("#4A5568"), alignment=1)
                    
                    # Keep image and caption together
                    story.append(KeepTogether([
                        img,
                        Spacer(1, 6),
                        Paragraph(clean_text(caption), caption_style),
                        Spacer(1, 12)
                    ]))
                except Exception as ex:
                    print(f"Error drawing image {abs_path}: {ex}")
            else:
                print(f"Image not found: {abs_path}")
            i += 1
            continue

        # Unordered list items
        if line.strip().startswith('* ') or line.strip().startswith('- '):
            item_text = clean_text(line.strip()[2:])
            story.append(Paragraph(f"• {item_text}", styles['BodyText']))
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Regular paragraph
        if line.strip():
            # Handle blockquotes
            if line.strip().startswith('>'):
                bq_text = clean_text(line.strip().lstrip('>').strip())
                story.append(Paragraph(bq_text, styles['BlockQuote']))
            else:
                story.append(Paragraph(clean_text(line.strip()), styles['BodyText']))
            story.append(Spacer(1, 8))

        i += 1

    return story


def build_pdf(md_path, pdf_path):
    # Setup document geometry with 0.75-inch (54pt) margins
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styling parameters
    styles['Normal'].fontSize = 10
    styles['Normal'].leading = 14
    styles['Normal'].textColor = colors.HexColor("#2D3748")
    
    styles['BodyText'].fontSize = 10
    styles['BodyText'].leading = 14
    styles['BodyText'].spaceAfter = 8
    
    styles['Heading1'].fontName = 'Helvetica-Bold'
    styles['Heading1'].fontSize = 18
    styles['Heading1'].leading = 22
    styles['Heading1'].textColor = colors.HexColor("#1A365D")
    styles['Heading1'].spaceAfter = 12
    styles['Heading1'].keepWithNext = True

    styles['Heading2'].fontName = 'Helvetica-Bold'
    styles['Heading2'].fontSize = 14
    styles['Heading2'].leading = 18
    styles['Heading2'].textColor = colors.HexColor("#2B6CB0")
    styles['Heading2'].spaceAfter = 10
    styles['Heading2'].keepWithNext = True

    styles['Heading3'].fontName = 'Helvetica-Bold'
    styles['Heading3'].fontSize = 11
    styles['Heading3'].leading = 15
    styles['Heading3'].textColor = colors.HexColor("#2D3748")
    styles['Heading3'].spaceAfter = 8
    styles['Heading3'].keepWithNext = True
    
    styles['Code'].fontName = 'Courier'
    styles['Code'].fontSize = 8
    styles['Code'].leading = 12
    styles['Code'].textColor = colors.HexColor("#1A202C")
    styles['Code'].backColor = colors.HexColor("#F7FAFC")
    styles['Code'].borderColor = colors.HexColor("#E2E8F0")
    styles['Code'].borderWidth = 0.5
    styles['Code'].borderPadding = 8
    styles['Code'].spaceAfter = 10
    
    styles.add(ParagraphStyle('BlockQuote', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=9.5, leading=13, textColor=colors.HexColor("#4A5568"), leftIndent=15, rightIndent=15, spaceAfter=10))

    figures_dir = os.path.abspath(os.path.join(os.path.dirname(md_path), "../figures"))
    story = parse_markdown_to_story(md_path, figures_dir, styles)

    # Build PDF using dynamic page count header/footer helper
    doc.build(story, canvasmaker=NumberedCanvas)


if __name__ == "__main__":
    md_file = r"c:\Users\ktstr\Documents\railway-flood-twin\report\drafts\final_report_template.md"
    pdf_file = r"c:\Users\ktstr\Documents\railway-flood-twin\report\drafts\final_report.pdf"
    print(f"Building PDF from {md_file}...")
    build_pdf(md_file, pdf_file)
    print(f"PDF built successfully: {pdf_file}")
