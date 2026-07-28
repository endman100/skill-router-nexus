#!/usr/bin/env python3
"""Copy the bundled box-motion HyperFrames template to a new project path."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a project from the bundled box-motion template."
    )
    parser.add_argument("output", type=Path, help="New project directory")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    template = skill_dir / "assets" / "templates" / "box-motion-hyperframes"
    output = args.output.expanduser().resolve()

    if not template.is_dir():
        raise SystemExit(f"Bundled template not found: {template}")
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing path: {output}")

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, output)

    project_name = output.name
    for filename in ("package.json", "meta.json"):
        path = output / filename
        data = json.loads(path.read_text(encoding="utf-8"))
        data["name"] = project_name
        if filename == "meta.json":
            data["id"] = project_name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Created box-motion project: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
