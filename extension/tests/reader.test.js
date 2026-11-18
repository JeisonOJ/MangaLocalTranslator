import {test} from 'node:test';
import assert from 'node:assert/strict';
import {tree} from './dom-fixture.js';

test('identical attributes are disambiguated by selected structural slot across documents',()=>{
 const a=tree();a.nav.append(new a.El('button'));const chosen=a.nav.append(new a.El('button'));const d=a.reader.describe(chosen);
 const b=tree();b.nav.append(new b.El('button'));const next=b.nav.append(new b.El('button',{title:'Next chapter',classList:['changed']}));
 assert.equal(b.reader.locateControl(d,b.doc).element,next);
 assert.equal(b.reader.locateControl(d,b.doc).match,'structural_path');
});
test('stored structural paths match by field values regardless of object key order',()=>{
 const a=tree();a.nav.append(new a.El('button'));const chosen=a.nav.append(new a.El('button')),d=a.reader.describe(chosen);
 d.path=d.path.map(({tag,index,family})=>({family,index,tag}));
 const b=tree();b.nav.append(new b.El('button'));const next=b.nav.append(new b.El('button'));
 assert.equal(b.reader.locateControl(d,b.doc).element,next);
});
test('picker overlay is excluded from saved paths before clean-document reacquisition',()=>{
 const a=tree();a.nav.append(new a.El('button'));const chosen=a.nav.append(new a.El('button'));
 const clean=a.reader.describe(chosen);
 a.root.append(new a.El('div',{'data-manga-capture-overlay':''}));
 const picked=a.reader.describe(chosen);assert.deepEqual(picked.path,clean.path);
 const b=tree();b.nav.append(new b.El('button'));const next=b.nav.append(new b.El('button'));
 assert.equal(b.reader.locateControl(picked,b.doc).element,next);
});
test('missing and changed ambiguous structure do not click an arbitrary identical control',()=>{
 const f=tree();const button=f.nav.append(new f.El('button'));const d=f.reader.describe(button);
 button.isConnected=false;f.nav.children=[];assert.equal(f.reader.locateControl(d,f.doc).error,'control_missing');
 f.nav.append(new f.El('button'));f.nav.append(new f.El('button'));assert.equal(f.reader.locateControl(d,f.doc).error,'control_ambiguous');
});
test('same live selection survives layout changes; hidden/stale reference is not used',()=>{
 const f=tree(),b=f.nav.append(new f.El('button')),d=f.reader.describe(b);
 f.nav.append(new f.El('button'));assert.equal(f.reader.locateControl(d,f.doc,b).element,b);
 b.hidden=true;assert.notEqual(f.reader.locateControl(d,f.doc,b).element,b);
 b.isConnected=false;assert.notEqual(f.reader.locateControl(d,f.doc,b).element,b);
});
test('labels, tooltip, classes, chapter destination and form placement are not suitability checks',()=>{
 const f=tree(),b=f.nav.append(new f.El('a',{href:'https://reader.example/chapter-99/page-1'})),d=f.reader.describe(b);
 b.attrs.title='Next chapter';b.attrs.target='_blank';b.textContent='unrelated text';b.classList=['different'];assert.equal(f.reader.locateControl(d,f.doc).element,b);
 b.href='https://external.example/page';assert.equal(f.reader.locateControl(d,f.doc).error,'cross_origin_blocked');
});
test('unique ID and ancestor chain can recover moved controls, duplicate IDs cannot',()=>{
 const f=tree(),b=f.nav.append(new f.El('button',{id:'chosen'})),d=f.reader.describe(b);
 f.nav.append(new f.El('button'));assert.equal(f.reader.locateControl(d,f.doc).element,b);
 f.nav.append(new f.El('button',{id:'chosen'}));assert.equal(f.reader.locateControl(d,f.doc).error,'control_ambiguous');
 b.disabled=true;assert.equal(f.reader.locateControl(d,f.doc,b).error,'control_unavailable');
});
