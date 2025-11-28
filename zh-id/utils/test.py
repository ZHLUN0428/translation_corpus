import re

def restore_html_and_remove_at(text):
    """
    將 HTML 實體還原為原始符號，並刪除中間的 '@@'。
    """
    # 還原 HTML 實體
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    # 刪除中間的 '@@'
    text = re.sub(r'@@\s*', '', text)
    text = re.sub(r'<\s*(.*?)\s*>', r'<\1>', text)
    return text

def process_file(input_file, output_file):
    # 打開輸入文件，逐行讀取並進行轉換
    with open(input_file, "r", encoding="utf-8") as infile, open(output_file, "w", encoding="utf-8") as outfile:
        for line in infile:
            # 對每一行進行標記還原處理
            cleaned_line = restore_html_and_remove_at(line)
            # 寫入處理後的行到輸出文件
            outfile.write(cleaned_line)

# 指定輸入和輸出文件
input_file = "/home/mi2s/translation-corpus/zh-id/data/id2zh_4.5M_ner/valid.id"   # 替換為你的輸入文件路徑
output_file = "/home/mi2s/translation-corpus/zh-id/data/id2zh_4.5M_ner/new/valid.id" # 替換為你的輸出文件路徑


process_file(input_file, output_file)
