'use strict';

// GIFs are opt-in: no automatic movement, including with reduced motion enabled.
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
const chapters = [...document.querySelectorAll('[data-time]')];
let pendingSeek = null;
video.addEventListener('loadedmetadata', () => {
  if (pendingSeek !== null) {
    video.currentTime = pendingSeek;
    pendingSeek = null;
  }
});
chapters.forEach(button => button.addEventListener('click', async () => {
  const time = Number(button.dataset.time);
  if (video.readyState >= 1) video.currentTime = time;
  else pendingSeek = time;
  try {
    await video.play();
    status.textContent = 'Playing the continuous in-game recording.';
  } catch {
    status.textContent = 'Press play in the video controls to listen.';
  }
}));
video.addEventListener('timeupdate', () => {
  const active = chapters.filter(button => Number(button.dataset.time) <= video.currentTime).at(-1);
  chapters.forEach(button => {
    button.classList.toggle('active', button === active);
    if (button === active) button.setAttribute('aria-current', 'true');
    else button.removeAttribute('aria-current');
  });
});
video.addEventListener('error', () => {
  status.textContent = 'The video could not load. Try reopening this page or download the clip below.';
});
