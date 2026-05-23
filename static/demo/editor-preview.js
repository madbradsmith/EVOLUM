// editor-preview.js — light Babylon top-down preview for the editor right pane.
// Subscribes to state changes and rebuilds the scene (debounced 300ms).

(function () {
  'use strict';

  let engine, scene, topCam;
  let worldNodes = []; // disposable handles for rebuild
  let agents = [];
  let rebuildTimer = null;
  let lastTime = performance.now();
  let renderHooked = false;
  let containerEl = null;
  let canvas = null;
  let mode = 'preview'; // preview | play
  let flyCam = null;
  let audio = null;
  let speech = null;
  let recBuffer = null;
  let recStart = 0;

  const C = (hex) => BABYLON.Color3.FromHexString(hex);
  const C4 = (hex, a) => { const c = C(hex); return new BABYLON.Color4(c.r, c.g, c.b, a == null ? 1 : a); };

  function mat(name, hex, opts) {
    const m = new BABYLON.StandardMaterial(name, scene);
    m.diffuseColor = C(hex);
    m.specularColor = new BABYLON.Color3(0, 0, 0);
    if (opts && opts.emissive) m.emissiveColor = C(opts.emissive).scale(opts.eIntensity || 1);
    if (opts && opts.alpha != null) m.alpha = opts.alpha;
    return m;
  }

  // ── Boot / mount ──
  function mount(canvasElement, opts) {
    opts = opts || {};
    mode = opts.mode || 'preview';
    canvas = canvasElement;
    engine = new BABYLON.Engine(canvas, true, { preserveDrawingBuffer: true, stencil: true, antialias: true });
    scene = new BABYLON.Scene(engine);
    scene.clearColor = C4('#06070b');
    scene.fogMode = BABYLON.Scene.FOGMODE_LINEAR;
    scene.fogColor = C('#06070b');
    scene.fogStart = mode === 'play' ? 600 : 800;
    scene.fogEnd = mode === 'play' ? 2400 : 3000;

    topCam = new BABYLON.UniversalCamera('previewTop', new BABYLON.Vector3(0, mode === 'play' ? 600 : 1400, 0), scene);
    topCam.upVector = new BABYLON.Vector3(0, 0, 1);
    topCam.setTarget(new BABYLON.Vector3(0, 0, 0));
    topCam.fov = mode === 'play' ? 1.35 : 1.5;
    topCam.minZ = 0.5;
    topCam.maxZ = 8000;
    scene.activeCamera = topCam;

    if (mode === 'play') {
      flyCam = new BABYLON.UniversalCamera('flyCam', new BABYLON.Vector3(0, 80, -200), scene);
      flyCam.setTarget(new BABYLON.Vector3(0, 0, 0));
      flyCam.speed = 8;
      flyCam.angularSensibility = 2200;
      flyCam.keysUp    = [87, 38];
      flyCam.keysDown  = [83, 40];
      flyCam.keysLeft  = [65, 37];
      flyCam.keysRight = [68, 39];
      flyCam.minZ = 0.5;
      flyCam.maxZ = 6000;
    }

    const hemi = new BABYLON.HemisphericLight('previewHemi', new BABYLON.Vector3(0.2, 1, 0.1), scene);
    hemi.intensity = mode === 'play' ? 0.45 : 0.55;
    hemi.diffuse = C('#b6c0d4');
    hemi.groundColor = C('#1e1c2e');
    if (mode === 'play') {
      const moon = new BABYLON.DirectionalLight('moon', new BABYLON.Vector3(-0.3, -1, -0.2), scene);
      moon.intensity = 0.30;
      moon.diffuse = C('#9bb0d0');
    }

    // pan on drag, zoom on wheel
    let dragging = false, lx = 0, ly = 0;
    canvas.addEventListener('pointerdown', (ev) => {
      if (scene.activeCamera !== topCam) return;
      dragging = true; lx = ev.clientX; ly = ev.clientY;
    });
    canvas.addEventListener('pointerup', () => { dragging = false; });
    canvas.addEventListener('pointerleave', () => { dragging = false; });
    canvas.addEventListener('pointermove', (ev) => {
      if (!dragging || scene.activeCamera !== topCam) return;
      const dx = ev.clientX - lx, dy = ev.clientY - ly;
      lx = ev.clientX; ly = ev.clientY;
      const f = topCam.position.y * 0.0028;
      topCam.position.x -= dx * f;
      topCam.position.z += dy * f;
      topCam.setTarget(new BABYLON.Vector3(topCam.position.x, 0, topCam.position.z));
    });
    canvas.addEventListener('wheel', (ev) => {
      if (scene.activeCamera !== topCam) return;
      ev.preventDefault();
      topCam.position.y = Math.max(120, Math.min(3000, topCam.position.y + ev.deltaY * 1.5));
      topCam.setTarget(new BABYLON.Vector3(topCam.position.x, 0, topCam.position.z));
    }, { passive: false });

    if (mode === 'play') {
      initAudioAndSpeech();
    }

    if (!renderHooked) {
      engine.runRenderLoop(() => {
        if (!scene) return;
        const now = performance.now();
        const dt = Math.min(0.1, (now - lastTime) / 1000);
        lastTime = now;
        const playing = mode === 'play' || window.EDITOR_STATE.get().editor.previewPlay;
        if (playing) {
          for (const ag of agents) ag.update(dt);
          if (mode === 'play') {
            updateProximityChatter(dt);
            updateAudioListener();
            checkBoundaryEggs();
            tickRecorder(dt);
          }
        }
        scene.render();
      });
      window.addEventListener('resize', () => engine && engine.resize());
      renderHooked = true;
    }

    // initial build + subscribe
    build();
    window.EDITOR_STATE.subscribe((s, kind) => {
      if (kind === 'select' || kind === 'camera') return;
      scheduleBuild();
    });
  }

  function unmount() {
    if (!engine) return;
    engine.dispose();
    engine = null; scene = null; topCam = null;
    worldNodes = []; agents = [];
    renderHooked = false;
  }

  // ── Rebuild ──
  function scheduleBuild() {
    clearTimeout(rebuildTimer);
    rebuildTimer = setTimeout(build, 280);
  }
  function build() {
    if (!scene) return;
    // dispose previous
    for (const n of worldNodes) { try { n.dispose && n.dispose(); } catch (e) {} }
    worldNodes = []; agents = [];

    const state = window.EDITOR_STATE.get();

    // Void floor
    const voidF = BABYLON.MeshBuilder.CreateGround('void', { width: 6000, height: 6000 }, scene);
    voidF.position.y = -0.5;
    voidF.material = mat('voidM', '#06070b');
    worldNodes.push(voidF, voidF.material);

    // ── Sections ──
    for (const s of state.sections) {
      const fl = BABYLON.MeshBuilder.CreateGround('floor_' + s.id, { width: s.w, height: s.h }, scene);
      fl.position.set(s.x, 0.1 + (s.raised || 0), s.y);
      if (s.rotation) fl.rotation.y = (s.rotation || 0) * Math.PI / 180;
      fl.material = mat('floorM_' + s.id, s.floor_color || '#1c1a28');
      worldNodes.push(fl, fl.material);

      if (s.raised) {
        const plat = BABYLON.MeshBuilder.CreateBox('plat_' + s.id, { width: s.w + 4, height: s.raised, depth: s.h + 4 }, scene);
        plat.position.set(s.x, s.raised / 2, s.y);
        if (s.rotation) plat.rotation.y = (s.rotation || 0) * Math.PI / 180;
        plat.material = mat('platM_' + s.id, '#252230');
        worldNodes.push(plat, plat.material);
      }

      if (s.walled === true || s.walled === 'partial') {
        const wallH = s.walled === 'partial' ? 26 : 60;
        const wallT = 4;
        const wallMat = mat('wallM_' + s.id, '#2a2438');
        worldNodes.push(wallMat);
        const root = new BABYLON.TransformNode('wallRoot_' + s.id, scene);
        root.position.set(s.x, 0, s.y);
        if (s.rotation) root.rotation.y = (s.rotation || 0) * Math.PI / 180;
        const sides = [
          { w: s.w, d: wallT, ox: 0,        oz: s.h / 2 },
          { w: s.w, d: wallT, ox: 0,        oz: -s.h / 2 },
          { w: wallT, d: s.h, ox: -s.w / 2, oz: 0 },
          { w: wallT, d: s.h, ox:  s.w / 2, oz: 0 },
        ];
        for (let i = 0; i < sides.length; i++) {
          if (s.walled === 'partial' && i === 0) continue; // drop one side
          const w = BABYLON.MeshBuilder.CreateBox('wall_' + s.id + '_' + i, { width: sides[i].w, height: wallH, depth: sides[i].d }, scene);
          w.position.set(sides[i].ox, wallH / 2, sides[i].oz);
          w.material = wallMat;
          w.parent = root;
          worldNodes.push(w);
        }
        worldNodes.push(root);
      }
    }

    // ── Roads (expand to out + back via export helper) ──
    const expanded = expandRoads(state);
    for (const r of expanded) {
      buildRoadRibbon(r);
      buildLampsAlong(r);
    }

    // ── Ring road ──
    if (state.ringRoad.enabled) {
      buildRing(state.ringRoad.radius, state.ringRoad.width);
      // intersections w/ traffic lights
      const inters = window.EDITOR_EXPORT.ringIntersections(expanded, state.ringRoad.radius);
      for (const ix of inters) buildTrafficLight(ix);
    }

    // ── Stops ──
    for (const stop of state.stops) {
      const road = expanded.find(r => r.id === stop.road + '_out');
      if (!road) continue;
      buildStop(stop, road);
    }

    // ── Stations ──
    for (const st of state.stations) {
      buildStation(st);
    }

    // ── Ghost packs ──
    for (const g of state.ghostPacks) {
      buildGhostPack(g);
    }

    // ── Boundary + eggs ──
    buildBoundaryLines(state.boundary);
    buildEggs(state.boundary, state.eggs);

    // ── Cast (entities) ──
    for (const c of state.cast) {
      const ag = buildAgent(c, state);
      if (ag) agents.push(ag);
    }
  }

  function expandRoads(state) {
    const out = [];
    for (const r of state.roads) {
      const outPts = window.EDITOR_EXPORT.makeCurve(r.p0, r.p3, r.sideOffset, r.intensity);
      const dx = r.p3.x - r.p0.x, dy = r.p3.y - r.p0.y;
      const len = Math.hypot(dx, dy) || 1;
      const nx = -dy / len, ny = dx / len;
      const back_p0 = r.p3;
      const back_p3 = { x: r.p0.x - nx * 120, y: r.p0.y - ny * 120 };
      const backPts = window.EDITOR_EXPORT.makeCurve(back_p0, back_p3, r.sideOffset, r.intensity);
      out.push(makeRoadObj(r.id + '_out', outPts, r));
      out.push(makeRoadObj(r.id + '_back', backPts, r));
    }
    return out;
  }

  function makeRoadObj(id, pts, r) {
    return {
      id, bezier: pts, width: r.width, theme: r.theme,
      destination: r.destination,
      at: (t) => window.EDITOR_EXPORT.bez(pts[0], pts[1], pts[2], pts[3], t),
      tangent: (t) => {
        const u = 1 - t;
        return {
          x: 3*u*u*(pts[1].x - pts[0].x) + 6*u*t*(pts[2].x - pts[1].x) + 3*t*t*(pts[3].x - pts[2].x),
          y: 3*u*u*(pts[1].y - pts[0].y) + 6*u*t*(pts[2].y - pts[1].y) + 3*t*t*(pts[3].y - pts[2].y),
        };
      },
      length: () => window.EDITOR_EXPORT.curveLength(pts),
    };
  }

  function buildRoadRibbon(road) {
    const segs = 36;
    const halfW = road.width / 2;
    const yLift = 0.2;
    const positions = [], indices = [];
    for (let i = 0; i <= segs; i++) {
      const t = i / segs;
      const p = road.at(t);
      const tg = road.tangent(t);
      const tl = Math.hypot(tg.x, tg.y) || 1;
      const nx = -tg.y / tl, ny = tg.x / tl;
      positions.push(p.x + nx * halfW, yLift, p.y + ny * halfW);
      positions.push(p.x - nx * halfW, yLift, p.y - ny * halfW);
      if (i < segs) {
        const a = i * 2, b = i * 2 + 1, c = (i + 1) * 2, d = (i + 1) * 2 + 1;
        indices.push(a, b, c, b, d, c);
      }
    }
    const m = new BABYLON.Mesh('road_' + road.id, scene);
    const vd = new BABYLON.VertexData();
    vd.positions = positions; vd.indices = indices;
    const normals = []; BABYLON.VertexData.ComputeNormals(positions, indices, normals);
    vd.normals = normals; vd.applyToMesh(m);
    m.material = mat('roadM_' + road.id, '#1a1a22');
    worldNodes.push(m, m.material);
  }

  function buildLampsAlong(road) {
    const every = 240;
    const len = road.length();
    const count = Math.max(2, Math.floor(len / every));
    for (let i = 1; i < count; i++) {
      const t = i / count;
      const p = road.at(t);
      const tg = road.tangent(t);
      const tl = Math.hypot(tg.x, tg.y) || 1;
      const nx = -tg.y / tl, ny = tg.x / tl;
      const cx = p.x + nx * 55, cz = p.y + ny * 55;
      const cap = BABYLON.MeshBuilder.CreateSphere('lampCap_' + Math.random(), { diameter: 6 }, scene);
      cap.position.set(cx, 50, cz);
      const themeColor = themeToColor(road.theme);
      const capMat = new BABYLON.StandardMaterial('lampM_' + Math.random(), scene);
      capMat.diffuseColor = C(themeColor);
      capMat.emissiveColor = C(themeColor).scale(0.7);
      capMat.specularColor = new BABYLON.Color3(0, 0, 0);
      cap.material = capMat;
      worldNodes.push(cap, capMat);
    }
  }

  function themeToColor(theme) {
    return ({ warm: '#ffd9a0', amber: '#ff9d6d', cyan: '#6dd8ff', purple: '#c279ff', white: '#e8edf8' }[theme] || '#ffd9a0');
  }

  function buildRing(radius, width) {
    const segs = 80;
    const halfW = width / 2;
    const positions = [], indices = [];
    for (let i = 0; i <= segs; i++) {
      const a = (i / segs) * Math.PI * 2;
      const cx = Math.cos(a), cz = Math.sin(a);
      positions.push((radius + halfW) * cx, 0.2, (radius + halfW) * cz);
      positions.push((radius - halfW) * cx, 0.2, (radius - halfW) * cz);
      if (i < segs) {
        const A = i * 2, B = i * 2 + 1, Cc = (i + 1) * 2, D = (i + 1) * 2 + 1;
        indices.push(A, B, Cc, B, D, Cc);
      }
    }
    const m = new BABYLON.Mesh('ring', scene);
    const vd = new BABYLON.VertexData();
    vd.positions = positions; vd.indices = indices;
    const normals = []; BABYLON.VertexData.ComputeNormals(positions, indices, normals);
    vd.normals = normals; vd.applyToMesh(m);
    m.material = mat('ringM', '#1a1a22');
    worldNodes.push(m, m.material);
  }

  function buildTrafficLight(ix) {
    const post = BABYLON.MeshBuilder.CreateCylinder('tl_' + ix.id, { diameter: 3, height: 60 }, scene);
    post.position.set(ix.x, 30, ix.y);
    post.material = mat('tlM_' + ix.id, '#1a1a22');
    worldNodes.push(post, post.material);
    const head = BABYLON.MeshBuilder.CreateBox('tlH_' + ix.id, { width: 8, height: 22, depth: 8 }, scene);
    head.position.set(ix.x, 60, ix.y);
    head.material = mat('tlHM_' + ix.id, '#46d9c5', { emissive: '#46d9c5', eIntensity: 0.6 });
    worldNodes.push(head, head.material);
  }

  function buildStop(stop, road) {
    const p = road.at(stop.t);
    const tg = road.tangent(stop.t);
    const tl = Math.hypot(tg.x, tg.y) || 1;
    const nx = -tg.y / tl, ny = tg.x / tl;
    const padOff = 70;
    const padX = p.x + nx * padOff, padZ = p.y + ny * padOff;

    const pad = BABYLON.MeshBuilder.CreateBox('pad_' + stop.id, { width: 60, height: 4, depth: 60 }, scene);
    pad.position.set(padX, 2.2, padZ);
    pad.material = mat('padM_' + stop.id, '#2a2638');
    worldNodes.push(pad, pad.material);

    const bench = BABYLON.MeshBuilder.CreateBox('bench_' + stop.id, { width: 70, height: 18, depth: 20 }, scene);
    bench.position.set(padX - nx * 12, 13, padZ - ny * 12);
    bench.material = mat('benchM_' + stop.id, '#3a3050');
    worldNodes.push(bench, bench.material);

    // glow pool
    const pool = BABYLON.MeshBuilder.CreateDisc('pool_' + stop.id, { radius: 55, tessellation: 24 }, scene);
    pool.rotation.x = Math.PI / 2;
    pool.position.set(padX, 0.16, padZ);
    const poolMat = new BABYLON.StandardMaterial('poolM_' + stop.id, scene);
    poolMat.diffuseColor = C(stop.lighting.color).scale(0.05);
    poolMat.emissiveColor = C(stop.lighting.color).scale(0.16);
    poolMat.alpha = 0.5;
    poolMat.specularColor = new BABYLON.Color3(0, 0, 0);
    pool.material = poolMat;
    worldNodes.push(pool, poolMat);

    const cap = BABYLON.MeshBuilder.CreateSphere('stopCap_' + stop.id, { diameter: 8 }, scene);
    cap.position.set(padX + nx * 18, 50, padZ + ny * 18);
    const capMat = new BABYLON.StandardMaterial('stopCapM_' + stop.id, scene);
    capMat.diffuseColor = C(stop.lighting.color);
    capMat.emissiveColor = C(stop.lighting.color).scale(stop.lighting.intensity || 1);
    capMat.specularColor = new BABYLON.Color3(0, 0, 0);
    cap.material = capMat;
    worldNodes.push(cap, capMat);
  }

  function buildStation(st) {
    const root = new BABYLON.TransformNode('stRoot_' + st.id, scene);
    root.position.set(st.x, 0, st.y);

    const plat = BABYLON.MeshBuilder.CreateBox('stPlat_' + st.id, { width: 280, height: 8, depth: 100 }, scene);
    plat.position.y = 4;
    plat.parent = root;
    plat.material = mat('stPlatM_' + st.id, '#2e2a3c');

    const gateMat = mat('gateM_' + st.id, '#0a0c12');
    const gate = BABYLON.MeshBuilder.CreateBox('gate_' + st.id, { width: 100, height: 60, depth: 2 }, scene);
    gate.position.set(0, 34, -30);
    gate.parent = root;
    gate.material = gateMat;

    // CTA label
    const tex = new BABYLON.DynamicTexture('ctaTex_' + st.id, { width: 512, height: 128 }, scene, true);
    const ctx = tex.getContext();
    ctx.fillStyle = '#0a0c12'; ctx.fillRect(0, 0, 512, 128);
    ctx.strokeStyle = '#46d9c5'; ctx.lineWidth = 4; ctx.strokeRect(6, 6, 500, 116);
    ctx.font = '600 36px ui-monospace, Menlo, monospace';
    ctx.fillStyle = '#46d9c5';
    ctx.textAlign = 'center';
    ctx.fillText(st.label || 'STATION', 256, 60);
    ctx.font = '500 22px ui-monospace, Menlo, monospace';
    ctx.fillStyle = '#b9c4e0';
    ctx.fillText('Full access in Simutum', 256, 96);
    tex.update();
    const ctaMat = new BABYLON.StandardMaterial('ctaMm_' + st.id, scene);
    ctaMat.diffuseTexture = tex;
    ctaMat.emissiveTexture = tex;
    ctaMat.specularColor = new BABYLON.Color3(0, 0, 0);
    ctaMat.disableLighting = true;
    const ctaP = BABYLON.MeshBuilder.CreatePlane('ctaP_' + st.id, { width: 80, height: 30 }, scene);
    ctaP.position.set(0, 34, -28.8);
    ctaP.parent = root;
    ctaP.material = ctaMat;

    worldNodes.push(plat, gate, gateMat, plat.material, ctaP, ctaMat, tex, root);
  }

  function buildGhostPack(g) {
    const base = BABYLON.MeshBuilder.CreateGround('ghost_' + g.id, { width: g.w, height: g.h }, scene);
    base.position.set(g.x, 0.05, g.y);
    base.material = mat('ghostM_' + g.id, g.color);
    worldNodes.push(base, base.material);
    // a few shapes for texture
    if (g.kind === 'theater') {
      for (let r = 0; r < 3; r++) for (let s = 0; s < 6; s++) {
        const b = BABYLON.MeshBuilder.CreateBox('gx', { width: 10, height: 5, depth: 8 }, scene);
        b.position.set(g.x - 30 + s * 12, 4, g.y - 30 + r * 14);
        b.material = base.material;
        worldNodes.push(b);
      }
    } else if (g.kind === 'bar') {
      const c = BABYLON.MeshBuilder.CreateBox('gbarc', { width: 100, height: 10, depth: 18 }, scene);
      c.position.set(g.x, 5, g.y);
      c.material = base.material; worldNodes.push(c);
    } else if (g.kind === 'field') {
      for (let i = 0; i < 5; i++) {
        const r = BABYLON.MeshBuilder.CreateSphere('grck', { diameter: 30 }, scene);
        r.scaling = new BABYLON.Vector3(1, 0.4, 0.7);
        r.position.set(g.x - 80 + i * 40, 6, g.y);
        r.material = base.material; worldNodes.push(r);
      }
    }
  }

  function buildBoundaryLines(b) {
    const lineMat = new BABYLON.StandardMaterial('boundLM', scene);
    lineMat.emissiveColor = C('#1c2630');
    lineMat.alpha = 0.4;
    lineMat.specularColor = new BABYLON.Color3(0, 0, 0);
    worldNodes.push(lineMat);
    const N = b.north, S = b.south, E = b.east, W = b.west;
    function bar(x, y, w, d) {
      const m = BABYLON.MeshBuilder.CreateBox('boundB', { width: w, height: 1, depth: d }, scene);
      m.position.set(x, 0.2, y);
      m.material = lineMat;
      worldNodes.push(m);
    }
    bar(0, N, E - W, 2);
    bar(0, S, E - W, 2);
    bar(E, 0, 2, N - S);
    bar(W, 0, 2, N - S);
  }

  function buildEggs(boundary, eggs) {
    function eggAt(x, y) {
      const post = BABYLON.MeshBuilder.CreateCylinder('eggPost', { diameter: 3, height: 28 }, scene);
      post.position.set(x, 14, y);
      post.material = mat('eggPostM' + x + y, '#1a2e1a');
      worldNodes.push(post, post.material);
      const screen = BABYLON.MeshBuilder.CreatePlane('eggScr', { width: 24, height: 30 }, scene);
      screen.position.set(x, 32, y);
      screen.rotation.y = Math.atan2(-x, -y);
      const m = new BABYLON.StandardMaterial('eggScrM' + x + y, scene);
      m.diffuseColor = new BABYLON.Color3(0, 0.06, 0.02);
      m.emissiveColor = new BABYLON.Color3(0, 1, 0.25);
      m.specularColor = new BABYLON.Color3(0, 0, 0);
      m.disableLighting = true;
      screen.material = m;
      worldNodes.push(screen, m);
    }
    if (eggs.north) eggAt(0, boundary.north);
    if (eggs.south) eggAt(0, boundary.south);
    if (eggs.east)  eggAt(boundary.east, 0);
    if (eggs.west)  eggAt(boundary.west, 0);
  }

  function buildAgent(c, state) {
    const root = new BABYLON.TransformNode('av_' + c.name, scene);
    const head = BABYLON.MeshBuilder.CreateSphere('head_' + c.name, { diameter: 14 }, scene);
    let totalH = 35, bodyH = 14;
    if (c.type === 'thinker') { head.scaling = new BABYLON.Vector3(1, 1.15, 1); totalH = 42; bodyH = 18; }
    else if (c.type === 'anchor') { head.scaling = new BABYLON.Vector3(1, 0.78, 1); totalH = 35; bodyH = 14; }
    else { totalH = 38; bodyH = 16; }
    const body = BABYLON.MeshBuilder.CreateCylinder('body_' + c.name, { diameter: 10, height: bodyH }, scene);
    body.position.y = bodyH / 2;
    head.position.y = bodyH + 10;
    head.parent = root; body.parent = root;
    const m = new BABYLON.StandardMaterial('avM_' + c.name, scene);
    m.diffuseColor = C(c.color);
    m.emissiveColor = C(c.color).scale(0.35);
    m.specularColor = new BABYLON.Color3(0, 0, 0);
    head.material = m; body.material = m;
    // spawn at section
    const sec = state.sections.find(s => s.id === c.spawn);
    if (sec) { root.position.set(sec.x, 0, sec.y); }

    worldNodes.push(root, head, body, m);

    return {
      name: c.name, color: c.color, spawn: c.spawn, agenda: c.agenda || {}, root,
      pos: new BABYLON.Vector3(sec ? sec.x : 0, 0, sec ? sec.y : 0),
      target: null, state: 'thinking', dwell: 1 + Math.random() * 2,
      update(dt) {
        if (this.state === 'thinking') {
          this.dwell -= dt;
          if (this.dwell <= 0) {
            // pick a random destination weighted by agenda
            const candidates = [];
            for (const s of state.sections) candidates.push({ x: s.x, y: s.y, w: (c.agenda && c.agenda.office) || 0.2, cat: 'office' });
            candidates.push({ x: 0, y: 0, w: (c.agenda && c.agenda.square) || 0.2, cat: 'square' });
            for (const stp of state.stops) {
              const rd = state.roads.find(r => r.id === stp.road);
              if (!rd) continue;
              const pts = window.EDITOR_EXPORT.makeCurve(rd.p0, rd.p3, rd.sideOffset, rd.intensity);
              const p = window.EDITOR_EXPORT.bez(pts[0], pts[1], pts[2], pts[3], stp.t);
              candidates.push({ x: p.x, y: p.y, w: (c.agenda && c.agenda.stop) || 0.2, cat: 'stop' });
            }
            if (state.boundary) {
              const bw = (c.agenda && c.agenda.boundary) || 0.05;
              candidates.push({ x: 0, y: state.boundary.north * 0.85, w: bw, cat: 'boundary' });
              candidates.push({ x: 0, y: state.boundary.south * 0.85, w: bw, cat: 'boundary' });
              candidates.push({ x: state.boundary.east * 0.85, y: 0, w: bw, cat: 'boundary' });
              candidates.push({ x: state.boundary.west * 0.85, y: 0, w: bw, cat: 'boundary' });
            }
            if (!candidates.length) { this.state = 'thinking'; this.dwell = 2; return; }
            const total = candidates.reduce((a, c2) => a + c2.w, 0);
            let r = Math.random() * total;
            let pick = candidates[0];
            for (const c2 of candidates) { r -= c2.w; if (r <= 0) { pick = c2; break; } }
            this.target = new BABYLON.Vector3(pick.x, 0, pick.y);
            this.state = 'walking';
            // notify play-mode for inner voice
            if (window.EDITOR_PREVIEW && window.EDITOR_PREVIEW.onDestinationPick) {
              window.EDITOR_PREVIEW.onDestinationPick(c.name, pick.cat);
            }
          }
          return;
        }
        if (this.state === 'walking') {
          const dx = this.target.x - this.pos.x, dz = this.target.z - this.pos.z;
          const d = Math.hypot(dx, dz);
          if (d < 2) { this.state = 'thinking'; this.dwell = 3 + Math.random() * 5; return; }
          const speed = 32;
          this.pos.x += (dx / d) * speed * dt;
          this.pos.z += (dz / d) * speed * dt;
          this.root.position.copyFrom(this.pos);
          this.root.rotation.y = Math.atan2(dx, dz);
        }
      },
    };
  }

  // ─────────────────────────────────────────────────────────
  // Play-mode features: audio, speech, eggs, recording.
  // ─────────────────────────────────────────────────────────

  // Stop audio loops (synthesized via Web Audio API).
  function initAudioAndSpeech() {
    if (audio) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = new AC();
    const master = ctx.createGain();
    master.gain.value = 0.5;
    master.connect(ctx.destination);
    audio = { ctx, master, stops: new Map(), unlocked: false };

    // Reverb impulse for inner voice
    const irLen = ctx.sampleRate * 1.6;
    const ir = ctx.createBuffer(2, irLen, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = ir.getChannelData(ch);
      for (let i = 0; i < irLen; i++) {
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / irLen, 2.5);
      }
    }
    audio.reverbIR = ir;

    speech = {
      synth: window.speechSynthesis,
      voices: [],
      perEntity: new Map(),
      lastPairTime: new Map(), // 'A|B' → timestamp
    };
    const refreshVoices = () => {
      if (!speech.synth) return;
      speech.voices = speech.synth.getVoices();
    };
    refreshVoices();
    if (speech.synth) speech.synth.onvoiceschanged = refreshVoices;
  }

  function unlockAudioOnGesture() {
    if (audio && audio.ctx.state === 'suspended') audio.ctx.resume();
    audio && (audio.unlocked = true);
  }

  function buildStopAudio(stop) {
    if (!audio) return null;
    const ctx = audio.ctx;
    const g = ctx.createGain();
    g.gain.value = 0;
    g.connect(audio.master);
    const sources = [];
    const noise = () => {
      const buf = ctx.createBuffer(1, ctx.sampleRate * 3, ctx.sampleRate);
      const d = buf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      return buf;
    };
    function noiseSrc(filterType, freq, q, gain) {
      const src = ctx.createBufferSource(); src.buffer = noise(); src.loop = true;
      const filt = ctx.createBiquadFilter(); filt.type = filterType; filt.frequency.value = freq; filt.Q.value = q;
      const sg = ctx.createGain(); sg.gain.value = gain;
      src.connect(filt).connect(sg).connect(g); src.start();
      sources.push(src);
      return { filt, g: sg };
    }
    function osc(type, freq, gain) {
      const o = ctx.createOscillator(); o.type = type; o.frequency.value = freq;
      const sg = ctx.createGain(); sg.gain.value = gain;
      o.connect(sg).connect(g); o.start();
      sources.push(o);
      return { o, g: sg };
    }
    function lfo(target, freq, depth) {
      const o = ctx.createOscillator(); o.frequency.value = freq;
      const sg = ctx.createGain(); sg.gain.value = depth;
      o.connect(sg).connect(target); o.start();
      sources.push(o);
    }
    switch (stop.audio) {
      case 'wind_low':         lfo(noiseSrc('lowpass', 360, 0.9, 0.22).filt.frequency, 0.13, 220); break;
      case 'wind_high':        lfo(noiseSrc('bandpass', 1200, 1.4, 0.18).filt.frequency, 0.22, 600); break;
      case 'wind_reeds': {
        lfo(noiseSrc('bandpass', 700, 2.5, 0.16).filt.frequency, 0.4, 280);
        lfo(osc('sine', 612, 0.012).o.frequency, 0.31, 40);
        break;
      }
      case 'transformer_hum': {
        osc('sine', 60, 0.06);
        const h = osc('sawtooth', 120, 0.018);
        lfo(h.g.gain, 0.7, 0.008);
        noiseSrc('highpass', 4000, 0.6, 0.025);
        break;
      }
      case 'distant_chatter': {
        const n = noiseSrc('bandpass', 900, 4, 0.16);
        lfo(n.g.gain, 1.7, 0.10);
        osc('triangle', 220, 0.012);
        break;
      }
      case 'engine_idle': {
        osc('sawtooth', 36, 0.04);
        const r = osc('square', 72, 0.012);
        lfo(r.o.frequency, 4, 6);
        noiseSrc('bandpass', 240, 1.2, 0.05);
        break;
      }
      case 'crate_creak':  noiseSrc('bandpass', 380, 2.5, 0.06); break;
      case 'insect_chirps': noiseSrc('lowpass', 280, 0.7, 0.07); break;
      case 'sensor_ping':  noiseSrc('highpass', 6000, 0.4, 0.018); break;
    }
    return { gain: g, sources };
  }

  function updateAudioListener() {
    if (!audio || !audio.unlocked) return;
    const camPos = scene.activeCamera.position;
    const state = window.EDITOR_STATE.get();
    for (const stop of state.stops) {
      let info = audio.stops.get(stop.id);
      if (!info) {
        info = buildStopAudio(stop);
        if (info) audio.stops.set(stop.id, info);
        else continue;
      }
      // compute stop world position
      const road = state.roads.find(r => r.id === stop.road);
      if (!road) continue;
      const pts = window.EDITOR_EXPORT.makeCurve(road.p0, road.p3, road.sideOffset, road.intensity);
      const p = window.EDITOR_EXPORT.bez(pts[0], pts[1], pts[2], pts[3], stop.t);
      const dx = camPos.x - p.x;
      const dz = camPos.z - p.y;
      const d = Math.hypot(dx, dz);
      const v = Math.max(0, Math.min(1, 1 - (d - 30) / 240));
      info.gain.gain.setTargetAtTime(v * 0.45, audio.ctx.currentTime, 0.4);
    }
  }

  function assignVoice(name) {
    if (!speech || !speech.voices.length) return null;
    if (speech.perEntity.has(name)) return speech.perEntity.get(name);
    // hash name → voice index
    let h = 0; for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
    const v = speech.voices[Math.abs(h) % speech.voices.length];
    // varied pitch/rate per entity
    const pitch = 0.85 + ((Math.abs(h) % 90) / 100) * 0.6;   // 0.85–1.45
    const rate  = 0.90 + ((Math.abs(h >> 4) % 50) / 100) * 0.4; // 0.90–1.30
    const config = { voice: v, pitch, rate };
    speech.perEntity.set(name, config);
    return config;
  }

  function speak(name, line) {
    if (!speech || !speech.synth) return;
    unlockAudioOnGesture();
    const cfg = assignVoice(name);
    if (!cfg) return;
    const u = new SpeechSynthesisUtterance(line);
    if (cfg.voice) u.voice = cfg.voice;
    u.pitch = cfg.pitch;
    u.rate  = cfg.rate;
    u.volume = 0.85;
    speech.synth.speak(u);
    recordSpeech(name, line, 'speech');
  }

  function innerVoice(name, line) {
    if (!speech || !speech.synth) return;
    unlockAudioOnGesture();
    const cfg = assignVoice(name);
    if (!cfg) return;
    const u = new SpeechSynthesisUtterance(line);
    if (cfg.voice) u.voice = cfg.voice;
    u.pitch = Math.max(0.1, cfg.pitch - 0.15);
    u.rate  = Math.max(0.1, cfg.rate * 0.82);
    u.volume = 0.40;
    speech.synth.speak(u);
    recordSpeech(name, line, 'inner');
  }

  // ── Conversation lines per role ──
  const CHAT_LINES = [
    "Standup's about to start.", "I was just heading to the square.",
    "You read the dashboard yet?", "Yeah, the chrome holds.",
    "Watch the lights — they cycle long today.",
    "Walking the edge. You?", "Lab side, then the bench.",
    "Frank's looking for someone.", "Tell him I'm filing.",
    "Cool light on the amber road.", "It always pulls me there.",
  ];
  const INNER_LINES = {
    office: ['…back to my desk…', '…filing…', '…paper there…'],
    square: ['…the square…', '…center of the room…', '…hold a beat…'],
    stop: ['…that stop on the amber road…', '…the bench…', '…lit corner…'],
    intersection: ['…the cycle…', '…watching the lights…', '…cross-traffic…'],
    boundary: ['…boundary again…', '…edge of the seam…', '…where it ends…'],
  };
  function pickInner(category) {
    const lib = INNER_LINES[category] || INNER_LINES.square;
    return lib[Math.floor(Math.random() * lib.length)];
  }

  function updateProximityChatter() {
    if (!speech) return;
    if (!speech.synth) return;
    if (speech.synth.speaking) return; // don't pile up
    const now = performance.now();
    for (let i = 0; i < agents.length; i++) {
      for (let j = i + 1; j < agents.length; j++) {
        const a = agents[i], b = agents[j];
        const d = Math.hypot(a.pos.x - b.pos.x, a.pos.z - b.pos.z);
        if (d > 80) continue;
        const key = [a.name, b.name].sort().join('|');
        const last = speech.lastPairTime.get(key) || 0;
        if (now - last < 15000) continue;
        speech.lastPairTime.set(key, now);
        // alternate speaker
        const speaker = Math.random() < 0.5 ? a : b;
        const line = CHAT_LINES[Math.floor(Math.random() * CHAT_LINES.length)];
        speak(speaker.name, line);
        return; // only one pair per tick
      }
    }
  }

  // Inner-voice hook called by agents when they pick a new target.
  function onDestinationPick(agentName, category) {
    if (mode !== 'play') return;
    if (Math.random() < 0.55) innerVoice(agentName, pickInner(category));
  }

  // ── Boundary egg reveal ──
  function checkBoundaryEggs() {
    const state = window.EDITOR_STATE.get();
    const b = state.boundary;
    const m = 60;
    const cam = scene.activeCamera.position;
    function reveal(face, x, y) {
      // find the egg pool/screen we built; tag visible (we built them visible already);
      // here we just flash the HUD if not already revealed
      const key = '_egg_seen_' + face;
      if (window[key]) return;
      window[key] = true;
      const hud = document.getElementById('rippleHud');
      if (hud) {
        const fEl = hud.querySelector('.face'); if (fEl) fEl.textContent = '· ' + face.toUpperCase() + ' WALL ·';
        hud.classList.add('visible');
        setTimeout(() => hud.classList.remove('visible'), 4200);
      }
    }
    if (state.eggs.north && cam.z >= b.north - m) reveal('north', 0, b.north);
    if (state.eggs.south && cam.z <= b.south + m) reveal('south', 0, b.south);
    if (state.eggs.east  && cam.x >= b.east  - m) reveal('east',  b.east,  0);
    if (state.eggs.west  && cam.x <= b.west  + m) reveal('west',  b.west,  0);
  }

  // ── Camera switching ──
  function setCameraMode(m) {
    if (m === 'fly' && flyCam) {
      scene.activeCamera = flyCam;
      flyCam.attachControl(canvas, true);
    } else {
      if (flyCam) flyCam.detachControl(canvas);
      scene.activeCamera = topCam;
    }
  }

  // ── Recording ──
  function startRecording() {
    recBuffer = { startedAt: Date.now(), ticks: [], speech: [] };
    recStart = performance.now();
  }
  function stopRecording() {
    if (!recBuffer) return null;
    const r = recBuffer; recBuffer = null;
    return r;
  }
  function recordSpeech(name, line, kind) {
    if (!recBuffer) return;
    const t = (performance.now() - recStart) / 1000;
    recBuffer.speech.push({ t: Math.round(t * 100) / 100, name, line, kind });
  }
  let lastTick = 0;
  function tickRecorder(dt) {
    if (!recBuffer) return;
    lastTick += dt;
    if (lastTick < 0.25) return;
    lastTick = 0;
    const t = (performance.now() - recStart) / 1000;
    const positions = agents.map(ag => ({
      name: ag.name,
      x: Math.round(ag.pos.x),
      y: Math.round(ag.pos.z),
      state: ag.state,
    }));
    recBuffer.ticks.push({ t: Math.round(t * 100) / 100, positions });
  }
  function exportRecording() {
    const r = recBuffer || { ticks: [], speech: [] };
    const blob = new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'replay.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // ── Mobile performance flag ──
  const IS_MOBILE = (navigator.maxTouchPoints || 0) > 1;

  // Expose
  window.EDITOR_PREVIEW = {
    mount, unmount, scheduleBuild,
    speak, innerVoice, unlockAudioOnGesture,
    setCameraMode, IS_MOBILE,
    startRecording, stopRecording, exportRecording,
    isRecording: () => !!recBuffer,
    onDestinationPick,
  };
})();
