// Broadcast-style overlay for Midnight Circuit, laid out on a 1280x720 stage.
import { CARS } from './timeline.js';

const hex = (n) => '#' + n.toString(16).padStart(6, '0');
const fmt = (s) => { const m = Math.floor(s / 60), r = s - m * 60; return `${m}:${r.toFixed(3).padStart(6, '0')}`; };

export function createHud(stage) {
  stage.insertAdjacentHTML('beforeend', `
  <div class="hud">
    <div class="bar top"></div><div class="bar bottom"></div>
    <div class="title"><div class="t1">MIDNIGHT<span>CIRCUIT</span></div><div class="t2"><b style="color:${hex(CARS[0].color)}">#${CARS[0].num} ${CARS[0].name}</b> &nbsp;VS&nbsp; <b style="color:${hex(CARS[1].color)}">#${CARS[1].num} ${CARS[1].name}</b><i>2 LAPS · NO RULES</i></div></div>
    <div class="lights">${'<i></i>'.repeat(5)}</div>
    <div class="go">GO!</div>
    <div class="race">
      <div class="lap"><span class="lapn">LAP 1/2</span><span class="clock">0:00.000</span></div>
      <div class="row r0"><b class="pos">P1</b><i class="chip"></i><span class="nm"></span><span class="gap"></span></div>
      <div class="row r1"><b class="pos">P2</b><i class="chip"></i><span class="nm"></span><span class="gap"></span></div>
    </div>
    <div class="speeds">${CARS.map((c, i) => `<div class="spd s${i}"><i class="chip" style="background:${hex(c.color)}"></i><span class="nm">#${c.num} ${c.name}</span><span class="kmh">0</span><span class="unit">KM/H</span><span class="gear">N</span></div>`).join('')}</div>
    <div class="slomo"><i></i>SUPER SLO-MO</div>
    <div class="caption"></div>
    <div class="winner"><div class="w1">WINNER</div><div class="w2"></div><div class="w3"></div></div>
  </div>`);
  const $ = (q) => stage.querySelector(q);
  const el = {
    root: $('.hud'), title: $('.title'), lights: [...stage.querySelectorAll('.lights i')], lightsBox: $('.lights'), go: $('.go'),
    race: $('.race'), lap: $('.lapn'), clock: $('.clock'), rows: [$('.r0'), $('.r1')], speeds: $('.speeds'),
    spd: [0, 1].map((i) => ({ kmh: $(`.s${i} .kmh`), gear: $(`.s${i} .gear`) })), slomo: $('.slomo'),
    caption: $('.caption'), winner: $('.winner'), w2: $('.w2'), w3: $('.w3'),
  };
  let lastCaption = null;

  return function update(h, cam) {
    el.root.style.opacity = (1 - cam.fade * 0.85).toFixed(3);
    el.title.style.opacity = h.title.toFixed(3);
    el.title.style.transform = `translate(-50%,-50%) skewX(-12deg) scale(${(1.08 - 0.08 * h.title).toFixed(3)})`;
    el.lightsBox.style.opacity = h.lights === 0 || h.go === 0 && h.lights < 0 ? 0 : 1;
    el.lights.forEach((l, i) => l.classList.toggle('on', h.lights > i));
    el.go.style.opacity = h.go.toFixed(3);
    el.go.style.transform = `translate(-50%,-50%) skewX(-12deg) scale(${(1.6 - 0.6 * h.go).toFixed(3)})`;

    el.race.style.opacity = el.speeds.style.opacity = h.show ? 1 : 0;
    el.lap.textContent = h.finished[0] || h.finished[1] ? 'FINISH' : `LAP ${h.lap}/${h.laps}`;
    el.clock.textContent = fmt(h.raceTime);
    h.order.forEach((ci, k) => {
      const r = el.rows[k];
      r.querySelector('.chip').style.background = hex(CARS[ci].color);
      r.querySelector('.nm').textContent = `#${CARS[ci].num} ${CARS[ci].name}`;
      r.querySelector('.gap').textContent = k === 0 ? 'LEADER' : `+${h.gapT.toFixed(3)}`;
    });
    h.speeds.forEach((v, i) => { el.spd[i].kmh.textContent = v; el.spd[i].gear.textContent = v < 2 ? 'N' : h.gears[i]; });
    el.slomo.style.opacity = h.slowmo && h.show ? (Math.floor(cam.tau * 3) % 2 ? 1 : 0.55) : 0;

    if (h.caption) {
      if (lastCaption !== h.caption.text) { el.caption.textContent = h.caption.text; lastCaption = h.caption.text; }
      const inK = Math.min(1, h.caption.age / 0.25), outK = Math.min(1, h.caption.left / 0.25);
      const x = (1 - inK) * -260 + (1 - outK) * 260;
      el.caption.style.opacity = Math.min(inK, outK).toFixed(3);
      el.caption.style.transform = `translate(calc(-50% + ${x.toFixed(1)}px), 0) skewX(-14deg)`;
    } else el.caption.style.opacity = 0;

    el.winner.style.opacity = h.winner.toFixed(3);
    el.winner.style.transform = `translate(-50%,-50%) skewX(-10deg) scale(${(1.25 - 0.25 * h.winner).toFixed(3)})`;
    el.w2.innerHTML = `#${h.winnerNum} ${h.winnerName}`;
    el.w3.textContent = `BY ${h.margin.toFixed(3)} SECONDS`;
  };
}
