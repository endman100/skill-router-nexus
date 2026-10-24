#!/usr/bin/env python3
"""以 Grok Build 收集角色圖片與來源網址。

最小權限（grok_headless.PROFILES["web"]）：Grok 在 <out>/.grok_collect_*/（空資料夾、沙箱 lora_min）
只用 web_search/web_fetch/read_file 找圖，以 structuredOutput 回傳圖片直連網址與來源頁；
無 shell、無寫檔、無子代理。圖片由本腳本下載（只收 http/https、需能被 PIL 開啟），
寫到 --out 並產生 sources.json（[{filename, source_url, image_url}]）。
"""
import argparse, hashlib, io, re, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image
from ws import parse_args
from codex_collect import make_prompt
from grok_headless import options, retry, report, write_json, entry, isolated_cwd

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["images"], "properties": {
    "images": {"type": "array", "maxItems": 300, "items": {
        "type": "object", "additionalProperties": False, "required": ["image_url", "source_url"],
        "properties": {"image_url": {"type": "string"}, "source_url": {"type": "string"}}}}}}
NOTE = ("用 web_search 找來源頁，再用 web_fetch 打開來源頁與圖片網址確認圖片確實存在且是目標角色；"
        "不要憑記憶或猜測拼出網址，沒有實際 fetch 確認過的網址不要回傳。"
        "不要存檔（沒有寫檔或 shell 工具）：以 structuredOutput.images 回傳每張圖的直連圖片網址 image_url"
        "（指向 .png/.jpg/.webp 等圖片檔，盡量用原尺寸）與找到它的頁面 source_url，由腳本下載。")
MAX_BYTES = 40 * 1024 * 1024
KEEP = {"logs", "summary.json", "failed.json"}


def has_urls(result):
    if not result["structured"]["images"]:
        raise ValueError("No image URLs returned")
    return result


def download(url, folder, number, hashes):
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise ValueError("not an http(s) URL")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (lora-collect)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("file too large")
    digest = hashlib.sha256(data).hexdigest()
    if digest in hashes:
        raise ValueError(f"duplicate of {hashes[digest]}")
    with Image.open(io.BytesIO(data)) as im:
        im.verify()
        kind = (im.format or "png").lower()
    ext = {"jpeg": "jpg"}.get(kind, kind)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(urllib.parse.urlsplit(url).path).stem)[:60] or "image"
    target = folder / f"{number:03d}_{stem}.{ext}"
    with target.open("xb") as handle:
        handle.write(data)
    hashes[digest] = target.name
    return target


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--query", required=True)
    p.add_argument("--out", type=Path, required=True)
    options(p)
    a = parse_args(p, "grok_collect", argv)
    if a.out.exists() and any(f.name not in KEEP and not f.name.startswith(".grok_") for f in a.out.iterdir()):
        raise ValueError(f"Destination is not empty: {a.out}")
    prompt = make_prompt(a.query).split("\n\n")[0] + "\n\n" + NOTE
    if a.dry_run:
        print(f"{prompt}\nprofile=web (web_search/web_fetch/read_file, dontAsk, lora_min); destination={a.out}; retries={a.retries}")
        return 0
    with isolated_cwd(a.out, "collect") as work:
        result, error = retry(prompt, work, a.out / "logs", "collect", a, schema=SCHEMA, profile="web",
                              accept=has_urls)
    rec = dict(name="collect", ok=False, error=error)
    if result:
        sources, failures, seen, hashes = [], [], set(), {}
        for item in result["structured"]["images"]:
            url = item["image_url"]
            if url in seen:
                continue
            seen.add(url)
            try:
                path = download(url, a.out, len(sources) + 1, hashes)
                sources.append(dict(filename=path.name, source_url=item["source_url"], image_url=url))
            except (OSError, ValueError) as exc:
                failures.append(dict(image_url=url, source_url=item["source_url"], error=str(exc)[:200]))
        write_json(a.out / "sources.json", sources)
        write_json(a.out / "download_failed.json", failures)
        rec.update(ok=bool(sources), images_copied=len(sources), download_failed=len(failures),
                   error=None if sources else "No image could be downloaded")
    return report(a.out, [rec])


if __name__ == "__main__":
    raise SystemExit(entry(main))
