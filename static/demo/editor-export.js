// editor-export.js — convert editor state ↔ Game World JSON spec.
//
// Editor stores roads as ONE config (auto-mirrors to out + back). The exported
// spec uses two roads per pair (matching the Game World runtime). Other shapes
// pass through with cosmetic rounding.

(function () {
  'use strict';

  // ── Cubic Bezier helpers (same as runtime/geometry.js) ──
  function bez(p0, p1, p2, p3, t) {
    const u = 1 - t;
    return {
      x: u*u*u*p0.x + 3*u*u*t*p1.x + 3*u*t*t*p2.x + t*t*t*p3.x,
      y: u*u*u*p0.y + 3*u*u*t*p1.y + 3*u*t*t*p2.y + t*t*t*p3.y,
    };
  }

  function makeCurve(p0, p3, sideOffset, intensity) {
    const I = intensity == null ? 1 : intensity;
    const dx = p3.x - p0.x, dy = p3.y - p0.y;
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len, ny = dx / len;
    const so = sideOffset * I;
    return [
      p0,
      { x: p0.x + dx * 0.30 + nx * so, y: p0.y + dy * 0.30 + ny * so },
      { x: p0.x + dx * 0.70 + nx * so, y: p0.y + dy * 0.70 + ny * so },
      p3,
    ];
  }

  function curveLength(pts) {
    let acc = 0, prev = pts[0];
    for (let i = 1; i <= 32; i++) {
      const t = i / 32;
      const p = bez(pts[0], pts[1], pts[2], pts[3], t);
      acc += Math.hypot(p.x - prev.x, p.y - prev.y);
      prev = p;
    }
    return acc;
  }

  function ringIntersections(roadsExpanded, radius) {
    const out = [];
    for (const r of roadsExpanded) {
      let best = null;
      const [p0, p1, p2, p3] = r.bezier;
      for (let i = 0; i <= 200; i++) {
        const t = i / 200;
        const p = bez(p0, p1, p2, p3, t);
        const dist = Math.abs(Math.hypot(p.x, p.y) - radius);
        if (!best || dist < best.d) best = { d: dist, t, x: p.x, y: p.y };
      }
      out.push({
        id: 'ix_' + r.id, road_id: r.id,
        t: Math.round(best.t * 1000) / 1000,
        x: Math.round(best.x),
        y: Math.round(best.y),
        traffic_light: true,
      });
    }
    return out;
  }

  function r2(n) { return Math.round(n * 100) / 100; }

  // ── State → Game World JSON spec ──
  function toSpec(state) {
    // Expand each road into out + back pair
    const expandedRoads = [];
    for (const r of state.roads) {
      const outCurve = makeCurve(r.p0, r.p3, r.sideOffset, r.intensity);
      // Return curve: mirrored — swap endpoints AND flip sideOffset (curves the OTHER way)
      // so the back road encloses area with the out road.
      // The return endpoints are nudged ~60u laterally to avoid overlapping the out road at its endpoints.
      const dx = r.p3.x - r.p0.x, dy = r.p3.y - r.p0.y;
      const len = Math.hypot(dx, dy) || 1;
      const nx = -dy / len, ny = dx / len;
      const back_p0 = r.p3;
      const back_p3 = { x: r.p0.x - nx * 120, y: r.p0.y - ny * 120 };
      const backCurve = makeCurve(back_p0, back_p3, r.sideOffset, r.intensity);

      expandedRoads.push({
        id: r.id + '_out', direction: 'out', destination: r.destination,
        width: r.width, theme: r.theme,
        bezier: outCurve.map(p => ({ x: r2(p.x), y: r2(p.y) })),
        length: Math.round(curveLength(outCurve)),
      });
      expandedRoads.push({
        id: r.id + '_back', direction: 'back', destination: r.destination,
        width: r.width, theme: r.theme,
        bezier: backCurve.map(p => ({ x: r2(p.x), y: r2(p.y) })),
        length: Math.round(curveLength(backCurve)),
      });
    }

    const intersections = state.ringRoad.enabled
      ? ringIntersections(expandedRoads, state.ringRoad.radius)
      : [];

    // stops — map editor's road-id to runtime's <id>_out (stops always on outbound)
    const stops = state.stops.map(s => ({
      id: s.id,
      road: s.road + '_out',
      t: s.t,
      poi: s.poi,
      lighting: s.lighting,
      audio: s.audio,
    }));

    const eggs = [];
    if (state.eggs.north) eggs.push({ id: 'egg_north', position: { x: 0, y: state.boundary.north } });
    if (state.eggs.south) eggs.push({ id: 'egg_south', position: { x: 0, y: state.boundary.south } });
    if (state.eggs.east)  eggs.push({ id: 'egg_east',  position: { x: state.boundary.east,  y: 0 } });
    if (state.eggs.west)  eggs.push({ id: 'egg_west',  position: { x: state.boundary.west,  y: 0 } });

    return {
      canvas: { width: 4000, height: 4000 },
      sections: state.sections.map(s => ({
        id: s.id, label: s.label,
        global_x: s.x, global_y: s.y,
        width: s.w, height: s.h,
        flags: {
          walled: s.walled || false,
          floor_color: s.floor_color,
          pack: 'demo_floor',
          ...(s.raised ? { raised: s.raised } : {}),
          ...(s.rotation ? { rotation: s.rotation } : {}),
        },
      })),
      roads: expandedRoads,
      ring_road: state.ringRoad.enabled ? {
        id: 'ring_road',
        radius: state.ringRoad.radius,
        width: state.ringRoad.width,
        intersections,
      } : null,
      stops,
      stations: state.stations.map(st => ({
        id: st.id, position: { x: st.x, y: st.y },
        target_pack: st.target_pack, label: st.label,
      })),
      ghost_packs: state.ghostPacks,
      easter_eggs: eggs,
      boundary: state.boundary,
      cast: state.cast,
    };
  }

  // ── Game World JSON spec → editor state (inverse) ──
  // Tries to fold out+back pairs back into single road configs.
  function fromSpec(spec) {
    const state = window.EDITOR_STATE.EMPTY_WORLD();
    state.meta = { name: 'Imported', createdAt: Date.now(), version: 1 };
    state.sections = (spec.sections || []).map(s => ({
      id: s.id,
      label: s.label,
      x: s.global_x, y: s.global_y,
      w: s.width, h: s.height,
      floor_color: (s.flags && s.flags.floor_color) || '#1c1a28',
      walled: !!(s.flags && s.flags.walled),
      rotation: (s.flags && s.flags.rotation) || 0,
      raised: (s.flags && s.flags.raised) || 0,
    }));
    // Fold roads: group by destination, take "_out" as canonical
    const byDest = {};
    for (const r of spec.roads || []) {
      const base = r.id.replace(/_(out|back)$/, '');
      if (!byDest[base] || r.direction === 'out') {
        byDest[base] = r;
      }
    }
    state.roads = Object.entries(byDest).map(([baseId, r]) => ({
      id: baseId,
      label: baseId,
      destination: r.destination,
      theme: r.theme || 'warm',
      width: r.width || 80,
      p0: r.bezier[0],
      p3: r.bezier[3],
      sideOffset: 240,
      intensity: 1.0,
    }));
    state.ringRoad = spec.ring_road ? {
      enabled: true,
      radius: spec.ring_road.radius,
      width: spec.ring_road.width,
    } : { enabled: false, radius: 900, width: 60 };
    state.stops = (spec.stops || []).map(s => ({
      id: s.id, road: s.road.replace(/_(out|back)$/, ''),
      t: s.t, poi: s.poi, lighting: s.lighting, audio: s.audio,
    }));
    state.stations = (spec.stations || []).map(st => ({
      id: st.id, x: st.position.x, y: st.position.y,
      label: st.label, target_pack: st.target_pack,
      road: Object.keys(byDest).find(k => byDest[k].destination === st.id) || '',
    }));
    state.ghostPacks = spec.ghost_packs || [];
    state.boundary = spec.boundary || { north: 1600, south: -1600, east: 1600, west: -1600 };
    state.eggs = { north: false, south: false, east: false, west: false };
    for (const e of (spec.easter_eggs || [])) {
      if (e.id.includes('north')) state.eggs.north = true;
      else if (e.id.includes('south')) state.eggs.south = true;
      else if (e.id.includes('east')) state.eggs.east = true;
      else if (e.id.includes('west')) state.eggs.west = true;
    }
    state.cast = (spec.cast || []).map(c => Object.assign({
      agenda: { office: 0.20, square: 0.30, stop: 0.25, intersection: 0.15, boundary: 0.10 },
    }, c, { agenda: c.agenda || { office: 0.20, square: 0.30, stop: 0.25, intersection: 0.15, boundary: 0.10 } }));
    state.editor = { activeTab: 'map', selection: null, camera: { x: 0, y: 0, zoom: 0.35 },
      gridSize: 10, previewPlay: true, wizardDone: true };
    return state;
  }

  // ── Download helpers ──
  function downloadJSON(filename, obj) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportWorld() {
    const spec = toSpec(window.EDITOR_STATE.get());
    downloadJSON('simutum_demo_world.json', spec);
  }
  function exportCast() {
    downloadJSON('simutum_cast.json', window.EDITOR_STATE.get().cast);
  }

  function importWorldText(text) {
    try {
      const parsed = JSON.parse(text);
      // Detect format: native editor state vs Game World JSON spec.
      const looksLikeSpec = Array.isArray(parsed.sections) &&
        parsed.sections[0] && typeof parsed.sections[0].global_x === 'number';
      const state = looksLikeSpec ? fromSpec(parsed) : Object.assign(window.EDITOR_STATE.EMPTY_WORLD(), parsed);
      // Ensure editor settings exist on import
      state.editor = Object.assign({
        activeTab: 'map', selection: null, camera: { x: 0, y: 0, zoom: 0.35 },
        gridSize: 10, previewPlay: true, wizardDone: true,
      }, state.editor || {});
      window.EDITOR_STATE.replace(state, 'import');
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  }

  window.EDITOR_EXPORT = {
    toSpec, fromSpec, exportWorld, exportCast, importWorldText,
    makeCurve, curveLength, ringIntersections, bez,
  };
})();
