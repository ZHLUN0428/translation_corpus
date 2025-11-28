import random
import re

# 20 個數字（中印兩語皆使用相同清單）
qty_list = [
    "10", "29", "35", "42", "57",
    "63", "76", "81", "90", "100",
    "115", "128", "134", "150", "167",
    "189", "200", "225", "250", "300"
]

# 20 種活動（中文與印尼文對照）
evt_list_zh = [
    "音樂會", "籃球比賽", "電影首映", "美食節", "展覽",
    "講座", "研討會", "馬拉松", "足球比賽", "藝術節",
    "嘉年華", "時裝秀", "博覽會", "演唱會", "攝影展",
    "書展", "慶典", "節日活動", "舞蹈比賽", "遊戲比賽"
]
evt_list_id = [
    "konser musik", "pertandingan bola basket", "pemutaran perdana film", "festival kuliner", "pameran",
    "kuliah umum", "seminar", "maraton", "pertandingan sepak bola", "festival seni",
    "karnaval", "pertunjukan busana", "pameran dagang", "konser", "pameran fotografi",
    "pameran buku", "perayaan", "acara festival", "kompetisi tari", "kompetisi game"
]

# 20 個日期（中文與印尼文對照）
dat_list_zh = [
    "2023年01月15日", "2023年02月20日", "2023年03月25日", "2023年04月30日", "2023年05月05日",
    "2023年06月10日", "2023年07月15日", "2023年08月20日", "2023年09月25日", "2023年10月30日",
    "2023年11月05日", "2023年12月10日", "2024年01月15日", "2024年02月20日", "2024年03月25日",
    "2024年04月30日", "2024年05月05日", "2024年06月10日", "2024年07月15日", "2024年08月20日"
]
dat_list_id = [
    "15 Januari 2023", "20 Februari 2023", "25 Maret 2023", "30 April 2023", "05 Mei 2023",
    "10 Juni 2023", "15 Juli 2023", "20 Agustus 2023", "25 September 2023", "30 Oktober 2023",
    "05 November 2023", "10 Desember 2023", "15 Januari 2024", "20 Februari 2024", "25 Maret 2024",
    "30 April 2024", "05 Mei 2024", "10 Juni 2024", "15 Juli 2024", "20 Agustus 2024"
]

# 20 個時間（中文與印尼文對照，用於替換 <TIM>）
times_zh = [
    "早上七點整", "早上八點半", "上午九點整", "上午十點十分", "中午十二點整",
    "下午一點半", "下午兩點整", "下午三點十分", "下午四點四十五分", "下午五點整",
    "傍晚六點半", "晚上七點整", "晚上八點十分", "晚上九點整", "晚上十點三十分",
    "午夜十二點整", "凌晨一點整", "凌晨兩點半", "清晨五點整", "清晨六點半"
]
times_id = [
    "Jam 7:00 pagi", "Jam 8:30 pagi", "Jam 9:00 pagi", "Jam 10:10 pagi", "Jam 12:00 siang",
    "Jam 1:30 siang", "Jam 2:00 siang", "Jam 3:10 sore", "Jam 4:45 sore", "Jam 5:00 sore",
    "Jam 6:30 sore", "Jam 7:00 malam", "Jam 8:10 malam", "Jam 9:00 malam", "Jam 10:30 malam",
    "Jam 12:00 tengah malam", "Jam 1:00 dini hari", "Jam 2:30 dini hari", "Jam 5:00 pagi", "Jam 6:30 pagi"
]

# 檔案設定（請根據實際路徑修改）
input_file_zh = 'ner.zh'
input_file_id = 'ner.id'
output_file_zh = 'ner.zh.out'
output_file_id = 'ner.id.out'

# 定義一個正規表達式，檢查是否含有 <QTY>, <EVT>, <DAT> 或 <TIM>
pattern = re.compile(r'<(QTY|EVT|DAT|TIM)>')

# 同時讀取平行語料，只處理包含目標標籤的行
with open(input_file_zh, 'r', encoding='utf-8') as f_zh, \
     open(input_file_id, 'r', encoding='utf-8') as f_id, \
     open(output_file_zh, 'w', encoding='utf-8') as out_zh, \
     open(output_file_id, 'w', encoding='utf-8') as out_id:
    
    for line_zh, line_id in zip(f_zh, f_id):
        # 若中文行中不包含任何指定的標籤，則跳過該行
        if not pattern.search(line_zh):
            continue

        # 為每種標籤選取隨機索引（各自獨立）
        idx_qty = random.randint(0, len(qty_list) - 1)
        idx_evt = random.randint(0, len(evt_list_zh) - 1)
        idx_dat = random.randint(0, len(dat_list_zh) - 1)
        idx_tim = random.randint(0, len(times_zh) - 1)
        
        new_line_zh = line_zh
        new_line_id = line_id
        
        # 替換 <QTY> 標籤
        new_line_zh = re.sub(r'<QTY>', qty_list[idx_qty], new_line_zh)
        new_line_id = re.sub(r'<QTY>', qty_list[idx_qty], new_line_id)
        
        # 替換 <EVT> 標籤
        new_line_zh = re.sub(r'<EVT>', evt_list_zh[idx_evt], new_line_zh)
        new_line_id = re.sub(r'<EVT>', evt_list_id[idx_evt], new_line_id)
        
        # 替換 <DAT> 標籤
        new_line_zh = re.sub(r'<DAT>', dat_list_zh[idx_dat], new_line_zh)
        new_line_id = re.sub(r'<DAT>', dat_list_id[idx_dat], new_line_id)
        
        # 替換 <TIM> 標籤
        new_line_zh = re.sub(r'<TIM>', times_zh[idx_tim], new_line_zh)
        new_line_id = re.sub(r'<TIM>', times_id[idx_tim], new_line_id)
        
        # 寫入替換後的行到對應的輸出檔案
        out_zh.write(new_line_zh)
        out_id.write(new_line_id)
