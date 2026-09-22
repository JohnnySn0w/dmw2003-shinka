'use strict';
const $ = id => document.getElementById(id);
let catalog, profile, token, context, buffers = [], controls = {}, nodes = [], sources = [];
let selected, sound, generation = 0, playing = false, solo = null, saveChain = Promise.resolve();
let saveFailed = false;
const db = value => 10 ** (value / 20);
const currentKey = () => `${selected.id}/${sound}`;
function message(text) { $('status').textContent = text; }
function stop() {
  for (const source of sources) { try { source.stop(); } catch {} source.disconnect(); }
  sources = []; nodes = []; playing = false; $('play').textContent = 'Play mix';
}
function stopComparisons() { $('before').pause(); $('after').pause(); }
function graph(ctx, buffer, values, destination) {
  const source = ctx.createBufferSource(); source.buffer = buffer;
  const gain = ctx.createGain(); gain.gain.value = db(values.gain);
  const warmth = ctx.createBiquadFilter(); warmth.type = 'peaking'; warmth.frequency.value = 300;
  warmth.Q.value = .7; warmth.gain.value = values.warmth;
  const presence = ctx.createBiquadFilter(); presence.type = 'peaking'; presence.frequency.value = 2500;
  presence.Q.value = .7; presence.gain.value = values.presence;
  source.connect(warmth).connect(presence).connect(gain).connect(destination);
  return {source, gain, warmth, presence};
}
function applyLive() {
  nodes.forEach((node, index) => {
    const part = selected.palettes[sound].parts[index], value = controls[part.part];
    const time = context.currentTime;
    node.gain.gain.setTargetAtTime(solo === null || solo === part.part ? db(value.gain) : 0, time, .015);
    node.warmth.gain.setTargetAtTime(value.warmth, time, .015);
    node.presence.gain.setTargetAtTime(value.presence, time, .015);
  });
}
function queueSave() {
  const key = currentKey(), values = structuredClone(controls);
  profile.values[key] = values;
  $('save').textContent = 'Saving…';
  saveChain = saveChain.then(async () => {
    if (saveFailed) throw new Error('Reload before saving more adjustments.');
    const response = await fetch('/api/profile', {method:'POST', headers:{'Content-Type':'application/json', 'X-Mixer-Token':token},
      body:JSON.stringify({identity:catalog.identity, revision:profile.revision, key, values})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Save failed');
    profile.revision = result.revision;
    $('save').textContent = 'Saved on this computer.';
  }).catch(error => {saveFailed = true; $('save').textContent = `Not saved: ${error.message}`;});
}
function showParts() {
  $('parts').replaceChildren();
  for (const part of selected.palettes[sound].parts) {
    const row = document.createElement('article'); row.className = 'part';
    const info = document.createElement('div'), title = document.createElement('h3'), note = document.createElement('small');
    title.textContent = `${String(part.part).padStart(2,'0')} · ${part.instrument}`;
    note.textContent = `Auto: ${part.gain_db > 0 ? '+' : ''}${part.gain_db.toFixed(1)} dB · warmth ${part.warmth} · presence ${part.presence}`;
    const button = document.createElement('button'); button.textContent = 'Solo'; button.setAttribute('aria-pressed','false');
    button.setAttribute('aria-label', `Solo part ${part.part}: ${part.instrument}`);
    button.onclick = () => { solo = solo === part.part ? null : part.part; showParts(); applyLive(); };
    button.setAttribute('aria-pressed', String(solo === part.part));
    info.append(title, note, button); row.append(info);
    for (const [key, name, limit] of [['gain','Volume',12], ['warmth','Warmth',6], ['presence','Presence',6]]) {
      const label = document.createElement('label'); label.className = 'control';
      const caption = document.createElement('span'), text = document.createElement('span'), output = document.createElement('output');
      text.textContent = name; output.textContent = `${controls[part.part][key].toFixed(1)} dB`;
      caption.append(text,output);
      const input = document.createElement('input'); input.type = 'range'; input.min = -limit; input.max = limit; input.step = .5;
      input.value = controls[part.part][key]; input.setAttribute('aria-label', `${name} part ${part.part}: ${part.instrument}`);
      input.oninput = () => { controls[part.part][key] = Number(input.value); output.textContent = `${Number(input.value).toFixed(1)} dB`; applyLive(); };
      input.onchange = queueSave;
      label.append(caption,input); row.append(label);
    }
    $('parts').append(row);
  }
}
async function select() {
  const ticket = ++generation;
  stop(); stopComparisons(); buffers = []; solo = null;
  for (const id of ['play','stop','export','reset']) $(id).disabled = true;
  selected = catalog.tracks.find(track => track.id === $('track').value); sound = $('palette').value;
  history.replaceState(null,'',`#${selected.id}/${sound}`);
  const data = selected.palettes[sound];
  controls = structuredClone(profile.values[currentKey()] || Object.fromEntries(data.parts.map(p => [p.part,{gain:0,warmth:0,presence:0}])));
  $('scene').textContent = selected.scene; $('save').textContent = saveFailed ? 'Changes are unsaved. Reload before editing.' : 'Changes are saved separately for each sound.';
  $('before').src = `/${selected.id}/${sound}.mp3`; $('before').volume = data.compare_original_gain;
  $('after').src = `/${data.mix}`; $('after').volume = data.compare_balanced_gain;
  $('balanced-download').href = `/${data.mix.replace(/mp3$/,'wav')}`; $('balanced-download').download = '';
  showParts(); message(`Loading ${data.parts.length} aligned instruments…`);
  try {
    context ||= new AudioContext({sampleRate:48000});
    const loaded = [];
    // Decode sequentially so changing tracks does not leave a large decode queue.
    for (const part of data.parts) {
      if (ticket !== generation) return;
      const response = await fetch(`/${part.file}`);
      if (!response.ok) throw new Error('Could not load instrument audio');
      loaded.push(await context.decodeAudioData(await response.arrayBuffer()));
    }
    if (ticket !== generation) return;
    buffers = loaded;
    for (const id of ['play','stop','export','reset']) $(id).disabled = false;
    message(`${data.parts.length} parts ready · ${Math.round(buffers[0].duration)} seconds`);
  } catch(error) { if (ticket === generation) message(error.message); }
}
$('play').onclick = async () => {
  if (playing) { stop(); return; }
  const ticket = generation;
  await context.resume(); if (ticket !== generation || !buffers.length) return;
  stopComparisons();
  const limiter = context.createDynamicsCompressor(); limiter.threshold.value = -2; limiter.knee.value = 0;
  limiter.ratio.value = 20; limiter.attack.value = .003; limiter.release.value = .1; limiter.connect(context.destination);
  nodes = buffers.map((buffer,i) => graph(context,buffer,controls[selected.palettes[sound].parts[i].part],limiter));
  sources = nodes.map(node => node.source); applyLive();
  const start = context.currentTime + .08;
  for (const source of sources) source.start(start);
  const first = sources[0]; first.onended = () => {if (sources[0] === first) stop(); limiter.disconnect();};
  playing = true; $('play').textContent = 'Stop mix';
};
$('stop').onclick = () => {stop(); stopComparisons();};
$('reset').onclick = () => {
  for (const value of Object.values(controls)) Object.assign(value,{gain:0,warmth:0,presence:0});
  showParts(); applyLive(); queueSave();
};
for (const id of ['before','after']) $(id).onplay = () => {stop(); $(id === 'before' ? 'after' : 'before').pause();};
$('export').onclick = async () => {
  const exportButton = $('export'), ticket = generation, trackId = selected.id, palette = sound;
  const settings = structuredClone(controls), parts = selected.palettes[sound].parts, audio = buffers.slice();
  exportButton.disabled = true; message('Rendering your mix…');
  try {
    const offline = new OfflineAudioContext(2, audio[0].length, 48000);
    audio.forEach((buffer,i) => graph(offline,buffer,settings[parts[i].part],offline.destination).source.start());
    const rendered = await offline.startRendering(), left = rendered.getChannelData(0), right = rendered.getChannelData(1);
    let peak = 0;
    for(let i=0;i<left.length;i++) peak = Math.max(peak,Math.abs(left[i]),Math.abs(right[i]));
    const gain = Math.min(1,.79 / Math.max(peak,1e-12)), bytes = new ArrayBuffer(44 + left.length*4), view = new DataView(bytes);
    const str = (offset,value) => [...value].forEach((c,i) => view.setUint8(offset+i,c.charCodeAt(0)));
    str(0,'RIFF'); view.setUint32(4,bytes.byteLength-8,true); str(8,'WAVE'); str(12,'fmt ');
    view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,2,true); view.setUint32(24,48000,true);
    view.setUint32(28,192000,true); view.setUint16(32,4,true); view.setUint16(34,16,true); str(36,'data'); view.setUint32(40,left.length*4,true);
    for(let i=0;i<left.length;i++) { view.setInt16(44+i*4,Math.round(left[i]*gain*32767),true); view.setInt16(46+i*4,Math.round(right[i]*gain*32767),true); }
    const url = URL.createObjectURL(new Blob([bytes],{type:'audio/wav'})), link = document.createElement('a');
    link.href = url; link.download = `${trackId}-${palette}-my-mix.wav`; link.click(); setTimeout(() => URL.revokeObjectURL(url),60000);
    if(ticket === generation) message(`Exported all parts${gain < 1 ? ` · safety trim ${(20*Math.log10(gain)).toFixed(1)} dB` : ''}. Solo does not affect export.`);
  } catch(error) {if(ticket === generation) message(`Export failed: ${error.message}`);}
  finally {if(ticket === generation) exportButton.disabled = false;}
};
$('track').onchange = select; $('palette').onchange = select;
window.addEventListener('pagehide',stop);
(async () => {
  try {
    const response = await fetch('/api/mixer'); if(!response.ok) throw new Error('Mix server unavailable');
    ({catalog,profile,token} = await response.json());
    for(const track of catalog.tracks) {const option = document.createElement('option'); option.value = track.id; option.textContent = `${track.title} · ${track.id}`; $('track').append(option);}
    const [track,sound] = location.hash.slice(1).split('/');
    if(catalog.tracks.some(t => t.id === track)) $('track').value = track;
    if(['sampled','ds','chip'].includes(sound)) $('palette').value = sound;
    await select();
  } catch(error) {message(error.message);}
})();
