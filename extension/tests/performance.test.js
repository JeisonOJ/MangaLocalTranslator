import {test} from 'node:test';
import assert from 'node:assert/strict';
import {elapsed,record,report} from '../performance.js';
test('monotonic calculation rejects missing, reversed and interrupted-worker marks',()=>{
 assert.equal(elapsed({lifetime:'a',t:10},{lifetime:'a',t:30}),20);
 for(const a of [null,{lifetime:'b',t:10},{lifetime:'a',t:40}])assert.equal(elapsed(a,{lifetime:'a',t:30}),null);
});
test('persisted records are bounded, deduplicated and reports exclude sensitive fields',()=>{
 const s={count:150,performanceElapsed:300000,phase:'waiting',detail:'secret URL',scope:{origin:'https://secret.example/token'}};
 for(let page=1;page<=150;page++)record(s,{page,download:1000,navigation:null,wait:page%2?null:2000});
 record(s,{page:150,download:999});assert.equal(s.timings.length,100);
 const copy=JSON.parse(JSON.stringify(s)),text=report(copy);assert.match(text,/Average download: 1.000 s/);assert.match(text,/Average next-image wait: 2.000 s/);assert(!text.includes('secret'));assert.match(text,/unavailable/);
 assert.match(report({count:1,timings:[{page:1,download:null,wait:null}]}),/Average download: unavailable/);
});
