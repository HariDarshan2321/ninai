"""Dependency-free control-center page served by the hosted API."""

CONTROL_CENTER_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ninai Control Center</title><style>
:root{font:15px system-ui;color:#18201d;background:#f4f7f5}body{max-width:1050px;margin:0 auto;padding:32px}
h1{margin-bottom:4px}.muted{color:#61706a}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.card{background:white;border:1px solid #dfe7e2;border-radius:12px;padding:18px;margin:12px 0}button{cursor:pointer}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:8px;border-bottom:1px solid #e5ebe7}
.danger{color:#9c2d25}code{font-size:12px}</style></head><body>
<h1>Ninai</h1><p class="muted">Hosted memory control center</p>
<div class="card"><label>Access token <input id="token" type="password" autocomplete="off" placeholder="Bearer token"></label>
<button onclick="connect()">Connect</button> <button onclick="disconnect()">Disconnect</button></div><div id="app">Enter an access token to continue.</div>
<script>
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let accessToken=sessionStorage.getItem('ninai_access_token')||'';document.querySelector('#token').value=accessToken;
function connect(){accessToken=document.querySelector('#token').value.trim();sessionStorage.setItem('ninai_access_token',accessToken);load()}
function disconnect(){accessToken='';sessionStorage.removeItem('ninai_access_token');document.querySelector('#token').value='';document.querySelector('#app').textContent='Disconnected.'}
async function api(path,options){if(!accessToken)throw Error('Enter an access token');let r=await fetch('/api/control'+path,{...options,headers:{'content-type':'application/json','authorization':'Bearer '+accessToken,...(options?.headers||{})}});if(!r.ok)throw Error((await r.json()).error||r.statusText);return r.status===204?null:r.json()}
async function act(path,body){await api(path,{method:'POST',body:JSON.stringify(body||{})});load()}
async function load(){try{let [o,m,c,a]=await Promise.all([api('/overview'),api('/memories?status=proposed'),api('/connections'),api('/activity')]);
document.querySelector('#app').innerHTML=`<div class="grid"><div class="card"><b>${o.counts.active_memories}</b><br>Active memories</div><div class="card"><b>${o.counts.proposals}</b><br>Proposals</div><div class="card"><b>${o.counts.active_connections}</b><br>Connections</div><div class="card"><b>${o.counts.disclosures}</b><br>Disclosures</div></div>
<section class="card"><h2>Review queue</h2>${m.items.length?`<table><tr><th>Memory</th><th>Source</th><th>Action</th></tr>${m.items.map(x=>`<tr><td>${esc(x.content)}</td><td><code>${esc(x.source_uri)}</code></td><td><button onclick="act('/memories/${x.id}/approve')">Approve</button> <button onclick="act('/memories/${x.id}/reject')">Reject</button></td></tr>`).join('')}</table>`:'<p class="muted">No proposals.</p>'}</section>
<section class="card"><h2>Connections</h2>${c.items.map(x=>`<p><b>${esc(x.display_name)}</b> · ${esc(x.provider)} · ${esc(x.status)} ${x.status==='active'?`<button class="danger" onclick="act('/connections/${x.id}/revoke')">Revoke</button>`:''}</p>`).join('')||'<p class="muted">No connections.</p>'}</section>
<section class="card"><h2>Recent disclosures</h2>${a.items.map(x=>`<p><b>${esc(x.tool_name)}</b> · ${esc(x.decision)} · ${esc(x.created_at)}</p>`).join('')||'<p class="muted">No activity.</p>'}</section>`}catch(e){document.querySelector('#app').innerHTML=`<div class="card danger">${esc(e.message)}</div>`}}load();
</script></body></html>"""
