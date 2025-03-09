import yaml
import json
from pathlib import Path
import structlog
from flare_ai_rag.utils.splitter import data_split

logger = structlog.get_logger(__name__)


def get_data(file: Path, base_path: Path, overlap: int = 900) -> list[dict]:
    chunk_size = 10 * overlap
    r = []
    extension = file.suffix
    content = file.read_text()
    meta_data = {}
    file_name = file.relative_to(base_path).as_posix()

    if extension in (".mdx", ".md"):
        if content.startswith("---"):
            _, mdata, content = content.split("---", 2)
            meta_data.update(yaml.safe_load(mdata))
            content = content.strip()
        title = ""
        if content.startswith("# "):
            title, content = content.split("\n", 1)
            content = content.strip()
            title = title.lstrip("# ")
            meta_data["title"] = title
        for section in data_split(content, ["\n# ", "\n## ", "\n### "], chunk_size, overlap):
            r.append({"content": section, "meta_data": meta_data,
                     "file_name": file_name, "type": "answer"})
    elif extension in (".js", ".sol", ".py"):
        seps = {
            ".js": ["\nfunction", "\nclass", "\nconst", "\nlet", "\nvar"],
            ".sol": ["\ncontract", "\nfunction", "\nmodifier", "\nevent", "\nstruct"],
            ".py": ["\ndef", "\nclass"]
        }
        for section in data_split(content, seps[extension], chunk_size, overlap):
            r.append({"content": section, "meta_data": meta_data,
                    "file_name": file_name, "type": "code"})
    else:
        for section in data_split(content, [], chunk_size, overlap):
            r.append({"content": content, "meta_data": meta_data,
                    "file_name": file_name, "type": "answer"})
    rr = []
    for i in r:
        if len(i["content"]) < 30:
            continue
        if len(i["content"]) >= 20000:
            logger.warning(f"Content too long in file: {i['file_name']}")
            continue
        rr.append(i)
    return rr


def make_data(data_path: Path) -> None:
    logger.info("Reading data files...")
    data = []
    for file in data_path.glob("files/**/*"):
        if not file.is_file():
            continue
        logger.info(f"Reading file: {file.name}")
        try:
            data.extend(get_data(file, data_path))
        except Exception:
            logger.exception(f"Error reading document. filename={file.name}")
            continue

    with open(data_path / "data.json", "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Data written to data.json")


if __name__ == "__main__":
    make_data(Path(__file__).parent.parent.parent / "data")
