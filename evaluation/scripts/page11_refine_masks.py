"""Evaluation-only pixel/connected-component mask review; no ML or network."""
from pathlib import Path
import json,hashlib,time
import numpy as np,cv2,psutil
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[2];OLD=R/'evaluation/results/google-page11-01/reconstruction/run-02';O=R/'evaluation/results/google-page11-01/mask-refinement/run-02';O.mkdir(parents=True,exist_ok=False)
start=time.perf_counter()
protected=[R/'ManualImageTest/11.jpg',*OLD.glob('*'),* (R/'evaluation/results/google-page11-01').glob('*.json'),*(R/'evaluation/results/page11-ocr').glob('*')]
protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
im=Image.open(R/'ManualImageTest/11.jpg').convert('RGB');rgb=np.array(im);gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY);H,W=gray.shape
def save(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
# Hand-reviewed character cells, source image pixel coordinates, x2/y2 exclusive.
cells={'R00':[(1258,1234,1309,1326)],'R04':[(698,1012,743,1174)],'R01':[(991,1568,1036,1736),(1036,1568,1090,1704)],'R02':[],'R03':[]}
for a,b in [(1546,1592),(1593,1638),(1640,1684),(1687,1735),(1736,1782),(1783,1829),(1830,1875)]:cells['R02'].append((191,a,244,b))
for a,b in [(1544,1592),(1593,1641),(1643,1696)]:cells['R02'].append((117,a,179,b))
for a,b in [(1549,1593),(1594,1641),(1642,1689),(1690,1737),(1738,1783),(1784,1827),(1828,1876)]:cells['R03'].append((825,a,884,b))
for a,b in [(1542,1593),(1594,1643),(1644,1695)]:cells['R03'].append((755,a,811,b))
cells['R02']=[(112,1537,192,1699),(186,1538,269,1880)]
cells['R03']=[(751,1538,827,1700),(822,1544,888,1882)]
furigana={'R00':[],'R04':[],'R01':[(1089,1568,1112,1667)],'R02':[(176,1559,192,1645),(242,1548,266,1624),(243,1699,260,1726),(242,1832,265,1875)],'R03':[(808,1554,825,1585)]}
# Deliberately conservative exclusions around large effects; all pixels including outlines protected.
fx=[(85,0,650,455),(900,250,1295,780),(110,970,430,1320),(268,1630,500,2030),(580,1580,752,1815),(735,1740,825,2048)]
exclude=np.zeros((H,W),np.uint8)
for x1,y1,x2,y2 in fx:exclude[y1:y2,x1:x2]=255
Image.fromarray(exclude).save(O/'protected-effects-zones.png')
records=[];union=np.zeros_like(gray);rejectunion=np.zeros_like(gray)
for rid in ['R00','R04','R01','R03','R02']:
 mask=np.zeros_like(gray);rejected=[]
 for kind,boxes in [('main',cells[rid]),('furigana',furigana[rid])]:
  for box in boxes:
   x1,y1,x2,y2=box;g=gray[y1:y2,x1:x2];binary=(g<150).astype(np.uint8)
   n,labels,stats,_=cv2.connectedComponentsWithStats(binary,8)
   selected=np.zeros_like(g)
   for i in range(1,n):
    x,y,w,h,area=map(int,stats[i]);border=x==0 or y==0 or x+w==g.shape[1] or y+h==g.shape[0]
    # Reject edge-crossing components in illustration text rather than guess their identity.
    if area<2:continue
    if rid in ('R02','R03') and border:
     rejected.append({'cell':box,'kind':kind,'component_xywh':[x+x1,y+y1,w,h],'area':area});rejectunion[y1:y2,x1:x2][labels==i]=255;continue
    selected[labels==i]=255
   expanded=cv2.dilate(selected,np.ones((3,3),np.uint8))
   mask[y1:y2,x1:x2]=cv2.bitwise_or(mask[y1:y2,x1:x2],expanded)
 mask[exclude>0]=0
 Image.fromarray(mask).save(O/(rid+'-refined-mask.png'));union=cv2.bitwise_or(union,mask)
 old=np.array(Image.open(OLD/(rid+'-mask-candidate.png')))
 rec={'id':rid,'main_character_cells':cells[rid],'furigana_cells':furigana[rid],'rejected_boundary_components':rejected,'old_pixels':int((old>0).sum()),'refined_pixels':int((mask>0).sum()),'added_pixels':int(((mask>0)&(old==0)).sum()),'excluded_old_pixels':int(((mask==0)&(old>0)).sum()),'risk':'lower, pending user review' if rid in ('R00','R04','R01') else 'high: illustration and halo uncertainty; do not inpaint'};records.append(rec)
 overlay=rgb.copy();sel=mask>0;overlay[sel]=(overlay[sel]*.3+np.array([255,0,0])*.7).astype('uint8')
 Image.fromarray(overlay).save(O/(rid+'-overlay.png'))
 if rid in ('R02','R03'):
  box=(100,1520,285,1900) if rid=='R02' else (740,1520,905,1900)
  Image.fromarray(overlay).crop(box).resize(((box[2]-box[0])*3,(box[3]-box[1])*3)).save(O/(rid+'-enlarged-overlay.png'))
Image.fromarray(union).save(O/'refined-mask.png');Image.fromarray(rejectunion).save(O/'rejected-ambiguous-components.png')
overlay=rgb.copy();sel=union>0;overlay[sel]=(overlay[sel]*.3+np.array([255,0,0])*.7).astype('uint8');Image.fromarray(overlay).save(O/'refined-overlay.png')
# Magenta on charcoal shows exact proposed removal pixels without altering the source.
pixels=np.full_like(rgb,32);pixels[sel]=[255,0,255];Image.fromarray(pixels).save(O/'pixels-to-remove.png')
old=np.array(Image.open(OLD/'mask-candidate.png'));delta=np.zeros_like(rgb);delta[(old>0)&(union==0)]=[0,180,255];delta[(old>0)&(union>0)]=[180,180,180];delta[(old==0)&(union>0)]=[255,150,0];Image.fromarray(delta).save(O/'mask-difference.png')
oldov=Image.open(OLD/'mask-overlay.png');pair=Image.new('RGB',(W*2,H+45),'white');pair.paste(oldov,(0,45));pair.paste(Image.fromarray(overlay),(W,45));d=ImageDraw.Draw(pair);d.text((15,12),'PREVIOUS mask',fill='black');d.text((W+15,12),'REFINED candidate - not approved',fill='black');pair.save(O/'before-after.png');pair.resize((1403,1047)).save(O/'before-after-preview.png')
save('review-metadata.json',{'method':'manual character cells + black-ink connected components (<150), 1px expansion; reject boundary components over artwork','regions':records,'effect_exclusion_rectangles':fx,'effect_zone_masked_pixels':int(((union>0)&(exclude>0)).sum()),'white_halos_not_fully_removed':True,'no_inpainting':True,'no_rendering':True,'caption_proposal':{'method':'separate external footer, original image preserved in full','extended_canvas':[1403,2268],'R03_box_xyxy':[723,2078,1373,2238],'R02_box_xyxy':[30,2078,680,2238],'reading_order':['R03','R02'],'note':'coordinates only, not rendered or adopted'}})
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
save('integrity.json',{'protected_file_count':len(protected),'all_unchanged':True,'elapsed_seconds':time.perf_counter()-start,'final_rss_bytes':psutil.Process().memory_info().rss,'available_ram_bytes':psutil.virtual_memory().available,'model_loads':0,'API_requests':0})
print(json.dumps(records,ensure_ascii=True))
