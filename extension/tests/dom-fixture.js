import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
export function tree() {
 const doc={};
 class El {
  constructor(tag,attrs={}) {Object.assign(this,{tagName:tag.toUpperCase(),id:'',attrs,children:[],classList:[],isConnected:true,ownerDocument:doc,textContent:'',hidden:false},attrs);}
  append(el){el.parentElement=this;this.children.push(el);return el;}
  getAttribute(k){return this.attrs[k]||null;}
  hasAttribute(k){return Object.hasOwn(this.attrs,k);}
  getBoundingClientRect(){return {left:5,top:-600,width:this.hidden?0:700,height:this.hidden?0:2048};}
  closest(selector){if(selector==='a[href]')return this.tagName==='A'&&this.href?this:this.parentElement?.closest(selector);return null;}
  addEventListener(_type,fn){this.clickObserver=fn;}
  removeEventListener(){this.clickObserver=null;}
  click(){if(this.clickError)throw Error('click exception');this.clickObserver?.();this.clicked=(this.clicked||0)+1;}
  dispatchEvent(event){this.lastEvent=event;this.click();return true;}
 }
 const root=new El('html'),body=root.append(new El('body')),nav=body.append(new El('nav'));
 doc.querySelectorAll=tag=>{const nodes=[];function walk(n){if(n.tagName.toLowerCase()===tag)nodes.push(n);n.children.forEach(walk);}walk(root);return nodes;};
 doc.images=[];doc.documentElement=root;
 const ctx=vm.createContext({URL,document:doc,location:{origin:'https://reader.example'}});
 vm.runInContext(fs.readFileSync(new URL('../reader.js',import.meta.url),'utf8'),ctx);
 return {doc,El,root,body,nav,reader:ctx.__captureReader};
}
// Only execute tests when this file is a test entry point; fixtures live in a separate helper.
