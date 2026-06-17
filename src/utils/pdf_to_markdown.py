"""
src/utils/pdf_to_markdown.py — PDF Text Extractor for LLMs
==========================================================
Converts scientific PDFs (e.g., academic papers, manuals) into structured
Markdown files. This is particularly useful for feeding documentation into
GitHub Copilot, Gemini, or other LLMs for context generation.

It strips excessive whitespace, preserves paragraphs, and adds page headers.

Dependency:
    pip install pymupdf  (provides the `fitz` module)

Relationship with other files:
    - Independent utility.
    - Outputs are typically saved to `data/references/markdown/`.

Example Usage:
    # Convert a reference PDF to Markdown:
    python src/utils/pdf_to_markdown.py data/references/hec_ras_manual.pdf data/references/markdown/hec_ras_manual.md
"""
import sys
import fitz  # PyMuPDF
from pathlib import Path


def pdf_to_markdown(pdf_path: Path, output_path: Path) -> None:
    """Extract text from a PDF and write it as a clean Markdown file.

    Args:
        pdf_path: Path to the source PDF file.
        output_path: Path to the output Markdown file.
    """
    doc = fitz.open(str(pdf_path))

    try:
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
        try:
            print(f"[OK] Converted: {pdf_path.name} -> {output_path.name}")
        except UnicodeEncodeError:
            print(
                f"[OK] Converted: "
                f"{pdf_path.name.encode('ascii', 'ignore').decode()} -> "
                f"{output_path.name.encode('ascii', 'ignore').decode()}"
            )
    finally:
        doc.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python src/utils/pdf_to_markdown.py <pdf_path> <output_md_path>")
        sys.exit(1)
    pdf_to_markdown(Path(sys.argv[1]), Path(sys.argv[2]))
