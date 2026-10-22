#!/usr/bin/env python3
"""打標 JSON → txt（與原 repo 完全相同的轉換，另加實跑已使用的 drop_empty）。

步驟：drop_empty（去掉空字串值與陣列中的空字串）→ 刪 detailed_description → json_to_string
→ merge_all_caption([only_prefix(['anime style', <trigger>]), 上一步結果])（內含 recreate_tags_format 去重）。
txt 以 `anime style, <trigger>, ` 開頭。不做其他過濾。
codex_caption_v2.py 使用本檔；也可單獨重轉一個資料夾的 JSON：

  python3 caption_convert.py <json資料夾> <txt輸出資料夾> --trigger <trigger> [--stage-out <stage_txt資料夾>]
"""
import argparse, json, sys
from pathlib import Path


def json_to_string(json_data):
    """LLM_checker.json_to_string（原樣）：list 展開、str 加入、其他型別略過。"""
    return_tags = []
    for key, value_list in json_data.items():
        if isinstance(value_list, list):
            return_tags += value_list[:]
        elif isinstance(value_list, str):
            return_tags.append(value_list)
    return ", ".join(return_tags)


def only_prefix(prompt_list):
    """add_prefix.only_prefix 的第一行（原樣）。"""
    first_line = ""
    for prompt in prompt_list:
        first_line += prompt if "." in prompt else prompt + ","
    return first_line + "\n"


def recreate_tags_format(s):
    """add_prefix.recreate_tags_format（原樣）。"""
    s = s.replace("，", ",").replace('"', "").replace("'", "").replace(".", "").strip()
    valid_tags = [tag.strip() for tag in s.split(",") if len(tag.strip()) > 0]
    valid_tags = list(dict.fromkeys(valid_tags))
    return ", ".join(valid_tags)


def merge_all_caption(parts):
    """add_prefix.merge_all_caption（單一檔案；parts = 依資料夾順序的內容）。"""
    caption_list = [p.strip() for p in parts if len(p) > 0]
    return recreate_tags_format(",".join(caption_list))


def drop_empty(data):
    """去掉空字串值（"" 與陣列中的 ""），避免多餘逗號。實跑已使用。"""
    out = {}
    for k, v in data.items():
        if isinstance(v, list):
            out[k] = [x for x in v if not (isinstance(x, str) and not x.strip())]
        elif isinstance(v, str) and not v.strip():
            continue
        else:
            out[k] = v
    return out


def stage_txt(data):
    """Qwen3-VL inference.process_image：刪 detailed_description → json_to_string。"""
    d = dict(data); d.pop("detailed_description", None)
    return json_to_string(d)


def final_txt(data, trigger):
    return merge_all_caption([only_prefix(["anime style", trigger]), stage_txt(data)])


def convert(data, trigger):
    """回傳 (stage_txt, final_txt)；data 為 Codex 輸出的 JSON dict。"""
    clean = drop_empty(data)
    return stage_txt(clean), final_txt(clean, trigger)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("json_dir", type=Path)
    p.add_argument("txt_out", type=Path)
    p.add_argument("--trigger", required=True)
    p.add_argument("--stage-out", type=Path)
    a = p.parse_args(argv)
    a.txt_out.mkdir(parents=True, exist_ok=True)
    if a.stage_out:
        a.stage_out.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(a.json_dir.glob("*.json")):
        stage, final = convert(json.loads(f.read_text("utf-8-sig")), a.trigger)
        (a.txt_out / f"{f.stem}.txt").write_text(final, "utf-8")
        if a.stage_out:
            (a.stage_out / f"{f.stem}.txt").write_text(stage, "utf-8")
        n += 1
    print(f"{n} txt -> {a.txt_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
