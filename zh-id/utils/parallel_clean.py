#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
parallel_clean.py
- 讀取: 當前工作目錄下 raw.zh, raw.id（與 clean_parallel.sh 相容）
- 規則:
  1) zh 只要含英文字母(A-Z/a-z) 或 數字(含全形 ０-９) → 丟棄整句對
  2) id 只要含數字(含全形 ０-９) → 丟棄整句對
  3) 兩側都刪除所有標點符號（Unicode P* 類別），但保留 <PER> 等 angle-bracket 標籤
- 輸出: clean.zh, clean.id
"""

import os
import re
import sys
import unicodedata
from typing import List, Tuple

RAW_ZH = "raw.zh"
RAW_ID = "raw.id"
OUT_ZH = "clean.zh"
OUT_ID = "clean.id"

# 規則偵測（半/全形數字都涵蓋）
RE_HAS_EN_OR_DIGIT_ZH = re.compile(r"[A-Za-z0-9\uFF10-\uFF19]")
RE_HAS_DIGIT_ID = re.compile(r"[0-9\uFF10-\uFF19]")

# 將 < PER > 類型鬆散標籤壓成 <PER>
TAG_TOLERANT = re.compile(r"<\s*([A-Za-z][A-Za-z0-9_]*)\s*>")

# 嚴格標籤（壓縮後的）形式：<PER>、<TIM_1>、<QTY12> ...
TAG_STRICT = re.compile(r"<[A-Za-z][A-Za-z0-9_]*>")

def normalize_compact_tags(s: str) -> str:
    return TAG_TOLERANT.sub(lambda m: f"<{m.group(1)}>", s)

def protect_tags(s: str) -> Tuple[str, List[str], List[str]]:
    """
    把 <TAG> 先換成 __TAGk__ 以避免被標點清洗影響。
    回傳 (被保護的字串, placeholders, 原標籤列表)
    """
    tags: List[str] = []
    placeholders: List[str] = []

    def _repl(m):
        idx = len(tags)
        tags.append(m.group(0))           # 如 <PER>
        ph = f"__TAG{idx}__"
        placeholders.append(ph)
        return ph

    protected = TAG_STRICT.sub(_repl, s)
    return protected, placeholders, tags

def restore_tags(s: str, placeholders: List[str], tags: List[str]) -> str:
    for ph, tg in zip(placeholders, tags):
        s = s.replace(ph, tg)
    return s

def remove_all_punct(s: str) -> str:
    """
    刪除所有 Unicode 標點（P* 類別）。角括號本身屬標點，但我們已先保護標籤。
    """
    out = []
    for ch in s:
        if not unicodedata.category(ch).startswith("P"):
            out.append(ch)
    return "".join(out)

def normalize_spaces(s: str) -> str:
    s = re.sub(r"\s+", " ", s)  # 多空白壓一個
    return s.strip()

def clean_text_preserve_tags(s: str) -> str:
    # 1) 標籤壓縮（< PER > -> <PER>）
    s = normalize_compact_tags(s)
    # 2) 保護標籤
    protected, placeholders, tags = protect_tags(s)
    # 3) 刪除標點
    no_punct = remove_all_punct(protected)
    # 4) 還原標籤
    restored = restore_tags(no_punct, placeholders, tags)
    # 5) 空白正規化
    return normalize_spaces(restored)

def main():
    if not (os.path.isfile(RAW_ZH) and os.path.isfile(RAW_ID)):
        print("[ERR] 找不到 raw.zh 或 raw.id，請在含有這兩個檔案的資料夾內執行。", file=sys.stderr)
        sys.exit(1)

    # 先看行數（若不相同會提示，但仍以 zip 對齊較短端）
    with open(RAW_ZH, "r", encoding="utf-8") as f:
        zh_lines_total = sum(1 for _ in f)
    with open(RAW_ID, "r", encoding="utf-8") as f:
        id_lines_total = sum(1 for _ in f)
    if zh_lines_total != id_lines_total:
        print(f"[WARN] 行數不一致：raw.zh={zh_lines_total}, raw.id={id_lines_total}；將以較短的一側對齊處理。", file=sys.stderr)

    kept = 0
    dropped = 0
    checked = 0

    with open(RAW_ZH, "r", encoding="utf-8") as fzh, \
         open(RAW_ID, "r", encoding="utf-8") as fid, \
         open(OUT_ZH, "w", encoding="utf-8") as ozh, \
         open(OUT_ID, "w", encoding="utf-8") as oid:

        for zh, id_ in zip(fzh, fid):
            checked += 1
            zh = zh.rstrip("\n").strip()
            id_ = id_.rstrip("\n").strip()

            # 規則 1：zh 含英文或數字 -> 丟棄整句對
            if RE_HAS_EN_OR_DIGIT_ZH.search(zh):
                dropped += 1
                continue

            # 規則 2：id 含數字 -> 丟棄整句對
            if RE_HAS_DIGIT_ID.search(id_):
                dropped += 1
                continue

            # 規則 3：移除標點但保留 <TAG>
            zh_clean = clean_text_preserve_tags(zh)
            id_clean = clean_text_preserve_tags(id_)

            # 避免空行輸出
            if not zh_clean or not id_clean:
                dropped += 1
                continue

            ozh.write(zh_clean + "\n")
            oid.write(id_clean + "\n")
            kept += 1

    print(f"[INFO] 已檢查句對：{checked}")
    print(f"[OK]   保留句對：{kept}")
    print(f"[DROP] 丟棄句對：{dropped}")
    print(f"[OUT]  {OUT_ZH}, {OUT_ID}")

if __name__ == "__main__":
    main()
