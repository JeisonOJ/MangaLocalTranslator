// Structural reacquisition of explicitly selected elements. No chapter/label heuristics.
(() => {
  function visible(el) {
    if(!el || el.isConnected===false)return false;
    const r=el.getBoundingClientRect();
    const style=typeof getComputedStyle==='function'?getComputedStyle(el):null;
    return r.width>0&&r.height>0&&style?.display!=='none'&&style?.visibility!=='hidden';
  }
  function path(el) {
    const out=[];
    for(let node=el;node?.parentElement;node=node.parentElement) {
      const siblings=[...node.parentElement.children].filter(s=>!s.hasAttribute?.('data-manga-capture-overlay'));
      out.unshift({tag:node.tagName,index:siblings.indexOf(node),family:siblings.map(s=>s.tagName).join(',')});
    }
    return out;
  }
  function describe(el) {
    return {tag:el.tagName,id:el.id||'',path:path(el),label:(el.getAttribute('aria-label')||el.getAttribute('title')||el.textContent||el.tagName).trim().slice(0,100)};
  }
  const samePath=(a,b)=>Boolean(a?.length && a.length===b?.length && a.every((part,i)=>part.tag===b[i].tag&&part.index===b[i].index&&part.family===b[i].family));
  const sameSelection=(a,b)=>Boolean(a&&b&&a.tag===b.tag&&a.id===b.id&&samePath(a.path,b.path)&&a.point?.x===b.point?.x&&a.point?.y===b.point?.y);
  function structurallyLocate(d,doc=document,live=null) {
    if(live?.isConnected&&live.ownerDocument===doc&&visible(live))return {element:live,match:'retained_live_selection'};
    if(!d?.path?.length)return {error:'selection_outdated'};
    const nodes=[...doc.querySelectorAll(d.tag.toLowerCase())].filter(visible);
    const exact=nodes.filter(el=>samePath(d.path,path(el)));
    if(exact.length===1)return {element:exact[0],match:'structural_path'};
    if(exact.length>1)return {error:'ambiguous'};
    // A unique stable ID can survive moved sibling positions; require the same ancestor tag chain.
    const chain=p=>p.map(n=>n.tag).join('/');
    const byId=d.id?nodes.filter(el=>el.id===d.id&&chain(path(el))===chain(d.path)):[];
    if(byId.length===1)return {element:byId[0],match:'unique_id_and_ancestor_chain'};
    return {error:byId.length>1||nodes.length>1?'ambiguous':'missing'};
  }
  function locateControl(d,doc=document,live=null) {
    const result=structurallyLocate(d,doc,live);
    if(result.error)return {error:result.error==='selection_outdated'?'selection_outdated':'control_'+result.error};
    const el=result.element;
    if(el.disabled||el.getAttribute('aria-disabled')==='true')return {error:'control_unavailable'};
    const href=el.closest('a[href]')?.href;
    if(href&&/^https?:/.test(href)&&new URL(href).origin!==location.origin)return {error:'cross_origin_blocked'};
    // Labels, CSS classes, destinations and chapter metadata are not suitability checks.
    return result;
  }
  globalThis.__captureReader={visible,path,describe,sameSelection,controlDescriptor:describe,structurallyLocate,locateControl};
})();
