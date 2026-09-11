'use strict';
let catalog, selected, labels = {}, token;
const drafts = new Map();
const $ = s => document.querySelector(s);
const node = (tag, text, cls) => { const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n; };
const labeled = p => Boolean(labels[p.key]?.instrument?.trim());
const progress = t => t.parts.filter(labeled).length;
function announce(message){$('#notice').textContent=message;}
function draft(p){
  if(!drafts.has(p.key)) drafts.set(p.key,{instrument:'',confidence:'unknown',notes:'',revision:0,audio_source:p.sources[0],...labels[p.key],dirty:false,version:0});
  return drafts.get(p.key);
}
function updateNavigation(){
  const all=catalog.tracks.flatMap(t=>t.parts);
  $('#total').textContent=`${all.filter(labeled).length} / ${all.length} instruments labeled`;
  const search=$('#search').value.toLowerCase();
  const list=$('#tracks'); list.replaceChildren();
  for(const t of catalog.tracks){
    if(!`${t.title} ${t.scene} ${t.id}`.toLowerCase().includes(search) || ($('#unfinished').checked && progress(t)===t.parts.length))continue;
    const b=node('button',t.title,t.id===selected?'active':'');
    b.append(node('small',`${progress(t)} / ${t.parts.length} labeled · ${t.id}`));
    b.onclick=()=>showTrack(t.id); list.append(b);
  }
  if(!list.children.length)list.append(node('p','No matching tracks.','empty'));
}
function stopAudio(){document.querySelectorAll('audio').forEach(a=>a.pause());}
function showTrack(id, focusKey){
  stopAudio();selected=id;location.hash=encodeURIComponent(id);updateNavigation();
  const t=catalog.tracks.find(t=>t.id===id), root=$('#workspace');root.replaceChildren();
  const head=node('div',undefined,'track-head');head.append(node('span',t.id,'eyebrow'),node('h2',t.title),node('p',t.scene));
  head.append(node('p',t.parts.some(p=>p.sources.includes('native'))?'Original in-game captures are available here and selected by default.':'These parts use the original samples in an approximate offline render.','hint'));
  head.append(node('p','Listen to a part, name what you hear, then save. “Tentative” is fine. Short excerpts have individual listening levels.','hint'));
  head.append(node('div',`${progress(t)} of ${t.parts.length} labeled`,'track-progress'));root.append(head);
  for(const p of t.parts)root.append(partCard(t,p));
  if(focusKey){const card=document.getElementById(`part-${focusKey}`);card.scrollIntoView({block:'center',behavior:'smooth'});card.querySelector('input').focus({preventScroll:true});}
}
function select(options, value, label){
  const s=node('select');s.setAttribute('aria-label',label);
  for(const [v,text] of options){const o=node('option',text);o.value=v;s.append(o);}s.value=value;return s;
}
function partCard(track,p){
  const d=draft(p), card=node('article',undefined,'part');card.id=`part-${p.key}`;
  const head=node('div',undefined,'part-head'), badge=node('span',labels[p.key]?.instrument||'Unlabeled','saved-label');
  head.append(node('h3',`${track.title} · Part ${p.number}`),badge);card.append(head);
  const player=node('audio');player.controls=true;player.preload='none';player.setAttribute('aria-label',`Part ${p.number} isolate`);
  const source=select(p.sources.map(s=>[s,s==='native'?'In-game capture':'Offline approximation']),d.audio_source,`Part ${p.number} audio source`);
  const length=select([['short','Short excerpt'],['full','Full part']],'short',`Part ${p.number} clip length`);
  const setAudio=()=>{player.pause();player.src=`/audio/${p.key}/${source.value}/${length.value}`;};setAudio();
  player.onplay=()=>document.querySelectorAll('audio').forEach(a=>{if(a!==player)a.pause();});
  const line=node('div',undefined,'audio-line');line.append(player,source,length);card.append(line);
  const fields=node('div',undefined,'fields'), nameLabel=node('label','Instrument'), name=node('input');
  name.value=d.instrument;name.maxLength=160;name.placeholder='e.g. accordion, metallic bell…';name.setAttribute('list','instruments');nameLabel.append(name);
  const confidenceLabel=node('label','Confidence'), confidence=select([['unknown','Not sure yet'],['tentative','Tentative'],['confident','Confident']],d.confidence,`Part ${p.number} confidence`);
  confidenceLabel.append(confidence);fields.append(nameLabel,confidenceLabel);card.append(fields);
  const noteLabel=node('label','Notes · optional','notes'), notes=node('textarea');notes.value=d.notes;notes.maxLength=3000;notes.rows=2;notes.placeholder='What does it sound like? Any alternative guesses?';noteLabel.append(notes);card.append(noteLabel);
  const actions=node('div',undefined,'actions'), save=node('button','Save label','primary'), next=node('button','Save & next unlabeled'), status=node('span',d.dirty?'Unsaved changes':labels[p.key]?'Saved':'','save-state');
  status.setAttribute('role','status');actions.append(save,next,status);card.append(actions);
  const changed=()=>{Object.assign(d,{instrument:name.value,confidence:confidence.value,notes:notes.value,audio_source:source.value,dirty:true,version:d.version+1});status.textContent='Unsaved changes';status.className='save-state';};
  name.oninput=changed;notes.oninput=changed;confidence.onchange=changed;
  source.onchange=()=>{setAudio();changed();};length.onchange=setAudio;
  const persist=async advance=>{
    if(save.disabled)return;
    changed();const version=d.version;save.disabled=next.disabled=true;status.textContent='Saving…';
    try{
      const response=await fetch('/api/labels',{method:'POST',headers:{'Content-Type':'application/json','X-Label-Token':token},body:JSON.stringify({key:p.key,instrument:d.instrument,confidence:d.confidence,notes:d.notes,revision:d.revision,audio_source:d.audio_source})});
      const result=await response.json();if(!response.ok)throw Error(result.error||'Could not save');
      labels[p.key]=result;d.revision=result.revision;
      if(d.version===version)Object.assign(d,result,{dirty:false});
      status.textContent=d.dirty?'Newer edits are unsaved':'Saved to disk';badge.textContent=result.instrument||'Unlabeled';updateNavigation();
      const current=catalog.tracks.find(t=>t.id===selected);
      $('.track-progress').textContent=`${progress(current)} of ${current.parts.length} labeled`;
      if(advance && !d.dirty && selected===track.id){
        const ordered=catalog.tracks.flatMap(t=>t.parts.map(part=>({t,part}))), i=ordered.findIndex(x=>x.part.key===p.key);
        const target=[...ordered.slice(i+1),...ordered.slice(0,i)].find(x=>!labeled(x.part));
        if(target)showTrack(target.t.id,target.part.key);else announce('Every part has a label. You can revisit any track to refine it.');
      }
    }catch(e){status.textContent=e.message;status.className='save-state error';}
    finally{save.disabled=next.disabled=false;}
  };
  save.onclick=()=>persist(false);next.onclick=()=>persist(true);
  card.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();persist(true);}};
  const detail=node('details',undefined,'metadata');detail.append(node('summary','Source details'),node('p',`Programs ${p.identity.programs.join(', ')} · Samples ${p.identity.samples.join(', ')}. Ctrl+Enter saves and advances.`));card.append(detail);
  return card;
}
window.addEventListener('beforeunload',e=>{if([...drafts.values()].some(d=>d.dirty)){e.preventDefault();e.returnValue='';}});
$('#search').oninput=()=>updateNavigation();$('#unfinished').onchange=()=>updateNavigation();
(async()=>{
  try{
    const response=await fetch('/api/catalog');if(!response.ok)throw Error('Could not open the labeling library.');
    catalog=await response.json();labels=catalog.labels;token=catalog.token;
    const requested=decodeURIComponent(location.hash.slice(1));
    showTrack(catalog.tracks.find(t=>t.id===requested)?.id||catalog.tracks.find(t=>t.id==='BGM018-000')?.id||catalog.tracks[0].id);
    if(document.modelContext?.registerTool){
      document.modelContext.registerTool({name:'read_instrument_labels',description:'Read saved labels for the current music track.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true},execute:input=>{
        if(!input || typeof input!=='object' || Array.isArray(input) || Object.keys(input).length)throw Error('This read tool takes an empty object.');
        return {track:selected,parts:catalog.tracks.find(t=>t.id===selected).parts.map(p=>({part:p.number,label:labels[p.key]||null}))};
      }});
    }
  }catch(e){announce(e.message);}
})();
