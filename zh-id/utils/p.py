import re

def clean_word(word):
    # 移除前後可能的附加詞綴，但只替換第一次出現的詞彙
    return re.sub(r'\b\w*(baik)\w*\b', r'<Adj>', word, count=1)

def process_files(raw_id_path, raw_zh_path, ner_id_path, ner_zh_path):
    # 讀取文件內容
    with open(raw_id_path, 'r', encoding='utf-8') as f:
        id_lines = f.readlines()
    
    with open(raw_zh_path, 'r', encoding='utf-8') as f:
        zh_lines = f.readlines()
    
    # 確保行數一致
    assert len(id_lines) == len(zh_lines), "文件行數不匹配"
    
    # 篩選同時包含 "baik" 和 "好"，且兩者均只出現一次的行
    filtered_pairs = [(id_line, zh_line) for id_line, zh_line in zip(id_lines, zh_lines) 
                      if id_line.count("baik") == 1 and zh_line.count("好") == 1]
    
    # 限制最多3000句
    filtered_pairs = filtered_pairs[:3000]
    
    # 進行替換，並確保每行指定詞彙只替換一次
    new_id_lines = [clean_word(id_line) for id_line, zh_line in filtered_pairs]
    new_zh_lines = [zh_line.replace("好", "<Adj>", 1) for id_line, zh_line in filtered_pairs]
    
    # 寫入新文件
    with open(ner_id_path, 'w', encoding='utf-8') as f:
        f.writelines(new_id_lines)
    
    with open(ner_zh_path, 'w', encoding='utf-8') as f:
        f.writelines(new_zh_lines)

# 指定文件路徑
process_files("/home/mi2s/translation-corpus/zh-id/data/id2zh_7M_ner_v1/raw.id", 
              "/home/mi2s/translation-corpus/zh-id/data/id2zh_7M_ner_v1/raw.zh", 
              "/home/mi2s/translation-corpus/zh-id/data/zh-id_3m/ner.id", 
              "/home/mi2s/translation-corpus/zh-id/data/zh-id_3m/ner.zh")
