import {active,settings,safeName,resource,extension,filename,duplicate,stopReason,inScope} from './core.js';
import {mark,elapsed,record} from './performance.js';
const read=async()=> (await chrome.storage.local.get('session')).session;
const write=async session=>{if(session.reason&&session.reason!=='test_complete'&&!session.performanceEnd)session.performanceEnd=mark();session.performanceElapsed=elapsed(session.performanceStart,session.performanceEnd||mark());await chrome.storage.local.set({session});};
let queue=Promise.resolve();
const serial=fn=>{const p=queue.then(fn);queue=p.catch(()=>{});return p;};
async function stop(s,reason,detail='') {if(!s)return;s.reason=reason;s.detail=detail;await write(s);await chrome.alarms.clear('capture');try{await chrome.tabs.sendMessage(s.tabId,{type:'halt'});}catch{/* Tab may have closed. */}}
async function inject(tabId,descriptor) {
  await chrome.scripting.executeScript({target:{tabId},files:['reader.js','content.js']});
  if(descriptor)await chrome.tabs.sendMessage(tabId,{type:'watch',descriptor});
}
async function navigate(s) {
  s.dispatchStart=mark();
  if(s.test)return stop(s,'test_complete','Start continues with the next page using the same settings.');
  if(s.count>=s.config.max)return stop(s,'safety_limit','Maximum page count reached.');
  // Persist intent BEFORE dispatch; a worker interruption here must not repeat an action.
  s.phase='waiting';s.detail=`${s.config.direction} requested; waiting for a new image resource.`;s.deadline=Date.now()+s.config.timeout*1000;s.last=s.seen.at(-1);s.observation=null;s.navigation={status:s.config.direction==='Click'?'click_requested':'arrow_requested',method:s.config.direction,started:Date.now()};await write(s);
  await chrome.alarms.create('capture',{periodInMinutes:.5});
  try {
    if(s.config.direction!=='Click') {
      s.navigation={...s.navigation,status:'arrow_requested',method:s.config.direction};await write(s);
      await chrome.scripting.executeScript({target:{tabId:s.tabId},world:'MAIN',func:key=>{
        if(document.activeElement?.matches('input,textarea,select'))document.activeElement.blur();
        const target=document.body||document.documentElement,code=key==='ArrowLeft'?37:39;
        for(const type of ['keydown','keyup'])target.dispatchEvent(new KeyboardEvent(type,{key,code:key,keyCode:code,which:code,bubbles:true,cancelable:true}));
      },args:[s.config.direction]});
      s.dispatchEnd=mark();s.navigation.status='arrow_dispatched';s.detail=`${s.config.direction} dispatched; waiting for a new image resource.`;await write(s);return;
    }
    const result=await chrome.tabs.sendMessage(s.tabId,{type:'clickNext',descriptor:s.control.descriptor});
    if(!result?.ok)return stop(s,result?.error||'control_missing',result?.detail||'No click: selected control could not be safely reacquired.');
    s.dispatchEnd=mark();s.navigation={...s.navigation,...result.diagnostic};s.detail=`${s.navigation.status} (${s.navigation.match||'selected control'}); waiting for a new image resource.`;await write(s);
  } catch(e) {s.navigation={...s.navigation,status:s.config.direction==='Click'?'click_ack_unavailable':'arrow_dispatch_failed',detail:e.message};await write(s);if(s.config.direction!=='Click')await stop(s,'navigation_failed',e.message);}
}
async function download(s,image) {
  s.performanceStart||=mark();
  image={...image,url:resource(image.url)};
  if(duplicate(s.seen,image))return stop(s,'duplicate_page','Previously captured resource or sampled content reappeared.');
  const ext=extension(image.url);if(!ext)return stop(s,'download_failure','Unknown source format; no guessed extension or transcoding.');
  // Exclusive durable intent. If the worker dies between browser dispatch and saving the ID,
  // recovery stops rather than issuing a potentially duplicate download.
  s.phase='download_intent';s.pending={image,index:s.count+1};s.deadline=Date.now()+120000;await write(s);
  await chrome.alarms.create('capture',{periodInMinutes:.5});
  try {
    s.pending.downloadStart=mark();
    s.pending.requestedRelativePath=filename(s.config,s.pending.index,ext);
    const id=await chrome.downloads.download({url:image.url,filename:s.pending.requestedRelativePath,conflictAction:'uniquify',saveAs:false});
    s.pending.downloadId=id;s.phase='downloading';await write(s);await reconcile(s);
  }catch(e){await stop(s,'download_failure',e.message);}
}
async function reconcile(s) {
  if(!active(s))return;
  if(s.phase==='download_intent')return stop(s,'download_uncertain','Dispatch interrupted. Inspect Edge Downloads; no automatic retry.');
  if(s.phase!=='downloading')return;
  const [item]=await chrome.downloads.search({id:s.pending.downloadId});
  if(!item)return stop(s,'download_failure','Download record missing; no retry.');
  if(item.state==='interrupted')return stop(s,'download_failure',item.error||'Interrupted; no retry.');
  if(item.state!=='complete') {if(Date.now()>=s.deadline)await stop(s,'download_failure','Download timeout; may still finish in Edge Downloads. No retry.');return;}
  if(!item.mime?.startsWith('image/'))return stop(s,'download_failure','Server returned non-image content. Inspect the retained download.');
  const final=resource(item.finalUrl||item.url);
  if(s.seen.some(p=>p.finalUrl===final))return stop(s,'duplicate_page','Download redirected to previously captured content; retained for inspection.');
  record(s,{page:s.count+1,download:elapsed(s.pending.downloadStart),navigation:s.count&&s.dispatchEnd?elapsed(s.dispatchStart,s.dispatchEnd):null,wait:s.count&&s.imageConfirmed?elapsed(s.dispatchEnd,s.imageConfirmed):null});
  s.count++;s.seen.push({...s.pending.image,finalUrl:final,downloadId:item.id,filename:item.filename,requestedRelativePath:s.pending.requestedRelativePath});s.pending=null;await write(s);await navigate(s);
}
async function observe(m,sender) {
  const s=await read();if(!active(s)||sender.tab?.id!==s.tabId||sender.frameId!==0)return;
  if(!inScope(s.scope,m.href))return stop(s,'cross_origin_blocked','Cross-origin navigation is outside this capture context.');
  if(s.phase==='downloading'||s.phase==='download_intent')return reconcile(s);
  if(s.phase!=='waiting')return;
  s.observation={...m.diagnostic,href:m.href,at:Date.now()};await write(s);
  let reason=stopReason(s,m.image,Date.now());
  if(reason==='image_missing'&&m.diagnostic?.imageStatus&&m.diagnostic.imageStatus!=='image_missing')reason='navigation_timeout';
  if(reason)return stop(s,reason,timeoutDetail(s));
  if(!m.image)return;
  const image={...m.image,url:resource(m.image.url)};
    let candidateFilename=new URL(image.url).pathname.split('/').pop();
    try{candidateFilename=decodeURIComponent(candidateFilename);}catch{/* Match literal filename if URL encoding is malformed. */}
    if(/loader/i.test(candidateFilename))return;
  // Unchanged resource is expected during navigation. It becomes timeout, not a duplicate.
  if(image.url===s.last.url && (!image.fingerprint||image.fingerprint===s.last.fingerprint))return;
  if(duplicate(s.seen,image))return stop(s,'duplicate_page','Previously captured image reappeared.');
  s.imageConfirmed=mark();await download(s,image);
}
function timeoutDetail(s) {
  const click=s.navigation?.status||'navigation_status_unknown',image=s.observation?.imageStatus||'no_image_observations';
  const changed=s.observation?.observedResource&&s.observation.observedResource!==s.last?.url;
  return `${click}; ${image}; ${changed?'changed resource observed but not ready':'no new image resource confirmed'}. A dispatched action does not prove the reader accepted navigation.`;
}
async function controlFor(tabId,origin) {
  const control=(await chrome.storage.local.get('control')).control;
  if(!control||control.tabId!==tabId||new URL(control.href).origin!==origin)throw Error('Click mode requires a selected next-page control in this reader tab.');
  const result=await chrome.tabs.sendMessage(tabId,{type:'inspectControl',descriptor:control.descriptor});
  if(!result?.ok)throw Error(`Click control unavailable (${result?.error||'no response'}). Select the control again or choose an arrow mode.`);
  return control;
}
async function command(m,sender) {
  if(m.event==='observed')return observe(m,sender);
  if(m.event==='controlSelected') {
    if(sender.frameId!==0)return;
    if(active(await read()))throw Error('Stop capture before changing the control.');
    await chrome.storage.local.set({control:{id:crypto.randomUUID(),tabId:sender.tab.id,descriptor:m.descriptor,href:m.href}});return;
  }
  if(m.event==='selected') {
    if(sender.frameId!==0)return;
    if(active(await read()))throw Error('Stop capture before changing the selection.');
    await chrome.storage.local.set({selection:{id:crypto.randomUUID(),tabId:sender.tab.id,image:{...m.image,url:resource(m.image.url)},descriptor:m.descriptor,href:m.href}});return;
  }
  // Only the extension popup can issue capture commands.
  if(sender.tab||sender.url!==chrome.runtime.getURL('popup.html'))throw Error('Untrusted command source.');
  let s=await read();
  if(m.command==='stop')return stop(s,'user_stopped','Completed downloads retained; an in-flight download may finish.');
  if(m.command==='clearControl') {
    const previous=(await chrome.storage.local.get('control')).control;
    await chrome.storage.local.remove('control');
    try{if(previous)await chrome.tabs.sendMessage(previous.tabId,{type:'clearControl'});}catch{/* Closed tab has no live reference. */}
    if(s){s.control=null;if(active(s)&&s.config.direction==='Click')await stop(s,'control_cleared','Navigation selection cleared; completed downloads retained.');else await write(s);}
    return;
  }
  if(m.command==='setNavigation') {
    if(!['ArrowRight','ArrowLeft','Click'].includes(m.direction))throw Error('Choose ArrowRight, ArrowLeft or Selected Click Control.');
    const saved=(await chrome.storage.local.get('settings')).settings||{};
    await chrome.storage.local.set({settings:{...saved,direction:m.direction}});
    if(active(s)) {
      s.config.direction=m.direction;s.control=null;
      if(m.direction==='Click')try{s.control=await controlFor(s.tabId,s.scope.origin);}catch(e){await stop(s,'control_missing',e.message);throw e;}
      s.detail=`Navigation method changed to ${m.direction}; already dispatched actions are not repeated.`;await write(s);
    }
    return;
  }
  if(active(s))throw Error('Capture is running. Stop it before starting another session.');
  if(m.command==='pick'||m.command==='pickControl'){await inject(m.tabId);await chrome.tabs.sendMessage(m.tabId,{type:m.command});return;}
  if(!['start','test'].includes(m.command))throw Error('Unknown command.');
  const config=settings(m.config),sel=(await chrome.storage.local.get('selection')).selection;
  const folders=(await chrome.storage.local.get('folders')).folders||{};
  const folder=JSON.stringify([safeName(config.title),safeName(config.chapter)]),owner=JSON.stringify([config.title,config.chapter]);
  if(folders[folder]&&folders[folder]!==owner)throw Error('Another title/chapter sanitizes to this folder. Choose a distinct name to avoid mixing chapters.');
  if(!sel||sel.tabId!==m.tabId)throw Error('Select the manga image in this tab first.');
  if(s?.selectionId===sel.id&&(s.config.title!==config.title||s.config.chapter!==config.chapter))throw Error('Title/chapter changed. Select the image again for a fresh capture context.');
  const tab=await chrome.tabs.get(m.tabId),scope={origin:new URL(sel.href).origin};
  if(!inScope(scope,tab.url))throw Error('Reader origin changed. Select the image again.');
  await inject(m.tabId,sel.descriptor);
  const control=config.direction==='Click'?await controlFor(m.tabId,scope.origin):null;
  const current=await chrome.tabs.sendMessage(m.tabId,{type:'inspect'});
  if(!current?.image||!inScope(scope,current.href))throw Error('Selected image is not loaded or cannot be safely reacquired.');
  if(current.image.url!==sel.image.url||(current.image.fingerprint&&sel.image.fingerprint&&current.image.fingerprint!==sel.image.fingerprint))throw Error('Selected image changed since picking. Select it again.');
  if(m.command==='start'&&s?.reason==='test_complete'&&s.selectionId===sel.id) {
    if(s.tabId!==m.tabId||JSON.stringify(s.descriptor)!==JSON.stringify(sel.descriptor))throw Error('Test selection changed. Reselect to create a new session.');
    s.reason=null;s.test=false;s.config=config;s.control=control;await navigate(s);return;
  }
  if(s?.selectionId===sel.id)throw Error('This capture context was already used. Select the image again to explicitly start a new capture; existing files are retained.');
  if(s)await chrome.storage.local.set({['history:'+s.id]:s});
  folders[folder]=owner;await chrome.storage.local.set({folders});
  s={id:crypto.randomUUID(),selectionId:sel.id,config,tabId:m.tabId,scope,control,descriptor:sel.descriptor,count:0,seen:[],phase:'ready',reason:null,test:m.command==='test'};
  await write(s);await download(s,current.image);
}
chrome.runtime.onMessage.addListener((m,sender,reply)=>{
  serial(()=>command(m,sender)).then(()=>reply({ok:true})).catch(async e=>{
    if(m.event){const s=await read();if(active(s))await stop(s,'error',e.message);}
    reply({ok:false,error:e.message});
  });return true;
});
chrome.downloads.onChanged.addListener(()=>serial(async()=>reconcile(await read())).catch(()=>{}));
chrome.alarms.onAlarm.addListener(a=>{if(a.name==='capture')serial(async()=>{
  const s=await read();if(!active(s))return;
  if(['downloading','download_intent'].includes(s.phase))return reconcile(s);
  if(s.phase==='waiting'&&Date.now()>=s.deadline)await stop(s,'navigation_timeout',timeoutDetail(s));
}).catch(()=>{});});
chrome.tabs.onUpdated.addListener((id,change,tab)=>serial(async()=>{
  const s=await read();if(!active(s)||s.tabId!==id)return;
  if(tab.url&&!inScope(s.scope,tab.url))return stop(s,'cross_origin_blocked','Cross-origin navigation is outside this capture context.');
  if(change.status==='complete')await inject(id,s.descriptor);
}).catch(async e=>{const s=await read();if(active(s))await stop(s,'image_missing',e.message);}));
chrome.tabs.onRemoved.addListener(id=>serial(async()=>{const s=await read();if(active(s)&&s.tabId===id)await stop(s,'user_stopped','Reader tab closed.');}));
chrome.runtime.onStartup.addListener(()=>serial(async()=>{const s=await read();if(active(s))await stop(s,'browser_restarted','Capture stopped after browser restart; files retained.');}));
