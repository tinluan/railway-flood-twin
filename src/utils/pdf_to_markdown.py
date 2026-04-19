"""
pdf_to_markdown.py
Converts a scientific PDF to a structured Markdown file for use with GitHub Copilot.
Usage: python src/utils/pdf_to_markdown.py <pdf_path> <output_md_path>
"""
import sys
import fitz  # PyMuPDF
from pathlib import Path


def pdf_to_markdown(pdf_path: Path, output_path: Path) -> None:
    """Extract text from a PDF and write it as a clean Markdown file."""
    doc = fitz.open(str(pdf_path))
    
    lines = []
    lines.append(f"# {pdf_path.stem}")
    lines.append(f"> **Source**: `{pdf_path.name}`")
    lines.append(f"> **Pages**: {doc.page_count}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            lines.append(f"## Page {i + 1}")
            lines.append("")
            # Clean up excessive whitespace while preserving paragraphs
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for para in paragraphs:
                # Collapse single newlines within paragraphs
                clean = " ".join(para.split("\n"))
                lines.append(clean)
                lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Converted: {pdf_path.name} -> {output_path.name}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python src/utils/pdf_to_markdown.py <pdf_path> <output_md_path>")
        sys.exit(1)
    pdf_to_markdown(Path(sys.argv[1]), Path(sys.argv[2]))
