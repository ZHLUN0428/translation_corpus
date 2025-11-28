#!/bin/bash

# 指定資料夾名稱
folder_name=$1

# 定義路徑
data_dir=~/translation-corpus/zh-en/data/
model_dir=~/translation-corpus/zh-en/models/

# 刪除指定資料夾及內容
rm -rf "$data_dir/$folder_name"
rm -rf "$model_dir/$folder_name"

echo "已刪除資料夾及內容：$folder_name"
