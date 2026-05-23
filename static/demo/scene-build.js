// scene-build.js — builds the 3D world geometry into a Babylon scene.
// Pure construction: no animation, no AI, no audio. Returns handles
// the runtime can poke (traffic lights, eggs, lamp materials, etc.).

(function () {
  'use strict';

  const W = window.SIMUTUM_WORLD;

  // ─── Color helpers ────────────────────────────────────────────────
  const C = (hex) => BABYLON.Color3.FromHexString(hex);
  const C4 = (hex, a) => { const c = C(hex); return new BABYLON.Color4(c.r, c.g, c.b, a == null ? 1 : a); };

  function mat(scene, name, hex, opts) {
    const m = new BABYLON.StandardMaterial(name, scene);
    m.diffuseColor = C(hex);
    m.specularColor = new BABYLON.Color3(0.04, 0.04, 0.06);
    if (opts && opts.emissive) m.emissiveColor = C(opts.emissive).scale(opts.eIntensity || 1);
    if (opts && opts.alpha != null) m.alpha = opts.alpha;
    return m;
  }

  // ─── Build map sections ───────────────────────────────────────────
  function buildSections(scene) {
    const out = { meshes: [], labels: [] };

    for (const s of W.SECTIONS) {
      // floor plane
      const floor = BABYLON.MeshBuilder.CreateGround('floor_' + s.id, { width: s.w, height: s.h, subdivisions: 1 }, scene);
      floor.position.set(s.x, 0.1 + (s.raised || 0), s.y);
      const fm = mat(scene, 'fm_' + s.id, s.floor_color);
      fm.specularColor = new BABYLON.Color3(0, 0, 0);
      floor.material = fm;
      out.meshes.push(floor);

      // raised platform (Boswell)
      if (s.raised) {
        const plat = BABYLON.MeshBuilder.CreateBox('plat_' + s.id, { width: s.w + 4, height: s.raised, depth: s.h + 4 }, scene);
        plat.position.set(s.x, s.raised / 2, s.y);
        plat.material = mat(scene, 'platm_' + s.id, '#252230');
        out.meshes.push(plat);
      }

      // accent — octagon tile pattern in the Square
      if (s.accent === 'octagon') {
        for (let i = 0; i < 3; i++) {
          const ring = BABYLON.MeshBuilder.CreateDisc('sq_ring_' + i, { radius: 30 + i * 28, tessellation: 8, sideOrientation: BABYLON.Mesh.DOUBLESIDE }, scene);
          ring.rotation.x = Math.PI / 2;
          ring.position.set(s.x, 0.15 + i * 0.02, s.y);
          const rm = mat(scene, 'sqring_' + i, '#46d9c5');
          rm.alpha = 0.06 - i * 0.015;
          rm.emissiveColor = C('#46d9c5').scale(0.12);
          rm.specularColor = new BABYLON.Color3(0, 0, 0);
          ring.material = rm;
          out.meshes.push(ring);
        }
      }

      // walls
      if (s.walled === true || s.walled === 'partial') {
        const wallH = s.walled === 'partial' ? 26 : 60;
        const wallT = 4;
        const wallMat = mat(scene, 'wm_' + s.id, '#2a2438');
        wallMat.specularColor = new BABYLON.Color3(0, 0, 0);

        const sides = [
          { name: 'north', isH: true,  x: s.x,            z: s.y + s.h / 2, w: s.w, d: wallT },
          { name: 'south', isH: true,  x: s.x,            z: s.y - s.h / 2, w: s.w, d: wallT },
          { name: 'west',  isH: false, x: s.x - s.w / 2,  z: s.y,           w: wallT, d: s.h },
          { name: 'east',  isH: false, x: s.x + s.w / 2,  z: s.y,           w: wallT, d: s.h },
        ];
        // For "partial" walls, drop the side that faces the Square (east for west-zones, west for east-zones)
        const dropSides = new Set();
        if (s.walled === 'partial') {
          // pick side facing the square (closer to x=0)
          if (s.x < 0) dropSides.add('east');
          else if (s.x > 0) dropSides.add('west');
          else dropSides.add('north');
        }
        // boswell — open all sides; not walled anyway.

        for (const side of sides) {
          if (dropSides.has(side.name)) continue;
          // door?
          if (s.door && s.door.side === side.name && s.walled === true) {
            const gw = s.door.width;
            // door on a horizontal side splits along x; on vertical along z
            if (side.isH) {
              const halfRem = (side.w - gw) / 2;
              if (halfRem > 1) {
                const l = BABYLON.MeshBuilder.CreateBox('wall_' + s.id + '_' + side.name + '_L', { width: halfRem, height: wallH, depth: wallT }, scene);
                l.position.set(side.x - (gw / 2 + halfRem / 2), wallH / 2, side.z);
                l.material = wallMat;
                const r = BABYLON.MeshBuilder.CreateBox('wall_' + s.id + '_' + side.name + '_R', { width: halfRem, height: wallH, depth: wallT }, scene);
                r.position.set(side.x + (gw / 2 + halfRem / 2), wallH / 2, side.z);
                r.material = wallMat;
              }
            } else {
              const halfRem = (side.d - gw) / 2;
              if (halfRem > 1) {
                const l = BABYLON.MeshBuilder.CreateBox('wall_' + s.id + '_' + side.name + '_L', { width: wallT, height: wallH, depth: halfRem }, scene);
                l.position.set(side.x, wallH / 2, side.z - (gw / 2 + halfRem / 2));
                l.material = wallMat;
                const r = BABYLON.MeshBuilder.CreateBox('wall_' + s.id + '_' + side.name + '_R', { width: wallT, height: wallH, depth: halfRem }, scene);
                r.position.set(side.x, wallH / 2, side.z + (gw / 2 + halfRem / 2));
                r.material = wallMat;
              }
            }
          } else {
            const wall = BABYLON.MeshBuilder.CreateBox('wall_' + s.id + '_' + side.name, { width: side.w, height: wallH, depth: side.d }, scene);
            wall.position.set(side.x, wallH / 2, side.z);
            wall.material = wallMat;
          }
        }
      }

      // section label — floating monospace
      const tex = new BABYLON.DynamicTexture('lblTex_' + s.id, { width: 512, height: 64 }, scene, true);
      tex.hasAlpha = true;
      const ctx = tex.getContext();
      ctx.clearRect(0, 0, 512, 64);
      ctx.font = '600 32px ui-monospace, Menlo, monospace';
      ctx.fillStyle = 'rgba(184,196,224,0.85)';
      ctx.textAlign = 'center';
      ctx.fillText(s.label.toUpperCase(), 256, 42);
      tex.update();
      const lblMat = new BABYLON.StandardMaterial('lblMat_' + s.id, scene);
      lblMat.diffuseTexture = tex;
      lblMat.emissiveTexture = tex;
      lblMat.opacityTexture = tex;
      lblMat.disableLighting = true;
      lblMat.specularColor = new BABYLON.Color3(0, 0, 0);
      const labelPlane = BABYLON.MeshBuilder.CreatePlane('lblP_' + s.id, { width: s.label.length * 4 + 30, height: 8 }, scene);
      labelPlane.position.set(s.x, 70, s.y);
      labelPlane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_Y;
      labelPlane.material = lblMat;
      out.labels.push(labelPlane);

      // PROPS per zone — primitive boxes/cylinders per brief §1
      buildProps(scene, s, out);
    }
    return out;
  }

  function buildProps(scene, s, out) {
    const furn = mat(scene, 'furn_' + s.id, '#3a3050');
    const accent = mat(scene, 'acc_' + s.id, '#4a3e68');

    function box(name, w, h, d, x, y, z, m) {
      const b = BABYLON.MeshBuilder.CreateBox(name, { width: w, height: h, depth: d }, scene);
      b.position.set(s.x + x, (s.raised || 0) + h / 2 + 0.2, s.y + z);
      b.material = m || furn;
      out.meshes.push(b);
      return b;
    }
    function cyl(name, diam, h, x, z) {
      const c = BABYLON.MeshBuilder.CreateCylinder(name, { diameter: diam, height: h }, scene);
      c.position.set(s.x + x, h / 2, s.y + z);
      c.material = furn;
      out.meshes.push(c);
      return c;
    }

    switch (s.id) {
      case 'the_square':
        // 4 standing-height pillar-tables at corners
        [[-95, 70], [95, 70], [-95, -70], [95, -70]].forEach((p, i) =>
          box('sq_pillar_' + i, 8, 28, 8, p[0], 0, p[1])
        );
        break;
      case 'frank_office':
        box('frank_desk_a', 90, 26, 30, 0, 0, 30);
        box('frank_desk_b', 30, 26, 60, -30, 0, 0);
        box('frank_credenza', 120, 18, 20, 0, 0, 60);
        box('frank_meet', 60, 24, 40, 40, 0, -30);
        box('frank_stool1', 12, 16, 12, 40, 0, -55);
        box('frank_stool2', 12, 16, 12, 60, 0, -55);
        break;
      case 'max_writers':
        box('max_table', 160, 26, 40, 0, 0, 0);
        for (let i = -2; i <= 2; i++) {
          box('max_chair_n_' + i, 16, 20, 16, i * 30, 0, 28);
          box('max_chair_s_' + i, 16, 20, 16, i * 30, 0, -28);
        }
        box('max_cork', 200, 60, 4, 0, 0, 58);
        cyl('max_lamp_post', 4, 60, 96, 0);
        const cap = BABYLON.MeshBuilder.CreateSphere('max_lamp_cap', { diameter: 8 }, scene);
        cap.position.set(s.x + 96, 60, s.y);
        const capMat = mat(scene, 'max_lampMat', '#ffd9a0', { emissive: '#ffd9a0', eIntensity: 0.8 });
        cap.material = capMat;
        out.meshes.push(cap);
        break;
      case 'florence_analysis':
        // triangle of pods
        [[0, 60], [-50, -30], [50, -30]].forEach((p, i) => {
          box('flo_desk_' + i, 60, 26, 35, p[0], 0, p[1]);
          box('flo_chair_' + i, 14, 18, 14, p[0], 0, p[1] - 22);
        });
        box('flo_shelf', 16, 40, 140, 70, 0, 0);
        break;
      case 'pat_audit':
        box('pat_desk', 70, 26, 35, 0, 0, 30);
        box('pat_files1', 20, 50, 20, -40, 0, 30);
        box('pat_files2', 20, 50, 20, 40, 0, 30);
        box('pat_shelf', 16, 40, 80, 50, 0, -10);
        break;
      case 'boswell_desk':
        box('bos_desk', 80, 26, 40, 0, 0, 0);
        box('bos_chair', 14, 18, 14, 0, 0, -25);
        box('bos_archive', 80, 50, 16, 0, 0, 32);
        break;
      case 'design_studio':
        // L-shape: arm A east, arm B west — one drafting table + 2 panels
        box('des_draft', 140, 22, 60, 50, 0, 0);
        box('des_stool1', 14, 18, 14, 0, 0, -22);
        box('des_stool2', 14, 18, 14, 100, 0, -22);
        // pin-up wall panels along south edge
        box('des_panel1', 100, 70, 4, -55, 0, -65, accent);
        box('des_panel2', 100, 70, 4, 60,  0, -65, accent);
        // floor tile shift for arm B (a subtle different square)
        const armB = BABYLON.MeshBuilder.CreateGround('armB', { width: 90, height: 130 }, scene);
        armB.position.set(s.x - 70, 0.18, s.y);
        const armBMat = mat(scene, 'armBMat', '#1a1824');
        armBMat.specularColor = new BABYLON.Color3(0, 0, 0);
        armB.material = armBMat;
        out.meshes.push(armB);
        break;
    }
  }

  // ─── Build curved ribbon mesh from a road curve ──────────────────
  function buildRoadRibbon(scene, road, opts) {
    opts = opts || {};
    const segs = 48;
    const halfW = road.width / 2;
    const sidewalkW = 20;
    const positions = [];
    const indices = [];
    const swPositions = [[], []]; // left, right sidewalks
    const swIndices = [[], []];
    const centerline = [];

    for (let i = 0; i <= segs; i++) {
      const t = i / segs;
      const p = road.curve.at(t);
      const tg = road.curve.tangent(t);
      const tl = Math.hypot(tg.x, tg.y) || 1;
      // perpendicular (left of forward)
      const nx = -tg.y / tl;
      const ny = tg.x / tl;
      const yLift = 0.2;

      // road surface
      positions.push(p.x + nx * halfW, yLift, p.y + ny * halfW);
      positions.push(p.x - nx * halfW, yLift, p.y - ny * halfW);
      centerline.push({ x: p.x, y: p.y, hx: tg.x / tl, hy: tg.y / tl });

      // sidewalks
      const swH = 4;
      swPositions[0].push(p.x + nx * halfW,            swH, p.y + ny * halfW);
      swPositions[0].push(p.x + nx * (halfW + sidewalkW), swH, p.y + ny * (halfW + sidewalkW));
      swPositions[1].push(p.x - nx * (halfW + sidewalkW), swH, p.y - ny * (halfW + sidewalkW));
      swPositions[1].push(p.x - nx * halfW,            swH, p.y - ny * halfW);

      if (i < segs) {
        const a = i * 2, b = i * 2 + 1, c = (i + 1) * 2, d = (i + 1) * 2 + 1;
        indices.push(a, b, c, b, d, c);
        swIndices[0].push(a, b, c, b, d, c);
        swIndices[1].push(a, b, c, b, d, c);
      }
    }

    function makeMesh(name, pos, idx, hex) {
      const m = new BABYLON.Mesh(name, scene);
      const vd = new BABYLON.VertexData();
      vd.positions = pos;
      vd.indices = idx;
      const normals = [];
      BABYLON.VertexData.ComputeNormals(pos, idx, normals);
      vd.normals = normals;
      vd.applyToMesh(m);
      m.material = mat(scene, name + 'M', hex);
      m.material.specularColor = new BABYLON.Color3(0, 0, 0);
      return m;
    }

    const roadMesh = makeMesh('road_' + road.id, positions, indices, '#1a1a22');
    const sw0 = makeMesh('sw0_' + road.id, swPositions[0].flat ? swPositions[0] : swPositions[0], swIndices[0], '#252232');
    const sw1 = makeMesh('sw1_' + road.id, swPositions[1], swIndices[1], '#252232');

    // center stripe — thin ribbon at y=0.3
    const stripePositions = [];
    const stripeIndices = [];
    for (let i = 0; i <= segs; i++) {
      const t = i / segs;
      const p = road.curve.at(t);
      const tg = road.curve.tangent(t);
      const tl = Math.hypot(tg.x, tg.y) || 1;
      const nx = -tg.y / tl, ny = tg.x / tl;
      stripePositions.push(p.x + nx * 0.6, 0.32, p.y + ny * 0.6);
      stripePositions.push(p.x - nx * 0.6, 0.32, p.y - ny * 0.6);
      if (i < segs) {
        const a = i * 2, b = i * 2 + 1, c = (i + 1) * 2, d = (i + 1) * 2 + 1;
        // dashed: only every other segment
        if (i % 2 === 0) stripeIndices.push(a, b, c, b, d, c);
      }
    }
    makeMesh('stripe_' + road.id, stripePositions, stripeIndices, '#3e3a52');

    return { roadMesh, centerline };
  }

  // ─── Build ring road (closed loop) ────────────────────────────────
  function buildRing(scene, radius, width) {
    const segs = 96;
    const halfW = width / 2;
    const swW = 16;
    const yLift = 0.2;
    const positions = [];
    const indices = [];
    const sw0Pos = [], sw0Idx = [];
    const sw1Pos = [], sw1Idx = [];
    for (let i = 0; i <= segs; i++) {
      const a = (i / segs) * Math.PI * 2;
      const cx = Math.cos(a), cz = Math.sin(a);
      positions.push((radius + halfW) * cx, yLift, (radius + halfW) * cz);
      positions.push((radius - halfW) * cx, yLift, (radius - halfW) * cz);
      sw0Pos.push((radius + halfW) * cx, 4, (radius + halfW) * cz);
      sw0Pos.push((radius + halfW + swW) * cx, 4, (radius + halfW + swW) * cz);
      sw1Pos.push((radius - halfW - swW) * cx, 4, (radius - halfW - swW) * cz);
      sw1Pos.push((radius - halfW) * cx, 4, (radius - halfW) * cz);
      if (i < segs) {
        const A = i * 2, B = i * 2 + 1, Cc = (i + 1) * 2, D = (i + 1) * 2 + 1;
        indices.push(A, B, Cc, B, D, Cc);
        sw0Idx.push(A, B, Cc, B, D, Cc);
        sw1Idx.push(A, B, Cc, B, D, Cc);
      }
    }
    function ribbon(name, pos, idx, hex) {
      const m = new BABYLON.Mesh(name, scene);
      const vd = new BABYLON.VertexData();
      vd.positions = pos; vd.indices = idx;
      const normals = []; BABYLON.VertexData.ComputeNormals(pos, idx, normals);
      vd.normals = normals;
      vd.applyToMesh(m);
      const mt = mat(scene, name + 'M', hex);
      mt.specularColor = new BABYLON.Color3(0, 0, 0);
      m.material = mt;
      return m;
    }
    ribbon('ring_road', positions, indices, '#1a1a22');
    ribbon('ring_sw_out', sw0Pos, sw0Idx, '#252232');
    ribbon('ring_sw_in', sw1Pos, sw1Idx, '#252232');
  }

  // ─── Street lamps along a road ────────────────────────────────────
  function buildLampsAlong(scene, road, every) {
    every = every || 200;
    const len = road.curve.length();
    const count = Math.max(2, Math.floor(len / every));
    const lamps = [];
    for (let i = 1; i < count; i++) {
      const t = i / count;
      const p = road.curve.at(t);
      const tg = road.curve.tangent(t);
      const tl = Math.hypot(tg.x, tg.y) || 1;
      const nx = -tg.y / tl, ny = tg.x / tl;
      const sideX = p.x + nx * 55;
      const sideZ = p.y + ny * 55;
      lamps.push(buildLamp(scene, sideX, sideZ, '#ffd9a0', 0.6));
    }
    return lamps;
  }

  function buildLamp(scene, x, z, colorHex, intensity) {
    const post = BABYLON.MeshBuilder.CreateCylinder('lamp_post', { diameter: 4, height: 70 }, BABYLON.Engine.LastCreatedScene);
    post.position.set(x, 35, z);
    post.material = mat(scene, 'lampPostM', '#1a1a22');
    const arm = BABYLON.MeshBuilder.CreateBox('lamp_arm', { width: 20, height: 2, depth: 2 }, scene);
    arm.position.set(x + 10, 66, z);
    arm.material = post.material;
    const cap = BABYLON.MeshBuilder.CreateSphere('lamp_cap', { diameter: 6 }, scene);
    cap.position.set(x + 18, 64, z);
    const capMat = new BABYLON.StandardMaterial('lampCapM', scene);
    capMat.diffuseColor = C(colorHex);
    capMat.emissiveColor = C(colorHex).scale(intensity || 0.6);
    capMat.specularColor = new BABYLON.Color3(0, 0, 0);
    cap.material = capMat;

    // small point light, weak
    const pl = new BABYLON.PointLight('pl_' + Math.random(), new BABYLON.Vector3(x + 18, 60, z), scene);
    pl.diffuse = C(colorHex);
    pl.intensity = 0.35 * (intensity || 0.6);
    pl.range = 140;

    return { post, cap, capMat, pl };
  }

  window.SIMUTUM_BUILD = {
    buildSections, buildRoadRibbon, buildRing, buildLampsAlong, buildLamp,
    mat, C, C4,
  };
})();
