import os,sys,json,time,pathlib,threading,traceback,socket,subprocess,hashlib
R=pathlib.Path(__file__).resolve().parents[2];BASE=R/'evaluation/results/google-full-page-01';O=BASE/'reconstruction/run-01';O.mkdir(parents=True,exist_ok=True)
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
 from manga_translator.utils import Quadrilateral,TextBlock,ModelWrapper
 from manga_translator.textline_merge import dispatch as merge
 from manga_translator.mask_refinement import dispatch as refine
 from manga_translator.inpainting.inpainting_lama_mpe import LamaLargeInpainter
 from manga_translator.config import InpainterConfig
 from manga_translator.rendering import dispatch as render
 ModelWrapper._MODEL_DIR=str(R/'evaluation/models')
 rows=json.loads((BASE/'translations.json').read_text(encoding='utf-8'));raw=json.loads((BASE/'response-raw.json').read_text(encoding='utf-8'))['data']['translations'];assert len(rows)==len(raw)==6
 source=R/'ManualImageTest/5.jpg';assert hashlib.sha256(source.read_bytes()).hexdigest()=='e57e26a93fa353ccd0c3b71b4ebd419b79124ff928785d7de293ab594dd9aa18'
 for i,row in enumerate(rows):assert row['id']=='page5-C%02d'%i and row['google_translatedText_exact']==raw[i]['translatedText']
 original=np.array(Image.open(source).convert('RGB'));assert original.shape==(2048,1403,3)
 async def run():
  if stage=='mask':
   saved=json.loads((R/'evaluation/results/first-page-test/C-ocr.json').read_text(encoding='utf-8'));approved=[q for row in rows for q in row['polygons']];quads=[Quadrilateral(np.array(q['polygon']),q['japanese_raw'],q['probability'],bg_r=255,bg_g=255,bg_b=255) for q in saved if q['polygon'] in approved]
   merged=await merge(quads,1403,2048);regions=[];meta=[]
   for row in rows:
    b=next(x for x in merged if x.lines.tolist()==row['polygons']);assert b.text==row['japanese'];regions.append(b);meta.append({'id':row['id'],'font_size':int(b.font_size),'angle':float(b.angle),'texts':b.texts,'lines':b.lines.tolist()})
   save('region-metadata.json',meta)
   mask=await refine(regions,original,np.array(Image.open(R/'evaluation/results/first-page-test/C-debug/mask_raw.png')),method='fit_text',dilation_offset=20,ignore_bubble=0,kernel_size=3)
   Image.fromarray(mask).save(O/'mask-final.png');overlay=original.copy();sel=mask>0;overlay[sel]=((overlay[sel].astype(float)*.35)+np.array([255,0,0])*.65).astype('uint8');Image.fromarray(overlay).save(O/'mask-overlay.png')
   save('mask-checks.json',{'masked_pixels':int(sel.sum()),'page_number_masked_pixels':int(sel[1933:1974,1224:1279].sum()),'dimensions':[1403,2048]})
  elif stage=='inpaint':
   mask=np.array(Image.open(O/'mask-final.png'));torch.cuda.reset_peak_memory_stats();model=LamaLargeInpainter();await model._load('cuda');start=time.perf_counter();out=await model._infer(original,mask,InpainterConfig(inpainter='lama_large',inpainting_size=1024,inpainting_precision='fp32'),1024,False);stats['inpaint_seconds']=time.perf_counter()-start
   outside=mask==0;assert np.array_equal(out[outside],original[outside]);Image.fromarray(out.astype('uint8')).save(O/'cleaned-page.png');save('outside-mask-check.json',{'unchanged_outside_mask':True});stats['peak_torch_allocated_bytes']=torch.cuda.max_memory_allocated();stats['peak_torch_reserved_bytes']=torch.cuda.max_memory_reserved();await model._unload()
  elif stage in ('render','render-fit'):
   meta=json.loads((O/'region-metadata.json').read_text(encoding='utf-8'));regions=[]
   for row,m in zip(rows,meta):
    b=TextBlock(m['lines'],texts=m['texts'],font_size=m['font_size'],angle=m['angle'],fg_color=(0,0,0),bg_color=(255,255,255),direction='horizontal',alignment='center',target_lang='ESP',translation=row['google_translatedText_exact']);b.adjust_bg_color=False;regions.append(b)
   cleaned=np.array(Image.open(O/'cleaned-page.png').convert('RGB'));render_mask=np.zeros(cleaned.shape[:2],dtype='uint8')
   if stage=='render-fit':
    from manga_translator.rendering import render as render_one,text_render
    text_render.set_font(str(R/'upstream/fonts/Arial-Unicode-Regular.ttf'))
    out=cleaned
    for b,size in zip(regions,[26,30,20,20,24,18]):
     b.font_size=size
     out=render_one(out,b,b.min_rect,False,None,False)
   else:
    out=await render(cleaned,regions,str(R/'upstream/fonts/Arial-Unicode-Regular.ttf'),font_size_minimum=-1,hyphenate=False,render_mask=render_mask)
   for row,b in zip(rows,regions):assert row['google_translatedText_exact']==b.translation
   Image.fromarray(out).save(O/'spanish-page.png');Image.fromarray(render_mask*255).save(O/'render-areas.png');save('render-status.json',[{'id':row['id'],'exact_spanish':b.translation,'text_passed_to_renderer':b.get_translation_for_rendering(),'font_size':b.font_size,'direction':b.direction,'status':'render_call_completed_needs_visual_QA'} for row,b in zip(rows,regions)])
  else:raise ValueError(stage)
 asyncio.run(run());stats['completed']=True
except BaseException:stats['failure']=traceback.format_exc();print(stats['failure'],flush=True)
finally:
 done=True;stats['elapsed_seconds']=time.perf_counter()-stats.pop('started');stats['blocked_network_attempts']=len(blocked);save(stage+'-resources.json',stats);print(json.dumps(stats),flush=True)
