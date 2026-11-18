// Monotonic marks are valid only within one worker lifetime. Never substitute wall time.
const lifetime=crypto.randomUUID();
export const mark=()=>({lifetime,t:performance.now()});
export function elapsed(a,b=mark()){return a?.lifetime===b?.lifetime&&Number.isFinite(a.t)&&b.t>=a.t?b.t-a.t:null;}
export function record(s,row){s.timings||=[];if(s.timings.some(r=>r.page===row.page))return;s.timings.push(row);s.timings=s.timings.slice(-100);}
const average=values=>{const valid=values.filter(Number.isFinite);return valid.length?valid.reduce((a,b)=>a+b,0)/valid.length:null;};
const fmt=v=>Number.isFinite(v)?`${(v/1000).toFixed(3)} s`:'unavailable';
export function report(s){
 if(!s)return 'No capture session.';
 const rows=s.timings||[],total=s.performanceElapsed;
 return ['Capture performance (last 100 completed-page records maximum)',`Status: ${s.reason||s.phase||'unknown'}`,`Completed pages: ${s.count||0}`,`Total session: ${fmt(total)}`,`Average elapsed per completed page: ${fmt(s.count&&Number.isFinite(total)?total/s.count:null)}`,`Average download: ${fmt(average(rows.map(r=>r.download)))}`,`Average next-image wait: ${fmt(average(rows.map(r=>r.wait)))}`,'Averages use available retained measurements only; unavailable samples are excluded.','Detector: E4B events + decode + two rendering frames; 700 ms fallback polling. Hidden/unsupported-frame contexts retain >=1000 ms stabilization. Individual contributions are not isolated. Older retained records may use the E4A detector.','Session duration includes the pause between Test and Start. No network/browser transfer timing is inferred.','page | download | preceding navigation dispatch | next-image wait',...rows.map(r=>`${r.page} | ${fmt(r.download)} | ${fmt(r.navigation)} | ${fmt(r.wait)}`)].join('\n');
}
