# 讀取檔案內容
with open("/home/mi2s/translation-corpus/zh-id/data/zh-id_9k_ner/ner.id", "r", encoding="utf-8") as file:
    content = file.read()

# 使用 replace() 方法替換字串
new_content = content.replace("<SENIN>", "<MON>")

# 將替換後的內容寫回檔案
with open("/home/mi2s/translation-corpus/zh-id/data/zh-id_9k_ner/ner.id", "w", encoding="utf-8") as file:
    file.write(new_content)
