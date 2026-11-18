import os,sys,json,time,pathlib,threading,traceback,socket,subprocess,hashlib
R=pathlib.Path(__file__).resolve().parents[2];BASE=R/'evaluation/results/page11-ocr';O=R/'evaluation/results/google-page11-01/reconstruction/run-02';O.mkdir(parents=True,exist_ok=False)
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
 import asyncio,numpy as np,cv2
 from PIL import Image
 from manga_translator.utils import TextBlock
 from manga_translator.mask_refinement import dispatch as refine
 source=R/'ManualImageTest/11.jpg'
 assert hashlib.sha256(source.read_bytes()).hexdigest()=='0848f0588e807b7ed1ddc7c380dc201529abcbfd6b4ea8632d184cc298885c92'
 original=np.array(Image.open(source).convert('RGB'))
 rows=json.loads((BASE/'ocr-regions.json').read_text(encoding='utf-8'))
 approved={'R00':'¿Eh?','R04':'¡Uoooh!','R01':'¿Un espíritu? ¡Es enorme!','R03':'No había visto nada tan grande','R02':'desde que murió mi padre.'}
 save('editorial-overrides.json',{'approved_text':approved,'glossary':{'幻妖':{'Spanish':'espíritu','status':'provisional user-approved'}},'original_API_responses_unchanged':True,'regions':rows})
 raw=np.array(Image.open(BASE/'detector-raw-mask.png'))
 async def run():
  total=np.zeros(original.shape[:2],np.uint8);checks=[]
  for row in rows:
   # Constrain the upstream refinement result to narrow text supports; never erase rectangles.
   support=np.zeros_like(total)
   cv2.fillPoly(support,[np.array(p,dtype=np.int32) for p in row['polygons']],255)
   support=cv2.dilate(support,np.ones((7,7),np.uint8))
   region=TextBlock(row['polygons'],texts=[row['japanese_raw']],font_size=40)
   mask=await refine([region],original,raw.copy(),method='fit_text',dilation_offset=-10,ignore_bubble=0,kernel_size=1)
   mask=cv2.bitwise_and(mask,support)
   Image.fromarray(mask).save(O/(row['id']+'-mask-candidate.png'))
   overlay=original.copy();sel=mask>0;overlay[sel]=(overlay[sel]*.3+np.array([255,0,0])*.7).astype(np.uint8)
   Image.fromarray(overlay).save(O/(row['id']+'-mask-overlay.png'))
   total=cv2.bitwise_or(total,mask);checks.append({'id':row['id'],'masked_pixels':int(sel.sum()),'furigana_not_separately_added':True})
  Image.fromarray(total).save(O/'mask-candidate.png');sel=total>0;overlay=original.copy();overlay[sel]=(overlay[sel]*.3+np.array([255,0,0])*.7).astype(np.uint8);Image.fromarray(overlay).save(O/'mask-overlay.png')
  Image.fromarray(overlay).crop((80,1500,920,2048)).resize((1680,1096)).save(O/'lower-left-mask-detail.png')
  save('mask-checks.json',{'regions':checks,'parameters':{'method':'fit_text','dilation_offset':-10,'kernel_size':1,'support_expansion_pixels':3},'status':'candidate_requires_visual_review','inpainting_authorized_by_mask_review':False})
 asyncio.run(run());stats['completed']=True
except BaseException:stats['failure']=traceback.format_exc();print(stats['failure'],flush=True)
finally:
 done=True;stats['elapsed_seconds']=time.perf_counter()-stats.pop('started');stats['blocked_network_attempts']=len(blocked);save(stage+'-resources.json',stats);print(json.dumps(stats),flush=True)
