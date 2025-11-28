#!/usr/bin/env bash
# 只依 similarity.tsv 分流（自動讀表頭：idx, cosine, id_sentence, zh_sentence）
# 用法：
#   ./export_filtered_from_sim.sh <folder_name> [--thr 0.6] [--prefix filtered] [--out_dir <path>]
# 例：
#   ./export_filtered_from_sim.sh zh2id_ner_v3 --thr 0.7 --prefix laser07

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <folder_name> [--thr 0.6] [--prefix filtered] [--out_dir <path>]"
  exit 1
fi

FOLDER="$1"; shift || true
THR="0.75"
PREFIX="filtered"

BASE="/home/mi2s/translation-corpus/zh-id"
SIM="${BASE}/models/${FOLDER}/laser_out/merged/similarity.tsv"
OUT_DIR="${BASE}/data/${FOLDER}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --thr) THR="$2"; shift 2;;
    --prefix) PREFIX="$2"; shift 2;;
    --out_dir) OUT_DIR="$2"; shift 2;;
    -h|--help)
      echo "Usage: $0 <folder_name> [--thr 0.6] [--prefix filtered] [--out_dir <path>]"
      exit 0;;
    *) echo "[ERROR] Unknown option: $1"; exit 1;;
  esac
done

# 支援 .tsv.gz
if [[ ! -f "$SIM" && -f "${SIM}.gz" ]]; then
  SIM="${SIM}.gz"
fi
[[ -f "$SIM" ]] || { echo "[ERROR] not found: $SIM"; exit 1; }

mkdir -p "$OUT_DIR"
thr_nodot="${THR//./}"

OUT_ID_GE="${OUT_DIR}/${PREFIX}.id"
OUT_ZH_GE="${OUT_DIR}/${PREFIX}.zh"
OUT_ID_LT="${OUT_DIR}/${PREFIX}_lt${thr_nodot}.id"
OUT_ZH_LT="${OUT_DIR}/${PREFIX}_lt${thr_nodot}.zh"

: > "$OUT_ID_GE"; : > "$OUT_ZH_GE"; : > "$OUT_ID_LT"; : > "$OUT_ZH_LT"

echo "[INFO] SIM     : $SIM"
echo "[INFO] OUT_DIR : $OUT_DIR"
echo "[INFO] THR     : $THR"
echo "[INFO] outputs :"
echo "  >= thr → $OUT_ID_GE , $OUT_ZH_GE"
echo "  <  thr → $OUT_ID_LT , $OUT_ZH_LT"

read_cmd="cat"; [[ "$SIM" == *.gz ]] && read_cmd="zcat"

# 只依 similarity.tsv 分流，會自動根據表頭找欄位：
#   score 欄：cosine / score / similarity 其一（不分大小寫）
#   句子欄：id_sentence / zh_sentence
$read_cmd -- "$SIM" | awk -v thr="$THR" \
  -v id_ge="$OUT_ID_GE" -v zh_ge="$OUT_ZH_GE" \
  -v id_lt="$OUT_ID_LT" -v zh_lt="$OUT_ZH_LT" \
  -F'\t' '
function lcase(s){ gsub(/[A-Z]/, "", s); return tolower(s) } # busybox 兼容保守做法
function is_number(x) { return (x ~ /^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$/) }

NR==1{
  # 解析表頭
  for(i=1;i<=NF;i++){
    key=lcase($i)
    if(key=="id_sentence") id_idx=i
    else if(key=="zh_sentence") zh_idx=i
    else if(key=="cosine" || key=="score" || key=="similarity") score_idx=i
  }
  if(!id_idx || !zh_idx || !score_idx){
    printf("[ERROR] header missing. Need columns: id_sentence, zh_sentence, and cosine/score/similarity\n") > "/dev/stderr"
    exit 2
  }
  next
}

{
  # 空行跳過
  empty=1
  for(i=1;i<=NF;i++){ if($i!=""){ empty=0; break } }
  if(empty) next

  sc = $(score_idx)
  if(!is_number(sc)) next  # 若資料列仍有非數字分數，跳過
  score = sc + 0

  if(score >= thr){
    print $(id_idx) >> id_ge
    print $(zh_idx) >> zh_ge
  }else{
    print $(id_idx) >> id_lt
    print $(zh_idx) >> zh_lt
  }
}
END{
  close(id_ge); close(zh_ge); close(id_lt); close(zh_lt)
}'
echo "[OK] done."
