#!/usr/bin/env bash
# 將 ~/translation-corpus/zh-id/data/<model_name>/ 下的
# train.{zh,id}, valid.{zh,id}, test.{zh,id} 做 < PER > -> <PER> 的標籤還原
# 依賴：~/translation-corpus/zh-id/utils/fix_tags.py

set -euo pipefail

BASE="$HOME/translation-corpus/zh-id"
DATA_DIR="$BASE/data"
UTILS_DIR="$BASE/utils"
PY_FIX="$UTILS_DIR/fix_tags.py"

src="zh"     # src 必須是中文
tgt="id"

usage() {
  cat <<EOF
用法：
  $(basename "$0") <model_name> [-i] [--suffix .normalized]

說明：
  - 會在 $DATA_DIR/<model_name>/ 底下尋找 train/valid/test 的 zh/id 檔案
  - 預設輸出新檔：train.zh -> train.normalized.zh
  - 指定 -i 則就地覆寫（會建立 .bak 備份）

參數：
  -i                 就地覆寫（in-place）
  --suffix <string>  非就地模式的輸出後綴（預設：.normalized）

範例：
  $(basename "$0") my_corpus
  $(basename "$0") my_corpus --suffix .fix
  $(basename "$0") my_corpus -i
EOF
}

# 參數解析
model_name="${1:-}"
[[ -z "$model_name" ]] && { usage; exit 1; }

inplace="0"
suffix=".normalized"
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    -i) inplace="1"; shift ;;
    --suffix)
      [[ $# -lt 2 ]] && { echo "缺少 --suffix 參數值" >&2; exit 1; }
      suffix="$2"; shift 2 ;;
    *) echo "未知參數：$1" >&2; usage; exit 1 ;;
  esac
done

# 檢查環境
[[ "$src" != "zh" ]] && { echo "錯誤：src 必須是 zh，現在是：$src" >&2; exit 1; }
[[ -f "$PY_FIX" ]] || { echo "找不到 Python 腳本：$PY_FIX" >&2; exit 1; }

TARGET_DIR="$DATA_DIR/$model_name"
[[ -d "$TARGET_DIR" ]] || { echo "找不到資料夾：$TARGET_DIR" >&2; exit 1; }

echo "[INFO] 目標資料夾：$TARGET_DIR"
echo "[INFO] 模式：$([[ "$inplace" == "1" ]] && echo "就地覆寫" || echo "輸出新檔（後綴：$suffix）")]"
echo

process_one() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "[SKIP] 不存在：$f"
    return 0
  fi

  if [[ "$inplace" == "1" ]]; then
    echo "[INPLACE] 處理：$f"
    python3 "$PY_FIX" --inplace "$f"
  else
    local dir base stem ext out
    dir="$(dirname "$f")"
    base="$(basename "$f")"
    stem="${base%.*}"
    if [[ "$base" == *.* ]]; then
      ext=".${base##*.}"
      out="${dir}/${stem}${suffix}${ext}"
    else
      out="${dir}/${base}${suffix}"
    fi
    echo "[WRITE] $f -> $out"
    python3 "$PY_FIX" "$f" "$out"
  fi
}

splits=(train valid test)
langs=("$src" "$tgt")

for s in "${splits[@]}"; do
  for l in "${langs[@]}"; do
    process_one "$TARGET_DIR/${s}.${l}"
  done
done

echo
echo "[DONE] 標籤還原完成。"
