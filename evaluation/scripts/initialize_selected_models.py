import os,sys,pathlib,json,threading,time,psutil,asyncio,traceback,gc
root=pathlib.Path(__file__).resolve().parents[2];os.environ['HF_HOME']=str(root/'evaluation/cache/huggingface');os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';sys.path.insert(0,str(root/'upstream'))
import torch
from manga_translator.utils import ModelWrapper
from manga_translator.detection.default import DefaultDetector
from manga_translator.ocr.model_48px import Model48pxOCR
from manga_translator.inpainting.inpainting_lama_mpe import LamaLargeInpainter
from manga_translator.translators.nllb import NLLBTranslator
ModelWrapper._MODEL_DIR=str(root/'evaluation/models')
report=[];process=psutil.Process();stop=False;current={}
def sample():
 while not stop:
  if current:
   current['peak_process_rss_bytes']=max(current.get('peak_process_rss_bytes',0),process.memory_info().rss)
   current['peak_system_used_ram_bytes']=max(current.get('peak_system_used_ram_bytes',0),psutil.virtual_memory().used)
  time.sleep(.05)
threading.Thread(target=sample,daemon=True).start()
async def main():
 global current
 for name,cls,device in [('detector',DefaultDetector,'cuda'),('ocr48',Model48pxOCR,'cuda'),('lama_large',LamaLargeInpainter,'cuda'),('nllb600',NLLBTranslator,'cpu')]:
  current={'model':name,'device':device};torch.cuda.reset_peak_memory_stats();obj=cls()
  try:
   if name=='nllb600':
    obj._TRANSLATOR_MODEL=str(root/'evaluation/models/nllb-600m')
    await obj._load('jpn_Jpan','spa_Latn','cpu')
    assert obj.tokenizer.convert_tokens_to_ids('spa_Latn')!=obj.tokenizer.unk_token_id
   else:await obj._load(device)
   current['loaded']=True
  except Exception:
   current['loaded']=False;current['error']=traceback.format_exc()
  current['peak_torch_gpu_allocated_bytes']=torch.cuda.max_memory_allocated();current['peak_torch_gpu_reserved_bytes']=torch.cuda.max_memory_reserved();report.append(dict(current));(root/'evaluation/models/loading-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(current),flush=True)
  failed=not current['loaded'];current={};del obj;gc.collect();torch.cuda.empty_cache()
  if failed:break
asyncio.run(main());stop=True
