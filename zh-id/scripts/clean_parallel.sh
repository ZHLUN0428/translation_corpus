#!/usr/bin/env bash
# clean_parallel.sh
# 用法：
#   ./clean_parallel.sh <folder_name> [--in-dir <abs_or_rel_path>] [--python <path_to_python>]
#
# 預設專案根：~/translation-corpus/zh-id
# 預設輸入資料夾：$ROOT/data/<folder_name>
# 會在同資料夾輸出：clean.zh、clean.id
#
# 規則（由 utils/parallel_clean.py 實作）：
#  1) zh 含英文/數字（含全形）→ 丟棄整句對
#  2) id 含數字（含全形）→ 丟棄整句對
#  3) 移除所有標點，保留 <PER> 等 angle-bracket 標籤

set -euo pipefail

ROOT="${HOME}/translation-corpus/zh-id"
UTILS="${ROOT}/utils"
SCRIPT_NAME="$(basename "$0")"
PY="${PYTHON:-python3}"

usage() {
  cat <<EOF
用法：
  ${SCRIPT_NAME} <folder_name> [--in-dir <abs_or_rel_path>] [--python <path_to_python>]

參數：
  <folder_name>            例如 my_corpus。預設輸入路徑會是 \$ROOT/data/<folder_name>
  --in-dir <path>          自訂輸入資料夾（包含 raw.zh / raw.id）。預設 \$ROOT/data/<folder_name>
  --python <path>          指定 Python（預設: python3）

說明：
  會切換到輸入資料夾執行 \$UTILS/parallel_clean.py，
  讀 raw.zh / raw.id，輸出 clean.zh / clean.id。
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

FOLDER_NAME="$1"; shift || true
IN_DIR=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --in-dir)
      shift
      IN_DIR="${1:-}"
      if [[ -z "${IN_DIR}" ]]; then
        echo "[ERR] --in-dir 需要路徑參數" >&2
        exit 1
      fi
      ;;
    --python)
      shift
      PY="${1:-python3}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[WARN] 未知參數：$1（忽略）" >&2
      ;;
  esac
  shift || true
done

# 預設輸入資料夾
if [[ -z "${IN_DIR}" ]]; then
  IN_DIR="${ROOT}/data/${FOLDER_NAME}"
fi

PY_SCRIPT="${UTILS}/parallel_clean.py"

echo "[INFO] ROOT       = ${ROOT}"
echo "[INFO] UTILS      = ${UTILS}"
echo "[INFO] IN_DIR     = ${IN_DIR}"
echo "[INFO] PYTHON     = ${PY}"
echo "[INFO] PY_SCRIPT  = ${PY_SCRIPT}"

# 基本檢查
if [[ ! -d "${IN_DIR}" ]]; then
  echo "[ERR] 找不到輸入資料夾：${IN_DIR}" >&2
  exit 1
fi

if [[ ! -f "${IN_DIR}/raw.zh" ]]; then
  echo "[ERR] 找不到檔案：${IN_DIR}/raw.zh" >&2
  exit 1
fi

if [[ ! -f "${IN_DIR}/raw.id" ]]; then
  echo "[ERR] 找不到檔案：${IN_DIR}/raw.id" >&2
  exit 1
fi

if [[ ! -f "${PY_SCRIPT}" ]]; then
  echo "[ERR] 找不到 Python 清洗腳本：${PY_SCRIPT}" >&2
  echo "      請先把 parallel_clean.py 放到 ${UTILS}/ ，或告訴我替你建立。" >&2
  exit 1
fi

# 執行清洗（在輸入資料夾內，讓 parallel_clean.py 直接讀/寫 raw.* / clean.*）
pushd "${IN_DIR}" >/dev/null

echo "[INFO] 開始清洗：$(pwd)"
set +e
"${PY}" "${PY_SCRIPT}"
status=$?
set -e
popd >/dev/null

if [[ ${status} -ne 0 ]]; then
  echo "[ERR] 清洗執行失敗（exit ${status)】" >&2
  exit ${status}
fi

# 簡單結果檢查
if [[ -s "${IN_DIR}/clean.zh" && -s "${IN_DIR}/clean.id" ]]; then
  zh_lines=$(wc -l < "${IN_DIR}/clean.zh" | tr -d ' ')
  id_lines=$(wc -l < "${IN_DIR}/clean.id" | tr -d ' ')
  echo "[OK] 完成。輸出："
  echo "     ${IN_DIR}/clean.zh  (行數: ${zh_lines})"
  echo "     ${IN_DIR}/clean.id  (行數: ${id_lines})"
  if [[ "${zh_lines}" != "${id_lines}" ]]; then
    echo "[WARN] 兩側行數不同，請檢查。"
  fi
else
  echo "[ERR] 找不到輸出 clean.zh / clean.id 或為空檔。" >&2
  exit 2
fi
