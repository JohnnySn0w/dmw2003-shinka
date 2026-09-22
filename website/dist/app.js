'use strict';

// Only the visitor starts playback. Keep one demonstration playing at a time.
const demos = [...document.querySelectorAll('video')];
demos.forEach(demo => demo.addEventListener('play', () => {
  demos.forEach(other => { if (other !== demo) other.pause(); });
}));

const video = document.getElementById('soundtrack');
const status = document.getElementById('sound-status');
const pause = document.getElementById('sound-pause');
const chapters = [...document.querySelectorAll('[data-time]')];
let pendingSeek = null;
let hasPlayed = false;

function updatePlayback() {
  const active = chapters.filter(button => Number(button.dataset.time) <= video.currentTime).at(-1);
  chapters.forEach(button => {
    button.classList.toggle('active', hasPlayed && button === active);
    if (hasPlayed && button === active) button.setAttribute('aria-current', 'true');
    else button.removeAttribute('aria-current');
  });
  if (!hasPlayed) return;
  pause.hidden = false;
  pause.textContent = video.ended ? 'Replay recording' : video.paused ? 'Resume recording' : 'Pause recording';
  const message = video.ended ? 'Recording complete. Choose a chapter to listen again.'
    : `${video.paused ? 'Paused' : 'Playing'}: ${active.dataset.label}. Continuous in-game recording.`;
  if (status.textContent !== message) status.textContent = message;
}

function applyPendingSeek() {
  if (pendingSeek !== null && video.readyState >= 2) {
    video.currentTime = pendingSeek;
    pendingSeek = null;
  }
}

async function playRecording() {
  try {
    await video.play();
    applyPendingSeek();
  } catch (error) {
    // A newer pause/seek may intentionally interrupt an earlier play request.
    if (error.name !== 'AbortError') {
      status.textContent = 'Press play in the video controls to listen, or download the clip.';
    }
  }
}
// Wait for frame data on the first request, including an immediate pause while
// loading. A later chapter choice replaces the queued destination.
video.addEventListener('loadeddata', applyPendingSeek);
video.addEventListener('canplay', applyPendingSeek);
chapters.forEach(button => button.addEventListener('click', () => {
  pendingSeek = Number(button.dataset.time);
  applyPendingSeek();
  playRecording();
}));
pause.addEventListener('click', () => {
  if (video.paused || video.ended) playRecording();
  else video.pause();
});
video.addEventListener('play', () => { hasPlayed = true; updatePlayback(); });
['pause', 'timeupdate', 'seeked', 'ended'].forEach(event => video.addEventListener(event, updatePlayback));
video.addEventListener('error', () => {
  status.textContent = 'The video could not load. Try reopening this page or download the clip.';
});


const sceneNames = { central: 'Central Park', badlands: 'North Badland W' };
document.querySelectorAll('[data-sound-scene]').forEach(button => {
  button.addEventListener('click', () => {
    if (button.getAttribute('aria-pressed') === 'true') return;
    video.pause();
    pendingSeek = null;
    hasPlayed = false;
    const scene = button.dataset.soundScene;
    video.querySelector('source').src = button.dataset.src;
    video.querySelector('track').src = button.dataset.captions;
    video.poster = button.dataset.poster;
    video.load();
    document.getElementById('sound-scene-name').textContent = sceneNames[scene];
    document.getElementById('sound-download').href = button.dataset.src;
    video.querySelector('a').href = button.dataset.src;
    document.querySelectorAll('[data-sound-scene]').forEach(other =>
      other.setAttribute('aria-pressed', String(other === button)));
    pause.hidden = true;
    status.textContent = `${sceneNames[scene]}. Choose a palette to hear it.`;
    updatePlayback();
  });
});

const comparisons = {
  album: 'Card Album with Eclipse Undo selected',
  title: 'Shinka title screen',
  field: 'Central Park field',
  battle: 'Battle command selection'
};
document.getElementById('comparison-scene').addEventListener('change', event => {
  const scene = event.target.value;
  const original = document.querySelector('.aspect-original');
  const wide = document.querySelector('.aspect-wide');
  original.src = event.target.selectedOptions[0].dataset.original;
  wide.src = event.target.selectedOptions[0].dataset.wide;
  original.alt = `${comparisons[scene]}, original 4:3 view`;
  wide.alt = `${comparisons[scene]}, widescreen view`;
});


const motionDemo = document.getElementById('motion-demo');
document.querySelectorAll('[data-motion]').forEach(button => {
  button.addEventListener('click', () => {
    if (button.getAttribute('aria-pressed') === 'true') return;
    motionDemo.pause();
    const rate = button.dataset.motion;
    motionDemo.querySelector('source').src = button.dataset.src;
    motionDemo.querySelector('track').src = button.dataset.captions;
    motionDemo.load();
    document.getElementById('motion-rate').textContent = `${rate}% pose speed`;
    document.querySelectorAll('[data-motion]').forEach(other =>
      other.setAttribute('aria-pressed', String(other === button)));
  });
});
