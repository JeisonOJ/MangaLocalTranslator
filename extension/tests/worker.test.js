import {test} from 'node:test';
import assert from 'node:assert/strict';
const events=()=>({listeners:[],addListener(fn){this.listeners.push(fn);},fire(...args){for(const f of this.listeners)f(...args);}});
const data={},items=new Map(),calls=[];let next=1,clickResult={ok:true,diagnostic:{status:'click_dispatched',eventObserved:true,match:'structural_path'}};
const image={url:'https://cdn.example/1.jpg',width:1403,height:2048,fingerprint:null};
const imagePath=[{tag:'IMG',index:0,family:'IMG'}],controlPath=[{tag:'BUTTON',index:1,family:'BUTTON,BUTTON'}];
let inspected=image;
globalThis.chrome={
 storage:{local:{async get(key){if(Array.isArray(key))return Object.fromEntries(key.map(k=>[k,structuredClone(data[k])]));return {[key]:structuredClone(data[key])};},async set(obj){Object.assign(data,structuredClone(obj));},async remove(key){delete data[key];}}},
 runtime:{getURL:p=>'chrome-extension://test/'+p,onMessage:events(),onStartup:events()},
 scripting:{async executeScript(o){calls.push(o);}},
 tabs:{async get(){return {url:'https://reader.example/start'};},async sendMessage(_id,m){calls.push(m);if(m.type==='inspect')return {image:inspected,href:'https://reader.example/start'};if(m.type==='clickNext')return clickResult;return {ok:true};},onUpdated:events(),onRemoved:events()},
 alarms:{async create(){},async clear(){},onAlarm:events()},
 downloads:{async download(o){calls.push(o);const id=next++;items.set(id,{id,url:o.url,finalUrl:o.url,state:'in_progress',mime:'image/jpeg',filename:o.filename});return id;},async search({id}){return items.has(id)?[items.get(id)]:[];},onChanged:events()}
};
await import('../background.js');
const popup={url:'chrome-extension://test/popup.html'},sender={tab:{id:7},frameId:0};
const message=(m,s=popup)=>new Promise(resolve=>chrome.runtime.onMessage.listeners[0](m,s,resolve));
const flush=()=>message({command:'invalid'});
const config={title:'Example',chapter:'1',direction:'Click',max:3,timeout:15};
const downloaded=()=>calls.filter(c=>c.filename).length,clicked=()=>calls.filter(c=>c.type==='clickNext').length;
async function select(){
 await message({command:'stop'});inspected=image;
 assert((await message({event:'selected',image,descriptor:{tag:'IMG',path:imagePath},href:'https://reader.example/start'},sender)).ok);
 await message({event:'controlSelected',descriptor:{tag:'BUTTON',path:controlPath,label:'any label'},href:'https://reader.example/start'},sender);
}
async function complete(){items.get(data.session.pending.downloadId).state='complete';chrome.downloads.onChanged.fire({});await flush();}
const observe=(im,href='https://reader.example/changed/path')=>message({event:'observed',image:im,href,diagnostic:{imageStatus:im?'image_ready':'image_missing',observedResource:im?.url}},sender);

test('Test Download followed by Start counts 0001 once; changing paths/resources continues sequentially',async()=>{
 await select();const before=downloaded(),clicks=clicked();assert((await message({command:'test',tabId:7,config})).ok);
 assert.equal(data.session.count,0);assert.equal(clicked(),clicks);assert.match(items.get(data.session.pending.downloadId).filename,/0001\.jpg$/);
 await complete();assert.equal(data.session.reason,'test_complete');assert.equal(data.session.count,1);assert.equal(clicked(),clicks);
 const timingStart=structuredClone(data.session.performanceStart);assert.equal(data.session.timings.length,1);assert.equal(data.session.timings[0].navigation,null);
 assert((await message({command:'start',tabId:7,config})).ok);assert.equal(downloaded(),before+1);assert.equal(clicked(),clicks+1);
 assert.deepEqual(data.session.performanceStart,timingStart);
 await observe(image);assert.equal(data.session.phase,'waiting','unchanged image is not downloaded again');
 chrome.tabs.onUpdated.fire(7,{status:'complete'},{url:'https://reader.example/other/path'});await flush();assert.equal(data.session.reason,null);
 assert(calls.some(c=>c.files?.includes('content.js')));
 await observe({...image,url:'https://cdn.example/2.jpg'});assert.equal(data.session.pending.index,2);await complete();assert.equal(clicked(),clicks+2);
 await observe({...image,url:'https://cdn.example/3.jpg'},'https://reader.example/yet/another/path');await complete();
 assert.equal(data.session.reason,'safety_limit');assert.equal(data.session.count,3);assert.equal(clicked(),clicks+2);
 assert.deepEqual(data.session.timings.map(r=>r.page),[1,2,3]);assert(Number.isFinite(data.session.timings[1].navigation));assert(Number.isFinite(data.session.timings[1].wait));assert(Number.isFinite(data.session.performanceElapsed));
});
test('Start without Test begins with 0001; Stop never advances an in-flight download',async()=>{
 await select();const n=clicked();assert((await message({command:'start',tabId:7,config})).ok);assert.equal(data.session.pending.index,1);
 await message({command:'stop'});await complete();assert.equal(data.session.reason,'user_stopped');assert.equal(clicked(),n);
});
test('duplicate resource or content is stopped without another download',async()=>{
 await select();await message({command:'start',tabId:7,config});await complete();
 await observe({...image,url:'https://cdn.example/2.jpg'});await complete();const n=downloaded();
 await observe(image);assert.equal(data.session.reason,'duplicate_page');assert.equal(downloaded(),n);
});
test('control acquisition failures and click errors are distinguished from unchanged-image timeout',async()=>{
 for(const error of ['control_missing','control_ambiguous','click_failed']) {
  await select();clickResult={ok:false,error};await message({command:'start',tabId:7,config});await complete();assert.equal(data.session.reason,error);
 }
 clickResult={ok:true,diagnostic:{status:'click_dispatched',eventObserved:true,match:'structural_path'}};
 await select();await message({command:'start',tabId:7,config});await complete();await observe(image);
 data.session.deadline=0;chrome.alarms.onAlarm.fire({name:'capture'});await flush();assert.equal(data.session.reason,'navigation_timeout');assert.match(data.session.detail,/click_dispatched; image_ready; no new image/);
});
test('download failure, maximum 1, missing image and cross-origin protections remain',async()=>{
 await select();await message({command:'start',tabId:7,config});items.get(data.session.pending.downloadId).state='interrupted';chrome.downloads.onChanged.fire({});await flush();assert.equal(data.session.reason,'download_failure');
 await select();const n=clicked();await message({command:'start',tabId:7,config:{...config,max:1}});await complete();assert.equal(data.session.reason,'safety_limit');assert.equal(clicked(),n);
 await select();await message({command:'start',tabId:7,config});await complete();data.session.deadline=0;await observe(null);assert.equal(data.session.reason,'image_missing');assert.match(data.session.detail,/image_missing/);
 await select();await message({command:'start',tabId:7,config});chrome.tabs.onUpdated.fire(7,{status:'loading'},{url:'https://other.example/page'});await flush();assert.equal(data.session.reason,'cross_origin_blocked');
});
test('changed title/chapter/source requires a fresh context and used contexts do not silently restart',async()=>{
 await select();await message({command:'test',tabId:7,config});await complete();const n=downloaded();
 assert.equal((await message({command:'start',tabId:7,config:{...config,title:'New title'}})).ok,false);
 assert.equal((await message({command:'start',tabId:7,config:{...config,chapter:'2'}})).ok,false);
 inspected={...image,url:'https://cdn.example/changed.jpg'};assert.equal((await message({command:'start',tabId:7,config})).ok,false);assert.equal(downloaded(),n);inspected=image;
 await message({command:'stop'});assert.equal((await message({command:'start',tabId:7,config})).ok,false);
 await select();assert((await message({command:'start',tabId:7,config})).ok);await message({command:'stop'});
});
test('persisted ambiguous dispatch does not issue another download',async()=>{
 data.session={reason:null,phase:'download_intent',pending:{index:1},config,count:0};const n=downloaded();chrome.alarms.onAlarm.fire({name:'capture'});await flush();assert.equal(data.session.reason,'download_uncertain');assert.equal(downloaded(),n);
});
test('ArrowRight and ArrowLeft need no selected control and never dispatch a click',async()=>{
 for(const direction of ['ArrowRight','ArrowLeft']) {
  await select();delete data.control;
  const beforeClick=clicked(),beforeArrow=calls.filter(c=>c.world==='MAIN').length;
  assert((await message({command:'start',tabId:7,config:{...config,direction}})).ok);
  await complete();assert.equal(clicked(),beforeClick);assert.equal(data.session.control,null);
  const arrows=calls.filter(c=>c.world==='MAIN');assert.equal(arrows.length,beforeArrow+1);assert.deepEqual(arrows.at(-1).args,[direction]);
  assert.equal(data.session.navigation.status,'arrow_dispatched');
  await observe({...image,url:'https://cdn.example/2.jpg'});assert.equal(data.session.pending.index,2);
  await message({command:'stop'});
 }
});
test('switching methods is persisted, uses no stale click control, and does not repeat pending actions',async()=>{
 await select();await message({command:'test',tabId:7,config});await complete();const savedControl=data.control.id,n=downloaded(),clicks=clicked();
 assert((await message({command:'setNavigation',direction:'ArrowRight'})).ok);assert.equal(data.settings.direction,'ArrowRight');
 assert((await message({command:'start',tabId:7,config:{...config,direction:data.settings.direction}})).ok);
 assert.equal(downloaded(),n);assert.equal(data.session.count,1);assert.equal(clicked(),clicks);assert.equal(data.session.control,null);assert.equal(data.control.id,savedControl);
 const actions=calls.length;
 assert((await message({command:'setNavigation',direction:'Click'})).ok);assert.equal(data.session.control.id,savedControl);assert.equal(clicked(),clicks,'switching does not repeat an action');
 await observe({...image,url:'https://cdn.example/2.jpg'});await complete();assert.equal(clicked(),clicks+1);
 await message({command:'setNavigation',direction:'ArrowLeft'});assert.equal(data.settings.direction,'ArrowLeft');assert.equal(data.session.control,null);assert(calls.length>actions);
 await observe({...image,url:'https://cdn.example/3.jpg'});await complete();assert.equal(data.session.reason,'safety_limit');assert.equal(clicked(),clicks+1);
});
test('clear selection preserves image/settings/downloads; arrows continue and Click fails clearly',async()=>{
 await select();data.settings={...config};await message({command:'test',tabId:7,config});await complete();
 const selection=structuredClone(data.selection),settings=structuredClone(data.settings),seen=structuredClone(data.session.seen),n=downloaded();
 assert((await message({command:'clearControl'})).ok);assert.equal(data.control,undefined);assert.deepEqual(data.selection,selection);assert.deepEqual(data.settings,settings);assert.deepEqual(data.session.seen,seen);assert.equal(data.session.count,1);assert.equal(data.session.reason,'test_complete');
 const missing=await message({command:'start',tabId:7,config});assert(!missing.ok);assert.match(missing.error,/Click mode requires/);assert.equal(downloaded(),n);
 assert((await message({command:'start',tabId:7,config:{...config,direction:'ArrowLeft'}})).ok);assert.equal(downloaded(),n);
 // Clearing while an arrow session is waiting does not stop or change its pending action.
 await message({command:'clearControl'});assert.equal(data.session.reason,null);assert.equal(data.session.phase,'waiting');
 const invalid=await message({command:'setNavigation',direction:'Click'});assert(!invalid.ok);assert.equal(data.session.reason,'control_missing');assert.equal(data.settings.direction,'Click');
});
test('clearing an active Click session stops before any later navigation and retains completed pages',async()=>{
 await select();await message({command:'start',tabId:7,config});await complete();const n=clicked();
 await message({command:'clearControl'});assert.equal(data.session.reason,'control_cleared');assert.equal(data.session.count,1);assert.equal(data.control,undefined);
 await observe({...image,url:'https://cdn.example/2.jpg'});assert.equal(clicked(),n);assert.equal(data.session.count,1);
});
test('loader filenames are ignored without count, download, navigation or deadline changes',async()=>{
 await select();await message({command:'start',tabId:7,config});await complete();
 const n=downloaded(),clicks=clicked(),deadline=data.session.deadline,seen=structuredClone(data.session.seen);
 for(const filename of ['ajax-loader.gif','page-loader.png','PAGE-LOADER.webp','page-%6Coader.jpg']) {
  await observe({...image,url:'https://cdn.example/'+filename});
  assert.equal(downloaded(),n);assert.equal(clicked(),clicks);assert.equal(data.session.count,1);assert.equal(data.session.phase,'waiting');assert.equal(data.session.deadline,deadline);assert.deepEqual(data.session.seen,seen);
 }
 data.session.deadline=0;await observe({...image,url:'https://cdn.example/ajax-loader.gif'});assert.equal(data.session.reason,'navigation_timeout');assert.equal(downloaded(),n);
});
test('normal JPG, WebP and legitimate GIF transitions remain immediately eligible',async()=>{
 for(const filename of ['page-2.jpg','page-2.webp','animation.gif']) {
  await select();await message({command:'start',tabId:7,config});await complete();const n=downloaded();
  await observe({...image,url:'https://cdn.example/loader-directory/'+filename+'?loader=1'});
  assert.equal(downloaded(),n+1);assert.equal(data.session.phase,'downloading');assert.equal(data.session.pending.index,2);
  await message({command:'stop'});
 }
});
test('initial manually selected loader-named resource is not filtered',async()=>{
 await select();const initial={...image,url:'https://cdn.example/user-loader.gif'};
 await message({event:'selected',image:initial,descriptor:{tag:'IMG',path:imagePath},href:'https://reader.example/start'},sender);inspected=initial;
 const n=downloaded();assert((await message({command:'start',tabId:7,config:{...config,max:1}})).ok);assert.equal(downloaded(),n+1);
 await complete();assert.equal(data.session.count,1);assert.equal(data.session.seen[0].url,initial.url);assert.equal(data.session.reason,'safety_limit');
});
test('Test and Start pass exact relative manga/chapter paths to downloads API and preserve continuity',async()=>{
 await select();const c={...config,title:'Nue no Onmyouji',chapter:'01'};
 await message({command:'test',tabId:7,config:c});
 const first=calls.filter(c=>c.filename).at(-1);assert.equal(first.filename,'Mangas/Nue no Onmyouji/Capítulo 01/0001.jpg');assert.equal(first.saveAs,false);assert.equal(first.conflictAction,'uniquify');
 // Edge's reported destination is diagnostic data, not used to change confirmation rules.
 items.get(data.session.pending.downloadId).filename='C:\\Downloads\\0001.jpg';await complete();
 assert.equal(data.session.seen[0].requestedRelativePath,first.filename);assert.equal(data.session.seen[0].filename,'C:\\Downloads\\0001.jpg');
 const n=downloaded();await message({command:'start',tabId:7,config:c});assert.equal(downloaded(),n);
 await observe({...image,url:'https://cdn.example/2.webp'});
 assert.equal(calls.filter(c=>c.filename).at(-1).filename,'Mangas/Nue no Onmyouji/Capítulo 01/0002.webp');await complete();
 assert.equal(data.session.count,2);await message({command:'stop'});
 await select();await message({command:'start',tabId:7,config:c});assert.equal(calls.filter(c=>c.filename).at(-1).filename,first.filename);await message({command:'stop'});
});
