// scene-stops.js — road stops, stations, ghost packs, easter eggs.
// Each stop has its own POI, a light, and a (deferred) audio loop.

(function () {
  'use strict';

  const W = window.SIMUTUM_WORLD;
  const B = window.SIMUTUM_BUILD;
  const C = B.C;

  // ─── Stops along roads ────────────────────────────────────────────
  function buildStops(scene, roadByID, audioCtx) {
    const out = [];
    for (const stop of W.STOPS) {
      const road = roadByID[stop.road];
      if (!road) continue;
      const p = road.curve.at(stop.t);
      const tg = road.curve.tangent(stop.t);
      const tl = Math.hypot(tg.x, tg.y) || 1;
      const nx = -tg.y / tl, ny = tg.x / tl; // left of forward
      const ax = tg.x / tl,  ay = tg.y / tl;  // forward (along road)

      // pull-off pad on left side
      const padOff = 70;
      const padX = p.x + nx * padOff;
      const padZ = p.y + ny * padOff;

      const pad = BABYLON.MeshBuilder.CreateBox('stop_pad_' + stop.id, { width: 60, height: 4, depth: 60 }, scene);
      pad.position.set(padX, 2.2, padZ);
      pad.rotation.y = -Math.atan2(ay, ax); // align with road
      pad.material = B.mat(scene, 'padM_' + stop.id, '#2a2638');
      pad.material.specularColor = new BABYLON.Color3(0, 0, 0);

      // bench (oriented toward road)
      const bench = BABYLON.MeshBuilder.CreateBox('bench_' + stop.id, { width: 70, height: 18, depth: 20 }, scene);
      bench.position.set(padX - nx * 12, 13, padZ - ny * 12);
      bench.rotation.y = -Math.atan2(ay, ax);
      bench.material = B.mat(scene, 'benchM_' + stop.id, '#3a3050');

      // POI
      const poiHandle = buildPOI(scene, stop, padX, padZ, ax, ay, nx, ny);

      // Lamp — colored to lighting spec
      const lamp = B.buildLamp(scene, padX + nx * 18, padZ + ny * 18, stop.lighting.color, stop.lighting.intensity);

      // Ground glow pool — a faint emissive disc
      const pool = BABYLON.MeshBuilder.CreateDisc('pool_' + stop.id, { radius: 55, tessellation: 32 }, scene);
      pool.rotation.x = Math.PI / 2;
      pool.position.set(padX, 0.16, padZ);
      const poolMat = new BABYLON.StandardMaterial('poolM_' + stop.id, scene);
      poolMat.diffuseColor = C(stop.lighting.color).scale(0.05);
      poolMat.emissiveColor = C(stop.lighting.color).scale(0.10);
      poolMat.specularColor = new BABYLON.Color3(0, 0, 0);
      poolMat.alpha = 0.55;
      pool.material = poolMat;

      // label
      const lblTex = new BABYLON.DynamicTexture('stopLblT_' + stop.id, { width: 512, height: 64 }, scene, true);
      lblTex.hasAlpha = true;
      const ctx = lblTex.getContext();
      ctx.clearRect(0, 0, 512, 64);
      ctx.font = '600 22px ui-monospace, Menlo, monospace';
      ctx.fillStyle = stop.lighting.color;
      ctx.textAlign = 'center';
      ctx.fillText(stop.id.toUpperCase(), 256, 36);
      lblTex.update();
      const lblMat = new BABYLON.StandardMaterial('stopLblM_' + stop.id, scene);
      lblMat.diffuseTexture = lblTex;
      lblMat.emissiveTexture = lblTex;
      lblMat.opacityTexture = lblTex;
      lblMat.disableLighting = true;
      lblMat.specularColor = new BABYLON.Color3(0, 0, 0);
      const lblPlane = BABYLON.MeshBuilder.CreatePlane('stopLblP_' + stop.id, { width: 80, height: 8 }, scene);
      lblPlane.position.set(padX, 36, padZ);
      lblPlane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_Y;
      lblPlane.material = lblMat;

      out.push({
        id: stop.id,
        position: { x: padX, z: padZ },
        worldPos: new BABYLON.Vector3(padX, 4, padZ),
        lighting: stop.lighting,
        lamp,
        pool,
        audio: stop.audio,
      });
    }
    return out;
  }

  function buildPOI(scene, stop, x, z, ax, ay, nx, ny) {
    function box(name, w, h, d, ox, oz, hex) {
      const b = BABYLON.MeshBuilder.CreateBox('poi_' + stop.id + '_' + name, { width: w, height: h, depth: d }, scene);
      b.position.set(x + nx * oz + ax * ox, h / 2 + 4, z + ny * oz + ay * ox);
      b.rotation.y = -Math.atan2(ay, ax);
      b.material = B.mat(scene, 'poiM_' + stop.id + '_' + name, hex || '#3a3050');
      return b;
    }
    function cyl(name, diam, h, ox, oz, hex) {
      const c = BABYLON.MeshBuilder.CreateCylinder('poi_' + stop.id + '_' + name, { diameter: diam, height: h }, scene);
      c.position.set(x + nx * oz + ax * ox, h / 2 + 4, z + ny * oz + ay * ox);
      c.material = B.mat(scene, 'poiM_' + stop.id + '_' + name, hex || '#2a2438');
      return c;
    }

    switch (stop.poi) {
      case 'notice_board':
        cyl('post', 4, 50, 0, 8);
        box('board', 50, 60, 3, 0, 8, '#3a3050').position.y = 40;
        break;
      case 'bench_cluster':
        box('benchB', 60, 18, 20, 0,  16, '#3a3050');
        box('benchC', 40, 20, 40, 0,   0, '#46d9c5'); // central low table — accent
        break;
      case 'road_marker':
        cyl('rm_post', 4, 90, 0, 8);
        box('rm_arm', 60, 4, 4, 0, 8, '#3a3050').position.y = 80;
        box('rm_sign', 60, 20, 2, 0, 8, '#46d9c5').position.y = 70;
        break;
      case 'vendor_table':
        box('vt', 80, 22, 30, 0, 8, '#3a3050');
        box('crate1', 20, 20, 20, -25, 16, '#2a2438');
        box('crate2', 20, 20, 20, -25, 16, '#2a2438').position.y = 28;
        break;
      case 'parked_vehicle':
        buildBus(scene, x + nx * 8 + ax * 0, z + ny * 8 + ay * 0, Math.atan2(ax, ay));
        break;
      case 'viewing_platform':
        // larger pull-off + railing
        box('vp_base', 100, 8, 80, 0, 8, '#2e2a40').position.y = 8;
        box('vp_rail', 100, 12, 4, 0, 28, '#3a3050').position.y = 14;
        break;
      case 'rock_bench':
        const rock = BABYLON.MeshBuilder.CreateSphere('rock', { diameter: 25 }, scene);
        rock.scaling = new BABYLON.Vector3(1, 0.56, 0.8);
        rock.position.set(x + nx * 16 + ax * -16, 6, z + ny * 16 + ay * -16);
        rock.material = B.mat(scene, 'rockM', '#2a2832');
        break;
      case 'observation_post':
        cyl('op_post', 4, 100, 0, 16);
        box('op_top', 24, 6, 24, 0, 16, '#3a3050').position.y = 96;
        break;
      case 'covered_alcove':
        box('al_left', 10, 50, 40, -30, 16, '#2a2438');
        box('al_right', 10, 50, 40, 30, 16, '#2a2438');
        box('al_roof', 80, 4, 50, 0, 16, '#2a2438').position.y = 50;
        box('al_bench', 50, 14, 16, 0, 14, '#3a3050');
        break;
    }
    return null;
  }

  // ─── Bus geometry ─────────────────────────────────────────────────
  function buildBus(scene, x, z, heading) {
    const root = new BABYLON.TransformNode('bus_root_' + Math.random(), scene);
    root.position.set(x, 0, z);
    root.rotation.y = heading || 0;

    const body = BABYLON.MeshBuilder.CreateBox('bus_body', { width: 28, height: 24, depth: 60 }, scene);
    body.position.y = 14;
    body.parent = root;
    body.material = B.mat(scene, 'busBodyM', '#3a3050');

    const roof = BABYLON.MeshBuilder.CreateBox('bus_roof', { width: 30, height: 4, depth: 66 }, scene);
    roof.position.y = 28;
    roof.parent = root;
    roof.material = B.mat(scene, 'busRoofM', '#2a2240');

    // windshield strip
    const wsh = BABYLON.MeshBuilder.CreateBox('bus_ws', { width: 28, height: 8, depth: 1 }, scene);
    wsh.position.set(0, 18, 30);
    wsh.parent = root;
    const wshMat = B.mat(scene, 'wshM', '#6db8ff', { emissive: '#6db8ff', eIntensity: 0.2 });
    wshMat.alpha = 0.6;
    wsh.material = wshMat;

    // accent stripe
    const stripe = BABYLON.MeshBuilder.CreateBox('bus_stripe', { width: 28.5, height: 2, depth: 60 }, scene);
    stripe.position.y = 16;
    stripe.parent = root;
    stripe.material = B.mat(scene, 'stripeM', '#6db8ff', { emissive: '#6db8ff', eIntensity: 0.3 });

    // wheels
    const wMat = B.mat(scene, 'wheelM', '#1a1a22');
    for (const [wx, wz] of [[-15, 20], [15, 20], [-15, -20], [15, -20]]) {
      const w = BABYLON.MeshBuilder.CreateCylinder('bus_w', { diameter: 10, height: 6 }, scene);
      w.rotation.z = Math.PI / 2;
      w.position.set(wx, 5, wz);
      w.parent = root;
      w.material = wMat;
    }

    return root;
  }

  // ─── Stations ─────────────────────────────────────────────────────
  function buildStations(scene) {
    const out = [];
    for (const st of W.STATIONS) {
      const root = new BABYLON.TransformNode('st_root_' + st.id, scene);
      root.position.set(st.x, 0, st.y);
      root.rotation.y = st.heading || 0;

      // platform
      const plat = BABYLON.MeshBuilder.CreateBox('plat_' + st.id, { width: 300, height: 8, depth: 100 }, scene);
      plat.position.y = 4;
      plat.parent = root;
      plat.material = B.mat(scene, 'platM_' + st.id, '#2e2a3c');

      // 4 columns
      const colMat = B.mat(scene, 'colM_' + st.id, '#2a2438');
      for (const [cx, cz] of [[-90, -35], [90, -35], [-90, 35], [90, 35]]) {
        const c = BABYLON.MeshBuilder.CreateCylinder('col_' + st.id, { diameter: 6, height: 50 }, scene);
        c.position.set(cx, 33, cz);
        c.parent = root;
        c.material = colMat;
      }

      // roof
      const roof = BABYLON.MeshBuilder.CreateBox('roof_' + st.id, { width: 200, height: 4, depth: 80 }, scene);
      roof.position.y = 60;
      roof.parent = root;
      roof.material = B.mat(scene, 'roofM_' + st.id, '#1f1c2a');

      // gate posts
      const gpMat = B.mat(scene, 'gpM_' + st.id, '#2a2438');
      const gp1 = BABYLON.MeshBuilder.CreateBox('gp1_' + st.id, { width: 12, height: 80, depth: 12 }, scene);
      gp1.position.set(-50, 40, -30);
      gp1.parent = root; gp1.material = gpMat;
      const gp2 = BABYLON.MeshBuilder.CreateBox('gp2_' + st.id, { width: 12, height: 80, depth: 12 }, scene);
      gp2.position.set(50, 40, -30);
      gp2.parent = root; gp2.material = gpMat;
      const gpBar = BABYLON.MeshBuilder.CreateBox('gpb_' + st.id, { width: 112, height: 6, depth: 12 }, scene);
      gpBar.position.set(0, 76, -30);
      gpBar.parent = root; gpBar.material = gpMat;

      // gate panel
      const gate = BABYLON.MeshBuilder.CreateBox('gate_' + st.id, { width: 100, height: 60, depth: 2 }, scene);
      gate.position.set(0, 34, -30);
      gate.parent = root;
      const gMat = B.mat(scene, 'gateM_' + st.id, '#0a0c12', { emissive: '#0a0c12', eIntensity: 0 });
      gMat.alpha = 0.85;
      gate.material = gMat;

      // CTA panel (texture)
      const ctaTex = new BABYLON.DynamicTexture('ctaT_' + st.id, { width: 512, height: 256 }, scene, true);
      ctaTex.hasAlpha = false;
      const c2 = ctaTex.getContext();
      c2.fillStyle = '#0a0c12';
      c2.fillRect(0, 0, 512, 256);
      c2.strokeStyle = '#46d9c5';
      c2.lineWidth = 4;
      c2.strokeRect(8, 8, 496, 240);
      c2.font = '600 36px ui-monospace, Menlo, monospace';
      c2.fillStyle = '#46d9c5';
      c2.textAlign = 'center';
      c2.fillText(st.label, 256, 72);
      c2.font = '500 22px ui-monospace, Menlo, monospace';
      c2.fillStyle = '#b9c4e0';
      c2.fillText('Full access in Simutum', 256, 128);
      c2.font = '600 24px ui-monospace, Menlo, monospace';
      c2.fillStyle = '#46d9c5';
      c2.fillText('[  Enter Now  ]', 256, 200);
      ctaTex.update();
      const ctaMat = new BABYLON.StandardMaterial('ctaM_' + st.id, scene);
      ctaMat.diffuseTexture = ctaTex;
      ctaMat.emissiveTexture = ctaTex;
      ctaMat.specularColor = new BABYLON.Color3(0, 0, 0);
      ctaMat.disableLighting = true;
      const ctaPlane = BABYLON.MeshBuilder.CreatePlane('ctaP_' + st.id, { width: 80, height: 40 }, scene);
      ctaPlane.position.set(0, 34, -28.8);
      ctaPlane.parent = root;
      ctaPlane.material = ctaMat;

      // hint of destination geometry "through the gate"
      buildPackHint(scene, root, st.target_pack);

      out.push({ id: st.id, root });
    }
    return out;
  }

  function buildPackHint(scene, parent, kind) {
    if (kind === 'theater') {
      // rows of seat boxes
      for (let r = 0; r < 5; r++) {
        for (let s = 0; s < 8; s++) {
          const seat = BABYLON.MeshBuilder.CreateBox('hint_seat', { width: 10, height: 6, depth: 8 }, scene);
          seat.position.set(-40 + s * 12, 7, -80 - r * 14);
          seat.parent = parent;
          seat.material = B.mat(scene, 'hintM_theater', '#1a1a2e');
        }
      }
      const stage = BABYLON.MeshBuilder.CreateBox('hint_stage', { width: 120, height: 4, depth: 30 }, scene);
      stage.position.set(0, 6, -180);
      stage.parent = parent;
      stage.material = B.mat(scene, 'hintM_theater_s', '#1a1a2e');
    } else if (kind === 'bar') {
      const counter = BABYLON.MeshBuilder.CreateBox('hint_counter', { width: 100, height: 12, depth: 20 }, scene);
      counter.position.set(0, 10, -100);
      counter.parent = parent;
      counter.material = B.mat(scene, 'hintM_bar', '#1e1a1a');
      const counter2 = BABYLON.MeshBuilder.CreateBox('hint_counter2', { width: 20, height: 12, depth: 60 }, scene);
      counter2.position.set(40, 10, -130);
      counter2.parent = parent;
      counter2.material = counter.material;
      for (let i = 0; i < 5; i++) {
        const st = BABYLON.MeshBuilder.CreateCylinder('hint_stool', { diameter: 8, height: 16 }, scene);
        st.position.set(-40 + i * 20, 8, -78);
        st.parent = parent;
        st.material = B.mat(scene, 'hintM_bar_s', '#1e1a1a');
      }
    } else if (kind === 'lab') {
      // benches + flask cylinders
      const bench = BABYLON.MeshBuilder.CreateBox('hint_bench', { width: 80, height: 6, depth: 20 }, scene);
      bench.position.set(0, 5, -90);
      bench.parent = parent;
      bench.material = B.mat(scene, 'hintM_lab', '#181e1a');
      for (let i = 0; i < 4; i++) {
        const fl = BABYLON.MeshBuilder.CreateCylinder('hint_flask', { diameterTop: 4, diameterBottom: 10, height: 14 }, scene);
        fl.position.set(-30 + i * 20, 14, -90);
        fl.parent = parent;
        fl.material = B.mat(scene, 'hintM_lab_f', '#181e1a');
      }
    }
  }

  // ─── Ghost packs in the void ──────────────────────────────────────
  function buildGhostPacks(scene) {
    for (const g of W.GHOST_PACKS) {
      const root = new BABYLON.TransformNode('ghost_' + g.id, scene);
      root.position.set(g.x, 0, g.y);
      // single silhouette base
      const base = BABYLON.MeshBuilder.CreateGround('gbase_' + g.id, { width: g.w, height: g.h }, scene);
      base.position.set(g.x, 0.05, g.y);
      base.material = B.mat(scene, 'gbaseM_' + g.id, g.color);
      base.material.specularColor = new BABYLON.Color3(0, 0, 0);
      // a few shape stubs
      if (g.kind === 'theater') {
        for (let r = 0; r < 4; r++) {
          for (let s = 0; s < 10; s++) {
            const box = BABYLON.MeshBuilder.CreateBox('gx', { width: 8, height: 6, depth: 8 }, scene);
            box.position.set(g.x - 40 + s * 9, 4, g.y - 30 + r * 12);
            box.material = B.mat(scene, 'gxM_' + g.id, g.color);
          }
        }
      } else if (g.kind === 'bar') {
        const counter = BABYLON.MeshBuilder.CreateBox('gbarc', { width: 100, height: 10, depth: 20 }, scene);
        counter.position.set(g.x, 6, g.y);
        counter.material = B.mat(scene, 'gbarcM_' + g.id, g.color);
        for (let i = 0; i < 5; i++) {
          const st = BABYLON.MeshBuilder.CreateCylinder('gbst', { diameter: 6, height: 12 }, scene);
          st.position.set(g.x - 40 + i * 20, 6, g.y + 25);
          st.material = counter.material;
        }
      } else if (g.kind === 'field') {
        // irregular rocks + bench line
        for (let i = 0; i < 6; i++) {
          const r = BABYLON.MeshBuilder.CreateSphere('grck', { diameter: 30 }, scene);
          r.scaling = new BABYLON.Vector3(1, 0.4, 0.7);
          r.position.set(g.x - 100 + i * 40 + Math.sin(i) * 30, 8, g.y - 80 + Math.cos(i) * 40);
          r.material = B.mat(scene, 'grckM', g.color);
        }
        const bench = BABYLON.MeshBuilder.CreateBox('gfb', { width: 80, height: 5, depth: 12 }, scene);
        bench.position.set(g.x, 4, g.y + 80);
        bench.material = B.mat(scene, 'gfbM', g.color);
      }
    }
  }

  // ─── Boundary walls + invisible easter eggs ──────────────────────
  function buildBoundary(scene) {
    const eggs = [];
    for (const e of W.EGGS) {
      // Container starts hidden — flares when player reveals it
      const root = new BABYLON.TransformNode('egg_root_' + e.id, scene);
      root.position.set(e.x, 0, e.y);
      // base
      const base = BABYLON.MeshBuilder.CreateBox('egg_base_' + e.id, { width: 40, height: 6, depth: 40 }, scene);
      base.position.y = 3;
      base.parent = root;
      base.material = B.mat(scene, 'eggBaseM_' + e.id, '#1a2e1a');
      base.isVisible = false;

      // post
      const post = BABYLON.MeshBuilder.CreateCylinder('egg_post_' + e.id, { diameter: 4, height: 30 }, scene);
      post.position.y = 18;
      post.parent = root;
      post.material = B.mat(scene, 'eggPostM_' + e.id, '#1a2e1a');
      post.isVisible = false;

      // screen
      const screen = BABYLON.MeshBuilder.CreatePlane('egg_screen_' + e.id, { width: 30, height: 40 }, scene);
      screen.position.y = 36;
      // face inward
      const inwardAngle = Math.atan2(-e.x, -e.y);
      screen.rotation.y = inwardAngle;
      screen.parent = root;
      const scrMat = new BABYLON.StandardMaterial('eggScrM_' + e.id, scene);
      scrMat.diffuseColor = new BABYLON.Color3(0, 0.05, 0.02);
      scrMat.emissiveColor = new BABYLON.Color3(0, 1, 0.25);
      scrMat.specularColor = new BABYLON.Color3(0, 0, 0);
      scrMat.disableLighting = true;
      screen.material = scrMat;
      screen.isVisible = false;

      // pool
      const pool = BABYLON.MeshBuilder.CreateDisc('egg_pool_' + e.id, { radius: 40, tessellation: 32 }, scene);
      pool.rotation.x = Math.PI / 2;
      pool.position.y = 0.2;
      pool.parent = root;
      const poolMat = new BABYLON.StandardMaterial('eggPoolM_' + e.id, scene);
      poolMat.diffuseColor = new BABYLON.Color3(0, 0.1, 0.04);
      poolMat.emissiveColor = new BABYLON.Color3(0, 0.7, 0.18);
      poolMat.alpha = 0.4;
      poolMat.specularColor = new BABYLON.Color3(0, 0, 0);
      poolMat.disableLighting = true;
      pool.material = poolMat;
      pool.isVisible = false;

      const pl = new BABYLON.PointLight('eggPL_' + e.id, new BABYLON.Vector3(e.x, 30, e.y), scene);
      pl.diffuse = new BABYLON.Color3(0, 1, 0.25);
      pl.intensity = 0;
      pl.range = 280;

      eggs.push({
        id: e.id, face: e.face, x: e.x, y: e.y,
        root, base, post, screen, pool, pl,
        revealed: false,
        reveal() {
          this.revealed = true;
          this.base.isVisible = true;
          this.post.isVisible = true;
          this.screen.isVisible = true;
          this.pool.isVisible = true;
          this.pl.intensity = 0.8;
        },
      });
    }
    return eggs;
  }

  window.SIMUTUM_STOPS = {
    buildStops, buildStations, buildGhostPacks, buildBoundary,
  };
})();
