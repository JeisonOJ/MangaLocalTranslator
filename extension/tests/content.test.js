import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import {tree} from './dom-fixture.js';
function page() {
 const f=tree(),messages=[],handlers={},frames=[];let listener,tick,now=0,mutation;
 class Img extends f.El {constructor(id){super('img',{id});Object.assign(this,{classList:['page'],alt:'Page 1',naturalWidth:1403,naturalHeight:2048,complete:true,currentSrc:'https://cdn.example/full.jpg',src:'https://cdn.example/thumb.jpg'});}}
 const im=f.body.append(new Img('page-1'));f.doc.images=[im];
 const overlay=new f.El('div');overlay.style={};overlay.setAttribute=(key,value)=>overlay.attrs[key]=value;
 overlay.remove=()=>{overlay.removed=true;if(overlay.parentElement)overlay.parentElement.children=overlay.parentElement.children.filter(n=>n!==overlay);};
 f.doc.createElement=type=>{if(type==='canvas')throw Error('tainted');return overlay;};
 f.doc.addEventListener=(k,v)=>handlers[k]=v;f.doc.removeEventListener=k=>delete handlers[k];
 const ctx=vm.createContext({queueMicrotask,requestAnimationFrame:fn=>frames.push(fn),MutationObserver:class{constructor(fn){mutation=fn;}observe(){}},window:{},MouseEvent:class{constructor(type,options){Object.assign(this,{type},options);}},HTMLImageElement:Img,document:f.doc,__captureReader:f.reader,location:{href:'https://reader.example/one'},Date:{now:()=>now},setInterval(fn){tick=fn;},chrome:{runtime:{sendMessage:async m=>messages.push(m),onMessage:{addListener(fn){listener=fn;}}}}});
 vm.runInContext(fs.readFileSync(new URL('../content.js',import.meta.url),'utf8'),ctx);
 const command=m=>{let out;listener(m,null,r=>out=r);return out;};
 return {...f,im,Img,overlay,messages,handlers,command,tick:()=>tick(),time:n=>now=n,mutation:()=>mutation(),frame:()=>frames.splice(0).forEach(fn=>fn())};
}
test('image picker uses currentSrc, tall geometry and Escape',()=>{
 const p=page();assert(p.command({type:'pick'}).ok);p.handlers.mousemove({target:p.im});assert.equal(p.overlay.style.top,'-600px');assert.equal(p.overlay.style.height,'2048px');
 p.handlers.click({target:p.im,preventDefault(){},stopImmediatePropagation(){}});assert.equal(p.messages[0].image.url,p.im.currentSrc);assert.equal(p.messages[0].image.fingerprint,null);
 p.command({type:'pick'});p.handlers.keydown({key:'Escape',preventDefault(){},stopImmediatePropagation(){}});assert(!p.handlers.click);
});
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
test('rapid decoded resources are eligible after two frames without waiting for polling',async()=>{
 const p=page();p.im.decode=()=>Promise.resolve();p.command({type:'watch',descriptor:p.reader.describe(p.im)});await flush();
 assert(!p.messages.some(m=>m.image));p.frame();await flush();assert(!p.messages.some(m=>m.image));p.frame();await flush();
 assert.equal(p.messages.at(-1).image.url,p.im.currentSrc);
 p.im.currentSrc='https://cdn.example/next.jpg';p.mutation();await flush();p.frame();await flush();p.frame();await flush();assert.equal(p.messages.at(-1).image.url,p.im.currentSrc);
});
test('delayed loading and superseded transient resources never produce ready observations',async()=>{
 const p=page();let resolve;p.im.complete=false;p.im.decode=()=>new Promise(r=>resolve=r);
 p.command({type:'watch',descriptor:p.reader.describe(p.im)});await flush();assert.equal(p.messages.at(-1).diagnostic.imageStatus,'image_loading');
 p.im.complete=true;p.im.currentSrc='https://cdn.example/transient.jpg';p.handlers.load();await flush();
 p.im.currentSrc='https://cdn.example/final.jpg';resolve();await flush();p.frame();p.frame();await flush();
 assert(!p.messages.some(m=>m.image?.url.includes('transient')));
 resolve();await flush();p.frame();await flush();p.frame();await flush();assert.equal(p.messages.at(-1).image.url,p.im.currentSrc);
});
test('decode errors stay ineligible and polling retains compatibility fallback',async()=>{
 const p=page();p.im.decode=()=>Promise.reject(Error('bad image'));p.command({type:'watch',descriptor:p.reader.describe(p.im)});await flush();p.time(2000);await p.tick();assert(!p.messages.some(m=>m.image));assert.equal(p.messages.at(-1).diagnostic.imageStatus,'image_decode_failed');
});
test('fresh document reacquires changed-ID image, hidden retained nodes do not block new resources',async()=>{
 const old=page(),d={...old.reader.describe(old.im),parent:'BODY.>HTML.',classes:'page',alt:'Page #',ratio:1403/2048};
 const p=page();p.im.id='page-2';p.im.currentSrc='https://cdn.example/2.jpg';p.command({type:'watch',descriptor:d});assert.equal(p.command({type:'inspect'}).image.url,p.im.currentSrc);
 p.im.hidden=true;const next=p.body.append(new p.Img('page-3'));next.currentSrc='https://cdn.example/3.jpg';p.doc.images.push(next);
 assert.equal(p.command({type:'inspect'}).image.url,next.currentSrc);
 await p.tick();p.time(1500);await p.tick();assert.equal(p.messages.at(-1).image.url,next.currentSrc);assert.equal(p.messages.at(-1).diagnostic.imageStatus,'image_ready');
});
test('click acknowledgement follows invocation and distinguishes errors',()=>{
 const p=page(),b=p.nav.append(new p.El('button')),d=p.reader.describe(b);
 const response=p.command({type:'clickNext',descriptor:d});assert.equal(b.clicked,1);assert.equal(response.diagnostic.status,'click_dispatched');assert(response.diagnostic.eventObserved);
 b.clickError=true;assert.equal(p.command({type:'clickNext',descriptor:d}).error,'click_failed');
});
test('clickable areas retain the user-selected relative point on subsequent clicks',()=>{
 const p=page(),area=p.nav.append(new p.El('div'));
 p.command({type:'pickControl'});
 p.handlers.click({target:area,clientX:635,clientY:424,preventDefault(){},stopImmediatePropagation(){}});
 const d=p.messages.at(-1).descriptor;assert.equal(d.point.x,.9);assert.equal(d.point.y,.5);
 assert(p.command({type:'clickNext',descriptor:d}).ok);assert.equal(area.lastEvent.clientX,635);assert.equal(area.lastEvent.clientY,424);
});
test('first click preserves the manually selected live node after storage reorders descriptor keys',()=>{
 const p=page(),chosen=p.nav.append(new p.El('button'));
 p.command({type:'pickControl'});
 p.handlers.click({target:chosen,clientX:355,clientY:424,preventDefault(){},stopImmediatePropagation(){}});
 const reorder=value=>Array.isArray(value)?value.map(reorder):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,reorder(value[k])])):value;
 const stored=reorder(p.messages.at(-1).descriptor);
 p.nav.append(new p.El('button')); // Same selected node survives a routine sibling DOM update.
 const response=p.command({type:'clickNext',descriptor:stored});
 assert(response.ok);assert.equal(chosen.clicked,1);assert.equal(response.diagnostic.match,'retained_live_selection');
});
