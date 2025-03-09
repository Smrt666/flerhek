import json
from pathlib import Path

import git
import structlog

logger = structlog.get_logger(__name__)
loc = Path(__file__).parent
data_files = loc.parent.parent / "data" / "files"


def read_settings():
    with open(data_files / "sources.json") as f:
        return json.load(f)


def update_sources() -> list[Path]:
    changed_files = []
    for source in read_settings():
        source_path = data_files / source["name"]
        branch = source.get("branch", "main")
        if not source_path.exists():
            repo = git.Repo.clone_from(source["url"], source_path)
            repo.git.checkout(branch)
            logger.info(f"Cloned {source['name']} from {source['url']}")
        else:
            repo = git.Repo(source_path)
            repo.git.checkout(branch)
            repo.remotes.origin.fetch()
            chs = repo.git.diff("--name-only", f"origin/{branch}")
            if chs:
                chs = chs.split("\n")
                changed_files.extend(chs)
                repo.remotes.origin.pull()
                logger.info(f"Pulled {source['name']} (Updated {len(chs)} files)")
    return changed_files


if __name__ == "__main__":
    print("Changed files:", *update_sources(), sep="\n")
