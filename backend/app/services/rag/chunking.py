def chunk_text(content: str, *, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    clean = " ".join(content.split())
    if len(clean) <= chunk_size:
        return [clean]

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + chunk_size, len(clean))
        chunks.append(clean[start:end])
        if end == len(clean):
            break
        start = max(0, end - overlap)
    return chunks
