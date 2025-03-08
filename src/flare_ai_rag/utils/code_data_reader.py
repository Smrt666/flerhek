from pathlib import Path
import json


def get_code_data(file: Path):
    with open(file, "r") as f:
        code = json.load(f)

    r = []
    for item in code:
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
        r.append({"content": content, "metadata": metadata,
                 "file_name": metadata["file_name"], "type": "code"})
    return r
