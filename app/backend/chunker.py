"""
Document Chunker module.
Performs section-aware, sliding-window chunking (300-500 tokens with overlap)
while preserving page and section provenance metadata for every chunk.
"""

from typing import List, Dict, Any


def chunk_document(
    doc_id: str,
    parsed_pdf: Dict[str, Any],
    target_chunk_size: int = 350,
    overlap_size: int = 60
) -> List[Dict[str, Any]]:
    """
    Chunks document page-by-page and paragraph-by-paragraph with overlap.
    
    Returns:
        List of chunks with metadata:
        [
            {
                "chunk_id": str,
                "doc_id": str,
                "page_number": int,
                "section_title": str,
                "text": str,
                "word_count": int,
                "extraction_method": str
            },
            ...
        ]
    """
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    for page_info in parsed_pdf.get("pages", []):
        page_num = page_info["page_number"]
        page_text = page_info["text"]
        headings = page_info.get("headings", [])
        primary_heading = headings[0] if headings else f"Page {page_num}"
        extraction_method = page_info.get("extraction_method", "pymupdf")

        if not page_text.strip():
            continue

        # Split into logical paragraphs / lines
        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
        
        # If no double newline, split by single newline
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in page_text.split("\n") if p.strip()]

        current_words: List[str] = []
        current_section = primary_heading

        for p in paragraphs:
            # Check if paragraph itself looks like a heading
            for h in headings:
                if h in p:
                    current_section = h
                    break

            words = p.split()
            if not words:
                continue

            current_words.extend(words)

            # Once we reach or exceed target chunk size, commit chunk
            if len(current_words) >= target_chunk_size:
                chunk_text = " ".join(current_words)
                chunk_id = f"{doc_id}_p{page_num}_c{chunk_index}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "page_number": page_num,
                    "section_title": current_section,
                    "text": chunk_text,
                    "word_count": len(current_words),
                    "extraction_method": extraction_method
                })
                chunk_index += 1

                # Keep overlap words
                if len(current_words) > overlap_size:
                    current_words = current_words[-overlap_size:]
                else:
                    current_words = []

        # Flush any remaining words on the page
        if current_words:
            chunk_text = " ".join(current_words)
            chunk_id = f"{doc_id}_p{page_num}_c{chunk_index}"
            chunks.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "page_number": page_num,
                "section_title": current_section,
                "text": chunk_text,
                "word_count": len(current_words),
                "extraction_method": extraction_method
            })
            chunk_index += 1

    return chunks
