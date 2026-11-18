import urllib.request,json,pathlib,hashlib,concurrent.futures
R=pathlib.Path(__file__).resolve().parents[2];O=R/'evaluation/results/m2m100-418m';P=R/'evaluation/models/m2m100-418m';P.mkdir(parents=True,exist_ok=True)
d=json.loads((O/'repository-metadata.json').read_text());rev=d['sha']
a=[x for x in d['siblings'] if x['rfilename'].endswith('.json') or x['rfilename'] in ['pytorch_model.bin','sentencepiece.bpe.model','README.md']]
assert sum(x['size'] for x in a)<2_000_000_000
rows=[]
def fetch(x):
 n=x['rfilename'];p=P/n;tmp=p.with_suffix(p.suffix+'.part');url=f'https://huggingface.co/facebook/m2m100_418M/resolve/{rev}/{n}'
 if not p.exists():
  with urllib.request.urlopen(url,timeout=120) as r,tmp.open('wb') as w:
   while b:=r.read(4*1024**2):w.write(b)
  tmp.replace(p)
 assert p.stat().st_size==x['size'];h=hashlib.sha256();git=hashlib.sha1(b'blob '+str(x['size']).encode()+b'\0')
 with p.open('rb') as f:
  while b:=f.read(4*1024**2):h.update(b);git.update(b)
 if x.get('lfs'):assert h.hexdigest()==x['lfs']['sha256']
 else:assert git.hexdigest()==x['blobId']
 print('Verified',n,flush=True);return {'file':n,'path':str(p),'bytes':x['size'],'sha256':h.hexdigest(),'url':url,'revision':rev}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fetch,a))
(O/'model-manifest.json').write_text(json.dumps(rows,indent=2))
