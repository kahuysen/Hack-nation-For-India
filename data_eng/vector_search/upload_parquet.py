"""Upload the local embedding artifact to a governed Unity Catalog Volume."""

import argparse
import subprocess
from pathlib import Path

from .config import settings
from .local_databricks import cli_executable, query_rows


def upload_embeddings(profile: str, source: Path) -> str:
    if not source.is_file():
        raise FileNotFoundError(source)
    query_rows(f"CREATE VOLUME IF NOT EXISTS {settings.volume_name}", profile)
    target = f"dbfs:{settings.staged_embeddings_path}"
    subprocess.run(
        [
            cli_executable(),
            "fs",
            "cp",
            str(source),
            target,
            "--overwrite",
            "--profile",
            profile,
        ],
        check=True,
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="codex")
    parser.add_argument("--input", type=Path, default=settings.embeddings_path)
    args = parser.parse_args()
    target = upload_embeddings(args.profile, args.input)
    print(f"Uploaded {args.input} to {target}")


if __name__ == "__main__":
    main()
