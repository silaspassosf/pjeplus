// CLICK CAPTURE BOOKMARKLET - Single line version below
// Paste this into a bookmarklet URL bar as: javascript:...

// ============ SINGLE LINE VERSION ============
javascript:(function(){let s={r:0,e:[],t:0};let b=document.createElement('button');b.innerHTML='⏺GRAB';b.style='position:fixed;bottom:20px;right:20px;z-index:999999;background:#1a73e8;color:#fff;border:none;border-radius:12px;padding:12px 20px;font-weight:600;cursor:pointer;box-shadow:0 4px 20px rgba(0,0,0,.4);font-family:system-ui;font-size:14px';document.documentElement.appendChild(b);const g=e=>{let s=[];if(e.dataset.testid)s.push(`[data-testid="${e.dataset.testid}"]`);if(e.id)s.push(`#${e.id}`);if(e.getAttribute('aria-label'))s.push(`[aria-label*="${e.getAttribute('aria-label').slice(0,20)}"]`);if(e.className){let c=e.className.split(' ').slice(0,4).join('.');s.push(`${e.tagName.toLowerCase()}.${c}`);}return s};document.addEventListener('click',e=>{if(!s.r)return;s.e.push({url:location.href,selector:g(e.target),text:e.target.innerText?.trim().slice(0,50)||'',class:e.target.className,id:e.target.id,tag:e.target.tagName.toLowerCase()})},true);b.onclick=async()=>{s.r=!s.r;b.innerHTML=s.r?'⏹STOP':'⏺GRAB';b.style.background=s.r?'#ea4335':'#1a73e8';if(s.r){s.t=Date.now();s.e=[];console.clear();console.log('🔴 Click Grab ON')}else{let r={summary:{clicks:s.e.length,duration:((Date.now()-s.t)/1e3).toFixed(1)+'s',timestamp:new Date().toISOString()},events:s.e};navigator.clipboard.writeText(JSON.stringify(r,null,2));let o=document.createElement('div');o.innerHTML='✅ JSON Copiado';o.style='position:fixed;top:20px;right:20px;z-index:999999;background:#0f9d58;color:white;padding:12px;border-radius:12px;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,.3);font-family:system-ui';document.documentElement.appendChild(o);setTimeout(()=>o.remove(),2500);try{await fetch('/api/collect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(r)})}catch(e){console.log('API call skipped')}console.table(r.events)}};console.log('📋 Click Capture Ativo - START > clique > STOP')})();

// ============ FORMATTED VERSION (for reading) ============
/*
javascript:(function(){
  let s={r:0,e:[],t:0};
  let b=document.createElement('button');
  b.innerHTML='⏺GRAB';
  b.style='position:fixed;bottom:20px;right:20px;z-index:999999;background:#1a73e8;color:#fff;border:none;border-radius:12px;padding:12px 20px;font-weight:600;cursor:pointer;box-shadow:0 4px 20px rgba(0,0,0,.4);font-family:system-ui;font-size:14px';
  document.documentElement.appendChild(b);
  
  const g=e=>{
    let s=[];
    if(e.dataset.testid)s.push(`[data-testid="${e.dataset.testid}"]`);
    if(e.id)s.push(`#${e.id}`);
    if(e.getAttribute('aria-label'))s.push(`[aria-label*="${e.getAttribute('aria-label').slice(0,20)}"]`);
    if(e.className){
      let c=e.className.split(' ').slice(0,4).join('.');
      s.push(`${e.tagName.toLowerCase()}.${c}`);
    }
    return s;
  };
  
  // CLICKS ONLY (removed mouseover)
  document.addEventListener('click', e=>{
    if(!s.r)return;
    s.e.push({
      url:location.href,
      selector:g(e.target),
      text:e.target.innerText?.trim().slice(0,50)||'',
      class:e.target.className,
      id:e.target.id,
      tag:e.target.tagName.toLowerCase()
    })
  }, true);
  
  b.onclick=async()=>{
    s.r=!s.r;
    b.innerHTML=s.r?'⏹STOP':'⏺GRAB';
    b.style.background=s.r?'#ea4335':'#1a73e8';
    
    if(s.r){
      s.t=Date.now();
      s.e=[];
      console.clear();
      console.log('🔴 Click Grab ON')
    } else {
      let r={
        summary:{
          clicks:s.e.length,
          duration:((Date.now()-s.t)/1e3).toFixed(1)+'s',
          timestamp:new Date().toISOString()
        },
        events:s.e
      };
      
      // Copy to clipboard
      navigator.clipboard.writeText(JSON.stringify(r,null,2));
      
      // Show confirmation
      let o=document.createElement('div');
      o.innerHTML='✅ JSON Copiado';
      o.style='position:fixed;top:20px;right:20px;z-index:999999;background:#0f9d58;color:white;padding:12px;border-radius:12px;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,.3);font-family:system-ui';
      document.documentElement.appendChild(o);
      setTimeout(()=>o.remove(),2500);
      
      // API call (with error handling)
      try{
        await fetch('/api/collect',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify(r)
        })
      }catch(e){
        console.log('API call skipped')
      }
      
      console.table(r.events);
    }
  };
  
  console.log('📋 Click Capture Ativo - START > clique > STOP')
})();
*/
