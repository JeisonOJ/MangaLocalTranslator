import os,json,pathlib,threading,time,psutil,traceback
R=pathlib.Path(__file__).resolve().parents[2];O=R/'evaluation/results/nllb-diagnosis'
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HOME']=str(R/'evaluation/cache/huggingface')
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
report={'scope':'One direct translation-only replay, same decoding parameters; no parameter search','samples':[]};stop=False;proc=psutil.Process()
def watch():
 while not stop:
  report['peak_process_rss_bytes']=max(report.get('peak_process_rss_bytes',0),proc.memory_info().rss)
  report['peak_system_used_ram_bytes']=max(report.get('peak_system_used_ram_bytes',0),psutil.virtual_memory().used)
  if psutil.virtual_memory().available<500*1024**2:
   report['stopped']='available RAM below 500 MiB';(O/'direct-test.json').write_text(json.dumps(report,indent=2));os._exit(70)
  time.sleep(.1)
threading.Thread(target=watch,daemon=True).start()
try:
 p=str(R/'evaluation/models/nllb-600m');t=AutoTokenizer.from_pretrained(p,local_files_only=True);m=AutoModelForSeq2SeqLM.from_pretrained(p,local_files_only=True);m.eval();t.src_lang='jpn_Jpan'
 s='は？何 お前 口悪いな';encoded=t([s],return_tensors='pt',padding=True,truncation=True,max_length=512);start=time.perf_counter()
 with torch.no_grad():out=m.generate(**encoded,forced_bos_token_id=t.convert_tokens_to_ids('spa_Latn'),max_length=512,num_beams=5)
 report['samples'].append({'japanese':s,'input_ids':encoded['input_ids'].tolist(),'output_ids':out.tolist(),'spanish_machine':t.batch_decode(out,skip_special_tokens=True),'seconds':time.perf_counter()-start,'generation_config':m.generation_config.to_dict()})
except BaseException:report['exception']=traceback.format_exc()
stop=True;(O/'direct-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True))
