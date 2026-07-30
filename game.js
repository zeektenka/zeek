/* ===========================================================
   NEON RAIDERS — retro arcade space shooter
   Vanilla canvas 2D + synthesized WebAudio sound effects.
   =========================================================== */

(() => {
  "use strict";

  // ---------- canvas setup ----------
  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;

  // ---------- DOM refs ----------
  const scoreEl = document.getElementById("score");
  const levelEl = document.getElementById("level");
  const hiscoreEl = document.getElementById("hiscore");
  const livesRow = document.getElementById("livesRow");
  const bossbar = document.getElementById("bossbar");
  const bossbarFill = document.getElementById("bossbarFill");
  const startScreen = document.getElementById("startScreen");
  const pauseScreen = document.getElementById("pauseScreen");
  const gameOverScreen = document.getElementById("gameOverScreen");
  const finalScoreEl = document.getElementById("finalScore");
  const newHighEl = document.getElementById("newHigh");
  const startBtn = document.getElementById("startBtn");
  const restartBtn = document.getElementById("restartBtn");
  const muteBtn = document.getElementById("muteBtn");
  const levelUpBanner = document.getElementById("levelUpBanner");
  const levelUpNum = document.getElementById("levelUpNum");
  const touchLeft = document.getElementById("touchLeft");
  const touchRight = document.getElementById("touchRight");

  const HI_KEY = "neonRaiders.hiscore";

  // ===========================================================
  // AUDIO ENGINE — everything synthesized, no external files
  // ===========================================================
  const Sound = (() => {
    let ctxA = null;
    let muted = false;
    let musicTimer = null;
    let musicStep = 0;

    function ensureCtx() {
      if (!ctxA) ctxA = new (window.AudioContext || window.webkitAudioContext)();
      if (ctxA.state === "suspended") ctxA.resume();
      return ctxA;
    }

    function env(gainNode, t, attack, sustain, release, peak) {
      const g = gainNode.gain;
      g.cancelScheduledValues(t);
      g.setValueAtTime(0.0001, t);
      g.linearRampToValueAtTime(peak, t + attack);
      g.linearRampToValueAtTime(peak * 0.6, t + attack + sustain);
      g.exponentialRampToValueAtTime(0.0001, t + attack + sustain + release);
    }

    function tone({ freq, type = "square", dur = 0.15, slide = 0, vol = 0.2, delay = 0 }) {
      if (muted) return;
      const ac = ensureCtx();
      const t = ac.currentTime + delay;
      const osc = ac.createOscillator();
      const gain = ac.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, t);
      if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(20, freq + slide), t + dur);
      env(gain, t, 0.005, dur * 0.4, dur * 0.6, vol);
      osc.connect(gain).connect(ac.destination);
      osc.start(t);
      osc.stop(t + dur + 0.05);
    }

    function noiseBurst({ dur = 0.3, vol = 0.3, cutoff = 1200, delay = 0 }) {
      if (muted) return;
      const ac = ensureCtx();
      const t = ac.currentTime + delay;
      const bufferSize = Math.floor(ac.sampleRate * dur);
      const buffer = ac.createBuffer(1, bufferSize, ac.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * (1 - i / bufferSize);
      }
      const src = ac.createBufferSource();
      src.buffer = buffer;
      const filt = ac.createBiquadFilter();
      filt.type = "lowpass";
      filt.frequency.setValueAtTime(cutoff, t);
      filt.frequency.exponentialRampToValueAtTime(80, t + dur);
      const gain = ac.createGain();
      gain.gain.setValueAtTime(vol, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + dur);
      src.connect(filt).connect(gain).connect(ac.destination);
      src.start(t);
      src.stop(t + dur + 0.02);
    }

    return {
      laser() {
        tone({ freq: 900, slide: -600, type: "square", dur: 0.11, vol: 0.15 });
      },
      enemyLaser() {
        tone({ freq: 300, slide: -150, type: "sawtooth", dur: 0.14, vol: 0.12 });
      },
      hit() {
        tone({ freq: 1400, type: "square", dur: 0.06, vol: 0.12 });
      },
      explosion(big = false) {
        noiseBurst({ dur: big ? 0.6 : 0.3, vol: big ? 0.45 : 0.28, cutoff: big ? 2200 : 1200 });
        tone({ freq: big ? 140 : 220, slide: -100, type: "triangle", dur: big ? 0.5 : 0.25, vol: big ? 0.25 : 0.15 });
      },
      powerup() {
        [520, 660, 780, 1040].forEach((f, i) => tone({ freq: f, type: "square", dur: 0.1, vol: 0.14, delay: i * 0.06 }));
      },
      shieldUp() {
        tone({ freq: 200, slide: 500, type: "sine", dur: 0.3, vol: 0.18 });
      },
      playerHit() {
        noiseBurst({ dur: 0.35, vol: 0.35, cutoff: 900 });
        tone({ freq: 180, slide: -80, type: "sawtooth", dur: 0.3, vol: 0.2 });
      },
      levelUp() {
        [440, 554, 659, 880].forEach((f, i) => tone({ freq: f, type: "triangle", dur: 0.16, vol: 0.16, delay: i * 0.09 }));
      },
      gameOver() {
        [400, 340, 280, 200].forEach((f, i) => tone({ freq: f, type: "sawtooth", dur: 0.35, vol: 0.2, delay: i * 0.18 }));
      },
      bossAlert() {
        [200, 200, 200].forEach((f, i) => tone({ freq: f, type: "square", dur: 0.18, vol: 0.22, delay: i * 0.25 }));
      },
      uiBeep() {
        tone({ freq: 700, type: "square", dur: 0.06, vol: 0.12 });
      },
      startMusic() {
        if (musicTimer) return;
        const bass = [55, 55, 82.4, 65.4];
        musicStep = 0;
        musicTimer = setInterval(() => {
          if (muted) { musicStep++; return; }
          const f = bass[musicStep % bass.length];
          tone({ freq: f, type: "triangle", dur: 0.16, vol: 0.06 });
          if (musicStep % 2 === 0) tone({ freq: f * 4, type: "square", dur: 0.05, vol: 0.03 });
          musicStep++;
        }, 260);
      },
      stopMusic() {
        clearInterval(musicTimer);
        musicTimer = null;
      },
      setMuted(m) {
        muted = m;
      },
      isMuted() { return muted; },
      unlock() { ensureCtx(); }
    };
  })();

  // ===========================================================
  // UTILITIES
  // ===========================================================
  const rand = (a, b) => a + Math.random() * (b - a);
  const randInt = (a, b) => Math.floor(rand(a, b + 1));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const overlap = (a, b) =>
    a.x - a.r < b.x + b.r && a.x + a.r > b.x - b.r &&
    a.y - a.r < b.y + b.r && a.y + a.r > b.y - b.r;

  function loadHi() { return parseInt(localStorage.getItem(HI_KEY) || "0", 10); }
  function saveHi(v) { localStorage.setItem(HI_KEY, String(v)); }

  // ===========================================================
  // STARFIELD
  // ===========================================================
  class Starfield {
    constructor() {
      this.layers = [
        { speed: 20, size: 1, count: 60, color: "#5566aa", stars: [] },
        { speed: 45, size: 1.6, count: 40, color: "#88ccff", stars: [] },
        { speed: 80, size: 2.2, count: 22, color: "#ff9ee6", stars: [] },
      ];
      for (const layer of this.layers) {
        for (let i = 0; i < layer.count; i++) {
          layer.stars.push({ x: rand(0, W), y: rand(0, H), tw: rand(0, Math.PI * 2) });
        }
      }
    }
    update(dt) {
      for (const layer of this.layers) {
        for (const s of layer.stars) {
          s.y += layer.speed * dt;
          s.tw += dt * 3;
          if (s.y > H) { s.y = -2; s.x = rand(0, W); }
        }
      }
    }
    draw() {
      for (const layer of this.layers) {
        for (const s of layer.stars) {
          const a = 0.5 + Math.sin(s.tw) * 0.5;
          ctx.globalAlpha = a;
          ctx.fillStyle = layer.color;
          ctx.fillRect(s.x, s.y, layer.size, layer.size);
        }
      }
      ctx.globalAlpha = 1;
    }
  }

  // ===========================================================
  // PARTICLES
  // ===========================================================
  class Particles {
    constructor() { this.items = []; }
    burst(x, y, color, count = 14, speed = 140, life = 0.6) {
      for (let i = 0; i < count; i++) {
        const ang = rand(0, Math.PI * 2);
        const sp = rand(speed * 0.3, speed);
        this.items.push({
          x, y,
          vx: Math.cos(ang) * sp,
          vy: Math.sin(ang) * sp,
          life, maxLife: life,
          color,
          size: rand(1.5, 3.5),
        });
      }
    }
    update(dt) {
      for (let i = this.items.length - 1; i >= 0; i--) {
        const p = this.items[i];
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.vx *= 0.96;
        p.vy *= 0.96;
        p.life -= dt;
        if (p.life <= 0) this.items.splice(i, 1);
      }
    }
    draw() {
      for (const p of this.items) {
        ctx.globalAlpha = clamp(p.life / p.maxLife, 0, 1);
        ctx.fillStyle = p.color;
        ctx.fillRect(p.x - p.size / 2, p.y - p.size / 2, p.size, p.size);
      }
      ctx.globalAlpha = 1;
    }
  }

  // ===========================================================
  // ENTITIES
  // ===========================================================
  class Bullet {
    constructor(x, y, vx, vy, r, color, dmg, fromPlayer) {
      this.x = x; this.y = y; this.vx = vx; this.vy = vy;
      this.r = r; this.color = color; this.dmg = dmg;
      this.fromPlayer = fromPlayer; this.dead = false;
    }
    update(dt) {
      this.x += this.vx * dt;
      this.y += this.vy * dt;
      if (this.y < -20 || this.y > H + 20 || this.x < -20 || this.x > W + 20) this.dead = true;
    }
    draw() {
      ctx.save();
      ctx.shadowColor = this.color;
      ctx.shadowBlur = 10;
      ctx.fillStyle = this.color;
      ctx.beginPath();
      ctx.ellipse(this.x, this.y, this.r, this.r * 2.2, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  class PowerUp {
    constructor(x, y, kind) {
      this.x = x; this.y = y; this.kind = kind; this.r = 11;
      this.vy = 70; this.dead = false; this.t = 0;
      this.colors = { rapid: "#ffcc00", spread: "#ff2bd6", shield: "#21f3ff", life: "#39ff6a" };
    }
    update(dt) {
      this.y += this.vy * dt;
      this.t += dt;
      if (this.y > H + 20) this.dead = true;
    }
    draw() {
      const c = this.colors[this.kind];
      ctx.save();
      ctx.translate(this.x, this.y + Math.sin(this.t * 4) * 4);
      ctx.rotate(this.t * 2);
      ctx.shadowColor = c; ctx.shadowBlur = 12;
      ctx.strokeStyle = c; ctx.lineWidth = 2;
      ctx.strokeRect(-9, -9, 18, 18);
      ctx.restore();
      ctx.save();
      ctx.fillStyle = c;
      ctx.font = "8px monospace";
      ctx.textAlign = "center";
      ctx.shadowColor = c; ctx.shadowBlur = 6;
      const label = { rapid: "R", spread: "S", shield: "P", life: "+" }[this.kind];
      ctx.fillText(label, this.x, this.y + Math.sin(this.t * 4) * 4 + 3);
      ctx.restore();
    }
  }

  class Player {
    constructor() {
      this.x = W / 2; this.y = H - 90;
      this.r = 14;
      this.speed = 260;
      this.cooldown = 0;
      this.fireRate = 0.24;
      this.lives = 3;
      this.invuln = 2;
      this.shield = 0;
      this.rapidT = 0;
      this.spreadT = 0;
      this.thrust = 0;
      this.dead = false;
    }
    update(dt, input) {
      let dx = 0;
      if (input.left) dx -= 1;
      if (input.right) dx += 1;
      this.x = clamp(this.x + dx * this.speed * dt, 20, W - 20);
      this.thrust = dx !== 0 || input.left || input.right ? 1 : 0.4;

      this.cooldown -= dt;
      this.invuln = Math.max(0, this.invuln - dt);
      this.shield = Math.max(0, this.shield - dt);
      this.rapidT = Math.max(0, this.rapidT - dt);
      this.spreadT = Math.max(0, this.spreadT - dt);
    }
    canFire() { return this.cooldown <= 0; }
    fire(bullets) {
      const rate = this.rapidT > 0 ? this.fireRate * 0.4 : this.fireRate;
      this.cooldown = rate;
      Sound.laser();
      const spread = this.spreadT > 0;
      const baseVy = -640;
      bullets.push(new Bullet(this.x, this.y - 20, 0, baseVy, 3.5, "#21f3ff", 1, true));
      if (spread) {
        bullets.push(new Bullet(this.x, this.y - 10, -160, baseVy, 3, "#21f3ff", 1, true));
        bullets.push(new Bullet(this.x, this.y - 10, 160, baseVy, 3, "#21f3ff", 1, true));
      }
    }
    hit() {
      if (this.invuln > 0 || this.shield > 0) return false;
      this.lives--;
      this.invuln = 2;
      Sound.playerHit();
      return true;
    }
    draw() {
      const flicker = this.invuln > 0 && Math.floor(this.invuln * 12) % 2 === 0;
      if (flicker) return;
      ctx.save();
      ctx.translate(this.x, this.y);

      // thruster flame
      const flameLen = 10 + this.thrust * 14 + Math.random() * 6;
      const flameGrad = ctx.createLinearGradient(0, 14, 0, 14 + flameLen);
      flameGrad.addColorStop(0, "#fff700");
      flameGrad.addColorStop(0.5, "#ff8a1e");
      flameGrad.addColorStop(1, "rgba(255,43,0,0)");
      ctx.fillStyle = flameGrad;
      ctx.beginPath();
      ctx.moveTo(-6, 12);
      ctx.lineTo(6, 12);
      ctx.lineTo(0, 12 + flameLen);
      ctx.closePath();
      ctx.fill();

      // hull
      ctx.shadowColor = "#21f3ff";
      ctx.shadowBlur = 14;
      ctx.fillStyle = "#0af0ff";
      ctx.beginPath();
      ctx.moveTo(0, -18);
      ctx.lineTo(14, 14);
      ctx.lineTo(6, 8);
      ctx.lineTo(0, 12);
      ctx.lineTo(-6, 8);
      ctx.lineTo(-14, 14);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "#ff2bd6";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.fillStyle = "#fff733";
      ctx.beginPath();
      ctx.ellipse(0, -2, 3, 5, 0, 0, Math.PI * 2);
      ctx.fill();

      if (this.shield > 0) {
        ctx.beginPath();
        ctx.strokeStyle = "rgba(33,243,255,0.8)";
        ctx.lineWidth = 2;
        ctx.shadowColor = "#21f3ff";
        ctx.shadowBlur = 16;
        ctx.arc(0, -2, 26, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.restore();
    }
  }

  const ENEMY_TYPES = {
    drone: { hp: 1, r: 13, speed: 60, score: 10, color: "#39ff6a", shootChance: 0.002 },
    striker: { hp: 2, r: 15, speed: 90, score: 25, color: "#ff2bd6", shootChance: 0.01 },
    brute: { hp: 4, r: 20, speed: 45, score: 50, color: "#ff8a1e", shootChance: 0.015 },
  };

  class Enemy {
    constructor(kind, x, level) {
      const def = ENEMY_TYPES[kind];
      this.kind = kind;
      this.x = x; this.y = -30;
      this.r = def.r;
      this.hp = def.hp + Math.floor(level / 4);
      this.maxHp = this.hp;
      this.speed = def.speed + level * 4;
      this.score = def.score;
      this.color = def.color;
      this.shootChance = def.shootChance + level * 0.0008;
      this.t = rand(0, Math.PI * 2);
      this.baseX = x;
      this.dead = false;
      this.dropChance = 0.12;
    }
    update(dt, bullets, playerX) {
      this.t += dt;
      this.y += this.speed * dt;
      if (this.kind === "striker") this.x = this.baseX + Math.sin(this.t * 2) * 70;
      if (this.kind === "drone") this.x = this.baseX + Math.sin(this.t * 1.2) * 20;
      if (this.y > 20 && this.y < H - 60 && Math.random() < this.shootChance) {
        const ang = Math.atan2(H - 90 - this.y, playerX - this.x);
        bullets.push(new Bullet(this.x, this.y + this.r, Math.cos(ang) * 220, Math.sin(ang) * 220, 3.5, "#ff5555", 1, false));
        Sound.enemyLaser();
      }
      if (this.y > H + 40) this.dead = true;
    }
    hit(dmg) {
      this.hp -= dmg;
      Sound.hit();
      return this.hp <= 0;
    }
    draw() {
      ctx.save();
      ctx.translate(this.x, this.y);
      ctx.shadowColor = this.color;
      ctx.shadowBlur = 12;
      ctx.fillStyle = this.color;
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1;

      if (this.kind === "drone") {
        ctx.beginPath();
        ctx.moveTo(0, this.r);
        ctx.lineTo(this.r, -this.r * 0.6);
        ctx.lineTo(0, -this.r * 0.2);
        ctx.lineTo(-this.r, -this.r * 0.6);
        ctx.closePath();
        ctx.fill();
      } else if (this.kind === "striker") {
        ctx.beginPath();
        ctx.moveTo(0, this.r * 1.1);
        ctx.lineTo(this.r, 0);
        ctx.lineTo(this.r * 0.5, -this.r);
        ctx.lineTo(-this.r * 0.5, -this.r);
        ctx.lineTo(-this.r, 0);
        ctx.closePath();
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.arc(0, 0, this.r, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.moveTo(-this.r, 0); ctx.lineTo(this.r, 0);
        ctx.stroke();
      }
      ctx.restore();

      if (this.maxHp > 1) {
        const w = this.r * 2;
        ctx.fillStyle = "rgba(0,0,0,0.5)";
        ctx.fillRect(this.x - w / 2, this.y - this.r - 10, w, 3);
        ctx.fillStyle = this.color;
        ctx.fillRect(this.x - w / 2, this.y - this.r - 10, w * (this.hp / this.maxHp), 3);
      }
    }
  }

  class Boss {
    constructor(level) {
      this.x = W / 2; this.y = -80;
      this.targetY = 110;
      this.r = 46;
      this.maxHp = 60 + level * 18;
      this.hp = this.maxHp;
      this.speed = 110;
      this.dir = 1;
      this.t = 0;
      this.phase = 0;
      this.dead = false;
      this.entering = true;
      this.score = 500 + level * 50;
    }
    update(dt, bullets, playerX) {
      this.t += dt;
      if (this.entering) {
        this.y += 60 * dt;
        if (this.y >= this.targetY) { this.entering = false; this.y = this.targetY; }
        return;
      }
      this.x += this.dir * this.speed * dt;
      if (this.x < 60) this.dir = 1;
      if (this.x > W - 60) this.dir = -1;

      if (Math.floor(this.t * 10) % 14 === 0) {
        for (let i = -2; i <= 2; i++) {
          const ang = Math.PI / 2 + i * 0.22;
          bullets.push(new Bullet(this.x, this.y + this.r, Math.cos(ang) * 200, Math.sin(ang) * 200, 4, "#ff3b3b", 1, false));
        }
        Sound.enemyLaser();
      }
      if (Math.floor(this.t * 10) % 25 === 0) {
        const ang = Math.atan2(H - 90 - this.y, playerX - this.x);
        bullets.push(new Bullet(this.x, this.y, Math.cos(ang) * 260, Math.sin(ang) * 260, 5, "#ff8a1e", 1, false));
      }
    }
    hit(dmg) {
      this.hp -= dmg;
      Sound.hit();
      return this.hp <= 0;
    }
    draw() {
      ctx.save();
      ctx.translate(this.x, this.y);
      const pulse = Math.sin(this.t * 6) * 3;
      ctx.shadowColor = "#ff3b3b";
      ctx.shadowBlur = 20;
      ctx.fillStyle = "#320018";
      ctx.strokeStyle = "#ff3b3b";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(-60, -10);
      ctx.lineTo(-30, -40 - pulse);
      ctx.lineTo(0, -20);
      ctx.lineTo(30, -40 - pulse);
      ctx.lineTo(60, -10);
      ctx.lineTo(40, 30);
      ctx.lineTo(-40, 30);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#ff2bd6";
      ctx.shadowColor = "#ff2bd6";
      ctx.beginPath();
      ctx.arc(-20, 0, 8, 0, Math.PI * 2);
      ctx.arc(20, 0, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }

  // ===========================================================
  // GAME STATE
  // ===========================================================
  const State = { START: 0, PLAYING: 1, PAUSED: 2, GAMEOVER: 3 };

  const game = {
    state: State.START,
    player: null,
    bullets: [],
    enemies: [],
    powerups: [],
    boss: null,
    particles: new Particles(),
    stars: new Starfield(),
    score: 0,
    hiscore: loadHi(),
    level: 1,
    killsThisWave: 0,
    killsNeeded: 8,
    spawnTimer: 0,
    spawnInterval: 1.1,
    last: 0,
    shakeT: 0,
    shakeMag: 0,
  };

  const input = { left: false, right: false, fire: false };

  function resetGame() {
    game.player = new Player();
    game.bullets = [];
    game.enemies = [];
    game.powerups = [];
    game.boss = null;
    game.particles = new Particles();
    game.score = 0;
    game.level = 1;
    game.killsThisWave = 0;
    game.killsNeeded = 8;
    game.spawnTimer = 0;
    game.spawnInterval = 1.1;
    updateHud();
  }

  function updateHud() {
    scoreEl.textContent = game.score;
    levelEl.textContent = game.level;
    hiscoreEl.textContent = game.hiscore;
    livesRow.innerHTML = "";
    for (let i = 0; i < game.player.lives; i++) {
      const d = document.createElement("div");
      d.className = "life-icon";
      livesRow.appendChild(d);
    }
  }

  function screenShake(mag, t) {
    game.shakeMag = mag;
    game.shakeT = t;
  }

  function spawnEnemy() {
    const level = game.level;
    const roll = Math.random();
    let kind = "drone";
    if (level >= 2 && roll > 0.7) kind = "striker";
    if (level >= 4 && roll > 0.92) kind = "brute";
    const x = rand(40, W - 40);
    game.enemies.push(new Enemy(kind, x, level));
  }

  function spawnBoss() {
    game.boss = new Boss(game.level);
    bossbar.classList.remove("hidden");
    Sound.bossAlert();
  }

  function triggerLevelUp() {
    game.level++;
    game.killsThisWave = 0;
    game.killsNeeded = 8 + game.level * 2;
    game.spawnInterval = Math.max(0.35, 1.1 - game.level * 0.05);
    levelUpNum.textContent = game.level;
    levelUpBanner.classList.remove("hidden");
    Sound.levelUp();
    setTimeout(() => levelUpBanner.classList.add("hidden"), 1600);
    updateHud();
    if (game.level % 5 === 0) spawnBoss();
  }

  function dropPowerup(x, y) {
    const kinds = ["rapid", "spread", "shield", "life"];
    const weights = [0.35, 0.3, 0.25, 0.1];
    let r = Math.random(), acc = 0, kind = kinds[0];
    for (let i = 0; i < kinds.length; i++) {
      acc += weights[i];
      if (r <= acc) { kind = kinds[i]; break; }
    }
    game.powerups.push(new PowerUp(x, y, kind));
  }

  function applyPowerup(kind) {
    const p = game.player;
    Sound.powerup();
    if (kind === "rapid") p.rapidT = 8;
    if (kind === "spread") p.spreadT = 8;
    if (kind === "shield") { p.shield = 5; Sound.shieldUp(); }
    if (kind === "life") p.lives = Math.min(p.lives + 1, 6);
    updateHud();
  }

  function endGame() {
    game.state = State.GAMEOVER;
    Sound.stopMusic();
    Sound.gameOver();
    bossbar.classList.add("hidden");
    finalScoreEl.textContent = `SCORE ${game.score}`;
    if (game.score > game.hiscore) {
      game.hiscore = game.score;
      saveHi(game.hiscore);
      newHighEl.classList.remove("hidden");
    } else {
      newHighEl.classList.add("hidden");
    }
    gameOverScreen.classList.remove("hidden");
  }

  // ===========================================================
  // MAIN UPDATE
  // ===========================================================
  function update(dt) {
    game.stars.update(dt);
    game.particles.update(dt);

    if (game.state !== State.PLAYING) return;

    const p = game.player;
    p.update(dt, input);
    if (input.fire && p.canFire()) p.fire(game.bullets);

    // spawning
    if (!game.boss) {
      game.spawnTimer -= dt;
      if (game.spawnTimer <= 0) {
        spawnEnemy();
        game.spawnTimer = game.spawnInterval;
      }
    }

    // bullets
    for (const b of game.bullets) b.update(dt);
    game.bullets = game.bullets.filter(b => !b.dead);

    // enemies
    for (const e of game.enemies) e.update(dt, game.bullets, p.x);
    game.enemies = game.enemies.filter(e => !e.dead);

    // boss
    if (game.boss) {
      game.boss.update(dt, game.bullets, p.x);
      bossbarFill.style.width = `${clamp((game.boss.hp / game.boss.maxHp) * 100, 0, 100)}%`;
    }

    // powerups
    for (const pu of game.powerups) pu.update(dt);
    game.powerups = game.powerups.filter(pu => !pu.dead);

    // collisions: player bullets vs enemies
    for (const b of game.bullets) {
      if (!b.fromPlayer || b.dead) continue;
      for (const e of game.enemies) {
        if (e.dead) continue;
        if (overlap(b, e)) {
          b.dead = true;
          if (e.hit(b.dmg)) {
            e.dead = true;
            game.particles.burst(e.x, e.y, e.color, 18, 160, 0.55);
            Sound.explosion(false);
            game.score += e.score;
            game.killsThisWave++;
            if (Math.random() < e.dropChance) dropPowerup(e.x, e.y);
            updateHud();
          }
          break;
        }
      }
      if (b.dead) continue;
      if (game.boss && overlap(b, game.boss)) {
        b.dead = true;
        game.particles.burst(b.x, b.y, "#ff8a1e", 6, 90, 0.3);
        if (game.boss.hit(b.dmg)) {
          game.particles.burst(game.boss.x, game.boss.y, "#ff3b3b", 60, 260, 1.1);
          Sound.explosion(true);
          screenShake(10, 0.4);
          game.score += game.boss.score;
          bossbar.classList.add("hidden");
          game.boss = null;
          updateHud();
          triggerLevelUp();
        }
      }
    }

    // collisions: enemy bullets vs player
    for (const b of game.bullets) {
      if (b.fromPlayer || b.dead) continue;
      if (overlap(b, p)) {
        b.dead = true;
        if (p.hit()) {
          game.particles.burst(p.x, p.y, "#21f3ff", 20, 180, 0.6);
          screenShake(8, 0.3);
          updateHud();
          if (p.lives <= 0) { p.dead = true; endGame(); return; }
        }
      }
    }

    // collisions: enemies vs player (ram damage)
    for (const e of game.enemies) {
      if (e.dead) continue;
      if (overlap(e, p)) {
        e.dead = true;
        game.particles.burst(e.x, e.y, e.color, 16, 150, 0.5);
        Sound.explosion(false);
        if (p.hit()) {
          screenShake(8, 0.3);
          updateHud();
          if (p.lives <= 0) { p.dead = true; endGame(); return; }
        }
      }
    }

    // collisions: powerups vs player
    for (const pu of game.powerups) {
      if (pu.dead) continue;
      if (overlap(pu, p)) {
        pu.dead = true;
        applyPowerup(pu.kind);
      }
    }

    // wave clear -> level up (only when no boss active)
    if (!game.boss && game.killsThisWave >= game.killsNeeded) {
      triggerLevelUp();
    }

    // screen shake decay
    if (game.shakeT > 0) game.shakeT -= dt;
  }

  // ===========================================================
  // MAIN DRAW
  // ===========================================================
  function draw() {
    ctx.clearRect(0, 0, W, H);

    ctx.save();
    if (game.shakeT > 0) {
      const m = game.shakeMag * (game.shakeT / 0.4);
      ctx.translate(rand(-m, m), rand(-m, m));
    }

    game.stars.draw();

    if (game.state === State.PLAYING || game.state === State.PAUSED) {
      for (const pu of game.powerups) pu.draw();
      for (const e of game.enemies) e.draw();
      if (game.boss) game.boss.draw();
      for (const b of game.bullets) b.draw();
      if (game.player && !game.player.dead) game.player.draw();
    }

    game.particles.draw();
    ctx.restore();
  }

  // ===========================================================
  // LOOP
  // ===========================================================
  function loop(ts) {
    const dt = Math.min(0.05, (ts - game.last) / 1000 || 0);
    game.last = ts;
    update(dt);
    draw();
    requestAnimationFrame(loop);
  }

  // ===========================================================
  // INPUT
  // ===========================================================
  window.addEventListener("keydown", (e) => {
    if (["ArrowLeft", "a", "A"].includes(e.key)) input.left = true;
    if (["ArrowRight", "d", "D"].includes(e.key)) input.right = true;
    if (e.key === " ") { input.fire = true; e.preventDefault(); }
    if ((e.key === "p" || e.key === "P") && game.state !== State.START && game.state !== State.GAMEOVER) togglePause();
    if (e.key === "Enter" && game.state === State.START) startGame();
  });
  window.addEventListener("keyup", (e) => {
    if (["ArrowLeft", "a", "A"].includes(e.key)) input.left = false;
    if (["ArrowRight", "d", "D"].includes(e.key)) input.right = false;
    if (e.key === " ") input.fire = false;
  });

  function bindTouchZone(el, onStart, onEnd) {
    el.addEventListener("touchstart", (e) => { e.preventDefault(); onStart(); }, { passive: false });
    el.addEventListener("touchend", (e) => { e.preventDefault(); onEnd(); }, { passive: false });
    el.addEventListener("mousedown", onStart);
    el.addEventListener("mouseup", onEnd);
    el.addEventListener("mouseleave", onEnd);
  }
  bindTouchZone(touchLeft, () => { input.left = true; input.fire = true; }, () => { input.left = false; input.fire = false; });
  bindTouchZone(touchRight, () => { input.right = true; input.fire = true; }, () => { input.right = false; input.fire = false; });

  // drag-to-move across whole screen for smoother mobile control
  let dragging = false;
  canvas.addEventListener("touchstart", () => { dragging = true; }, { passive: true });
  canvas.addEventListener("touchend", () => { dragging = false; }, { passive: true });
  canvas.addEventListener("touchmove", (e) => {
    if (!dragging || !game.player) return;
    const rect = canvas.getBoundingClientRect();
    const t = e.touches[0];
    const relX = (t.clientX - rect.left) / rect.width * W;
    game.player.x = clamp(relX, 20, W - 20);
  }, { passive: true });

  // ===========================================================
  // FLOW CONTROL
  // ===========================================================
  function togglePause() {
    if (game.state === State.PLAYING) {
      game.state = State.PAUSED;
      pauseScreen.classList.remove("hidden");
      Sound.stopMusic();
    } else if (game.state === State.PAUSED) {
      game.state = State.PLAYING;
      pauseScreen.classList.add("hidden");
      Sound.startMusic();
    }
  }

  function startGame() {
    Sound.unlock();
    resetGame();
    game.state = State.PLAYING;
    startScreen.classList.add("hidden");
    gameOverScreen.classList.add("hidden");
    Sound.startMusic();
  }

  startBtn.addEventListener("click", startGame);
  restartBtn.addEventListener("click", startGame);
  muteBtn.addEventListener("click", () => {
    const m = !Sound.isMuted();
    Sound.setMuted(m);
    muteBtn.textContent = `SOUND: ${m ? "OFF" : "ON"}`;
    if (m) Sound.stopMusic();
  });

  hiscoreEl.textContent = game.hiscore;

  requestAnimationFrame(loop);
})();
