def data_split(content: str, seps: list[str], chunk_size: int = 10000, overlap: int = 1000) -> list[str]:
    """
    Split the content into chunks of max_chunk_size with overlap. If overlap is too large compared to max_chunk_size
    then expect wierd results."""
    assert overlap * 4 <= chunk_size, "Overlap is too large compared to max_chunk_size"
    r = []
    seps = seps + ["\n\n", "\n", " "]
    i = 0
    while len(content) - i > chunk_size:
        j = -1
        for sep in seps:
            j = content.find(sep, i + chunk_size - 2 * overlap, i + chunk_size)
            if j != -1:
                break
        if j == -1:
            j = i + chunk_size - overlap
        r.append(content[i:j].strip())

        ii = j - overlap
        jj = -1
        for sep in seps:
            jj = content.find(sep, ii - overlap // 4, ii + overlap // 4)
            if jj != -1:
                break
        if jj == -1:
            i = ii
        else:
            i = jj
    r.append(content[i:].strip())
    return r

