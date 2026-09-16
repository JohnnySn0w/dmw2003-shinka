'use strict';

// Animation and audio begin only after an explicit visitor action.
document.querySelectorAll('[data-toggle]').forEach(button => {
  const picture = document.getElementById(button.dataset.toggle);
  const label = button.textContent.replace(/^Play /, '');
  button.addEventListener('click', () => {
    const playing = button.getAttribute('aria-pressed') === 'true';
    picture.src = playing ? picture.dataset.still : picture.dataset.gif;
    button.setAttribute('aria-pressed', String(!playing));
    button.textContent = `${playing ? 'Play' : 'Stop'} ${label}`;
  });
});

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
