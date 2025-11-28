#!/bin/sh

src=zh
tgt=en
model_name=$1

SCRIPTS=~/translation-corpus/mosesdecoder/scripts
TOKENIZER=${SCRIPTS}/tokenizer/tokenizer.perl
DETOKENIZER=${SCRIPTS}/tokenizer/detokenizer.perl
LC=${SCRIPTS}/tokenizer/lowercase.perl
TRAIN_TC=${SCRIPTS}/recaser/train-truecaser.perl
TC=${SCRIPTS}/recaser/truecase.perl
DETC=${SCRIPTS}/recaser/detruecase.perl
NORM_PUNC=${SCRIPTS}/tokenizer/normalize-punctuation.perl
CLEAN=${SCRIPTS}/training/clean-corpus-n.perl
BPEROOT=~/translation-corpus/subword-nmt/subword_nmt
MULTI_BLEU=${SCRIPTS}/generic/multi-bleu.perl
MTEVAL_V14=${SCRIPTS}/generic/mteval-v14.pl

data_dir=~/translation-corpus/zh-en/data/$model_name
model_dir=~/translation-corpus/zh-en/models/$model_name
utils=~/translation-corpus/zh-en/utils

echo "===============init_success==============="

perl ${NORM_PUNC} -l $tgt < ${data_dir}/raw.$tgt > ${data_dir}/norm.$tgt
perl ${NORM_PUNC} -l $src < ${data_dir}/raw.$src > ${data_dir}/norm.$src

echo "===============norm_success==============="

python ${utils}/hanlp_segment.py -if ${data_dir}/norm.$src -of ${data_dir}/norm.seg.$src

echo "===============hanlp_success==============="

${TOKENIZER} -l $tgt < ${data_dir}/norm.$tgt > ${data_dir}/norm.tok.$tgt
${TOKENIZER} -l $src < ${data_dir}/norm.seg.$src > ${data_dir}/norm.seg.tok.$src

echo "===============TOKENIZER_success==============="

${TRAIN_TC} --model ${model_dir}/truecase-model.$tgt --corpus ${data_dir}/norm.tok.$tgt
${TC} --model ${model_dir}/truecase-model.$tgt < ${data_dir}/norm.tok.$tgt > ${data_dir}/norm.tok.true.$tgt

echo "===============TC_success==============="

python ${BPEROOT}/learn_joint_bpe_and_vocab.py --input ${data_dir}/norm.tok.true.$tgt  -s 32000 -o ${model_dir}/bpecode.$tgt --write-vocabulary ${model_dir}/voc.$tgt
python ${BPEROOT}/apply_bpe.py -c ${model_dir}/bpecode.$tgt --vocabulary ${model_dir}/voc.$tgt < ${data_dir}/norm.tok.true.$tgt > ${data_dir}/norm.tok.true.bpe.$tgt
python ${BPEROOT}/learn_joint_bpe_and_vocab.py --input ${data_dir}/norm.seg.tok.$src  -s 32000 -o ${model_dir}/bpecode.$src --write-vocabulary ${model_dir}/voc.$src
python ${BPEROOT}/apply_bpe.py -c ${model_dir}/bpecode.$src --vocabulary ${model_dir}/voc.$src < ${data_dir}/norm.seg.tok.$src > ${data_dir}/norm.seg.tok.bpe.$src

echo "===============BPE_success================="

mv ${data_dir}/norm.seg.tok.bpe.$src ${data_dir}/toclean.$src
mv ${data_dir}/norm.tok.true.bpe.$tgt ${data_dir}/toclean.$tgt 
${CLEAN} ${data_dir}/toclean $src $tgt ${data_dir}/clean 1 256

echo "===============CLEAN_success==============="

python ${utils}/split.py ${data_dir}/clean.$src ${data_dir}/clean.$tgt ${data_dir}/

ls $data_dir | grep -Ev '^(raw|valid|test|train)\.(en|zh)$' | xargs -I {} rm -f $data_dir/{}
echo "===============Preprocess_success==============="