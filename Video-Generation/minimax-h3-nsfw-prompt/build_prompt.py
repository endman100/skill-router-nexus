#!/usr/bin/env python3
"""Compose the final MiniMax H3 pic1ref prompt from template.txt and a vars JSON.

Usage: python3 build_prompt.py vars.json [-o out.txt] [-t template.txt]
vars.json holds the 13 variables, e.g. {"female_appearance": "...", "background": "...", ...}.
Fails if a template variable is missing or empty, or if vars.json has unknown keys.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VAR = re.compile(r"\{\{(\w+)\}\}")

def build(template, values):
    need = set(VAR.findall(template))
    missing = sorted(k for k in need if not str(values.get(k, "")).strip())
    unknown = sorted(set(values) - need)
    if missing or unknown:
        sys.exit(f"missing/empty: {missing}  unknown: {unknown}")
    return VAR.sub(lambda m: str(values[m.group(1)]).strip(), template)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vars")
    ap.add_argument("-t", "--template", default=os.path.join(HERE, "template.txt"))
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    template = open(a.template, encoding="utf-8").read()
    values = json.load(open(a.vars, encoding="utf-8"))
    prompt = build(template, values)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(prompt)
    else:
        sys.stdout.write(prompt)

if __name__ == "__main__":
    main()
