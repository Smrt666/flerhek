from pathlib import Path
from flare_ai_rag.utils.splitter import data_split
import json


def get_code_data(file: Path, overlap: int = 900) -> list[dict]:
    chunk_size = 10 * overlap
    with open(file, "r") as f:
        code = json.load(f)

    r = []
    for item in code:
        if len(r) > 50:  # TODO: Remove this
            break
        if not "SourceCode" in item:
            continue
        content = item["SourceCode"]
        metadata = {}
        if "AdditionalSources" in item:
            metadata["additional_sources"] = [
                source["Filename"] for source in item["AdditionalSources"]
            ]

        if "FileName" in item:
            metadata["file_name"] = item["FileName"]
        if "Address" in item:
            metadata["address"] = item["Address"]

        if not metadata.get("file_name"):
            continue
        for section in data_split(content, ["\ncontract", "\nfunction", "\nmodifier", "\nevent", "\nstruct"], chunk_size, overlap):
            r.append({"content": section, "metadata": metadata,
                      "file_name": metadata["file_name"], "type": "code"})
    return r
