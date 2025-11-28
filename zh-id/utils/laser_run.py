#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
laser_run.py
- 用 LASER2 (laser_encoders) 對 raw.id / raw.zh 批量編碼
- 產出：
  - raw.id.emb.npy / raw.zh.emb.npy
  - similarity.tsv   : 逐行 cosine 分數
  - scores_summary.json : 統計 (mean/median/p90/max/min, >=threshold 計數)
  - nn_top1.tsv (可選 --write_nn): 最近鄰對齊（大資料會吃記憶體，謹慎使用）

需求套件：laser-encoders, numpy, tqdm
（本檔自帶 cosine 計算，不依賴 scikit-learn）
"""

import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Iterable, Tuple

import numpy as np
from tqdm import tqdm

# === 寫死裝置：想用 CPU 改成 "cpu" ===
DEVICE_HARD = "cuda"

# LASER2 pipeline
from laser_encoders import LaserEncoderPipeline

CLEAN_TAG_RE = re.compile(r"<[^>\n]{1,64}>")  # 移除 <NER> / <POS> 之類標記


def read_lines(fp: Path) -> List[str]:
    with fp.open("r", encoding="utf-8") as f:
        return [ln.strip() for ln in f]


def maybe_clean(lines: Iterable[str], remove_tags: bool) -> List[str]:
    if not remove_tags:
        return list(lines)
    out = []
    for s in lines:
        s2 = CLEAN_TAG_RE.sub("", s)
        out.append(s2.strip())
    return out


def batched(xs: List[str], batch_size: int):
    for i in range(0, len(xs), batch_size):
        yield xs[i:i+batch_size], i, min(i+batch_size, len(xs))


def encode_sentences(
    sentences: List[str],
    lang_code: str,
    batch_size: int = 256,
    normalize: bool = True,
    device_ignored: str = "auto",  # 已忽略，為相容舊參數
) -> np.ndarray:
    """
    使用 LASER2 直接吃原文；內建 SentencePiece 分詞。
    注意：本版本裝置寫死為 DEVICE_HARD。
    """
    # 不在 constructor 帶 device，避免舊版 laser_encoders 報 TypeError
    pipe = LaserEncoderPipeline(lang=lang_code)

    device_eff = DEVICE_HARD
    embs = []
    total = (len(sentences) + batch_size - 1) // batch_size
    for batch, s, e in tqdm(
        batched(sentences, batch_size),
        total=total,
        desc=f"Encoding {lang_code} on {device_eff}",
    ):
        # 優先嘗試在 encode_sentences() 傳 device；不支援則退回不帶
        try:
            X = pipe.encode_sentences(
                batch, normalize_embeddings=normalize, device=device_eff
            )
        except TypeError:
            X = pipe.encode_sentences(batch, normalize_embeddings=normalize)
        embs.append(X)
    return np.vstack(embs) if embs else np.zeros((0, 1024), dtype=np.float32)


def cosine_diag(A: np.ndarray, B: np.ndarray, assume_normalized: bool) -> np.ndarray:
    """
    計算對齊行 (i vs i) 的 cosine 分數。
    若 assume_normalized=True，A/B 已為單位向量，可用點積。
    """
    if A.shape != B.shape:
        n = min(len(A), len(B))
        A, B = A[:n], B[:n]
    if assume_normalized:
        return (A * B).sum(axis=1)
    # 未正規化：cos = (a·b) / (||a||*||b||)
    dot = (A * B).sum(axis=1)
    na = np.linalg.norm(A, axis=1) + 1e-12
    nb = np.linalg.norm(B, axis=1) + 1e-12
    return dot / (na * nb)


def cosine_matrix(A: np.ndarray, B: np.ndarray, assume_normalized: bool, chunk: int = 0) -> np.ndarray:
    """
    回傳整個 cosine 相似度矩陣（可能很大）。可選擇分塊以節省記憶體。
    """
    if assume_normalized:
        # 單位向量時，cos = A @ B.T
        if chunk and (len(A) * len(B) > chunk * chunk):
            # 分塊
            M = np.empty((len(A), len(B)), dtype=np.float32)
            for i in range(0, len(A), chunk):
                i2 = min(i + chunk, len(A))
                M[i:i2] = A[i:i2] @ B.T
            return M
        return A @ B.T
    # 未正規化：cos = (A @ B.T) / (||A|| ||B||)
    A_norm = np.linalg.norm(A, axis=1, keepdims=True) + 1e-12
    B_norm = np.linalg.norm(B, axis=1, keepdims=True) + 1e-12
    An = A / A_norm
    Bn = B / B_norm
    if chunk and (len(An) * len(Bn) > chunk * chunk):
        M = np.empty((len(An), len(Bn)), dtype=np.float32)
        for i in range(0, len(An), chunk):
            i2 = min(i + chunk, len(An))
            M[i:i2] = An[i:i2] @ Bn.T
        return M
    return An @ Bn.T


def summarize_scores(scores: np.ndarray, thresholds: Tuple[float, ...]) -> dict:
    scores = np.asarray(scores, dtype=np.float32)
    if scores.size == 0:
        return {
            "count": 0, "mean": None, "median": None, "p90": None, "max": None, "min": None,
            "threshold_counts": {str(t): 0 for t in thresholds}
        }
    return {
        "count": int(scores.size),
        "mean": float(scores.mean()),
        "median": float(np.median(scores)),
        "p90": float(np.percentile(scores, 90)),
        "max": float(scores.max()),
        "min": float(scores.min()),
        "threshold_counts": {str(t): int((scores >= t).sum()) for t in thresholds}
    }


def main():
    import time
    ap = argparse.ArgumentParser(description="LASER2 encode & score for raw.id/raw.zh")
    ap.add_argument("--id", required=True, help="Path to raw.id")
    ap.add_argument("--zh", required=True, help="Path to raw.zh")
    ap.add_argument("--id_lang", default="ind_Latn", help="FLORES200 code for Indonesian (default: ind_Latn)")
    ap.add_argument("--zh_lang", default="zho_Hant", help="FLORES200 code for Chinese (zho_Hant or zho_Hans)")
    ap.add_argument("--out_dir", default="laser_out", help="Output directory")
    ap.add_argument("--batch_size", type=int, default=512)
    ap.add_argument("--no_norm", action="store_true", help="Disable L2 normalization (預設有做正規化)")
    ap.add_argument("--device", default="auto", help='(ignored) kept for CLI compatibility')
    ap.add_argument("--remove_tags", action="store_true", help="Remove <TAG> like tokens before encoding")
    ap.add_argument("--write_nn", action="store_true", help="Also write top-1 nearest neighbor alignments (O(N^2) memory)")
    ap.add_argument("--nn_chunk", type=int, default=0, help="Block size for cosine matrix (0=naive all-at-once). Use when --write_nn with big data.")
    ap.add_argument("--thresholds", default="0.6,0.7,0.8,0.9", help="Comma-separated thresholds for summary counts")
    ap.add_argument("--max_lines", type=int, default=0, help="Only process first N lines (0 = all)")
    ap.add_argument("--eta_only", action="store_true", help="Benchmark on --max_lines and print ETA for full data without saving files")
    args = ap.parse_args()

    id_path = Path(args.id)
    zh_path = Path(args.zh)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    id_lines = maybe_clean(read_lines(id_path), args.remove_tags)
    zh_lines = maybe_clean(read_lines(zh_path), args.remove_tags)

    total_pairs = min(len(id_lines), len(zh_lines))
    if args.max_lines and args.max_lines > 0:
        n = min(args.max_lines, total_pairs)
        id_lines = id_lines[:n]
        zh_lines = zh_lines[:n]
    else:
        n = total_pairs

    if n == 0:
        print("[ERROR] No lines to process. Check your input files.")
        sys.exit(2)

    normalize = (not args.no_norm)

    t0 = time.time()
    id_vecs = encode_sentences(id_lines, args.id_lang, args.batch_size, normalize, args.device)
    zh_vecs = encode_sentences(zh_lines, args.zh_lang, args.batch_size, normalize, args.device)
    t1 = time.time()

    elapsed = t1 - t0
    rate = n / elapsed if elapsed > 0 else float("inf")
    print(f"[BENCH] Encoded {n} pairs in {elapsed:.2f}s  ->  {rate:.2f} pairs/sec")

    if args.eta_only:
        if rate > 0:
            eta_sec = total_pairs / rate
            print(f"[ETA] Projected time for all {total_pairs} pairs: ~{eta_sec:.1f}s")
        else:
            print("[ETA] Rate is 0? Check device/batch size.")
        return

    # 儲存 embeddings
    np.save(out_dir / "raw.id.emb.npy", id_vecs)
    np.save(out_dir / "raw.zh.emb.npy", zh_vecs)

    # 逐行 cosine（同索引）
    diag_scores = cosine_diag(id_vecs, zh_vecs, assume_normalized=normalize)

    # 輸出每行分數
    sim_tsv = out_dir / "similarity.tsv"
    with sim_tsv.open("w", encoding="utf-8") as f:
        f.write("idx\tcosine\tid_sentence\tzh_sentence\n")
        for i, (c, si, sz) in enumerate(zip(diag_scores, id_lines, zh_lines)):
            f.write(f"{i}\t{c:.6f}\t{si}\t{sz}\n")

    # 統計
    thresholds = tuple(float(x) for x in args.thresholds.split(",") if x.strip())
    summary = summarize_scores(diag_scores, thresholds)
    with (out_dir / "scores_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # （可選）最近鄰對齊
    if args.write_nn:
        print("[INFO] Building cosine matrix for nearest neighbors... (may be large)")
        S = cosine_matrix(id_vecs, zh_vecs, assume_normalized=normalize, chunk=args.nn_chunk)
        nn_idx = S.argmax(axis=1)
        nn_val = S.max(axis=1)
        with (out_dir / "nn_top1.tsv").open("w", encoding="utf-8") as f:
            f.write("id_idx\tzh_idx\tcosine\tid_sentence\tzh_sentence\n")
            for i, (j, c) in enumerate(zip(nn_idx, nn_val)):
                f.write(f"{i}\t{int(j)}\t{c:.6f}\t{id_lines[i]}\t{zh_lines[int(j)]}\n")

    print(f"[DONE] Saved to: {out_dir}")
    print(f"[INFO] Summary: {summary}")


if __name__ == "__main__":
    main()
