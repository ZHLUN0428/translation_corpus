import hanlp
import argparse

# 加載 HanLP 的多任務模型
pipe = hanlp.load(hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH)

def parse(fname: str = 'norm.zh', dest_fname: str = 'norm.seg.zh'):
    with open(fname, 'r', encoding='utf-8') as f, open(dest_fname, 'w', encoding='utf-8') as o:
        for line in f:
            # 使用 HanLP 進行分詞
            seg = pipe(line)
            # 將分詞結果寫入輸出文件
            o.write(' '.join(seg['tok/fine']) + '\n')

if __name__ == '__main__':
    # 設置命令行參數
    parser = argparse.ArgumentParser()
    parser.add_argument('-if', '--inputfile', required=True, help="Input file path")
    parser.add_argument('-of', '--outputfile', required=True, help="Output file path")
    args = parser.parse_args()

    # 調用 parse 函數進行文件處理
    parse(args.inputfile, args.outputfile)
