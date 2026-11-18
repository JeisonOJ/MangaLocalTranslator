import os,json,pathlib,time,threading,traceback,socket
R=pathlib.Path(__file__).resolve().parents[2];O=R/'evaluation/results/m2m100-418m'
for k,v in {'HF_HOME':str(R/'evaluation/cache/huggingface'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}.items():os.environ[k]=v
def deny(*a,**k):raise RuntimeError('Network prohibited in translation test')
socket.socket.connect=deny;socket.create_connection=deny
import torch,psutil
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
report={'model':'facebook/m2m100_418M','device':'cuda','dtype':'float32','settings':{'source':'ja','target':'es','num_beams':5,'max_input_length':512,'max_length':512},'samples':[]};done=False;proc=psutil.Process();start=time.perf_counter()
def save(): (O/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def monitor():
 while not done:
  report['peak_process_rss_bytes']=max(report.get('peak_process_rss_bytes',0),proc.memory_info().rss)
  report['peak_system_used_bytes']=max(report.get('peak_system_used_bytes',0),psutil.virtual_memory().used)
  if psutil.virtual_memory().available<500*1024**2:report['failure']='Available system RAM below 500 MiB';save();os._exit(70)
  time.sleep(.1)
threading.Thread(target=monitor,daemon=True).start()
try:
 torch.cuda.reset_peak_memory_stats();p=str(R/'evaluation/models/m2m100-418m');t=AutoTokenizer.from_pretrained(p,local_files_only=True);m=AutoModelForSeq2SeqLM.from_pretrained(p,local_files_only=True).to('cuda');m.eval();report['load_seconds']=time.perf_counter()-start;t.src_lang='ja';target=t.get_lang_id('es');report['target_id']=target;report['tokenizer_class']=type(t).__name__;report['parameter_count']=sum(x.numel() for x in m.parameters());report['source_id']=t.get_lang_id('ja')
 verified=json.loads((R/'evaluation/results/first-page-test/verified-text-spanish.json').read_text(encoding='utf-8'))
 inputs=[{'id':'manga-'+str(x['id']),'kind':'user-verified manga excerpt','japanese':x['japanese_user_verified'],'nllb_raw':x['spanish_machine']} for x in verified]
 inputs += [{**x,'kind':'previously authored sanity fixture, not page transcription'} for x in json.loads((R/'evaluation/known-japanese.json').read_text(encoding='utf-8'))]
 for x in inputs:
  before=time.perf_counter();tokens=t([x['japanese']],return_tensors='pt',padding=True,truncation=True,max_length=512);inputids=tokens['input_ids'].tolist();tokens={k:v.to('cuda') for k,v in tokens.items()}
  with torch.no_grad():out=m.generate(**tokens,forced_bos_token_id=target,max_length=512,num_beams=5)
  torch.cuda.synchronize();x['spanish_raw']=t.batch_decode(out,skip_special_tokens=True)[0];x['input_ids']=inputids;x['output_ids']=out.cpu().tolist();x['seconds']=time.perf_counter()-before;report['samples'].append(x);save();print(json.dumps(x,ensure_ascii=True),flush=True)
 report['completed']=True
except BaseException:report['failure']=traceback.format_exc();print(report['failure'],flush=True)
finally:
 done=True;report['peak_gpu_allocated_bytes']=torch.cuda.max_memory_allocated();report['peak_gpu_reserved_bytes']=torch.cuda.max_memory_reserved();report['total_seconds']=time.perf_counter()-start;save()
