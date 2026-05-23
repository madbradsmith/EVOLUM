// gw-extensions.js — Final compilation extensions for the Game World.
// Adds: session timer, stats overlay, photo mode, speech bubbles, intro cinematic,
// session skins, time of day, crowd pack, greenroom, minimap upgrades, relationships, props.
//
// Loaded AFTER the core runtime. All systems hook into window.SIMUTUM_RUNTIME.

(function () {
  'use strict';

  // ─── Default constants (set on window before this loads to override) ──
  window.RELATIONSHIPS = window.RELATIONSHIPS || [];   // [{a, b, type: 'rivalry'|'mentor'|'drift'}]
  window.PROPS         = window.PROPS         || [];   // [{section, type}]
  window.CROWD_SIZE    = window.CROWD_SIZE    || 0;    // 0-20 background ghosts
  window.SESSION_SKIN  = window.SESSION_SKIN  || 'default';
  window.TIME_OF_DAY   = window.TIME_OF_DAY   || 'night';
  window.GREENROOM     = window.GREENROOM     || false;

  // Wait for runtime
  function whenReady(fn) {
    const tick = () => {
      const R = window.SIMUTUM_RUNTIME;
      if (R && R.scene && R.getAgents) fn(R); else setTimeout(tick, 200);
    };
    tick();
  }

  whenReady(initAll);

  function initAll(R) {
    initSessionTimer();
    initStatsOverlay(R);
    initPhotoMode(R);
    initSpeechBubbles(R);
    initIntroCinematic(R);
    initTimeOfDay(R);
    initSessionSkin(R);
    initCrowd(R);
    initRelationships(R);
    initProps(R);
    initMinimapUpgrades(R);
    initGreenroom(R);
  }

  // ─── 1.1 Session Timer HUD ────────────────────────────────
  function initSessionTimer() {
    const banner = document.querySelector('.banner');
    if (!banner) return;
    const el = document.createElement('div');
    el.style.cssText = 'font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#46d9c5;letter-spacing:.06em;margin:0 12px;padding:4px 9px;border:1px solid rgba(70,217,197,0.3);border-radius:3px';
    el.textContent = '· 00:00:00 ·';
    el.id = 'sessionTimer';
    const meta = banner.querySelector('.banner__meta');
    if (meta) banner.insertBefore(el, meta); else banner.appendChild(el);

    let started = false;
    let startT = 0;
    function tick() {
      if (started) {
        const s = Math.floor((Date.now() - startT) / 1000);
        const hh = String(Math.floor(s / 3600)).padStart(2, '0');
        const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
        const ss = String(s % 60).padStart(2, '0');
        el.textContent = '· ' + hh + ':' + mm + ':' + ss + ' ·';
      }
      requestAnimationFrame(tick);
    }
    tick();

    // Start on audio unlock (already gated by the overlay)
    const startWhenAudio = () => {
      if (started) return;
      started = true; startT = Date.now();
    };
    document.getElementById('audioStart') && document.getElementById('audioStart').addEventListener('click', startWhenAudio);
    document.addEventListener('click', startWhenAudio, { once: true });
    window.SIMUTUM_SESSION_START = () => startT || Date.now();
  }

  // ─── 1.2 Stats Overlay ────────────────────────────────────
  function initStatsOverlay(R) {
    const btn = document.createElement('button');
    btn.textContent = 'STATS';
    btn.className = 'rec-btn';
    btn.style.cssText = 'position:fixed;top:60px;left:84px;z-index:50;background:rgba(14,16,24,0.78);backdrop-filter:blur(8px);border:1px solid rgba(184,196,224,0.22);color:#b9c4e0;padding:6px 12px;font-family:ui-monospace,Menlo,monospace;font-size:10.5px;letter-spacing:.10em;text-transform:uppercase;border-radius:4px;cursor:pointer';
    document.body.appendChild(btn);

    const panel = document.createElement('div');
    panel.style.cssText = 'position:fixed;top:104px;left:16px;z-index:50;width:240px;padding:14px 16px;background:rgba(14,16,24,0.88);backdrop-filter:blur(10px);border:1px solid rgba(184,196,224,0.22);border-radius:6px;font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#d8dde9;display:none';
    panel.innerHTML = '<div style="font-size:9.5px;letter-spacing:.10em;text-transform:uppercase;color:rgba(184,196,224,0.55);margin-bottom:10px">Session Stats</div><div id="statsBody"></div>';
    document.body.appendChild(panel);

    let open = false;
    btn.addEventListener('click', () => {
      open = !open;
      panel.style.display = open ? 'block' : 'none';
      btn.style.color = open ? '#46d9c5' : '#b9c4e0';
      btn.style.borderColor = open ? '#46d9c5' : 'rgba(184,196,224,0.22)';
    });

    let convCount = 0, boundaryVisits = 0;
    // hook into onPointerObservable for boundary detection
    R.scene.onBeforeRenderObservable.add(() => {
      // conversation count tracked via speech track if available
      if (window.SIMUTUM_RUNTIME && window.SIMUTUM_RUNTIME.scene._convCount != null) {
        convCount = window.SIMUTUM_RUNTIME.scene._convCount;
      }
    });

    // Refresh every 5 seconds
    setInterval(() => {
      if (!open) return;
      const agents = R.getAgents();
      let atSquare = 0, atStops = 0;
      const stops = R.getStops() || [];
      for (const a of agents) {
        const p = a.avatar.root.position;
        if (Math.hypot(p.x, p.z) < 120) atSquare++;
        for (const s of stops) {
          if (Math.hypot(p.x - s.position.x, p.z - s.position.z) < 60) { atStops++; break; }
        }
      }
      const ts = document.getElementById('sessionTimer');
      const timer = ts ? ts.textContent : '00:00:00';
      document.getElementById('statsBody').innerHTML =
        statRow('At square',  Math.round(atSquare/agents.length*100) + '%') +
        statRow('At stops',   Math.round(atStops/agents.length*100) + '%') +
        statRow('Conversations', convCount) +
        statRow('Boundary visits', boundaryVisits) +
        statRow('Session', timer.replace(/[· ]/g,''));
    }, 1000);

    function statRow(k, v) {
      return '<div style="display:flex;justify-content:space-between;padding:3px 0"><span style="color:rgba(184,196,224,0.55)">' + k + '</span><span style="color:#46d9c5;font-variant-numeric:tabular-nums">' + v + '</span></div>';
    }
  }

  // ─── 1.3 Photo Mode ──────────────────────────────────────
  function initPhotoMode(R) {
    const btn = document.createElement('button');
    btn.textContent = 'PHOTO';
    btn.style.cssText = 'position:fixed;top:60px;left:166px;z-index:50;background:rgba(14,16,24,0.78);backdrop-filter:blur(8px);border:1px solid rgba(184,196,224,0.22);color:#b9c4e0;padding:6px 12px;font-family:ui-monospace,Menlo,monospace;font-size:10.5px;letter-spacing:.10em;text-transform:uppercase;border-radius:4px;cursor:pointer';
    document.body.appendChild(btn);

    let active = false;
    const HIDDEN_SELECTORS = ['.banner', '.controls', '#mapCanvas', '.mapLabel', '#worldControls', '#recBtn', '.rec-btn', '.demoChip'];

    btn.addEventListener('click', () => {
      active = !active;
      // freeze entities
      for (const a of R.getAgents()) a._photoFrozen = active;
      // hide HUD
      for (const sel of HIDDEN_SELECTORS) {
        document.querySelectorAll(sel).forEach(el => {
          if (el === btn || el.contains(btn)) return;
          el.dataset._oldDisplay = el.style.display;
          el.style.display = active ? 'none' : (el.dataset._oldDisplay || '');
        });
      }
      btn.textContent = active ? 'CAPTURE' : 'PHOTO';
      btn.style.color = active ? '#46d9c5' : '#b9c4e0';
      btn.style.borderColor = active ? '#46d9c5' : 'rgba(184,196,224,0.22)';
      btn.style.display = ''; // keep visible

      // attach pause to agent updates
      if (active) {
        if (!R._origAgentUpdate) {
          for (const a of R.getAgents()) {
            a._origUpdate = a.update;
            a.update = function () { if (!a._photoFrozen) a._origUpdate.apply(a, arguments); };
          }
          R._origAgentUpdate = true;
        }
        // Now if button is clicked again while active, it captures
        btn.onclick = () => { capture(); };
      } else {
        btn.onclick = null;
        btn.addEventListener('click', arguments.callee);
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && active) btn.click();
    });

    function capture() {
      // grab canvas image
      const canvas = document.getElementById('renderCanvas');
      if (!canvas) return;
      R.engine.beginFrame();
      R.scene.render();
      R.engine.endFrame();
      requestAnimationFrame(() => {
        const url = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = url; a.download = 'simutum-' + Date.now() + '.png';
        document.body.appendChild(a); a.click(); a.remove();
        btn.click(); // exit photo mode
      });
    }
  }

  // ─── 1.4 Speech Bubbles ──────────────────────────────────
  function initSpeechBubbles(R) {
    // we hook the speech synth via wrapping
    if (!window.speechSynthesis) return;
    const origSpeak = window.speechSynthesis.speak.bind(window.speechSynthesis);
    R.scene._convCount = 0;
    window.speechSynthesis.speak = function (utterance) {
      origSpeak(utterance);
      // find which agent is speaking based on utterance pitch+rate? hard.
      // simpler: any non-empty utterance with volume > 0.5 = conversation
      if (utterance.volume > 0.5) {
        R.scene._convCount++;
        // find closest agent — show bubble above them
        const cam = R.scene.activeCamera;
        const agents = R.getAgents();
        let best = null, bd = 1e9;
        for (const a of agents) {
          const p = a.avatar.root.position;
          const d = Math.hypot(p.x - cam.position.x, p.z - cam.position.z);
          if (d < bd) { bd = d; best = a; }
        }
        if (best) showBubble(R, best, utterance.text);
      }
    };
  }

  function showBubble(R, agent, text) {
    const words = text.split(/\s+/).slice(0, 6).join(' ') + (text.split(/\s+/).length > 6 ? '…' : '');
    const tex = new BABYLON.DynamicTexture('bubbleTex_' + Math.random(), { width: 512, height: 128 }, R.scene, true);
    tex.hasAlpha = true;
    const ctx = tex.getContext();
    ctx.clearRect(0, 0, 512, 128);
    ctx.fillStyle = 'rgba(14,16,24,0.92)';
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(20, 30, 472, 68, 8); else ctx.rect(20, 30, 472, 68);
    ctx.fill();
    ctx.strokeStyle = 'rgba(70,217,197,0.6)';
    ctx.lineWidth = 1.5; ctx.stroke();
    ctx.fillStyle = '#d8dde9';
    ctx.font = '600 22px ui-monospace, Menlo, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(words, 256, 72);
    tex.update();

    const mat = new BABYLON.StandardMaterial('bubbleMat_' + Math.random(), R.scene);
    mat.diffuseTexture = tex;
    mat.emissiveTexture = tex;
    mat.opacityTexture = tex;
    mat.disableLighting = true;
    mat.specularColor = new BABYLON.Color3(0, 0, 0);

    const plane = BABYLON.MeshBuilder.CreatePlane('bubble_' + Math.random(), { width: 100, height: 25 }, R.scene);
    plane.position.set(agent.avatar.root.position.x, 60, agent.avatar.root.position.z);
    plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
    plane.material = mat;
    plane.parent = agent.avatar.root;
    plane.position.y = 40;

    // fade out over 3s
    let alpha = 1;
    const fadeStart = performance.now();
    const fade = () => {
      const t = (performance.now() - fadeStart) / 3000;
      mat.alpha = 1 - t;
      if (t >= 1) { plane.dispose(); mat.dispose(); tex.dispose(); }
      else requestAnimationFrame(fade);
    };
    fade();
  }

  // ─── 1.5 Intro Cinematic ─────────────────────────────────
  function initIntroCinematic(R) {
    const overlay = document.getElementById('audioOverlay');
    if (!overlay) return;
    const startBtn = document.getElementById('audioStart');
    if (!startBtn) return;
    let cinematicRun = false;
    const origClick = startBtn.onclick;
    startBtn.addEventListener('click', () => {
      if (cinematicRun) return;
      cinematicRun = true;
      runCinematic();
    });

    function runCinematic() {
      const cam = R.scene.activeCamera;
      if (!cam || cam.name !== 'topCam') return;
      const fromY = 30, toY = cam.position.y || 600;
      const startTime = performance.now();
      const dur = 4000;
      cam.position.y = fromY;
      const obs = R.scene.onBeforeRenderObservable.add(() => {
        const t = Math.min(1, (performance.now() - startTime) / dur);
        const e = t * t * (3 - 2 * t); // smoothstep
        cam.position.y = fromY + (toY - fromY) * e;
        cam.setTarget(new BABYLON.Vector3(cam.position.x, 0, cam.position.z));
        if (t >= 1) R.scene.onBeforeRenderObservable.remove(obs);
      });
    }
  }

  // ─── 1.9 Session Skin ────────────────────────────────────
  function initSessionSkin(R) {
    apply(window.SESSION_SKIN);
    // expose for runtime swap
    window.applySessionSkin = apply;

    function apply(skin) {
      // remove previous overlay
      const old = document.getElementById('sessionSkinOverlay');
      if (old) old.remove();
      // reset scene effects
      R.scene.imageProcessingConfiguration && (R.scene.imageProcessingConfiguration.colorGradingEnabled = false);

      if (skin === 'hollywood') {
        addOverlay('sepia');
        // film grain noise overlay handled in CSS
      } else if (skin === 'noir') {
        addOverlay('grayscale');
        // spotlight follow added below
      } else if (skin === 'cyberpunk') {
        addOverlay('cyber');
        // force rain
        const ctl = document.getElementById('ctlAtmosphere');
        if (ctl && ctl.value !== 'rain') { ctl.value = 'rain'; ctl.dispatchEvent(new Event('change')); }
      } else if (skin === 'sunrise') {
        // gradual brightening on a 60min clock
        startSunrise();
      }
    }
    function addOverlay(kind) {
      const ov = document.createElement('div');
      ov.id = 'sessionSkinOverlay';
      ov.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:35;mix-blend-mode:overlay;background:transparent';
      if (kind === 'sepia') {
        ov.style.background = 'linear-gradient(rgba(180,130,60,0.10), rgba(80,60,30,0.20))';
        ov.style.mixBlendMode = 'multiply';
        // grain
        ov.style.backgroundImage = 'radial-gradient(circle at 30% 40%, rgba(255,220,180,0.08) 0%, transparent 40%), radial-gradient(circle at 70% 60%, rgba(255,180,120,0.06) 0%, transparent 40%)';
      } else if (kind === 'grayscale') {
        ov.style.background = 'rgba(0,0,0,0.18)';
        ov.style.backdropFilter = 'grayscale(0.85) contrast(1.18)';
        ov.style.webkitBackdropFilter = ov.style.backdropFilter;
      } else if (kind === 'cyber') {
        ov.style.background = 'linear-gradient(rgba(50,30,80,0.18), rgba(255,40,180,0.06))';
        ov.style.backdropFilter = 'saturate(1.6) contrast(1.1)';
        ov.style.webkitBackdropFilter = ov.style.backdropFilter;
      }
      document.body.appendChild(ov);
    }
    function startSunrise() {
      const startT = performance.now();
      const ov = document.createElement('div');
      ov.id = 'sessionSkinOverlay';
      ov.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:35;background:transparent;transition:background 4s ease';
      document.body.appendChild(ov);
      setInterval(() => {
        const t = (performance.now() - startT) / (60 * 60 * 1000); // 0..1 over 60 min
        const k = Math.min(1, t);
        ov.style.background = `linear-gradient(rgba(255,210,160,${k * 0.18}), rgba(255,160,80,${k * 0.10}))`;
      }, 5000);
    }
  }

  // ─── 1.10 Time of Day ────────────────────────────────────
  function initTimeOfDay(R) {
    const tod = window.TIME_OF_DAY;
    const hemi = R.scene.lights.find(l => l.name === 'hemi');
    const moon = R.scene.lights.find(l => l.name === 'moon');
    if (!hemi) return;
    const C = BABYLON.Color3.FromHexString;
    if (tod === 'dawn') {
      hemi.intensity = 0.55;
      hemi.diffuse = C('#d8c6b6'); hemi.groundColor = C('#3a2e26');
      if (moon) moon.diffuse = C('#f5b86b');
    } else if (tod === 'day') {
      hemi.intensity = 0.80;
      hemi.diffuse = C('#e8edf8'); hemi.groundColor = C('#9ba6b8');
      if (moon) moon.diffuse = C('#ffffff');
    } else if (tod === 'dusk') {
      hemi.intensity = 0.50;
      hemi.diffuse = C('#c898a6'); hemi.groundColor = C('#4a2a3a');
      if (moon) moon.diffuse = C('#ff7d4a');
    }
    // 'night' is the default — leave it
  }

  // ─── 1.7 Props ──────────────────────────────────────────
  function initProps(R) {
    if (!window.PROPS.length) return;
    const W = window.SIMUTUM_WORLD;
    for (const p of window.PROPS) {
      const sec = W.SECTIONS && W.SECTIONS.find(s => s.id === p.section);
      if (!sec) continue;
      const offX = (Math.random() - 0.5) * sec.w * 0.6;
      const offZ = (Math.random() - 0.5) * sec.h * 0.6;
      const mesh = makeProp(R.scene, p.type);
      if (!mesh) continue;
      mesh.position.set(sec.x + offX, mesh.position.y, sec.y + offZ);
    }
    function makeProp(scene, type) {
      const mat = new BABYLON.StandardMaterial('propM_' + Math.random(), scene);
      mat.diffuseColor = BABYLON.Color3.FromHexString('#3a3050');
      mat.specularColor = new BABYLON.Color3(0, 0, 0);
      let mesh;
      if (type === 'desk') {
        mesh = BABYLON.MeshBuilder.CreateBox('prop_desk', { width: 80, height: 26, depth: 35 }, scene);
        mesh.position.y = 13;
      } else if (type === 'chair') {
        mesh = BABYLON.MeshBuilder.CreateBox('prop_chair', { width: 14, height: 18, depth: 14 }, scene);
        mesh.position.y = 9;
      } else if (type === 'whiteboard') {
        mesh = BABYLON.MeshBuilder.CreateBox('prop_wb', { width: 100, height: 60, depth: 4 }, scene);
        mesh.position.y = 30;
        mat.diffuseColor = BABYLON.Color3.FromHexString('#e8e8ec');
      } else if (type === 'camera') {
        mesh = BABYLON.MeshBuilder.CreateCylinder('prop_cam', { diameter: 14, height: 60 }, scene);
        mesh.position.y = 30;
      } else if (type === 'scripts') {
        mesh = BABYLON.MeshBuilder.CreateBox('prop_scripts', { width: 18, height: 8, depth: 22 }, scene);
        mesh.position.y = 4;
        mat.diffuseColor = BABYLON.Color3.FromHexString('#d4c08a');
      } else if (type === 'table') {
        mesh = BABYLON.MeshBuilder.CreateBox('prop_table', { width: 160, height: 26, depth: 40 }, scene);
        mesh.position.y = 13;
      }
      if (mesh) mesh.material = mat;
      return mesh;
    }
  }

  // ─── 1.8 Crowd Pack ─────────────────────────────────────
  function initCrowd(R) {
    if (!window.CROWD_SIZE || window.CROWD_SIZE <= 0) return;
    const n = Math.min(20, Math.max(0, window.CROWD_SIZE | 0));
    const ghosts = [];
    for (let i = 0; i < n; i++) {
      const root = new BABYLON.TransformNode('ghost_' + i, R.scene);
      const head = BABYLON.MeshBuilder.CreateSphere('ghHead_' + i, { diameter: 12 }, R.scene);
      const body = BABYLON.MeshBuilder.CreateCylinder('ghBody_' + i, { diameter: 9, height: 14 }, R.scene);
      body.position.y = 7;
      head.position.y = 18;
      head.parent = root; body.parent = root;
      const mat = new BABYLON.StandardMaterial('ghM_' + i, R.scene);
      mat.diffuseColor = new BABYLON.Color3(0.4, 0.5, 0.6);
      mat.alpha = 0.6;
      mat.specularColor = new BABYLON.Color3(0, 0, 0);
      head.material = mat; body.material = mat;
      // start somewhere randomly within boundary
      root.position.set((Math.random() - 0.5) * 2400, 0, (Math.random() - 0.5) * 2400);
      ghosts.push({ root, pos: root.position.clone(), target: null, dwell: 1 + Math.random() * 3 });
    }
    R.scene.onBeforeRenderObservable.add(() => {
      const dt = R.engine.getDeltaTime() / 1000;
      for (const g of ghosts) {
        if (!g.target) g.target = new BABYLON.Vector3((Math.random() - 0.5) * 2400, 0, (Math.random() - 0.5) * 2400);
        const dx = g.target.x - g.pos.x, dz = g.target.z - g.pos.z;
        const d = Math.hypot(dx, dz);
        if (d < 4) { g.target = null; g.dwell = 1 + Math.random() * 3; return; }
        g.pos.x += (dx / d) * 18 * dt;
        g.pos.z += (dz / d) * 18 * dt;
        g.root.position.copyFrom(g.pos);
        g.root.rotation.y = Math.atan2(dx, dz);
      }
    });
  }

  // ─── 1.6 Relationships ─────────────────────────────────
  function initRelationships(R) {
    if (!window.RELATIONSHIPS.length) return;
    const agents = R.getAgents();
    const byName = Object.fromEntries(agents.map(a => [a.name, a]));
    for (const rel of window.RELATIONSHIPS) {
      const A = byName[rel.a], B = byName[rel.b];
      if (!A || !B) continue;
      if (rel.type === 'rivalry') {
        // 40% of the time, B matches A's last destination
        const origPick = B.pickNext.bind(B);
        B.pickNext = function () {
          if (Math.random() < 0.4 && A.target) {
            this.target = new BABYLON.Vector3(A.target.x, 0, A.target.z);
            this.state = 'walking';
            this.lastDest = A.lastDest;
            return;
          }
          origPick();
        };
      } else if (rel.type === 'mentor') {
        // B drifts toward A's last position with 10s delay
        const buffer = []; // [{t, x, z}]
        R.scene.onBeforeRenderObservable.add(() => {
          buffer.push({ t: performance.now(), x: A.avatar.root.position.x, z: A.avatar.root.position.z });
          while (buffer.length && (performance.now() - buffer[0].t) > 11000) buffer.shift();
          const old = buffer[0];
          if (!old) return;
          // gentle drift
          if (B.state === 'walking' || B.state === 'dwelling') return;
          if (Math.random() < 0.005) {
            B.target = new BABYLON.Vector3(old.x, 0, old.z);
            B.state = 'walking';
          }
        });
      } else if (rel.type === 'drift') {
        // never same category simultaneously
        const origPick = B.pickNext.bind(B);
        B.pickNext = function () {
          let tries = 0;
          do { origPick(); tries++; }
          while (tries < 5 && A.lastCategory === this.lastCategory);
        };
      }
    }
  }

  // ─── 1.12 Minimap Upgrades ─────────────────────────────
  function initMinimapUpgrades(R) {
    const cv = document.getElementById('mapCanvas');
    if (!cv) return;
    // zoom buttons
    const zoomPlus = document.createElement('button');
    const zoomMinus = document.createElement('button');
    [zoomPlus, zoomMinus].forEach(b => {
      b.style.cssText = 'position:fixed;width:24px;height:24px;font-family:ui-monospace,Menlo,monospace;font-size:14px;background:rgba(14,16,24,0.92);border:1px solid rgba(184,196,224,0.22);color:#46d9c5;border-radius:3px;cursor:pointer;z-index:32';
    });
    zoomPlus.textContent = '+'; zoomMinus.textContent = '−';
    zoomPlus.style.right = '298px'; zoomPlus.style.bottom = '256px';
    zoomMinus.style.right = '298px'; zoomMinus.style.bottom = '226px';
    document.body.appendChild(zoomPlus);
    document.body.appendChild(zoomMinus);
    window.MAP_ZOOM = window.MAP_ZOOM || 1;
    zoomPlus.addEventListener('click', () => { window.MAP_ZOOM = Math.min(3, window.MAP_ZOOM * 1.25); });
    zoomMinus.addEventListener('click', () => { window.MAP_ZOOM = Math.max(0.5, window.MAP_ZOOM / 1.25); });

    // Hover tooltip for entities
    const tip = document.createElement('div');
    tip.style.cssText = 'position:fixed;display:none;background:rgba(14,16,24,0.95);border:1px solid #46d9c5;color:#46d9c5;font-family:ui-monospace,Menlo,monospace;font-size:11px;padding:3px 8px;border-radius:3px;pointer-events:none;z-index:33';
    document.body.appendChild(tip);
    cv.addEventListener('mousemove', (e) => {
      const r = cv.getBoundingClientRect();
      const sx = e.clientX - r.left, sy = e.clientY - r.top;
      const range = 3400 / window.MAP_ZOOM;
      const scale = Math.min(r.width, r.height) / range * (window.devicePixelRatio || 1);
      const worldX = (sx * (window.devicePixelRatio || 1) - r.width * (window.devicePixelRatio || 1) / 2) / scale;
      const worldZ = -(sy * (window.devicePixelRatio || 1) - r.height * (window.devicePixelRatio || 1) / 2) / scale;
      // find nearest agent
      const agents = R.getAgents();
      let best = null, bd = 80;
      for (const a of agents) {
        const ap = a.avatar.root.position;
        const d = Math.hypot(ap.x - worldX, ap.z - worldZ);
        if (d < bd) { bd = d; best = a; }
      }
      if (best) {
        tip.textContent = best.name;
        tip.style.color = best.color;
        tip.style.borderColor = best.color;
        tip.style.left = (e.clientX + 14) + 'px';
        tip.style.top = (e.clientY + 14) + 'px';
        tip.style.display = 'block';
      } else {
        tip.style.display = 'none';
      }
    });
    cv.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
  }

  // ─── 1.11 Greenroom ────────────────────────────────────
  function initGreenroom(R) {
    if (!window.GREENROOM) return;
    // overlay banner with countdown
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:120;padding:24px 32px;background:rgba(14,16,24,0.92);border:1px solid #46d9c5;border-radius:10px;font-family:ui-monospace,Menlo,monospace;text-align:center;color:#d8dde9';
    overlay.innerHTML = '<div style="font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#46d9c5;margin-bottom:10px">·· greenroom ··</div>' +
      '<div style="font-size:24px;font-weight:600;margin-bottom:6px">Cast assembling…</div>' +
      '<div style="font-size:13px;color:rgba(184,196,224,0.55);margin-bottom:14px">Doors open in <span id="grCount" style="color:#46d9c5;font-weight:700">30</span>s</div>';
    document.body.appendChild(overlay);
    // park entities in a corridor (off-screen south)
    const agents = R.getAgents();
    for (const a of agents) {
      a.avatar.root.position.set((Math.random() - 0.5) * 200, 0, -1700);
      a._photoFrozen = true;
    }
    let n = 30;
    const tick = setInterval(() => {
      n--;
      document.getElementById('grCount').textContent = n;
      if (n <= 0) {
        clearInterval(tick);
        overlay.remove();
        // unfreeze and let them path home
        for (const a of agents) a._photoFrozen = false;
      }
    }, 1000);
  }

})();
