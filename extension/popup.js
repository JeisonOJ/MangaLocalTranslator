import {settings} from './core.js';
import {report} from './performance.js';
const $ = id => document.getElementById(id);
let tabId;
const fields = ['title','chapter','direction','max','timeout'];
const read = () => settings(Object.fromEntries(fields.map(k => [k,$(k).value])));
async function send(command, extra={}) {
  $('error').textContent='';
  const result=await chrome.runtime.sendMessage({command,tabId,...extra});
  if (!result?.ok) throw Error(result?.error || 'Extension worker unavailable.');
  await refresh();
}
async function refresh() {
  const {selection,session,control}=await chrome.storage.local.get(['selection','session','control']);
  $('performance').textContent=report(session);
  $('control').textContent=control ? `Selected: ${control.descriptor.label || control.descriptor.tag}` : 'No control selected.';
  $('selected').textContent=selection ? `${selection.image.width} × ${selection.image.height} — ${selection.image.url}` : 'No image selected.';
  $('counter').textContent=`Downloaded: ${session?.count || 0}`;
  const lastDownload=session?.seen?.at(-1);
  $('downloadPath').textContent=lastDownload?`Last download requested: ${lastDownload.requestedRelativePath||'unavailable for older records'}. Edge reported: ${lastDownload.filename||'unavailable'}`:'';
  $('status').textContent=session ? `${session.reason || session.phase}${session.detail ? ': '+session.detail : ''}` : 'Ready.';
  const running=session && !session.reason;
  const direction=running?session.config.direction:$('direction').value;
  $('activeMethod').textContent=`Active navigation: ${direction==='Click'?'Selected Click Control':direction}`;
  if(direction==='Click'&&!control)$('control').textContent='Click mode: select a next-page control before starting.';
  else if(direction!=='Click')$('control').textContent+=(control?' — saved but not used in arrow mode.':' Arrow mode does not need a click control.');
  for(const id of ['pick','pickControl','start','test',...fields.filter(f=>f!=='direction')]) $(id).disabled=Boolean(running);
  $('clearControl').disabled=!control;
  $('stop').disabled=!running;
}
function action(id, fn) { $(id).onclick=async()=>{try{await fn();}catch(e){$('error').textContent=e.message;}}; }
for(const command of ['pick','pickControl'])action(command,async()=>{
  const tab=await chrome.tabs.get(tabId); const origin=new URL(tab.url).origin;
  if(!/^https?:/.test(origin))throw Error('Open an HTTP(S) reader tab first.');
  if(!await chrome.permissions.request({origins:[origin+'/*']}))throw Error('Reader-origin permission was not granted.');
  await send(command); window.close();
});
for(const id of ['test','start'])action(id,async()=>{const config=read();await chrome.storage.local.set({settings:config});await send(id,{config});});
action('stop',()=>send('stop'));
action('clearControl',()=>send('clearControl'));
action('copyPerformance',async()=>{const {session}=await chrome.storage.local.get('session');await navigator.clipboard.writeText(report(session));$('copyStatus').textContent='Performance report copied.';});
const [tab]=await chrome.tabs.query({active:true,currentWindow:true});tabId=tab?.id;
const saved=(await chrome.storage.local.get('settings')).settings;
if(saved)for(const k of fields)if(saved[k]!==undefined)$(k).value=saved[k];
for(const k of fields.filter(f=>f!=='direction'))$(k).addEventListener('change',()=>chrome.storage.local.set({settings:Object.fromEntries(fields.map(f=>[f,$(f).value]))}));
$('direction').addEventListener('change',async()=>{try{await send('setNavigation',{direction:$('direction').value});}catch(e){$('error').textContent=e.message;await refresh();}});
chrome.storage.onChanged.addListener(()=>refresh().catch(e=>$('error').textContent=e.message));
await refresh();
