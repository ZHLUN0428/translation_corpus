def count_crd(line):
    """計算一行中 <CRD> 出現的次數。"""
    return line.count("<PER>")


def filter_parallel_corpus(file1_path, file2_path, output_file1, output_file2):
    """檢查兩個檔案中每行的 <CRD> 數量是否一致，若不一致則刪除該行。"""
    with open(file1_path, 'r', encoding='utf-8') as f1, \
         open(file2_path, 'r', encoding='utf-8') as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()

    if len(lines1) != len(lines2):
        raise ValueError("兩個檔案的行數不一致。")

    filtered_lines1 = []
    filtered_lines2 = []

    for line1, line2 in zip(lines1, lines2):
        if (count_crd(line1) == count_crd(line2)) and count_crd(line1) != 0:
            filtered_lines1.append(line1)
            filtered_lines2.append(line2)

    with open(output_file1, 'w', encoding='utf-8') as out1, \
         open(output_file2, 'w', encoding='utf-8') as out2:
        out1.writelines(filtered_lines1)
        out2.writelines(filtered_lines2)

    print(f"已完成篩選，結果已儲存至 '{output_file1}' 和 '{output_file2}'。")


# 範例使用
file1 = '/home/mi2s/translation-corpus/zh-id/data/zh-id_9k_ner/per.id.ner'
file2 = '/home/mi2s/translation-corpus/zh-id/data/zh-id_9k_ner/per.zh.ner'
output1 = '/home/mi2s/translation-corpus/zh-id/data/zh-id_9k_ner/filtered_file1.id'
output2 = '/home/mi2s/translation-corpus/zh-id/data/zh-id_9k_ner/filtered_file2.zh'

filter_parallel_corpus(file1, file2, output1, output2)
