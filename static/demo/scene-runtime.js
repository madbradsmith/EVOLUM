// scene-runtime.js — Boots Babylon, assembles the world, runs the loop.
// Also: 2D top-down overlay, JSON export, boundary collision → egg reveal.

(function () {
  'use strict';

  const W = window.SIMUTUM_WORLD;
  const B = window.SIMUTUM_BUILD;
  const S = window.SIMUTUM_STOPS;
  const E = window.SIMUTUM_ENTITIES;
  const A = window.SIMUTUM_AUDIO;

  // Global state — read by tweaks panel + runtime
  const STATE = window.SIMUTUM_STATE = {
    curveIntensity: 1.0,
    ringRadius: 900,
    lightingPalette: 'destination', // destination | warm | cool | mixed
    trafficCycleSec: 8,
    entitySpeed: 1.0,
    cameraMode: 'top', // top | fly | chase
    showOverlay: true,
    showLabels: true,
    showFog: true,
    sound: true,
    listeners: new Set(),
  };
  STATE.subscribe = (fn) => { STATE.listeners.add(fn); return () => STATE.listeners.delete(fn); };
  STATE.set = (key, val) => {
    if (STATE[key] === val) return;
    STATE[key] = val;
    STATE.listeners.forEach(fn => fn(key, val));
  };

  // ─── Boot ─────────────────────────────────────────────────────────
  const canvas = document.getElementById('renderCanvas');
  const engine = new BABYLON.Engine(canvas, true, { preserveDrawingBuffer: true, stencil: true, antialias: true });
  const scene = new BABYLON.Scene(engine);
  scene.clearColor = B.C4('#06070b');
  scene.fogMode = BABYLON.Scene.FOGMODE_LINEAR;
  scene.fogColor = B.C('#06070b');
  scene.fogStart = 600;
  scene.fogEnd = 2400;

  // Cameras
  // Top-down camera. Use explicit upVector to avoid the gimbal singularity
  // when looking straight down the -Y axis. Default Y=600 reads the whole
  // map + start of roads on spawn; user scrolls in toward the brief's Y=320.
  const topCam = new BABYLON.UniversalCamera('topCam', new BABYLON.Vector3(0, 600, 0), scene);
  topCam.upVector = new BABYLON.Vector3(0, 0, 1);  // +z (north) renders as screen-up
  topCam.setTarget(new BABYLON.Vector3(0, 0, 0));
  topCam.fov = 1.35;
  topCam.minZ = 0.5;
  topCam.maxZ = 6000;

  const flyCam = new BABYLON.UniversalCamera('flyCam', new BABYLON.Vector3(0, 80, -200), scene);
  flyCam.setTarget(new BABYLON.Vector3(0, 0, 0));
  flyCam.speed = 8;
  flyCam.angularSensibility = 2200;
  flyCam.keysUp    = [87, 38];
  flyCam.keysDown  = [83, 40];
  flyCam.keysLeft  = [65, 37];
  flyCam.keysRight = [68, 39];
  flyCam.minZ = 0.5;
  flyCam.maxZ = 6000;

  scene.activeCamera = topCam;

  // Lights
  const hemi = new BABYLON.HemisphericLight('hemi', new BABYLON.Vector3(0.2, 1, 0.1), scene);
  hemi.intensity = 0.45;
  hemi.diffuse = B.C('#b6c0d4');
  hemi.groundColor = B.C('#1e1c2e');

  const moon = new BABYLON.DirectionalLight('moon', new BABYLON.Vector3(-0.3, -1, -0.2), scene);
  moon.intensity = 0.30;
  moon.diffuse = B.C('#9bb0d0');

  // ─── Build world (initial — call build() to rebuild after tweaks) ──
  let WORLD_HANDLES = null;
  let ROAD_BY_ID = {};

  function build() {
    if (WORLD_HANDLES) {
      // dispose previous world meshes (everything except cameras + lights)
      const keep = new Set([topCam, flyCam, hemi, moon]);
      scene.meshes.slice().forEach(m => { if (!keep.has(m)) m.dispose(); });
      scene.transformNodes.slice().forEach(n => n.dispose());
      scene.lights.slice().forEach(l => { if (!keep.has(l)) l.dispose(); });
      scene.materials.slice().forEach(m => m.dispose());
      // re-add core lights since we wiped them
      hemi._scene = scene; moon._scene = scene;
    }
    const sections = B.buildSections(scene);
    const roads = W.buildRoads(STATE.curveIntensity);
    ROAD_BY_ID = {};
    roads.forEach(r => { ROAD_BY_ID[r.id] = r; });
    for (const road of roads) {
      B.buildRoadRibbon(scene, road);
      B.buildLampsAlong(scene, road, 200);
    }
    B.buildRing(scene, STATE.ringRadius, 60);

    // intersection markers + traffic lights
    const intersections = W.ringIntersections(roads, STATE.ringRadius);
    const trafficLights = E.buildTrafficLights(scene, intersections);

    // stops
    const stops = S.buildStops(scene, ROAD_BY_ID);
    // register audio
    for (const st of stops) {
      A.registerStop(st.id, st.worldPos, st.audio);
    }

    // stations, ghost packs, boundary eggs
    const stations = S.buildStations(scene);
    S.buildGhostPacks(scene);
    const eggs = S.buildBoundary(scene);

    // entities
    const sectionByID = {};
    W.SECTIONS.forEach(s => sectionByID[s.id] = s);
    const dests = E.buildDestinations(W, stops, intersections);
    const agents = W.CAST.map(c => E.makeAgent(scene, c, dests, sectionByID));

    // boundary visualization (subtle line at the wall)
    buildBoundaryLines(scene);

    // outside-the-world dark plane (so void reads as void)
    const voidFloor = BABYLON.MeshBuilder.CreateGround('void', { width: 6000, height: 6000 }, scene);
    voidFloor.position.y = -0.5;
    voidFloor.material = B.mat(scene, 'voidM', '#06070b');
    voidFloor.material.specularColor = new BABYLON.Color3(0, 0, 0);

    WORLD_HANDLES = { sections, roads, intersections, trafficLights, stops, stations, eggs, agents };
    return WORLD_HANDLES;
  }

  function buildBoundaryLines(scene) {
    const lineMat = new BABYLON.StandardMaterial('boundaryM', scene);
    lineMat.diffuseColor = new BABYLON.Color3(0, 0, 0);
    lineMat.emissiveColor = B.C('#1c2630');
    lineMat.alpha = 0.35;
    lineMat.specularColor = new BABYLON.Color3(0, 0, 0);
    for (const side of ['n', 's', 'e', 'w']) {
      const isH = side === 'n' || side === 's';
      const w = isH ? 3200 : 2;
      const d = isH ? 2 : 3200;
      const x = side === 'e' ? 1600 : side === 'w' ? -1600 : 0;
      const z = side === 'n' ? 1600 : side === 's' ? -1600 : 0;
      const ln = BABYLON.MeshBuilder.CreateBox('bound_' + side, { width: w, height: 1, depth: d }, scene);
      ln.position.set(x, 0.2, z);
      ln.material = lineMat;
    }
  }

  build();

  // ─── Traffic light cycle ──────────────────────────────────────────
  function tickTrafficLights(dt) {
    for (const tl of WORLD_HANDLES.trafficLights) {
      tl.phase += dt / STATE.trafficCycleSec;
      const p = tl.phase % 1;
      let s = 'red';
      if (p < 0.45) s = 'green';
      else if (p < 0.55) s = 'yellow';
      if (tl.state !== s) tl.setState(s);
    }
  }

  // ─── Stop lighting effects (flicker, pulse) ──────────────────────
  function tickStopLighting(t) {
    for (const stop of WORLD_HANDLES.stops) {
      if (!stop.lighting) continue;
      const lp = stop.lamp.pl;
      const baseI = 0.35 * stop.lighting.intensity;
      if (stop.lighting.type === 'flicker') {
        // sharp random dips
        const r = Math.random();
        const dip = r < 0.06 ? 0.3 : 1.0;
        lp.intensity = baseI * dip;
        stop.lamp.capMat.emissiveColor = B.C(stop.lighting.color).scale(stop.lighting.intensity * dip);
      } else if (stop.lighting.type === 'pulse') {
        const m = 0.7 + 0.3 * Math.sin(t * 1.4);
        lp.intensity = baseI * m;
        stop.lamp.capMat.emissiveColor = B.C(stop.lighting.color).scale(stop.lighting.intensity * m);
      } else if (stop.lighting.type === 'pool') {
        // steady but a bit brighter pool
        lp.intensity = baseI * 1.1;
      }
    }
  }

  // ─── Boundary check (any camera or any entity) → reveal egg ──────
  function checkBoundary() {
    const camPos = scene.activeCamera.position;
    for (const e of WORLD_HANDLES.eggs) {
      if (e.revealed) continue;
      let trigger = false;
      const margin = 50;
      if (e.face === 'north' && camPos.z >= W.BOUNDARY.north - margin) trigger = true;
      if (e.face === 'south' && camPos.z <= W.BOUNDARY.south + margin) trigger = true;
      if (e.face === 'east'  && camPos.x >= W.BOUNDARY.east  - margin) trigger = true;
      if (e.face === 'west'  && camPos.x <= W.BOUNDARY.west  + margin) trigger = true;
      if (trigger) {
        e.reveal();
        triggerRippleHUD(e);
      }
      // Also check if any agent reached the wall
      for (const ag of WORLD_HANDLES.agents) {
        const ap = ag.avatar.root.position;
        if (e.face === 'north' && ap.z >= W.BOUNDARY.north - margin) { e.reveal(); break; }
        if (e.face === 'south' && ap.z <= W.BOUNDARY.south + margin) { e.reveal(); break; }
        if (e.face === 'east'  && ap.x >= W.BOUNDARY.east  - margin) { e.reveal(); break; }
        if (e.face === 'west'  && ap.x <= W.BOUNDARY.west  + margin) { e.reveal(); break; }
      }
    }
  }

  function triggerRippleHUD(egg) {
    const el = document.getElementById('rippleHud');
    if (!el) return;
    el.classList.add('visible');
    el.querySelector('.face').textContent = '· ' + egg.face.toUpperCase() + ' WALL ·';
    setTimeout(() => el.classList.remove('visible'), 4200);
  }

  // ─── Loop ─────────────────────────────────────────────────────────
  let lastT = performance.now();
  scene.onBeforeRenderObservable.add(() => {
    const now = performance.now();
    const dt = Math.min(0.1, (now - lastT) / 1000);
    lastT = now;
    const t = now * 0.001;

    tickTrafficLights(dt);
    tickStopLighting(t);

    // entities
    for (const ag of WORLD_HANDLES.agents) {
      ag.update(dt * STATE.entitySpeed);
    }

    checkBoundary();

    // audio listener
    A.update(scene.activeCamera.position);

    // fog toggle
    scene.fogStart = STATE.showFog ? 600 : 4000;
    scene.fogEnd = STATE.showFog ? 2400 : 6500;

    // labels toggle
    if (WORLD_HANDLES.sections) {
      for (const l of WORLD_HANDLES.sections.labels) l.isVisible = STATE.showLabels;
    }
  });

  engine.runRenderLoop(() => scene.render());
  window.addEventListener('resize', () => engine.resize());

  // ─── Camera switching ─────────────────────────────────────────────
  function setCameraMode(mode) {
    STATE.set('cameraMode', mode);
    flyCam.detachControl(canvas);
    topCam.detachControl(canvas);
    if (mode === 'fly') {
      scene.activeCamera = flyCam;
      flyCam.attachControl(canvas, true);
    } else {
      scene.activeCamera = topCam;
      // top cam — drag to pan
      attachTopDrag();
    }
  }
  function attachTopDrag() {
    let dragging = false; let lx = 0, ly = 0;
    const cv = canvas;
    cv.onpointerdown = (ev) => { dragging = true; lx = ev.clientX; ly = ev.clientY; };
    cv.onpointerup = () => { dragging = false; };
    cv.onpointerleave = () => { dragging = false; };
    cv.onpointermove = (ev) => {
      if (!dragging || scene.activeCamera !== topCam) return;
      const dx = ev.clientX - lx; const dy = ev.clientY - ly;
      lx = ev.clientX; ly = ev.clientY;
      const f = topCam.position.y * 0.0028;
      topCam.position.x -= dx * f;
      topCam.position.z += dy * f;
      topCam.setTarget(new BABYLON.Vector3(topCam.position.x, 0, topCam.position.z));
    };
    cv.onwheel = (ev) => {
      if (scene.activeCamera !== topCam) return;
      ev.preventDefault();
      topCam.position.y = Math.max(80, Math.min(2000, topCam.position.y + ev.deltaY * 0.6));
      topCam.setTarget(new BABYLON.Vector3(topCam.position.x, 0, topCam.position.z));
    };
  }
  attachTopDrag();

  // ─── Top-down 2D overlay (vector minimap) ────────────────────────
  function drawOverlay() {
    const cv = document.getElementById('mapCanvas');
    if (!cv || !STATE.showOverlay) { if (cv) cv.style.display = 'none'; return; }
    cv.style.display = 'block';
    const ctx = cv.getContext('2d');
    const W2D = cv.width = cv.clientWidth * (window.devicePixelRatio || 1);
    const H2D = cv.height = cv.clientHeight * (window.devicePixelRatio || 1);
    ctx.clearRect(0, 0, W2D, H2D);

    // world coords: -1700..1700; map to canvas
    const range = 3400;
    const scale = Math.min(W2D, H2D) / range;
    function wx(x) { return W2D / 2 + x * scale; }
    function wy(y) { return H2D / 2 - y * scale; }

    // bg
    ctx.fillStyle = 'rgba(6,7,11,0.85)';
    ctx.fillRect(0, 0, W2D, H2D);

    // boundary
    ctx.strokeStyle = 'rgba(70,217,197,0.25)';
    ctx.lineWidth = 1;
    ctx.strokeRect(wx(-1600), wy(1600), 3200 * scale, 3200 * scale);

    // ring
    ctx.beginPath();
    ctx.arc(wx(0), wy(0), STATE.ringRadius * scale, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(184,196,224,0.20)';
    ctx.lineWidth = 60 * scale;
    ctx.stroke();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(70,217,197,0.4)';
    ctx.stroke();

    // road curves
    for (const road of WORLD_HANDLES.roads) {
      ctx.beginPath();
      for (let i = 0; i <= 48; i++) {
        const p = road.curve.at(i / 48);
        const X = wx(p.x), Y = wy(p.y);
        if (i === 0) ctx.moveTo(X, Y); else ctx.lineTo(X, Y);
      }
      ctx.strokeStyle = road.direction === 'out' ? 'rgba(70,217,197,0.7)' : 'rgba(255,157,109,0.6)';
      ctx.lineWidth = Math.max(1, road.width * scale * 0.6);
      ctx.stroke();
    }

    // map sections
    for (const s of W.SECTIONS) {
      ctx.fillStyle = 'rgba(58,48,80,0.5)';
      ctx.fillRect(wx(s.x - s.w / 2), wy(s.y + s.h / 2), s.w * scale, s.h * scale);
      ctx.strokeStyle = 'rgba(184,196,224,0.3)';
      ctx.lineWidth = 0.5;
      ctx.strokeRect(wx(s.x - s.w / 2), wy(s.y + s.h / 2), s.w * scale, s.h * scale);
    }
    // square accent
    ctx.fillStyle = 'rgba(70,217,197,0.12)';
    ctx.fillRect(wx(-110), wy(90), 220 * scale, 180 * scale);

    // intersections
    for (const ix of WORLD_HANDLES.intersections) {
      ctx.beginPath();
      ctx.arc(wx(ix.x), wy(ix.y), 4, 0, Math.PI * 2);
      ctx.fillStyle = '#46d9c5';
      ctx.fill();
    }

    // stops
    for (const stop of WORLD_HANDLES.stops) {
      ctx.beginPath();
      ctx.arc(wx(stop.position.x), wy(stop.position.z), 3, 0, Math.PI * 2);
      ctx.fillStyle = stop.lighting.color;
      ctx.fill();
    }

    // stations
    for (const st of W.STATIONS) {
      ctx.fillStyle = '#46d9c5';
      ctx.fillRect(wx(st.x - 15), wy(st.y + 5), 30 * scale + 4, 10 * scale + 4);
      ctx.fillStyle = '#06070b';
      ctx.font = '700 ' + Math.max(8, 10) + 'px ui-monospace, Menlo, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(st.label, wx(st.x), wy(st.y) - 14);
    }

    // ghost packs
    for (const g of W.GHOST_PACKS) {
      ctx.fillStyle = 'rgba(60,60,80,0.5)';
      ctx.fillRect(wx(g.x - g.w / 2), wy(g.y + g.h / 2), g.w * scale, g.h * scale);
    }

    // agents
    for (const ag of WORLD_HANDLES.agents) {
      const p = ag.avatar.root.position;
      ctx.beginPath();
      ctx.arc(wx(p.x), wy(p.z), 3.5, 0, Math.PI * 2);
      ctx.fillStyle = ag.color;
      ctx.fill();
    }

    // camera
    const cp = scene.activeCamera.position;
    ctx.beginPath();
    ctx.arc(wx(cp.x), wy(cp.z), 5, 0, Math.PI * 2);
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // eggs that are revealed
    for (const e of WORLD_HANDLES.eggs) {
      if (!e.revealed) continue;
      ctx.beginPath();
      ctx.arc(wx(e.x), wy(e.y), 5, 0, Math.PI * 2);
      ctx.fillStyle = '#00ff41';
      ctx.fill();
    }
  }
  setInterval(drawOverlay, 100);

  // ─── JSON export ──────────────────────────────────────────────────
  function exportJSON() {
    const spec = W.toJSONSpec({ curveIntensity: STATE.curveIntensity, ringRadius: STATE.ringRadius });
    const blob = new Blob([JSON.stringify(spec, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'simutum_demo_world.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // ─── Rebuild on tweak ──────────────────────────────────────────────
  let rebuildTimer = null;
  STATE.subscribe((key) => {
    if (key === 'curveIntensity' || key === 'ringRadius') {
      clearTimeout(rebuildTimer);
      rebuildTimer = setTimeout(() => build(), 220);
    }
    if (key === 'cameraMode') {
      setCameraMode(STATE.cameraMode);
    }
    if (key === 'sound') {
      A.mute(!STATE.sound);
    }
  });

  // ─── Audio start on first user gesture ─────────────────────────────
  function unlockAudio() {
    if (!A.isInitialized()) {
      A.init();
      A.mute(!STATE.sound);
    }
    document.getElementById('audioOverlay').classList.add('hidden');
  }
  document.getElementById('audioStart').addEventListener('click', unlockAudio);
  canvas.addEventListener('click', () => {
    if (!A.isInitialized()) unlockAudio();
  }, { once: true });

  // ─── Expose ──────────────────────────────────────────────────────
  window.SIMUTUM_RUNTIME = {
    scene, engine, build, setCameraMode, exportJSON,
    getAgents: () => WORLD_HANDLES.agents,
    getStops: () => WORLD_HANDLES.stops,
    getTrafficLights: () => WORLD_HANDLES.trafficLights,
    getEggs: () => WORLD_HANDLES.eggs,
  };
})();
