const message=document.querySelector('#message');let offset=0, accessToken=null, expiryTimer=null;
function setSession(session){
  clearTimeout(expiryTimer);accessToken=session ? session.access_token : null;offset=0;
  document.querySelector('#auth').hidden=!!session;
  document.querySelector('#logout').hidden=!session;
  document.querySelector('#link-fields').disabled=!session;
  document.querySelector('#refresh').disabled=!session;
  document.querySelector('#more').disabled=!session;
  document.querySelector('#account-status').textContent=session?'Signed in as '+session.user.email:'Sign in or create an account to manage your links.';
  document.querySelector('#links').textContent=session?'Loading your links…':'Sign in to see your links.';
  if(session)expiryTimer=setTimeout(()=>{setSession(null);status('Your session expired. Sign in again.');},session.expires_in*1000);
}
setSession(null);
document.querySelector('#logout').onclick=()=>{setSession(null);status('Signed out.');};
async function authenticate(action){
  const form=document.querySelector('#auth');
  if(!form.reportValidity())return;
  const f=new FormData(form),buttons=form.querySelectorAll('button');buttons.forEach(b=>b.disabled=true);
  try{const session=await api('/api/auth/'+action,{method:'POST',body:JSON.stringify({email:f.get('email'),password:f.get('password')})});
    form.reset();document.querySelector('#auth-message').textContent='';setSession(session);status('You can now create and manage your links.');await load();
  }catch(e){document.querySelector('#auth-message').textContent=e.message;}finally{buttons.forEach(b=>b.disabled=false)}
}
document.querySelector('#auth').onsubmit=e=>{e.preventDefault();return authenticate('login');};
document.querySelector('#register').onclick=()=>authenticate('register');
async function api(path,options={}){const res=await fetch(path,{...options,headers:{'Content-Type':'application/json',...(accessToken?{Authorization:'Bearer '+accessToken}:{})}});if(!res.ok){if(res.status===401 && accessToken)setSession(null);const e=await res.json();throw Error(typeof e.detail==='string'?e.detail:JSON.stringify(e.detail))}return res.status===204?null:res.json()}
function status(text){message.textContent=text}
async function load(){try{const rows=await api('/api/links?offset='+offset),root=document.querySelector('#links');root.replaceChildren();if(!rows.length)root.textContent='No links on this page.';for(const r of rows){const node=document.createElement('div');node.className='link';const a=document.createElement('a');a.href=r.short_path;a.textContent=location.origin+r.short_path;a.target='_blank';a.rel='noopener';const p=document.createElement('p');p.textContent=r.original_url+' · '+(r.expires_at?'Expires '+new Date(r.expires_at).toLocaleString():'No expiration');node.append(a,p);const actions=document.createElement('div');actions.className='actions';for(const [label,fn] of [['Copy',async()=>{await navigator.clipboard.writeText(a.href);status('Copied link')}],['Edit',async()=>{const url=prompt('New destination URL',r.original_url);if(!url)return;const expiry=prompt('Expiration as ISO timestamp, or blank to clear',r.expires_at||'');if(expiry===null)return;await api('/api/links/'+r.code,{method:'PUT',body:JSON.stringify({original_url:url,expires_at:expiry||null})});await load()}],['Delete',async()=>{if(confirm('Delete this link?')){await api('/api/links/'+r.code,{method:'DELETE'});await load()}}]]){const b=document.createElement('button');b.className='secondary';b.textContent=label;b.onclick=()=>fn().catch(e=>status(e.message));actions.append(b)}node.append(actions);root.append(node)}}catch(e){status(e.message)}}
document.querySelector('#create').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);try{const r=await api('/api/links',{method:'POST',body:JSON.stringify({original_url:f.get('original_url'),alias:f.get('alias')||null,expires_at:f.get('expires_at')?new Date(f.get('expires_at')).toISOString():null})});status('Created '+location.origin+r.short_path);offset=0;await load()}catch(e){status(e.message)}};
document.querySelector('#refresh').onclick=()=>{offset=0;load()};document.querySelector('#more').onclick=()=>{offset+=100;load()};
