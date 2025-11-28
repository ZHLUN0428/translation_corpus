#!/bin/bash

# 指定資料夾名稱

folder_name=$1
data_dir=~/translation-corpus/zh-en/data/
model_dir=~/translation-corpus/zh-en/models/
# 檢查並在 data 和 models 資料夾中創建子資料夾
mkdir -p "$data_dir/$folder_name" "$model_dir/$folder_name"

echo "資料夾已在 data 和 models 中創建：$folder_name"
