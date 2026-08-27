#!/usr/bin/env python3
import importlib.metadata
import json
import shutil
import sys


PACKAGES = ("torch", "transformers", "accelerate", "qwen-vl-utils", "decord")


def main() -> int:
    versions = {}
    missing = []
    for package in PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            missing.append(package)

    result = {
        "python": sys.version.split()[0],
        "packages": versions,
        "missing_packages": missing,
        "ffmpeg": shutil.which("ffmpeg"),
        "cuda_available": False,
    }
    if "torch" not in missing:
        import torch

        result["torch_cuda_version"] = torch.version.cuda
        result["cuda_available"] = torch.cuda.is_available()
        if result["cuda_available"]:
            props = torch.cuda.get_device_properties(0)
            result["gpu"] = props.name
            result["gpu_memory_gib"] = round(props.total_memory / 1024**3, 2)
            result["recommended"] = props.total_memory >= 12 * 1024**3

    result["ok"] = not missing and result["cuda_available"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
