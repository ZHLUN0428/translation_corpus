#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, Response
import subprocess
import os
import json

app = Flask(__name__)


def run(cmd, input_str):
    """Run a subprocess with stdin=input_str and return stdout"""
    p = subprocess.Popen(cmd,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         text=True)
    out, err = p.communicate(input_str)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{err}")
    return out.strip()


def preprocess_all(model_name: str,
                   text: str,
                   do_normalize: bool = True,
                   do_hanlp: bool = True,
                   do_tokenize: bool = True,
                   do_truecase: bool = True,
                   do_bpe: bool = True) -> dict:
    """
    按步骤预处理：
      normalize → HanLP segmentation → Moses tokenization → optional truecase → BPE
    各步骤可通过参数开关控制是否执行。
    """
    src = "zh"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(base_dir, '..'))
    moses_scripts = os.path.join(repo, '../mosesdecoder/scripts')
    bpe_root = os.path.join(repo, '../subword-nmt')
    utils_dir = os.path.join(repo, 'utils')
    model_dir = os.path.join(repo, 'models', model_name)

    # 各工具路径
    norm_punc    = os.path.join(moses_scripts, 'tokenizer/normalize-punctuation.perl')
    hanlp_seg    = os.path.join(utils_dir, 'hanlp_segment.py')
    tokenizer    = os.path.join(moses_scripts, 'tokenizer/tokenizer.perl')
    truecase_tool= os.path.join(moses_scripts, 'recaser/truecase.perl')
    apply_bpe    = os.path.join(bpe_root, 'apply_bpe.py')

    # 各模型文件
    truecase_model = os.path.join(model_dir, f'truecase-model.{src}')
    bpe_code       = os.path.join(model_dir, f'bpecode.{src}')
    vocab_file     = os.path.join(model_dir, f'voc.{src}')

    result = {}
    current = text

    # 1. normalize punctuation
    if do_normalize:
        current = run(['perl', norm_punc, '-l', src], current)
        result['normalized'] = current

    # 2. HanLP segmentation
    if do_hanlp:
        current = run(['python3', hanlp_seg, '-if', '/dev/stdin', '-of', '/dev/stdout'], current)
        result['hanlp_segmented'] = current

    # 3. Moses tokenization
    if do_tokenize:
        current = run([tokenizer, '-l', src], current)
        result['moses_tokenized'] = current

    # 4. truecase （若模型文件存在且开关开启）
    if do_truecase and os.path.isfile(truecase_model):
        current = run(['perl', truecase_tool, '--model', truecase_model], current)
        result['truecased'] = current

    # 5. apply BPE
    if do_bpe:
        current = run(['python3', apply_bpe, '-c', bpe_code, '--vocabulary', vocab_file], current)
        result['bpe'] = current

    # 如果没有任何步骤，返回原句
    if not result:
        result['sentence'] = text

    return result


@app.route('/preprocess', methods=['POST'])
def api_preprocess():
    data = request.get_json(force=True)
    model_name = data.get('model_name')
    sentence   = data.get('sentence')

    if not model_name or not sentence:
        return jsonify({'error': 'model_name and sentence are required'}), 400

    # 读取各步骤开关，默认都执行
    do_normalize = data.get('normalize', True)
    do_hanlp     = data.get('hanlp', True)
    do_tokenize  = data.get('tokenize', True)
    do_truecase  = data.get('truecase', True)
    do_bpe       = data.get('bpe', True)

    try:
        result = preprocess_all(
            model_name, sentence,
            do_normalize=do_normalize,
            do_hanlp=do_hanlp,
            do_tokenize=do_tokenize,
            do_truecase=do_truecase,
            do_bpe=do_bpe
        )
        return Response(
            json.dumps(result, ensure_ascii=False),
            mimetype='application/json; charset=utf-8'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000)
