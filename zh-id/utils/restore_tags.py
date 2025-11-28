import re

def restore_tags(text):
    # 使用正規表達式捕捉 &lt; 與 &gt; 之間的內容，並移除左右多餘空白
    return re.sub(r'&lt;\s*(.*?)\s*&gt;', lambda m: f"<{m.group(1)}>", text)

def process_file(input_file, output_file):
    # 讀取整個檔案內容、替換並寫入到新檔案
    with open(input_file, "r", encoding="utf-8") as infile:
        content = infile.read()
    
    # 將整個檔案內容作轉換
    restored_content = restore_tags(content)
    
    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write(restored_content)

# 範例：設定輸入與輸出檔案的路徑
input_file = "/home/mi2s/translation-corpus/zh-id/data/id2zh_7M_ner_v3/valid.id"    # 請替換為你的輸入檔案路徑
output_file = "/home/mi2s/translation-corpus/zh-id/data/id2zh_7M_ner_v3/valid.id"  # 請替換為你想儲存的新檔案路徑

# 執行檔案處理
process_file(input_file, output_file)
print(f"檔案處理完成，結果已輸出至 {output_file}")
