#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import argparse
from pathlib import Path
import tempfile, shutil, os

# 針對 HTML 實體的佔位標籤：&lt;  ...  &gt;
ENTITY_TAG_PATTERN = re.compile(r"&lt;[\s\u3000]*([A-Z][A-Z0-9_]*)[\s\u3000]*&gt;")
# 針對真正尖括號的佔位標籤：<  ...  >
ANGLE_TAG_PATTERN  = re.compile(r"<[\s\u3000]*([A-Z][A-Z0-9_]*)[\s\u3000]*>")

def normalize_tags(text: str) -> str:
    # 先把 &lt; ... &gt; 轉成 <...>
    text = ENTITY_TAG_PATTERN.sub(lambda m: f"<{m.group(1)}>", text)
    # 再把 <  ...  > 裡的空白去掉
    text = ANGLE_TAG_PATTERN.sub(lambda m: f"<{m.group(1)}>", text)
    return text

def process_file(in_path: Path, out_path: Path):
    data = in_path.read_text(encoding="utf-8", errors="ignore")
    fixed = normalize_tags(data)
    out_path.write_text(fixed, encoding="utf-8")

def inplace_overwrite(path: Path):
    bak = path.with_suffix(path.suffix + ".bak")
    tmp_fd, tmp_name = tempfile.mkstemp(prefix="normalize_tags_", suffix=".tmp")
    os.close(tmp_fd)
    tmp = Path(tmp_name)
    try:
        shutil.copy2(path, bak)
        process_file(path, tmp)
        shutil.move(str(tmp), str(path))
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    print(f"[INPLACE] 覆寫完成：{path}（備份：{bak}）")

def main():
    ap = argparse.ArgumentParser(description="修正標籤空白與 HTML 實體：< PER > / &lt; PER &gt; → <PER>")
    ap.add_argument("-i", "--inplace", action="store_true", help="就地覆寫（會建立 .bak 備份）")
    ap.add_argument("input", nargs="?", help="輸入檔")
    ap.add_argument("output", nargs="?", help="輸出檔（未提供時預設為 <input>.normalized[.ext]）")
    args = ap.parse_args()

    if not args.input:
        p = input("請輸入檔案路徑：").strip()
        if not p:
            print("未提供檔案路徑。", file=sys.stderr); sys.exit(1)
        args.input = p

    in_path = Path(args.input).expanduser().resolve()
    if not in_path.is_file():
        print(f"找不到檔案：{in_path}", file=sys.stderr); sys.exit(1)

    if args.inplace:
        inplace_overwrite(in_path)
        return

    if args.output:
        out_path = Path(args.output).expanduser().resolve()
    else:
        out_path = (in_path.with_name(in_path.stem + ".normalized" + in_path.suffix)
                    if in_path.suffix else in_path.with_name(in_path.name + ".normalized"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    process_file(in_path, out_path)
    print(f"[WRITE] {in_path} -> {out_path}")

if __name__ == "__main__":
    if not sys.stdin.isatty() and len(sys.argv) == 1:
        sys.stdout.write(normalize_tags(sys.stdin.read()))
    else:
        main()
