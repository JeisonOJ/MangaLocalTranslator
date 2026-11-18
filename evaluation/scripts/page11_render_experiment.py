"""One experimental layout using approved Run-02 whole-word fit/centering rules."""
from pathlib import Path
import json,itertools,time,hashlib
from PIL import Image,ImageDraw,ImageFont
import psutil
R=Path(__file__).resolve().parents[2];O=R/'evaluation/results/google-page11-01/reconstruction/experiment-01';assert not (O/'spanish-page.png').exists()
t=time.perf_counter();clean=Image.open(O/'cleaned-page.png').convert('RGB');original=Image.open(R/'ManualImageTest/11.jpg').convert('RGB');result=clean.copy();draw=ImageDraw.Draw(result);fontpath=R/'upstream/fonts/Arial-Unicode-Regular.ttf'
items=[('R00','¿Eh?',(1249,1230,1318,1338),28),('R04','¡Uoooh!',(677,1010,764,1178),26),('R01','¿Un espíritu? ¡Es enorme!',(986,1568,1117,1738),26),('R03','No había visto nada tan grande',(752,1539,888,1880),26),('R02','desde que murió mi padre.',(115,1540,267,1878),26)]
records=[]
for rid,text,box,preferred in items:
 if psutil.virtual_memory().available<500*1024**2:raise RuntimeError('RAM guard')
 x1,y1,x2,y2=box;W=x2-x1-8;H=y2-y1-8;words=text.split(' ');selected=None
 for size in range(preferred,15,-1):
  font=ImageFont.truetype(str(fontpath),size);options=[]
  for bits in itertools.product([False,True],repeat=len(words)-1):
   lines=[];current=words[0]
   for split,word in zip(bits,words[1:]):
    if split:lines.append(current);current=word
    else:current+=' '+word
   lines.append(current);widths=[draw.textlength(s,font=font) for s in lines];bbs=[draw.textbbox((0,0),s,font=font) for s in lines];lh=max(b[3]-b[1] for b in bbs);gap=round(size*.2);height=lh*len(lines)+gap*(len(lines)-1)
   if max(widths)<=W and height<=H:options.append(((len(lines),sum((W-w)**2 for w in widths)),lines,bbs,lh,gap,height))
  if options:selected=(size,font,min(options,key=lambda v:v[0]));break
 if not selected:raise RuntimeError('No complete-word fit for '+rid)
 size,font,(_,lines,bbs,lh,gap,height)=selected;assert ' '.join(lines)==text
 ink=Image.new('L',clean.size);idraw=ImageDraw.Draw(ink);top=y1+(y2-y1-height)/2
 for line,bb in zip(lines,bbs):
  left=x1+(x2-x1-(bb[2]-bb[0]))/2-bb[0];idraw.text((round(left),round(top-bb[1])),line,font=font,fill=255);top+=lh+gap
 ib=ink.getbbox();assert ib[0]>=x1 and ib[1]>=y1 and ib[2]<=x2 and ib[3]<=y2
 # Experimental full-page authorization: record nonwhite overlap rather than silently omit a region.
 overlap=sum(ink.getpixel((x,y))>0 and min(clean.getpixel((x,y)))<230 for y in range(ib[1],ib[3]) for x in range(ib[0],ib[2]))
 result.paste((0,0,0),(0,0,*clean.size),ink);records.append({'id':rid,'exact_spanish':text,'font_size':size,'lines':lines,'box_xyxy':box,'ink_bbox':ib,'word_splits':0,'complete_text':True,'ink_over_nonwhite_background_pixels':overlap,'status':'rendered_experimental_needs_visual_review'})
result.save(O/'spanish-page.png');pair=Image.new('RGB',(2806,2093),'white');pair.paste(original,(0,45));pair.paste(result,(1403,45));d=ImageDraw.Draw(pair);d.text((20,12),'ORIGINAL',fill='black');d.text((1423,12),'EXPERIMENTAL SPANISH - NOT APPROVED',fill='black');pair.save(O/'side-by-side.png');pair.resize((1403,1047)).save(O/'side-by-side-preview.png')
for rid,box in [('R03',(735,1510,920,2048)),('R02',(95,1510,290,1930))]:
 a=original.crop(box);b=result.crop(box);p=Image.new('RGB',(a.width*2,a.height));p.paste(a,(0,0));p.paste(b,(a.width,0));p.resize((p.width*2,p.height*2)).save(O/(rid+'-before-after.png'))
hashes=json.loads((O/'protected-hashes.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
(O/'render-status.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8');(O/'render-resources.json').write_text(json.dumps({'elapsed_seconds':time.perf_counter()-t,'end_rss_bytes':psutil.Process().memory_info().rss,'available_ram_bytes':psutil.virtual_memory().available,'all_protected_files_unchanged':True,'dimensions':list(result.size)}));print(json.dumps(records))
