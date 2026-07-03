from PyPDF2 import PdfMerger, PdfReader


def merge_pdfs(text: str) -> str:
    text = text.lower()
    parts = text.replace("merge pdf", "").split(" and ")

    if len(parts) != 2:
        return "Please say: merge pdf file1.pdf and file2.pdf"

    pdf1 = parts[0].strip()
    pdf2 = parts[1].strip()
    output_file = "merged.pdf"

    try:
        merger = PdfMerger()
        merger.append(pdf1)
        merger.append(pdf2)
        merger.write(output_file)
        merger.close()
        return f"PDFs merged successfully into {output_file}"
    except FileNotFoundError as fnf_err:
        return f"File not found: {fnf_err}"
    except Exception as e:
        return f"Merge failed: {str(e)}"


def extract_text(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def summarize_pdf(text: str) -> str:
    text = text.lower()
    pdf_path = text.replace("summarize pdf", "").strip()

    if not pdf_path:
        return "Please provide the PDF file name to summarize."

    content = extract_text(pdf_path)
    if not content:
        return "No text found in the PDF or file not accessible."

    summary = content[:1000]
    return summary
