import os,sys,json,time,pathlib,threading,traceback,socket,subprocess,hashlib
R=pathlib.Path(__file__).resolve().parents[2];BASE=R/'evaluation/results/google-page11-01';O=BASE/'reconstruction/experiment-01';O.mkdir(parents=True,exist_ok=False)
stage=sys.argv[1];stats={'stage':stage,'started':time.perf_counter()};done=False
import psutil
proc=psutil.Process()
def save(name,d):(O/name).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def watch():
 last=0
 while not done:
  v=psutil.virtual_memory();stats['peak_rss_bytes']=max(stats.get('peak_rss_bytes',0),proc.memory_info().rss);stats['peak_system_used_bytes']=max(stats.get('peak_system_used_bytes',0),v.used);stats['minimum_available_ram_bytes']=min(stats.get('minimum_available_ram_bytes',v.available),v.available)
  if v.available<500*1024**2:stats['failure']='Available RAM below 500 MiB';save(stage+'-resources.json',stats);os._exit(70)
  if time.time()-last>1:
   last=time.time()
   try:
    line=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader,nounits'],creationflags=subprocess.CREATE_NO_WINDOW,text=True).strip();used,free=map(int,line.split(','));stats['peak_total_gpu_used_MiB']=max(stats.get('peak_total_gpu_used_MiB',0),used);stats['minimum_gpu_free_MiB']=min(stats.get('minimum_gpu_free_MiB',free),free)
   except Exception:pass
  time.sleep(.05)
threading.Thread(target=watch,daemon=True).start()
for k,v in {'HF_HOME':str(R/'evaluation/cache/huggingface'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','TORCH_HOME':str(R/'evaluation/cache/torch')}.items():os.environ[k]=v
blocked=[]
def deny(*a,**kw):blocked.append('blocked external network attempt');raise RuntimeError('No network during reconstruction')
original_connect=socket.socket.connect
def local_connect(self,address):
 if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'):return original_connect(self,address)
 return deny()
socket.socket.connect=local_connect;socket.create_connection=deny
sys.path.insert(0,str(R/'upstream'))
try:
 import asyncio,numpy as np,torch
 from PIL import Image
 from manga_translator.utils import ModelWrapper
 from manga_translator.inpainting.inpainting_lama_mpe import LamaLargeInpainter
 from manga_translator.config import InpainterConfig
 ModelWrapper._MODEL_DIR=str(R/'evaluation/models')
 async def nodownload(self,*a,**kw):
  if not self._check_downloaded():raise RuntimeError('Downloads prohibited: missing local weights')
 ModelWrapper.download=nodownload
 source=R/'ManualImageTest/11.jpg';assert hashlib.sha256(source.read_bytes()).hexdigest()=='0848f0588e807b7ed1ddc7c380dc201529abcbfd6b4ea8632d184cc298885c92'
 protected=[source,*(BASE.glob('*.json')),*(R/'evaluation/results/page11-ocr').glob('*.json'),*(BASE/'reconstruction/run-02').glob('*'),*(BASE/'mask-refinement/run-02').glob('*'),*(R/'evaluation/results/google-full-page-01/reconstruction/run-02').glob('*')]
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()};save('protected-hashes.json',hashes)
 original=np.array(Image.open(source).convert('RGB'));maskpath=BASE/'mask-refinement/run-02/refined-mask.png';mask=np.array(Image.open(maskpath));assert mask.shape==original.shape[:2]
 save('provenance.json',{'mask_source':str(maskpath),'mask_sha256':hashlib.sha256(maskpath.read_bytes()).hexdigest(),'LaMa_passes_maximum':1,'dimensions':[1403,2048],'precision':'fp32','processing_limit':1024})
 Image.fromarray(mask).save(O/'mask-used.png');overlay=original.copy();sel=mask>0;overlay[sel]=(overlay[sel]*.3+np.array([255,0,0])*.7).astype('uint8');Image.fromarray(overlay).save(O/'mask-overlay.png')
 async def run():
  torch.cuda.reset_peak_memory_stats();model=LamaLargeInpainter();await model._load('cuda');t=time.perf_counter()
  out=await model._infer(original,mask,InpainterConfig(inpainter='lama_large',inpainting_size=1024,inpainting_precision='fp32'),1024,False)
  stats['inpaint_seconds']=time.perf_counter()-t;assert np.array_equal(out[mask==0],original[mask==0]);Image.fromarray(out.astype('uint8')).save(O/'cleaned-page.png')
  stats['peak_torch_allocated_bytes']=torch.cuda.max_memory_allocated();stats['peak_torch_reserved_bytes']=torch.cuda.max_memory_reserved();await model._unload()
  save('pixel-integrity.json',{'all_pixels_outside_mask_unchanged':True,'one_inpainting_pass':True})
 asyncio.run(run());assert all(hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items());stats['completed']=True
except BaseException:stats['failure']=traceback.format_exc();print(stats['failure'],flush=True)
finally:
 done=True;stats['elapsed_seconds']=time.perf_counter()-stats.pop('started');stats['blocked_network_attempts']=len(blocked);save(stage+'-resources.json',stats);print(json.dumps(stats),flush=True)
