import json,urllib.request,pathlib
p=pathlib.Path('evaluation/metadata.json'); out=json.loads(p.read_text(encoding='utf-8'))
for name,repo in [('lama','dreMaz/AnimeMangaInpainting'),('mocr','kha-white/manga-ocr-base'),('m2m','facebook/m2m100_418M')]:
 try:
  with urllib.request.urlopen('https://huggingface.co/api/models/'+repo+'?blobs=true',timeout=25) as r: d=json.load(r)
  out[name]=d
  print(name,d.get('sha'),'license',d.get('cardData',{}).get('license'),[(s['rfilename'],s.get('size')) for s in d.get('siblings',[]) if s['rfilename'].endswith(('.ckpt','.bin','.safetensors'))])
 except Exception as e: print(name,str(e))
print('nllb license',out['nllb'].get('cardData',{}).get('license'))
p.write_text(json.dumps(out,indent=2),encoding='utf-8')
