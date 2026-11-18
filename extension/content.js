(() => {
  if (globalThis.__mangaCapture) return;
  globalThis.__mangaCapture=true;
  const reader=globalThis.__captureReader;
  let selected=null, descriptor=null, picking=false, overlay=null, busy=false, watching=false;
  let navControl=null,navDescriptor=null;
  const send=msg=>chrome.runtime.sendMessage(msg).catch(()=>{});
  const parentKey=im=>{let p=im.parentElement,out=[];for(let i=0;p && i<3;i++,p=p.parentElement)out.push(p.tagName+'.'+[...p.classList].sort().join('.'));return out.join('>');};
  function describe(im) {return {...reader.describe(im),classes:[...im.classList].sort().join(' '),parent:parentKey(im),alt:im.alt.replace(/\d+/g,'#'),ratio:im.naturalWidth/im.naturalHeight,width:im.naturalWidth,height:im.naturalHeight};}
  function score(im) {
    const c=describe(im),d=descriptor,r=Math.min(d.ratio/c.ratio,c.ratio/d.ratio);
    if(!Number.isFinite(r)||r<.85)return 0;
    return (d.parent===c.parent?4:0)+(d.classes && d.classes===c.classes?3:0)+(d.id && d.id===c.id?2:0)+(d.alt && d.alt===c.alt?1:0)+r;
  }
  function locate() {
    if(selected?.isConnected&&reader.visible(selected))return selected;
    if(!descriptor)return null;
    const structural=reader.structurallyLocate(descriptor);
    if(structural.element){selected=structural.element;return selected;}
    const ranked=[...document.images].filter(i=>i.naturalWidth>0&&reader.visible(i)).map(i=>[i,score(i)]).sort((a,b)=>b[1]-a[1]);
    if(!ranked.length||ranked[0][1]<5||(ranked[1] && ranked[0][1]-ranked[1][1]<1))return null;
    selected=ranked[0][0];return selected;
  }
  function snapshot(im) {
    if(!im?.complete||!im.naturalWidth||!im.naturalHeight)return null;
    const url=im.currentSrc||im.src;
    if(!/^https?:/.test(url))return null;
    let fingerprint=null;
    try {const c=document.createElement('canvas');c.width=64;c.height=64;const ctx=c.getContext('2d',{willReadFrequently:true});ctx.drawImage(im,0,0,64,64);const data=ctx.getImageData(0,0,64,64).data;let hash=2166136261;for(const b of data)hash=Math.imul(hash^b,16777619);fingerprint=`sample-v1:${im.naturalWidth}x${im.naturalHeight}:${hash>>>0}`;}catch{/* Cross-origin taint: URL identity only; never request CORS bypass. */}
    return {url,width:im.naturalWidth,height:im.naturalHeight,fingerprint};
  }
  function cancel() {picking=false;overlay?.remove();overlay=null;document.removeEventListener('mousemove',hover,true);document.removeEventListener('click',choose,true);document.removeEventListener('keydown',escape,true);}
  let pickMode='image';
  function target(e) {return pickMode==='image' ? (e.target instanceof HTMLImageElement?e.target:null) : (e.target.closest('a,button,[role="button"],[role="link"]')||e.target);}
  function hover(e) {const im=target(e);if(!im){overlay.style.display='none';return;}const r=im.getBoundingClientRect();Object.assign(overlay.style,{display:'block',left:r.left+'px',top:r.top+'px',width:r.width+'px',height:r.height+'px'});}
  function choose(e) {
    const el=target(e);if(!el)return;
    if(pickMode==='control') {
      e.preventDefault();e.stopImmediatePropagation();const d=reader.controlDescriptor(el),r=el.getBoundingClientRect();
      d.point={x:Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))};
      navControl=el;navDescriptor=d;cancel();send({event:'controlSelected',descriptor:d,href:location.href});return;
    }
    e.preventDefault();e.stopImmediatePropagation();const image=snapshot(e.target);if(!image)return;
    selected=e.target;descriptor=describe(selected);cancel();send({event:'selected',image,descriptor,href:location.href});
  }
  function escape(e) {if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();cancel();}}
  chrome.runtime.onMessage.addListener((m,_s,reply)=>{
    if(m.type==='inspect')reply({image:snapshot(locate()),href:location.href});
    if(m.type==='clickNext') {
      if(!reader.sameSelection(navDescriptor,m.descriptor))navControl=null;
      const found=reader.locateControl(m.descriptor,document,navControl);
      if(found.error){reply({ok:false,error:found.error,detail:`No click: ${found.error}; live selection ${navControl?.isConnected?'connected but unavailable':'not available'}; stored structural position could not be resolved uniquely. Select the control again.`});return;}
      navControl=found.element;navDescriptor=m.descriptor;
      let eventObserved=false;
      const observeClick=()=>{eventObserved=true;};
      navControl.addEventListener('click',observeClick,{capture:true,once:true});
      try {
        const r=navControl.getBoundingClientRect(),p=m.descriptor.point||{x:.5,y:.5};
        const event=new MouseEvent('click',{bubbles:true,cancelable:true,composed:true,view:window,button:0,clientX:r.left+r.width*p.x,clientY:r.top+r.height*p.y});
        navControl.dispatchEvent(event);
        reply({ok:true,diagnostic:{status:eventObserved?'click_dispatched':'click_unconfirmed',match:found.match,eventObserved,defaultPrevented:event.defaultPrevented,point:p}});
      }
      catch(e){reply({ok:false,error:'click_failed',detail:e.message});}
      finally{navControl.removeEventListener('click',observeClick,true);}
    }
    if(m.type==='pick'||m.type==='pickControl') {cancel();pickMode=m.type==='pickControl'?'control':'image';picking=true;overlay=document.createElement('div');overlay.setAttribute('data-manga-capture-overlay','');Object.assign(overlay.style,{position:'fixed',pointerEvents:'none',zIndex:'2147483647',outline:'4px solid #2385ff',background:'rgba(35,133,255,.15)'});document.documentElement.append(overlay);document.addEventListener('mousemove',hover,true);document.addEventListener('click',choose,true);document.addEventListener('keydown',escape,true);reply({ok:true});}
    if(m.type==='inspectControl') {
      if(!reader.sameSelection(navDescriptor,m.descriptor))navControl=null;
      const found=reader.locateControl(m.descriptor,document,navControl);
      if(found.element){navControl=found.element;navDescriptor=m.descriptor;}
      reply(found.error?{ok:false,error:found.error}:{ok:true,match:found.match});
    }
    if(m.type==='clearControl'){navControl=null;navDescriptor=null;reply({ok:true});}
    if(m.type==='watch'){if(!reader.sameSelection(descriptor,m.descriptor))selected=null;descriptor=m.descriptor;watching=true;schedule();reply({ok:true});}
    if(m.type==='halt'){watching=false;reply({ok:true});}
  });
  // Event-driven readiness; polling remains a watchdog for changes without DOM/load events.
  let candidate=null,queued=false,rescan=false;
  const identity=(node,image)=>JSON.stringify([image,location.href,node?.getAttribute('src'),node?.getAttribute('srcset'),node?.getAttribute('sizes')]);
  function schedule() {
    if(busy){rescan=true;return;}
    if(queued||!watching)return;queued=true;
    queueMicrotask(()=>{queued=false;scan();});
  }
  function beginDecode(c) {
    if(typeof c.node.decode!=='function')return;
    c.decodePending=true;
    Promise.resolve().then(()=>c.node.decode()).then(()=>{
      c.decodePending=false;c.decoded=true;
      if(candidate!==c||!watching)return;
      if(typeof requestAnimationFrame!=='function'||document.visibilityState==='hidden'){schedule();return;}
      requestAnimationFrame(()=>requestAnimationFrame(()=>{
        if(candidate!==c||!watching)return;
        const node=locate(),image=snapshot(node);
        if(node!==c.node||identity(node,image)!==c.key){schedule();return;}
        c.frameVerified=true;schedule();
      }));
    }).catch(()=>{c.decodePending=false;c.decodeFailed=true;if(candidate===c)schedule();});
  }
  async function scan() {
    if(busy||picking||!descriptor||!watching)return;busy=true;
    try {
      const node=locate(),image=snapshot(node),key=identity(node,image);
      if(!candidate||candidate.node!==node||candidate.key!==key){
        candidate={node,key,firstSeen:Date.now(),decoded:false,frameVerified:false};
        if(image)beginDecode(candidate);
      }
      const c=candidate,hasDecode=typeof node?.decode==='function';
      const legacy=!hasDecode||typeof requestAnimationFrame!=='function'||document.visibilityState==='hidden';
      const stable=image&&!c.decodeFailed&&(legacy?(!hasDecode||c.decoded)&&Date.now()-c.firstSeen>=1000:c.frameVerified);
      await send({event:'observed',image:stable?image:null,href:location.href,diagnostic:{imageStatus:!node?'image_missing':!image?'image_loading':c.decodeFailed?'image_decode_failed':!stable?'image_settling':'image_ready',readiness:legacy?'legacy_stabilization':'decode_and_two_frames',observedResource:image?.url||null}});
    }finally{busy=false;if(rescan){rescan=false;schedule();}}
  }
  if(typeof MutationObserver==='function')new MutationObserver(schedule).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['src','srcset','sizes','class','style','hidden']});
  document.addEventListener('load',schedule,true);
  document.addEventListener('error',schedule,true);
  document.addEventListener('visibilitychange',schedule);
  setInterval(scan,700);
})();
