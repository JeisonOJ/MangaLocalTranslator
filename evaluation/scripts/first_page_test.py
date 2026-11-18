import os,sys,json,time,pathlib,hashlib,shutil,asyncio,gc,threading,traceback,socket,subprocess
R=pathlib.Path(__file__).resolve().parents[2]; O=R/'evaluation/results/first-page-test';O.mkdir(parents=True,exist_ok=True)
source=R/'ManualImageTest/5.jpg';
if not (O/'original-5.jpg').exists():shutil.copy2(source,O/'original-5.jpg')
def save(name,data): (O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
save('input-reference.json',{'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
for k,v in {'HF_HOME':str(R/'evaluation/cache/huggingface'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TORCH_HOME':str(R/'evaluation/cache/torch')}.items():os.environ[k]=v
sys.path.insert(0,str(R/'upstream'))
def deny(*a,**kw):raise RuntimeError('Network forbidden in controlled test')
original_connect=socket.socket.connect
def local_connect(self,address):
 if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'):return original_connect(self,address)
 return deny()
socket.socket.connect=local_connect
import torch,numpy as np,psutil
from PIL import Image,ImageDraw
from manga_translator import MangaTranslator
from manga_translator.config import Config
from manga_translator.utils import ModelWrapper,Context
from manga_translator import detection,ocr,inpainting,translators
from manga_translator.textline_merge import dispatch as merge
cfg=Config(**json.loads((R/'evaluation/configs/local.json').read_text()))
ModelWrapper._MODEL_DIR=str(R/'evaluation/models')
async def nodownload(self,*a,**kw):
 if not self._check_downloaded():raise RuntimeError('Missing local model; downloads forbidden')
ModelWrapper.download=nodownload
stats=[];active={};done=False;proc=psutil.Process();t0=time.perf_counter()
def monitor():
 while not done:
  if active:
   active['peak_rss_bytes']=max(active.get('peak_rss_bytes',0),proc.memory_info().rss)
   active['peak_system_used_bytes']=max(active.get('peak_system_used_bytes',0),psutil.virtual_memory().used)
   if psutil.virtual_memory().available<300*1024**2:
    save('memory-stop.json',{'stage':active,'reason':'Available system RAM below 300 MiB'});os._exit(70)
  time.sleep(.1)
threading.Thread(target=monitor,daemon=True).start()
def start(stage):
 global active
 active={'stage':stage,'started':time.perf_counter()};torch.cuda.reset_peak_memory_stats();print('START',stage,flush=True)
def finish():
 active['seconds']=time.perf_counter()-active.pop('started');active['peak_gpu_allocated_bytes']=torch.cuda.max_memory_allocated();active['peak_gpu_reserved_bytes']=torch.cuda.max_memory_reserved();stats.append(dict(active));save('timings-memory.json',stats);print('DONE',active,flush=True);active.clear()
async def release(kind):
 if kind=='detector':
  await detection.unload(cfg.detector.detector)
  import manga_translator.detection.default as d;d.MODEL=None
 elif kind=='ocr':await ocr.unload(cfg.ocr.ocr)
 elif kind=='inpaint':await inpainting.unload(cfg.inpainter.inpainter)
 elif kind=='translator':
  tr=translators.get_translator('nllb')
  if tr.is_loaded():await tr.unload('cpu')
 gc.collect();torch.cuda.empty_cache()
def rows(lines):return [{'id':i,'polygon':q.pts.tolist(),'japanese_raw':q.text,'probability':float(q.prob)} for i,q in enumerate(lines)]
def regions(items):return [{'id':i,'polygon':q.lines.tolist(),'japanese':q.text,'spanish_machine':getattr(q,'translation','')} for i,q in enumerate(items)]
def overlay(items,name):
 im=Image.open(source).convert('RGB');d=ImageDraw.Draw(im)
 for i,q in enumerate(items):
  p=np.array(q['polygon']).reshape(-1,2).tolist();d.line([tuple(x) for x in p]+[tuple(p[0])],fill='red',width=3);d.text(tuple(p[0]),str(i),fill='blue',stroke_width=1)
 im.save(O/name)
def localtr():
 tr=translators.get_translator('nllb');tr._TRANSLATOR_MODEL=str(R/'evaluation/models/nllb-600m');tr._check_downloaded=lambda:True;tr._downloaded=True;return tr
class Instrumented(MangaTranslator):
 def _result_path(self,path):
  p=O/'C-debug'/path;p.parent.mkdir(parents=True,exist_ok=True);return str(p)
 async def _run_detection(self,c,x):
  start('C-detection');r=await super()._run_detection(c,x);save('C-detection.json',rows(r[0]));finish();await release('detector');return r
 async def _run_ocr(self,c,x):
  start('C-ocr');r=await super()._run_ocr(c,x);save('C-ocr.json',rows(r));finish();await release('ocr');return r
 async def _run_text_translation(self,c,x):
  start('C-translation');save('C-translation-input.json',regions(x.text_regions));r=await super()._run_text_translation(c,x);save('C-translations.json',regions(r));finish();await release('translator');return r
 async def _run_mask_refinement(self,c,x):
  start('C-mask');r=await super()._run_mask_refinement(c,x);finish();return r
 async def _run_inpainting(self,c,x):
  start('C-inpainting');r=await super()._run_inpainting(c,x);finish();await release('inpaint');return r
 async def _run_text_rendering(self,c,x):
  start('C-rendering');r=await super()._run_text_rendering(c,x);finish();return r
async def main():
 image=np.array(Image.open(source).convert('RGB'))
 start('A-detection');lines,mask,_=await detection.dispatch(cfg.detector.detector,image,1536,.5,.7,2.3,False,False,False,device='cuda');save('detected.json',rows(lines));overlay(rows(lines),'detected-regions.png');finish();await release('detector')
 start('A-ocr');lines=await ocr.dispatch(cfg.ocr.ocr,image,lines,cfg.ocr,device='cuda');raw=rows(lines);save('ocr-lines.json',raw);finish();await release('ocr')
 grouped=await merge(lines,image.shape[1],image.shape[0]);a=regions(grouped);save('ocr-regions.json',a);overlay(a,'ocr-regions.png');(O/'japanese-raw.txt').write_text('\n'.join(('[%s] %s' % (x['id'],x['japanese'])) for x in a),encoding='utf-8')
 start('B-translation');tr=localtr();await tr.load('JPN','ESP','cpu')
 outputs=[]
 for x in a:
  result=await tr.translate('JPN','ESP',[x['japanese']]);outputs.append({**x,'spanish_machine':result});save('ocr-derived-spanish.json',outputs)
 verified=[]
 for i,s in enumerate(['いや てめえらで行ってこいよ タコ','は？何 お前 口悪いな','ねえ やばいんじゃない？']):
  result=await tr.translate('JPN','ESP',[s]);verified.append({'id':i,'japanese_user_verified':s,'spanish_machine':result});save('verified-text-spanish.json',verified)
 finish();await release('translator')
 localtr();pipe=Instrumented({'use_gpu_limited':True,'kernel_size':3,'models_ttl':1,'model_dir':str(R/'evaluation/models'),'font_path':str(R/'upstream/fonts/Arial-Unicode-Regular.ttf'),'verbose':True,'input':[str(source)]})
 ctx=await pipe.translate(Image.open(source).convert('RGB'),cfg);ctx.result.save(O/'spanish-page.png');save('C-final-regions.json',regions(ctx.text_regions));save('completion.json',{'completed':True,'total_seconds':time.perf_counter()-t0})
try:asyncio.run(main())
except BaseException:
 save('failure.json',{'stage':active,'traceback':traceback.format_exc()});print(traceback.format_exc(),flush=True)
finally:done=True
