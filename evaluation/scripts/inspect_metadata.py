import json, urllib.request, pathlib
out = {}
urls = {
 'release': 'https://api.github.com/repos/zyddnys/manga-image-translator/releases/tags/beta-0.3',
 'nllb': 'https://huggingface.co/api/models/facebook/nllb-200-distilled-600M?blobs=true',
 'torch': 'https://pypi.org/pypi/torch/2.14.1/json',
 'transformers': 'https://pypi.org/pypi/transformers/5.19.0/json',
}
for name,url in urls.items():
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MangaLocalTranslator-evaluation'}),timeout=25) as r: data=json.load(r)
  out[name]=data
  if name=='release': print(name, [(a['name'],a['size']) for a in data['assets'] if a['name'] in ['detect-20241225.ckpt','ocr_ar_48px.ckpt','alphabet-all-v7.txt','inpainting_lama_large_512px.ckpt','inpainting_lama_large.ckpt']])
  elif name=='nllb': print(name, data.get('sha'),[(s['rfilename'],s.get('size')) for s in data['siblings']])
  else: print(name, data['info']['version'], 'python',data['info'].get('requires_python'),[(x['filename'],x['size']) for x in data['urls'] if 'win_amd64' in x['filename'] or name=='transformers'])
 except Exception as e: out[name]={'error':str(e)}; print(name,str(e))
pathlib.Path('evaluation/metadata.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
