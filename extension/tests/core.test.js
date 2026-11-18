import {test} from 'node:test';
import assert from 'node:assert/strict';
import {safeName,settings,filename,resource,extension,duplicate,stopReason,inScope,equivalentScore} from '../core.js';
const config={title:'Example',chapter:'1',direction:'Click',max:3,timeout:15};
test('safe paths and sequential filenames',()=>{
 assert.equal(filename(config,1,'jpg'),'Mangas/Example/Capítulo 1/0001.jpg');
 assert.equal(filename(config,12,'webp'),'Mangas/Example/Capítulo 1/0012.webp');
 assert.equal(safeName('../bad\\name: '),'.._bad_name_');assert.equal(safeName('CON'),'_CON');
 assert.throws(()=>safeName('...'));assert.throws(()=>filename(config,1,'exe'));
});
test('manga/chapter folder paths preserve leading zeros, valid names and original extensions',()=>{
 const c=settings({...config,title:'Nue no Onmyouji',chapter:'01'});
 assert.equal(c.chapter,'01');assert.equal(filename(c,1,'jpg'),'Mangas/Nue no Onmyouji/Capítulo 01/0001.jpg');
 assert.equal(filename(c,2,'webp'),'Mangas/Nue no Onmyouji/Capítulo 01/0002.webp');
 assert.equal(filename({...c,title:'Árbol & 雪',chapter:'001.5'},3,'jpeg'),'Mangas/Árbol & 雪/Capítulo 001.5/0003.jpeg');
 assert.equal(filename({...c,title:'Nue: / Test\\?',chapter:'01/02'},1,'jpg'),'Mangas/Nue_ _ Test__/Capítulo 01_02/0001.jpg');
});
test('settings reject unbounded loops and invalid keys',()=>{
 assert.deepEqual(settings(config),config);
 for(const patch of [{max:0},{max:1001},{timeout:1},{direction:'Enter'}])assert.throws(()=>settings({...config,...patch}));
 for(const direction of ['ArrowLeft','ArrowRight','Click'])assert.equal(settings({...config,direction}).direction,direction);
});
test('resource identity keeps meaningful query parameters and detects fingerprints',()=>{
 assert.equal(resource('https://cdn.example/1.jpg?token=x#hash'),'https://cdn.example/1.jpg?token=x');
 assert.throws(()=>resource('javascript:alert(1)'));assert.equal(extension('https://cdn.example/1.webp?q=a'),'webp');assert.equal(extension('https://cdn.example/image'),null);
 assert(duplicate([{url:'a',fingerprint:'abc'}],{url:'b',fingerprint:'abc'}));assert(!duplicate([{url:'a'}],{url:'b'}));
});
test('stopping conditions distinguish missing image, timeout, duplicate, limit',()=>{
 const s={config,count:1,phase:'waiting',deadline:200,seen:[{url:'a'}]};
 assert.equal(stopReason(s,{url:'a'},199),null);assert.equal(stopReason(s,{url:'a'},200),'navigation_timeout');
 assert.equal(stopReason(s,null,200),'image_missing');assert.equal(stopReason({...s,count:3},null,1),'safety_limit');
 assert.equal(stopReason({...s,phase:'ready'},{url:'a'},1),'duplicate_page');
});
test('same origin permits changed pathnames without chapter evidence; cross-origin stops',()=>{
 const scope={origin:'https://reader.example'};
 assert(inScope(scope,'https://reader.example/completely/different/path'));
 assert(!inScope(scope,'https://other.example/series/1'));
});
test('equivalent element matching does not require an unchanged ID',()=>{
 const d={ratio:.7,parent:'DIV.reader',classes:'page',id:'page-1',alt:'Page #'};
 assert(equivalentScore(d,{...d,width:1400,height:2000,id:'page-2'})>=8);
 assert.equal(equivalentScore(d,{...d,ratio:3,width:300,height:100}),0);
});
