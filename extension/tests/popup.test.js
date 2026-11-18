import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import {settings} from '../core.js';
import {report} from '../performance.js';
const source=fs.readFileSync(new URL('../popup.js',import.meta.url),'utf8').replace(/^import .*;$/gm,'');
async function openPopup(state,calls) {
 const elements=Object.fromEntries(['performance','copyPerformance','copyStatus','title','chapter','direction','max','timeout','selected','control','activeMethod','counter','status','error','pick','pickControl','clearControl','start','test','stop'].map(id=>[id,{value:'',textContent:'',disabled:false,listeners:{},addEventListener(event,fn){this.listeners[event]=fn;}}]));
 Object.assign(elements.direction,{value:'Click'});elements.max.value='50';elements.timeout.value='15';
 const chrome={storage:{local:{async get(keys){return Object.fromEntries((Array.isArray(keys)?keys:[keys]).map(k=>[k,structuredClone(state[k])]));},async set(obj){Object.assign(state,structuredClone(obj));}},onChanged:{addListener(){}}},tabs:{async query(){return [{id:7}];}},runtime:{async sendMessage(m){calls.push(m);if(m.command==='setNavigation'){state.settings={...state.settings,direction:m.direction};if(state.session&&!state.session.reason)state.session.config.direction=m.direction;}if(m.command==='clearControl')delete state.control;return {ok:true};}}};
 elements.downloadPath={textContent:''};
 const context=vm.createContext({settings,report,chrome,document:{getElementById:id=>elements[id]},window:{close(){}}});
 await vm.runInContext('(async()=>{'+source+'})()',context);return elements;
}
test('popup navigation mode persists on reopen and Clear does not alter image or form fields',async()=>{
 const state={settings:{title:'Example',chapter:'1',direction:'Click',max:3,timeout:15},selection:{image:{width:1403,height:2048,url:'https://cdn.example/1.jpg'}},control:{descriptor:{label:'Next'}},session:{reason:'test_complete',count:1,phase:'downloading',config:{direction:'Click'}}},calls=[];
 let ui=await openPopup(state,calls);assert.equal(ui.direction.value,'Click');assert.match(ui.activeMethod.textContent,/Selected Click Control/);
 ui.direction.value='ArrowRight';await ui.direction.listeners.change();assert.equal(calls.at(-1).command,'setNavigation');assert.equal(state.settings.direction,'ArrowRight');
 ui=await openPopup(state,calls);assert.equal(ui.direction.value,'ArrowRight');assert.match(ui.activeMethod.textContent,/ArrowRight/);assert.match(ui.control.textContent,/not used in arrow mode/);
 const selected=structuredClone(state.selection),before=structuredClone(state.settings);await ui.clearControl.onclick();assert.equal(state.control,undefined);assert.deepEqual(state.selection,selected);assert.deepEqual(state.settings,before);assert.equal(ui.title.value,'Example');assert.equal(ui.chapter.value,'1');assert.match(ui.counter.textContent,/1/);
 ui.direction.value='Click';await ui.direction.listeners.change();assert.match(ui.control.textContent,/select a next-page control/);
});
test('active capture permits explicit mode changes and clearing; partial saved settings preserve defaults',async()=>{
 const state={settings:{direction:'ArrowLeft'},control:{descriptor:{label:'Next'}},session:{reason:null,count:1,phase:'waiting',config:{direction:'ArrowLeft'}}},calls=[];
 const ui=await openPopup(state,calls);assert.equal(ui.max.value,'50');assert.equal(ui.timeout.value,'15');assert.equal(ui.direction.disabled,false);assert.equal(ui.clearControl.disabled,false);assert.equal(ui.title.disabled,true);assert.match(ui.activeMethod.textContent,/ArrowLeft/);
 ui.direction.value='ArrowRight';await ui.direction.listeners.change();assert.equal(state.session.config.direction,'ArrowRight');assert.match(ui.activeMethod.textContent,/ArrowRight/);
});
