import pathlib,os,sys,json,hashlib,shutil,time,asyncio,threading,traceback,socket
R=pathlib.Path(__file__).resolve().parents[2];O=R/'evaluation/results/page11-ocr';O.mkdir(parents=True,exist_ok=False);src=R/'ManualImageTest/11.jpg';shutil.copy2(src,O/'original-11.jpg')
def save(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
save('input-reference.json',{'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['HF_HOME']=str(R/'evaluation/cache/huggingface')
originalconnect=socket.socket.connect
def guard(self,a):
 if isinstance(a,tuple) and a[0] in ('127.0.0.1','::1'):return originalconnect(self,a)
 raise RuntimeError('External network blocked')
socket.socket.connect=guard
import psutil
stats={};done=False;proc=psutil.Process()
def watch():
 while not done:
  v=psutil.virtual_memory();stats['peak_rss_bytes']=max(stats.get('peak_rss_bytes',0),proc.memory_info().rss);stats['peak_system_used_bytes']=max(stats.get('peak_system_used_bytes',0),v.used)
  if v.available<500*1024**2:stats['failure']='Available RAM below 500 MiB';save('resources.json',stats);os._exit(70)
  time.sleep(.1)
threading.Thread(target=watch,daemon=True).start();sys.path.insert(0,str(R/'upstream'));start=time.perf_counter()
try:
 import torch,numpy as np,gc
 from PIL import Image
 from manga_translator.utils import ModelWrapper
 from manga_translator import detection,ocr
 from manga_translator.config import Detector,Ocr,OcrConfig
 from manga_translator.textline_merge import dispatch as merge
 ModelWrapper._MODEL_DIR=str(R/'evaluation/models')
 async def nodownload(self,*a,**k):
  if not self._check_downloaded():raise RuntimeError('Missing selected model; downloads forbidden')
 ModelWrapper.download=nodownload
 def rows(qs):return [{'id':i,'polygon':q.pts.tolist(),'japanese_raw':q.text,'probability':float(q.prob)} for i,q in enumerate(qs)]
 async def main():
  im=np.array(Image.open(src).convert('RGB'));save('dimensions.json',{'width':im.shape[1],'height':im.shape[0]});torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
  lines,raw,_=await detection.dispatch(Detector.default,im,1536,.5,.7,2.3,False,False,False,device='cuda');save('detected.json',rows(lines));Image.fromarray(raw).save(O/'detector-raw-mask.png');stats['detection_seconds']=time.perf_counter()-t
  await detection.unload(Detector.default)
  import manga_translator.detection.default as dm;dm.MODEL=None;gc.collect();torch.cuda.empty_cache();t=time.perf_counter()
  lines=await ocr.dispatch(Ocr.ocr48px,im,lines,OcrConfig(ocr='48px',min_text_length=0,ignore_bubble=0),device='cuda');save('ocr-lines.json',rows(lines));stats['ocr_seconds']=time.perf_counter()-t
  await ocr.unload(Ocr.ocr48px);gc.collect();torch.cuda.empty_cache()
  grouped=await merge(lines,im.shape[1],im.shape[0]);data=[{'id':'R%02d'%i,'raw_group_index':i,'polygons':q.lines.tolist(),'japanese_raw':q.text,'probability':float(q.prob)} for i,q in enumerate(grouped)];save('ocr-regions.json',data);(O/'japanese-raw.txt').write_text('\n'.join(x['id']+' '+x['japanese_raw'] for x in data),encoding='utf-8');stats['peak_gpu_allocated_bytes']=torch.cuda.max_memory_allocated();stats['peak_gpu_reserved_bytes']=torch.cuda.max_memory_reserved()
 asyncio.run(main());stats['completed']=True
except BaseException:stats['failure']=traceback.format_exc();print(stats['failure'],flush=True)
finally:done=True;stats['total_seconds']=time.perf_counter()-start;save('resources.json',stats);print(json.dumps(stats),flush=True)
