// scene-entities.js — autonomous entity AI + traffic lights.
//
// Entities are NOT scripted. Each tick they (a) pick a destination from
// places that match their current "interest", (b) walk there along the
// nearest path (zone interior → corridor → road), (c) pause to "think"
// for a randomized dwell, (d) pick a new interest based on personality.
//
// Output: an array of agents with .update(dt) and .mesh handles.

(function () {
  'use strict';

  const W = window.SIMUTUM_WORLD;
  const B = window.SIMUTUM_BUILD;
  const C = B.C;

  // ─── Avatar geometry per type (Anchor / Thinker / Creative) ──────
  function buildAvatar(scene, name, hex, type) {
    const root = new BABYLON.TransformNode('av_' + name, scene);
    const headHex = hex;
    const bodyHex = darken(hex, 0.4, 0.3);

    let body, neck, head, totalH;
    if (type === 'anchor') {
      head = BABYLON.MeshBuilder.CreateSphere('head_' + name, { diameter: 14, segments: 12 }, scene);
      head.scaling = new BABYLON.Vector3(1, 0.78, 1);
      neck = BABYLON.MeshBuilder.CreateCylinder('neck_' + name, { diameter: 5, height: 5 }, scene);
      body = BABYLON.MeshBuilder.CreateCylinder('body_' + name, { diameter: 11, height: 14 }, scene);
      totalH = 35;
      body.position.y = 7;
      neck.position.y = 14 + 2.5;
      head.position.y = 14 + 5 + 14 * 0.78 / 2;
    } else if (type === 'thinker') {
      head = BABYLON.MeshBuilder.CreateSphere('head_' + name, { diameter: 13, segments: 12 }, scene);
      head.scaling = new BABYLON.Vector3(1, 1.15, 1);
      neck = BABYLON.MeshBuilder.CreateCylinder('neck_' + name, { diameter: 4, height: 7 }, scene);
      body = BABYLON.MeshBuilder.CreateCylinder('body_' + name, { diameter: 9, height: 18 }, scene);
      totalH = 42;
      body.position.y = 9;
      neck.position.y = 18 + 3.5;
      head.position.y = 18 + 7 + 13 * 1.15 / 2;
    } else { // creative
      head = BABYLON.MeshBuilder.CreateSphere('head_' + name, { diameter: 14, segments: 12 }, scene);
      neck = BABYLON.MeshBuilder.CreateCylinder('neck_' + name, { diameter: 5, height: 6 }, scene);
      // tapered: cone-ish via two cylinders blended visually
      body = BABYLON.MeshBuilder.CreateCylinder('body_' + name, { diameterTop: 8, diameterBottom: 11, height: 16 }, scene);
      totalH = 38;
      body.position.y = 8;
      neck.position.y = 16 + 3;
      head.position.y = 16 + 6 + 7;
      head.position.z = 2;
      const torus = BABYLON.MeshBuilder.CreateTorus('torus_' + name, { diameter: 14, thickness: 1.5, tessellation: 24 }, scene);
      torus.position.y = 10;
      torus.parent = root;
      const trMat = B.mat(scene, 'trM_' + name, hex, { emissive: hex, eIntensity: 0.4 });
      torus.material = trMat;
    }

    const headMat = B.mat(scene, 'hM_' + name, headHex, { emissive: hex, eIntensity: 0.25 });
    const bodyMat = B.mat(scene, 'bM_' + name, bodyHex);
    head.material = headMat;
    neck.material = bodyMat;
    body.material = bodyMat;
    head.parent = root; neck.parent = root; body.parent = root;

    // name label
    const tex = new BABYLON.DynamicTexture('avTex_' + name, { width: 256, height: 64 }, scene, true);
    tex.hasAlpha = true;
    const ctx = tex.getContext();
    ctx.clearRect(0, 0, 256, 64);
    ctx.font = '700 32px ui-monospace, Menlo, monospace';
    ctx.fillStyle = hex;
    ctx.textAlign = 'center';
    ctx.fillText(name.toUpperCase(), 128, 42);
    tex.update();
    const lblMat = new BABYLON.StandardMaterial('avLM_' + name, scene);
    lblMat.diffuseTexture = tex;
    lblMat.emissiveTexture = tex;
    lblMat.opacityTexture = tex;
    lblMat.disableLighting = true;
    lblMat.specularColor = new BABYLON.Color3(0, 0, 0);
    const lblPlane = BABYLON.MeshBuilder.CreatePlane('avLP_' + name, { width: 28, height: 7 }, scene);
    lblPlane.position.y = totalH + 14;
    lblPlane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
    lblPlane.material = lblMat;
    lblPlane.parent = root;

    return { root, head, body, neck, totalH, labelPlane: lblPlane };
  }

  function darken(hex, satFac, lumFac) {
    const c = BABYLON.Color3.FromHexString(hex);
    // convert to HSV
    let max = Math.max(c.r, c.g, c.b), min = Math.min(c.r, c.g, c.b);
    let v = max, d = max - min, s = max === 0 ? 0 : d / max;
    let h = 0;
    if (d !== 0) {
      if (max === c.r) h = ((c.g - c.b) / d) % 6;
      else if (max === c.g) h = (c.b - c.r) / d + 2;
      else h = (c.r - c.g) / d + 4;
    }
    h *= 60; if (h < 0) h += 360;
    s = Math.max(0, s * (1 - satFac));
    v = Math.max(0, v * (1 - lumFac));
    // HSV → RGB
    const C2 = v * s, X = C2 * (1 - Math.abs(((h / 60) % 2) - 1)), m = v - C2;
    let r = 0, g = 0, b = 0;
    if (h < 60) { r = C2; g = X; }
    else if (h < 120) { r = X; g = C2; }
    else if (h < 180) { g = C2; b = X; }
    else if (h < 240) { g = X; b = C2; }
    else if (h < 300) { r = X; b = C2; }
    else { r = C2; b = X; }
    const toHex = (v) => Math.round((v + m) * 255).toString(16).padStart(2, '0');
    return '#' + toHex(r) + toHex(g) + toHex(b);
  }

  // ─── Destination registry ─────────────────────────────────────────
  // What an agent might decide to do. Each destination has a category
  // and a world position. The agent picks based on its current interest.
  function buildDestinations(world, stops, intersections) {
    const dests = [];

    // Office spawn points (the zone they came from)
    for (const s of W.SECTIONS) {
      dests.push({ id: s.id, category: 'office', x: s.x, z: s.y, label: s.label });
    }
    // Square corners (gathering spot)
    dests.push({ id: 'square_center', category: 'square', x: 0, z: 0 });
    dests.push({ id: 'square_n', category: 'square', x: 0, z: 60 });
    dests.push({ id: 'square_s', category: 'square', x: 0, z: -60 });
    dests.push({ id: 'square_e', category: 'square', x: 70, z: 0 });
    dests.push({ id: 'square_w', category: 'square', x: -70, z: 0 });

    // Road stops
    for (const stop of stops) {
      dests.push({
        id: stop.id, category: 'stop',
        x: stop.position.x, z: stop.position.z,
        lighting: stop.lighting,
      });
    }

    // Ring road intersections
    for (const ix of intersections) {
      dests.push({ id: ix.id, category: 'intersection', x: ix.x, z: ix.y });
    }

    // Boundary survey points (Pat-style audit)
    dests.push({ id: 'boundary_n', category: 'boundary', x: 0, z: 1500 });
    dests.push({ id: 'boundary_s', category: 'boundary', x: 0, z: -1500 });
    dests.push({ id: 'boundary_e', category: 'boundary', x: 1500, z: 0 });
    dests.push({ id: 'boundary_w', category: 'boundary', x: -1500, z: 0 });

    return dests;
  }

  // ─── Per-cast agendas (interest distributions) ────────────────────
  // Each is a weighted set of categories the agent gravitates toward.
  // No script — just preferences. The actual destination is sampled live.
  const AGENDAS = {
    Frank:    { office: 0.20, square: 0.45, intersection: 0.15, stop: 0.15, boundary: 0.05 },
    Max:      { office: 0.30, square: 0.30, stop: 0.30, intersection: 0.05, boundary: 0.05 },
    Florence: { office: 0.30, stop: 0.40, intersection: 0.10, square: 0.10, boundary: 0.10 },
    Pat:      { office: 0.20, boundary: 0.40, intersection: 0.20, square: 0.10, stop: 0.10 },
    Boswell:  { office: 0.20, square: 0.25, stop: 0.40, intersection: 0.10, boundary: 0.05 },
    Design:   { office: 0.35, square: 0.30, stop: 0.20, intersection: 0.10, boundary: 0.05 },
  };

  function weightedPick(weights) {
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    let r = Math.random() * total;
    for (const k in weights) {
      r -= weights[k];
      if (r <= 0) return k;
    }
    return Object.keys(weights)[0];
  }

  // ─── Agent ────────────────────────────────────────────────────────
  function makeAgent(scene, castEntry, dests, sectionByID) {
    const avatar = buildAvatar(scene, castEntry.name, castEntry.color, castEntry.type);
    const spawn = sectionByID[castEntry.spawn];
    avatar.root.position.set(spawn.x, 0, spawn.y);

    const agent = {
      name: castEntry.name,
      color: castEntry.color,
      type: castEntry.type,
      avatar,
      pos: new BABYLON.Vector3(spawn.x, 0, spawn.y),
      target: null,
      state: 'thinking', // thinking | walking | dwelling
      dwellTimer: 1 + Math.random() * 2,
      speed: 30 + Math.random() * 12, // units / second
      lastDest: null,
      lastCategory: 'office',
      thought: '',
      thoughts: [],
      pickNext() {
        const weights = AGENDAS[this.name] || AGENDAS.Frank;
        let category;
        let attempts = 0;
        do {
          category = weightedPick(weights);
          attempts++;
        } while (category === this.lastCategory && attempts < 3);
        this.lastCategory = category;
        const pool = dests.filter(d => d.category === category && d.id !== this.lastDest);
        if (pool.length === 0) {
          this.target = null;
          return;
        }
        const pick = pool[Math.floor(Math.random() * pool.length)];
        this.target = new BABYLON.Vector3(pick.x, 0, pick.z);
        this.lastDest = pick.id;
        this.thought = thoughtFor(this.name, category, pick);
        this.thoughts.push({ t: performance.now(), thought: this.thought, dest: pick.id });
        if (this.thoughts.length > 6) this.thoughts.shift();
        this.state = 'walking';
      },
      update(dt) {
        if (this.state === 'thinking') {
          this.dwellTimer -= dt;
          if (this.dwellTimer <= 0) {
            this.pickNext();
          }
          return;
        }
        if (this.state === 'walking') {
          if (!this.target) {
            this.state = 'thinking';
            this.dwellTimer = 1 + Math.random() * 2;
            return;
          }
          const dx = this.target.x - this.pos.x;
          const dz = this.target.z - this.pos.z;
          const d = Math.hypot(dx, dz);
          if (d < 2) {
            this.state = 'dwelling';
            this.dwellTimer = 3 + Math.random() * 6;
            return;
          }
          const step = Math.min(d, this.speed * dt);
          this.pos.x += (dx / d) * step;
          this.pos.z += (dz / d) * step;
          // turn body toward direction
          this.avatar.root.rotation.y = Math.atan2(dx, dz);
          this.avatar.root.position.copyFrom(this.pos);
          // gentle bob
          this.avatar.root.position.y = Math.sin(performance.now() * 0.008) * 0.5;
          return;
        }
        if (this.state === 'dwelling') {
          this.dwellTimer -= dt;
          if (this.dwellTimer <= 0) {
            this.state = 'thinking';
            this.dwellTimer = 0.5 + Math.random() * 1.5;
          }
        }
      },
    };
    return agent;
  }

  // Generated thoughts — flavor, not script. Sampled by category.
  function thoughtFor(name, category, dest) {
    const lib = {
      Frank: {
        office: ['Back to the corner. Need to think.', 'Checking the desk.', 'Door faces the action. Good.'],
        square: ['Reading the room.', 'Calling a standup.', 'Holding the center.'],
        stop: ['Walking the perimeter.', 'Want to see how the road reads.', 'Heading to ' + (dest.id || 'the road') + '.'],
        intersection: ['Watching the cross-traffic.', 'Ring road tells you a lot.', 'Lights cycling. Good.'],
        boundary: ['Edge audit.', 'Looking for the seam.'],
      },
      Max: {
        office: ['Need the table.', 'Voice work. The room helps.', 'Pacing it out.'],
        square: ['Listening.', 'The chrome is the voice.', 'Looking for an argument.'],
        stop: ['Sketching a scene on the road.', 'This bench writes better than mine.', 'Lit corner. Good page.'],
        intersection: ['Crowd flow makes sentences.', 'Watching the lights.'],
        boundary: ['Walking out where it gets quiet.'],
      },
      Florence: {
        office: ['Pre-reg.', 'Running the calc.', 'AAR draft.'],
        square: ['Surfacing a number.', 'Checking the dashboard read.'],
        stop: ['This bench is for thinking. Sitting.', 'Recalculating under the lamp.', 'Cooler light here. Better for spreadsheets.'],
        intersection: ['Counting cycle time.', 'Sample size on the lights.'],
        boundary: ['Sampling the edge.'],
      },
      Pat: {
        office: ['Filing.', 'Audit trail open.', 'Process pass.'],
        square: ['Quick spot check.', 'Listening for flags.'],
        stop: ['Auditing the road.', 'POI inventory at this stop.', 'Bench in spec.'],
        intersection: ['Traffic light timing — within range.', 'Cross-section audit.'],
        boundary: ['Boundary check. This is the job.', 'Edge integrity.', 'Looking for a seam.'],
      },
      Boswell: {
        office: ['Filing the log.', 'Updating the picture story.', 'Notes.'],
        square: ['Logging the standup.', 'Within earshot. As it should be.'],
        stop: ['Documenting this stop.', 'Adding to the corpus.', 'Picture story at ' + (dest.id || 'the bench') + '.'],
        intersection: ['Light cycle: 8 seconds. Logging.', 'Recording cross-traffic.'],
        boundary: ['Walking the boundary.', 'Logged: edge condition.'],
      },
      Design: {
        office: ['Re-pinning the wall.', 'Drafting.', 'Studio time.'],
        square: ['Looking at the read.', 'How does it feel from here?'],
        stop: ['Color study at ' + (dest.id || 'this stop') + '.', 'Lit by the road.', 'Drafting on a bench.'],
        intersection: ['Watching the rhythm of the lights.', 'Composition study.'],
        boundary: ['Studio walk. Long way around.'],
      },
    };
    const set = (lib[name] || lib.Frank)[category] || ['Walking.'];
    return set[Math.floor(Math.random() * set.length)];
  }

  // ─── Traffic lights at ring intersections ────────────────────────
  function buildTrafficLights(scene, intersections) {
    const lights = [];
    for (const ix of intersections) {
      // pole on the inner side of the ring
      const root = new BABYLON.TransformNode('tl_root_' + ix.id, scene);
      const dirFromCenter = Math.atan2(ix.x, ix.y);
      const inwardX = ix.x - Math.sin(dirFromCenter) * 50;
      const inwardZ = ix.y - Math.cos(dirFromCenter) * 50;
      root.position.set(inwardX, 0, inwardZ);

      const post = BABYLON.MeshBuilder.CreateCylinder('tl_post_' + ix.id, { diameter: 3, height: 80 }, scene);
      post.position.y = 40;
      post.parent = root;
      post.material = B.mat(scene, 'tlPM_' + ix.id, '#1a1a22');

      const head = BABYLON.MeshBuilder.CreateBox('tl_head_' + ix.id, { width: 8, height: 24, depth: 8 }, scene);
      head.position.y = 72;
      head.parent = root;
      head.material = B.mat(scene, 'tlHM_' + ix.id, '#0a0c12');

      function lamp(color, y, hex) {
        const s = BABYLON.MeshBuilder.CreateSphere('tlL_' + ix.id + '_' + color, { diameter: 5 }, scene);
        s.position.set(0, y, 4.5);
        s.parent = root;
        const m = new BABYLON.StandardMaterial('tlLM_' + ix.id + '_' + color, scene);
        m.diffuseColor = C(hex).scale(0.25);
        m.emissiveColor = C(hex).scale(0.3);
        m.specularColor = new BABYLON.Color3(0, 0, 0);
        s.material = m;
        return { mesh: s, mat: m, hex };
      }
      const red    = lamp('red',    80, '#ff5a5a');
      const yellow = lamp('yellow', 72, '#ffd86d');
      const green  = lamp('green',  64, '#46d9c5');

      // small accent light at base color when active
      const pl = new BABYLON.PointLight('tlPL_' + ix.id, new BABYLON.Vector3(inwardX, 78, inwardZ), scene);
      pl.intensity = 0;
      pl.range = 120;

      lights.push({
        id: ix.id, root, head, post, red, yellow, green, pl,
        phase: Math.random(),
        state: 'red',
        setState(s) {
          this.state = s;
          // dim all
          [this.red, this.yellow, this.green].forEach(L => {
            L.mat.emissiveColor = C(L.hex).scale(0.15);
          });
          let active = this.red;
          if (s === 'yellow') active = this.yellow;
          else if (s === 'green') active = this.green;
          active.mat.emissiveColor = C(active.hex).scale(1.5);
          this.pl.diffuse = C(active.hex);
          this.pl.intensity = 0.6;
        },
      });
    }
    return lights;
  }

  window.SIMUTUM_ENTITIES = {
    buildAvatar, makeAgent, buildDestinations, buildTrafficLights, AGENDAS,
  };
})();
