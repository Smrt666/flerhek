import yaml
import json
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)


def get_data(file: Path, base_path: Path) -> list[dict]:
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
        if "\n## " in content:
            for i, section in enumerate(content.split("\n## ")):
                if not section:
                    continue
                if i == 0 and not content.startswith("\n##"):
                    section_content = section.strip()
                else:
                    section_content = section.strip()

                if section_content.startswith("<") and section_content.endswith(">"):
                    continue

                if r and len(r[-1]["content"]) + len(section_content) < 5000:
                    r[-1]["content"] += "\n\n" + section_content
                else:
                    section_content = meta_data.get("title", "") + "\n\n" + section_content
                    r.append({"content": section_content.strip(), "file_name": file_name,
                             "meta_data": meta_data, "type": "answer"})
        else:
            r.append({"content": content, "meta_data": meta_data,
                     "file_name": file_name, "type": "answer"})
    elif extension in (".js", ".sol", ".py"):
        r.append({"content": content, "meta_data": meta_data,
                 "file_name": file_name, "type": "code"})
    else:
        r.append({"content": content, "meta_data": meta_data,
                 "file_name": file_name, "type": "answer"})
    rr = []
    for i in r:
        if len(i["content"]) < 30:
            continue
        if len(i["content"]) > 10000:
            logger.warning(f"Content too long in file: {i['file_name']}")
            continue
        rr.append(i)
    return rr


def make_data(data_path: Path) -> None:
    logger.info("Reading data files...")
    data = []
    for file in data_path.rglob("*"):
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
    path = input("Specify path to data.json parent folder: ")
    make_data(Path(path))
