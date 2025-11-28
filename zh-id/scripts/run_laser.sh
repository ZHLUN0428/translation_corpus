#!/usr/bin/env bash
# run_laser.sh  (folder-name + fixed absolute paths, fairseq-like GPU picking, chunking & merge, overwrite + custom chunk size)
# 用法：
#   ./run_laser.sh <folder_name> [選項...]
# 例：
#   ./run_laser.sh my_corpus --gpus all --remove_tags --batch 512
#   ./run_laser.sh my_corpus --gpus 0,2 --batch 512
#   ./run_laser.sh my_corpus --device cpu
#   ./run_laser.sh my_corpus --device cuda
#   ./run_laser.sh my_corpus --chunk 200000   # 每片 20 萬行
#
# 本版功能：
# - 以每 CHUNK_SIZE 行切片（id/zh 對齊），逐片呼叫 laser_run.py
# - 各片輸出到 OUT_DIR/chunk_XX，完成後合併 *.tsv/*.csv 到 OUT_DIR/merged/
# - 支援 --overwrite：若 OUT_DIR 已存在則刪除重建；每片資料夾亦會先刪後建避免殘留
# - 預設於每片完成後刪除 .npy/.npz 以節省磁碟（如需保留加 --keep_emb）
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "用法：$0 <folder_name> [選項...]"
  echo "例：  $0 my_corpus --gpus all --remove_tags"
  exit 1
fi

FOLDER_NAME="$1"
shift || true

# === 固定根路徑 ===
BASE_DATA_DIR="/home/mi2s/translation-corpus/zh-id/data"
BASE_MODEL_DIR="/home/mi2s/translation-corpus/zh-id/models"
PY_SCRIPT="/home/mi2s/translation-corpus/zh-id/utils/laser_run.py"

DATA_DIR="${BASE_DATA_DIR}/${FOLDER_NAME}"
OUT_DIR_DEFAULT="${BASE_MODEL_DIR}/${FOLDER_NAME}/laser_out"

# 預設參數（可被選項覆寫）
OUT_DIR="$OUT_DIR_DEFAULT"
ID_LANG="ind_Latn"
ZH_LANG="zho_Hant"
DEVICE="auto"         # auto | cpu | cuda
GPUS_ARG="all"        # all | 0,1,2
BATCH=256
REMOVE_TAGS=0
WRITE_NN=0
NN_CHUNK=0
THRESHOLDS="0.6,0.7,0.8,0.9"
MAX_LINES=0           # 若 >0，僅用前 N 行（會作用在切片前）
ETA_ONLY=0
OVERWRITE=0           # 1=清空 OUT_DIR 後重建
CHUNK_SIZE=1000000     # 預設每片 200,000 行（較安全）
KEEP_EMB=0            # 1=保留嵌入檔；0=每片完成即刪除 .npy/.npz

# 解析可選參數
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT_DIR="$2"; shift 2;;
    --id_lang) ID_LANG="$2"; shift 2;;
    --zh_lang) ZH_LANG="$2"; shift 2;;
    --device) DEVICE="$2"; shift 2;;
    --gpus) GPUS_ARG="$2"; shift 2;;
    --batch) BATCH="$2"; shift 2;;
    --remove_tags) REMOVE_TAGS=1; shift 1;;
    --nn) WRITE_NN=1; shift 1;;
    --nn_chunk) NN_CHUNK="$2"; shift 2;;
    --thresholds) THRESHOLDS="$2"; shift 2;;
    --max) MAX_LINES="$2"; shift 2;;
    --eta_only) ETA_ONLY=1; shift 1;;
    --overwrite) OVERWRITE=1; shift 1;;
    --chunk) CHUNK_SIZE="$2"; shift 2;;
    --chunk_size) CHUNK_SIZE="$2"; shift 2;;
    --keep_emb) KEEP_EMB=1; shift 1;;
    -h|--help)
      cat <<'EOF'
用法：run_laser.sh <folder_name> [選項...]
  固定路徑：
    DATA_DIR  = /home/mi2s/translation-corpus/zh-id/data/<folder_name>
    OUT_DIR   = /home/mi2s/translation-corpus/zh-id/models/<folder_name>/laser_out  (可用 --out 覆寫)
  GPU 選項（fairseq 風格）：
    --gpus all|0,1,2
    --device auto|cpu|cuda
  其他選項：
    --out DIR
    --id_lang CODE
    --zh_lang CODE
    --batch N
    --remove_tags
    --nn
    --nn_chunk N
    --thresholds a,b,c
    --max N              僅處理前 N 行（在切片前截斷）
    --eta_only           只估時不產出檔案（仍會逐片跑，但 python 端不寫出）
    --overwrite          若 OUT_DIR 已存在則先刪除後重建（覆蓋）
    --chunk N            每個切片的行數（預設 200000）
    --chunk_size N       與 --chunk 相同
    --keep_emb           不自動刪除每片輸出的 .npy/.npz（預設不保留會刪除）
EOF
      exit 0;;
    *) echo "[ERROR] Unknown option: $1"; exit 1;;
  esac
done

# 參數檢查：CHUNK_SIZE
if ! [[ "$CHUNK_SIZE" =~ ^[0-9]+$ ]] || [[ "$CHUNK_SIZE" -le 0 ]]; then
  echo "[ERROR] --chunk / --chunk_size 必須為 > 0 的整數（目前：$CHUNK_SIZE）"
  exit 1
fi

# 檢查資料夾與 Python 腳本
[[ -d "$DATA_DIR" ]] || { echo "[ERROR] 資料夾不存在：$DATA_DIR"; exit 1; }
[[ -f "$PY_SCRIPT" ]] || { echo "[ERROR] 找不到 Python 腳本：$PY_SCRIPT"; exit 1; }

# === fairseq-like：處理 --gpus → CUDA_VISIBLE_DEVICES ===
if [[ "$GPUS_ARG" != "all" ]]; then
  export CUDA_VISIBLE_DEVICES="$GPUS_ARG"
  echo "[INFO] CUDA_VISIBLE_DEVICES set to: $CUDA_VISIBLE_DEVICES"
else
  unset CUDA_VISIBLE_DEVICES || true
  echo "[INFO] CUDA_VISIBLE_DEVICES: (all visible)"
fi

# === auto 模式：偵測 torch.cuda 是否可用，決定 --device ===
if [[ "$DEVICE" == "auto" ]]; then
  CUDA_OK="$(python - <<'PY' 2>/dev/null || echo "False")"
import sys
try:
    import torch
    print("True" if torch.cuda.is_available() else "False")
except Exception:
    print("False")
PY
  if [[ "$CUDA_OK" == "True" ]]; then
    DEVICE="cuda"
    echo "[INFO] Auto device: cuda"
  else
    DEVICE="cpu"
    echo "[INFO] Auto device: cpu"
  fi
fi

# 在資料夾中尋找 raw.id / raw.zh 的 helper
pick_file() {
  local pattern="$1"
  local base="$2"
  if [[ -f "$base/$pattern" ]]; then
    echo "$base/$pattern"; return 0
  fi
  local hit
  if hit=$(find "$base" -type f -iname "$pattern" -print -quit 2>/dev/null); then
    [[ -n "${hit:-}" ]] && { echo "$hit"; return 0; }
  fi
  return 1
}

ID_PATH=""; ZH_PATH=""
# 找 raw.id
if ID_PATH=$(pick_file "raw.id" "$DATA_DIR"); then :; else
  if ID_PATH=$(find "$DATA_DIR" -type f -iname "*.id" -print -quit 2>/dev/null); then
    echo "[WARN] 未找到 raw.id，改用第一個 *.id：$ID_PATH"
  else
    echo "[ERROR] 找不到 raw.id（或 *.id）於：$DATA_DIR"; exit 1
  fi
fi
# 找 raw.zh
if ZH_PATH=$(pick_file "raw.zh" "$DATA_DIR"); then :; else
  if ZH_PATH=$(find "$DATA_DIR" -type f -iname "*.zh" -print -quit 2>/dev/null); then
    echo "[WARN] 未找到 raw.zh，改用第一個 *.zh：$ZH_PATH"
  else
    echo "[ERROR] 找不到 raw.zh（或 *.zh）於：$DATA_DIR"; exit 1
  fi
fi

echo "[INFO] DATA_DIR: $DATA_DIR"
echo "[INFO] OUT_DIR : $OUT_DIR"
echo "[INFO] ID      : $ID_PATH"
echo "[INFO] ZH      : $ZH_PATH"
echo "[INFO] DEVICE  : $DEVICE"
echo "[INFO] CHUNK_SIZE : $CHUNK_SIZE"

# 依賴檢查
python - <<'PY'
import importlib, sys
for mod in ("laser_encoders","numpy","tqdm"):
    try:
        importlib.import_module(mod)
    except Exception:
        print(f"[MISSING] {mod} not found. Please: pip install {mod}", file=sys.stderr)
        sys.exit(3)
print("[OK] deps found")
PY

# === 準備暫存與輸出結構（支援覆蓋） ===
if [[ "$OVERWRITE" -eq 1 ]]; then
  if [[ -n "${OUT_DIR:-}" && "$OUT_DIR" != "/" ]]; then
    echo "[INFO] --overwrite 啟用，清理輸出資料夾：$OUT_DIR"
    rm -rf -- "$OUT_DIR"
  else
    echo "[ERROR] OUT_DIR 非法（空或 /），中止以避免誤刪。"; exit 1
  fi
fi
mkdir -p "$OUT_DIR"

CHUNK_DIR="$OUT_DIR/chunks_src"
MERGED_DIR="$OUT_DIR/merged"
mkdir -p "$CHUNK_DIR" "$MERGED_DIR"

# 產生新切片前，先移除舊切片殘留（避免混入）
rm -f -- "$CHUNK_DIR"/id.part* "$CHUNK_DIR"/zh.part* "$CHUNK_DIR"/raw.id.head "$CHUNK_DIR"/raw.zh.head 2>/dev/null || true

# === 如 --max > 0，先各自截斷（確保行對齊） ===
ID_SRC="$ID_PATH"
ZH_SRC="$ZH_PATH"
if [[ "$MAX_LINES" -gt 0 ]]; then
  echo "[INFO] --max=$MAX_LINES 啟用，先截斷來源檔"
  ID_SRC="$CHUNK_DIR/raw.id.head"
  ZH_SRC="$CHUNK_DIR/raw.zh.head"
  head -n "$MAX_LINES" "$ID_PATH" > "$ID_SRC"
  head -n "$MAX_LINES" "$ZH_PATH" > "$ZH_SRC"
fi

# === 行數檢查 ===
N_ID=$(wc -l < "$ID_SRC")
N_ZH=$(wc -l < "$ZH_SRC")
if [[ "$N_ID" -ne "$N_ZH" ]]; then
  echo "[ERROR] 行數不一致：id=$N_ID, zh=$N_ZH"
  exit 1
fi
echo "[INFO] 總行數：$N_ID"

# === 切片（自訂大小） ===
LINES_PER_CHUNK="$CHUNK_SIZE"
NUM_CHUNKS=$(( (N_ID + LINES_PER_CHUNK - 1) / LINES_PER_CHUNK ))

# 至少兩位數更整齊（01, 02, ...）；也可改回 ${#NUM_CHUNKS}
SUFFIX_WIDTH=$(( ${#NUM_CHUNKS} < 2 ? 2 : ${#NUM_CHUNKS} ))
printf -v FMT "%%0%dd" "$SUFFIX_WIDTH"

echo "[INFO] 開始切片：每片 $LINES_PER_CHUNK 行，共 $NUM_CHUNKS 片"

NEED_NORMALIZE=0
if split --help 2>&1 | grep -q -- '--numeric-suffixes'; then
  # GNU coreutils：直接產生零填充後綴，避免事後改名
  split -d -l "$LINES_PER_CHUNK" --numeric-suffixes=0 --suffix-length="$SUFFIX_WIDTH" \
    "$ID_SRC" "$CHUNK_DIR/id.part"
  split -d -l "$LINES_PER_CHUNK" --numeric-suffixes=0 --suffix-length="$SUFFIX_WIDTH" \
    "$ZH_SRC" "$CHUNK_DIR/zh.part"
else
  # BusyBox 等：先切再正規化
  split -d -l "$LINES_PER_CHUNK" "$ID_SRC" "$CHUNK_DIR/id.part"
  split -d -l "$LINES_PER_CHUNK" "$ZH_SRC" "$CHUNK_DIR/zh.part"
  NEED_NORMALIZE=1
fi

# 後綴正規化（僅在 NEED_NORMALIZE=1 時執行）
normalize_suffixes() {
  local prefix="$1"
  for f in "$prefix"*; do
    [[ -f "$f" ]] || continue
    local suf="${f##*$prefix}"
    [[ "$suf" =~ ^[0-9]+$ ]] || continue
    local newsuf
    printf -v newsuf "$FMT" "$suf"
    local target="${prefix}${newsuf}"
    [[ "$f" == "$target" ]] && continue
    mv -f -- "$f" "$target"
  done
}
if [[ "$NEED_NORMALIZE" -eq 1 ]]; then
  normalize_suffixes "$CHUNK_DIR/id.part"
  normalize_suffixes "$CHUNK_DIR/zh.part"
fi

# 確認所有 id/zh 分片數相同且對齊（null-safe）
readarray -d '' -t ID_PARTS < <(find "$CHUNK_DIR" -maxdepth 1 -type f -name 'id.part*' -print0 | sort -z)
readarray -d '' -t ZH_PARTS < <(find "$CHUNK_DIR" -maxdepth 1 -type f -name 'zh.part*' -print0 | sort -z)
if [[ "${#ID_PARTS[@]}" -ne "${#ZH_PARTS[@]}" || "${#ID_PARTS[@]}" -eq 0 ]]; then
  echo "[ERROR] 分片數不一致或為 0：id=${#ID_PARTS[@]} zh=${#ZH_PARTS[@]}"
  exit 1
fi

# === 逐片執行 laser_run.py ===
for ((i=0; i<${#ID_PARTS[@]}; i++)); do
  ID_CHUNK="${ID_PARTS[$i]}"
  ZH_CHUNK="${ZH_PARTS[$i]}"
  SUF="${ID_CHUNK##*id.part}"   # e.g., 00, 01, ...
  OUT_CHUNK_DIR="$OUT_DIR/chunk_${SUF}"
  rm -rf -- "$OUT_CHUNK_DIR"
  mkdir -p "$OUT_CHUNK_DIR"

  echo "[INFO] === 處理分片 #$((i+1))/${#ID_PARTS[@]} (suffix=$SUF) ==="
  echo "[INFO]   id: $ID_CHUNK"
  echo "[INFO]   zh: $ZH_CHUNK"
  echo "[INFO]   out: $OUT_CHUNK_DIR"

  python "$PY_SCRIPT" \
    --id "$ID_CHUNK" \
    --zh "$ZH_CHUNK" \
    --out_dir "$OUT_CHUNK_DIR" \
    --id_lang "$ID_LANG" \
    --zh_lang "$ZH_LANG" \
    --device "$DEVICE" \
    --batch_size "$BATCH" \
    $( [[ "$REMOVE_TAGS" == "1" ]] && echo --remove_tags ) \
    $( [[ "$WRITE_NN" == "1" ]] && echo --write_nn ) \
    --nn_chunk "$NN_CHUNK" \
    --thresholds "$THRESHOLDS" \
    --max_lines 0 \
    $( [[ "$ETA_ONLY" == "1" ]] && echo --eta_only )

  # === 清理本片的嵌入大檔，避免 / 爆空間 ===
  if [[ "$KEEP_EMB" -eq 0 ]]; then
    echo "[INFO]  清理 chunk_${SUF} 內的 .npy/.npz 以釋放空間"
    to_free_bytes=$(
      find "$OUT_CHUNK_DIR" -maxdepth 1 -type f \( -name '*.npy' -o -name '*.npz' \) -printf '%s\n' 2>/dev/null \
      | awk '{s+=$1} END{print s+0}'
    )
    find "$OUT_CHUNK_DIR" -maxdepth 1 -type f \( -name '*.npy' -o -name '*.npz' \) -print -exec rm -f -- {} + 2>/dev/null || true
    if [[ "${to_free_bytes:-0}" -gt 0 ]]; then
      if command -v numfmt >/dev/null 2>&1; then
        human="$(numfmt --to=iec "${to_free_bytes}")"
        echo "[INFO]  已釋放：$human"
      else
        echo "[INFO]  已釋放：${to_free_bytes} bytes"
      fi
    else
      echo "[INFO]  沒有需要清理的 .npy/.npz"
    fi
  else
    echo "[INFO]  --keep_emb 啟用，保留 chunk_${SUF} 的嵌入檔"
  fi
done

# === 合併 *.tsv / *.csv 到 OUT_DIR/merged ===
echo "[INFO] 開始合併 *.tsv / *.csv 檔案 → $MERGED_DIR"

# 清空 merged 既有內容（若存在）
find "$MERGED_DIR" \( -name "*.tsv" -o -name "*.csv" \) -type f -exec rm -f -- {} + 2>/dev/null || true

# 收集所有 chunk 裡的 tsv/csv（可能為空；null-safe）
readarray -d '' -t ALL_TABLES < <(
  find "$OUT_DIR" -maxdepth 1 -type d -name "chunk_*" -print0 \
  | xargs -0 -I{} find {} -type f \( -name "*.tsv" -o -name "*.csv" \) -print0 \
  | sort -z
)

if [[ ${#ALL_TABLES[@]} -eq 0 ]]; then
  echo "[INFO] 找不到可合併的表格檔案，略過合併步驟。"
else
  # 取出唯一的 basename 清單
  mapfile -t UNIQUE_BASES < <(
    for f in "${ALL_TABLES[@]}"; do basename "$f"; done | sort -u
  )

  same_first_line() {
    local f1="$1"; local f2="$2"
    [[ -f "$f1" && -f "$f2" ]] || return 1
    local a b
    a="$(head -n 1 "$f1")"
    b="$(head -n 1 "$f2")"
    [[ "$a" == "$b" ]]
  }

  for base in "${UNIQUE_BASES[@]}"; do
    out_file="$MERGED_DIR/$base"
    echo "[INFO]  合併檔名：$base"
    : > "$out_file"
    first=1
    ref_header_file=""

    mapfile -t FILES_FOR_BASE < <(
      for f in "${ALL_TABLES[@]}"; do
        if [[ "$(basename "$f")" == "$base" ]]; then
          echo "$f"
        fi
      done | sort
    )

    for f in "${FILES_FOR_BASE[@]}"; do
      if [[ "$first" -eq 1 ]]; then
        cat "$f" >> "$out_file"
        ref_header_file="$f"
        first=0
      else
        if same_first_line "$ref_header_file" "$f"; then
          tail -n +2 "$f" >> "$out_file"
        else
          cat "$f" >> "$out_file"
        fi
      fi
    done
  done
fi

echo "[INFO] 合併完成。"
echo "[INFO] chunk 個別輸出保留於：$OUT_DIR/chunk_XX/"
echo "[INFO] 合併表格輸出位於：$MERGED_DIR/"
