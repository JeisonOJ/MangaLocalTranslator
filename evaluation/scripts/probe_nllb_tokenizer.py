import os,json,pathlib
R=pathlib.Path(__file__).resolve().parents[2];os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HOME']=str(R/'evaluation/cache/huggingface')
from transformers import AutoTokenizer
p=str(R/'evaluation/models/nllb-600m');s='いや てめえらで行ってこいよ タコ'
r={}
for label,kw in [('upstream-default',{}),('explicit-source',{'src_lang':'jpn_Jpan'})]:
 t=AutoTokenizer.from_pretrained(p,local_files_only=True,**kw)
 before=t(s)['input_ids'];t.src_lang='jpn_Jpan';after=t(s)['input_ids']
 r[label]={'class':type(t).__name__,'src_lang':getattr(t,'src_lang',None),'japanese_id':t.convert_tokens_to_ids('jpn_Jpan'),'spanish_id':t.convert_tokens_to_ids('spa_Latn'),'unk_id':t.unk_token_id,'before':before,'after':after,'before_tokens':t.convert_ids_to_tokens(before),'after_tokens':t.convert_ids_to_tokens(after)}
(R/'evaluation/results/nllb-diagnosis/tokenizer-probe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,ensure_ascii=True,indent=2))
