"""Evaluation-only Spanish typography experiment. No ML imports or network."""
import pathlib,json,hashlib,itertools,time
from PIL import Image,ImageDraw,ImageFont
R=pathlib.Path(__file__).resolve().parents[2];BASE=R/'evaluation/results/google-full-page-01';OLD=BASE/'reconstruction/run-01';OUT=BASE/'reconstruction/run-02';OUT.mkdir(parents=True,exist_ok=False)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected={str(p.relative_to(R)):digest(p) for p in OLD.rglob('*') if p.is_file()}
for p in [BASE/'translations.json',BASE/'response-raw.json',R/'ManualImageTest/5.jpg']:protected[str(p.relative_to(R))]=digest(p)
(OUT/'protected-files-before.json').write_text(json.dumps(protected,indent=2))
start=time.perf_counter();rows=json.loads((BASE/'translations.json').read_text(encoding='utf-8'));clean=Image.open(OLD/'cleaned-page.png').convert('RGB');old=Image.open(OLD/'spanish-page.png').convert('RGB');result=clean.copy();draw=ImageDraw.Draw(result)
fontpath=R/'upstream/fonts/Arial-Unicode-Regular.ttf'
boxes=[(795,115,995,315),(600,430,860,680),(310,930,440,1150),(940,1525,1065,1665),(690,1565,845,1765),(525,1540,655,1735)]
records=[]
for row,box,preferred in zip(rows,boxes,[32,32,26,26,26,26]):
 text=row['google_translatedText_exact'];words=text.split(' ');assert ' '.join(words)==text
 x1,y1,x2,y2=box;W=x2-x1-8;H=y2-y1-8;selected=None
 # Search only a bounded typographic size range; never change characters or split a word.
 for size in range(preferred,17,-1):
  font=ImageFont.truetype(str(fontpath),size);options=[]
  for bits in itertools.product([False,True],repeat=len(words)-1):
   lines=[];current=words[0]
   for split,word in zip(bits,words[1:]):
    if split:lines.append(current);current=word
    else:current+=' '+word
   lines.append(current);widths=[draw.textlength(s,font=font) for s in lines]
   bboxes=[draw.textbbox((0,0),s,font=font) for s in lines];lineheight=max(b[3]-b[1] for b in bboxes);gap=round(size*.2);height=lineheight*len(lines)+gap*(len(lines)-1)
   if max(widths)>W or height>H:continue
   score=(len(lines),sum((W-w)**2 for w in widths))
   options.append((score,lines,bboxes,lineheight,gap,height,widths))
  if options:selected=(size,font,min(options,key=lambda v:v[0]));break
 if not selected:
  result.paste(old.crop(box),box[:2]);records.append({'id':row['id'],'status':'baseline_fallback_no_fit','exact_text':text});continue
 size,font,(_,lines,bboxes,lineheight,gap,height,widths)=selected
 assert ' '.join(lines)==text
 ink=Image.new('L',clean.size,0);idraw=ImageDraw.Draw(ink);top=y1+(y2-y1-height)/2;placements=[]
 for line,bb,width in zip(lines,bboxes,widths):
  left=x1+(x2-x1-(bb[2]-bb[0]))/2-bb[0];y=top-bb[1]
  idraw.text((round(left),round(y)),line,font=font,fill=255);placements.append([round(left),round(y)]);top+=lineheight+gap
 ib=ink.getbbox();assert ib and ib[0]>=x1 and ib[1]>=y1 and ib[2]<=x2 and ib[3]<=y2
 # No new ink may cover dark/nonwhite artwork or balloon borders.
 bad=sum(1 for yy in range(ib[1],ib[3]) for xx in range(ib[0],ib[2]) if ink.getpixel((xx,yy))>0 and min(clean.getpixel((xx,yy)))<230)
 if bad:
  result.paste(old.crop(box),box[:2]);status='baseline_fallback_artwork_guard'
 else:
  result.paste((0,0,0),(0,0,*clean.size),ink);status='experimental_rendered'
 records.append({'id':row['id'],'status':status,'exact_text':text,'lines':lines,'font_size':size,'baseline_font_size':dict(zip(['page5-C%02d'%i for i in range(6)],[26,30,20,20,24,18]))[row['id']],'box_xyxy':box,'ink_bbox':ib,'placements':placements,'word_splits':0,'text_exact_after_join':True,'new_ink_over_nonwhite_pixels':bad})
result.save(OUT/'spanish-page.png')
# Native-size comparison, with labels outside image content.
comparison=Image.new('RGB',(old.width*2,old.height+60),'#dddddd');label=ImageDraw.Draw(comparison);lf=ImageFont.truetype(str(fontpath),24);label.text((20,15),'RUN-01 — unchanged baseline',fill='black',font=lf);label.text((old.width+20,15),'RUN-02 — experimental typography',fill='black',font=lf);comparison.paste(old,(0,60));comparison.paste(result,(old.width,60));comparison.save(OUT/'side-by-side.png')
comparison.resize((1403,1054)).save(OUT/'side-by-side-preview.png')
# Larger per-region comparisons make visual regressions inspectable.
for record,box in zip(records,boxes):
 pad=30;b=(box[0]-pad,box[1]-pad,box[2]+pad,box[3]+pad);a=old.crop(b);c=result.crop(b);pair=Image.new('RGB',(a.width*2,a.height),'white');pair.paste(a,(0,0));pair.paste(c,(a.width,0));pair.resize((pair.width*2,pair.height*2)).save(OUT/(record['id']+'-comparison.png'))
assert all(digest(R/p)==h for p,h in protected.items())
(OUT/'render-status.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'integrity.json').write_text(json.dumps({'all_protected_files_unchanged':True,'dimensions':list(result.size),'elapsed_seconds':time.perf_counter()-start,'protected_files':len(protected),'network_requests':0,'model_loads':0},indent=2))
print(json.dumps(records,ensure_ascii=True,indent=2))
