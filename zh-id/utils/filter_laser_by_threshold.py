#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
讀取 LASER 輸出的 similarity.tsv，將 cosine 分數 > threshold 的句對
輸出成兩個檔案（.id / .zh）。
"""

import argparse
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True, help="Path to similarity.tsv")
    ap.add_argument("--threshold", type=float, default=0.6, help="Keep pairs with cosine > threshold (default 0.6)")
    ap.add_argument("--out_id", required=True, help="Output file path for filtered.id")
    ap.add_argument("--out_zh", required=True, help="Output file path for filtered.zh")
    args = ap.parse_args()

    sim_path = Path(args.sim)
    out_id = Path(args.out_id)
    out_zh = Path(args.out_zh)
    out_id.parent.mkdir(parents=True, exist_ok=True)
    out_zh.parent.mkdir(parents=True, exist_ok=True)

    kept = 0
    total = 0

    with sim_path.open("r", encoding="utf-8") as f, \
         out_id.open("w", encoding="utf-8") as fid, \
         out_zh.open("w", encoding="utf-8") as fzh:
        header = f.readline()  # idx\tcosine\tid_sentence\tzh_sentence
        for line in f:
            total += 1
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            try:
                score = float(parts[1])
            except ValueError:
                continue
            if score > args.threshold:
                fid.write(parts[2] + "\n")
                fzh.write(parts[3] + "\n")
                kept += 1

    print(f"[DONE] total={total}, kept(score>{args.threshold})={kept}")
    print(f"[OUT] {out_id}")
    print(f"[OUT] {out_zh}")

if __name__ == "__main__":
    main()
