// geometry.js — Simutum Demo World
// All coordinates center-origin. Brief axes: +x = east, +y = north.
// Maps to Babylon as (x, 0, y) — Y is up, +z = north.
//
// This file is the single source of truth for world layout.
// It produces both the 3D scene and the exported JSON spec.

(function () {
  'use strict';

  // ─── Cubic Bezier helpers ─────────────────────────────────────────
  function bez(p0, p1, p2, p3, t) {
    const u = 1 - t;
    const uu = u * u, uuu = uu * u;
    const tt = t * t, ttt = tt * t;
    return {
      x: uuu * p0.x + 3 * uu * t * p1.x + 3 * u * tt * p2.x + ttt * p3.x,
      y: uuu * p0.y + 3 * uu * t * p1.y + 3 * u * tt * p2.y + ttt * p3.y,
    };
  }
  function bezTan(p0, p1, p2, p3, t) {
    const u = 1 - t;
    return {
      x: 3 * u * u * (p1.x - p0.x) + 6 * u * t * (p2.x - p1.x) + 3 * t * t * (p3.x - p2.x),
      y: 3 * u * u * (p1.y - p0.y) + 6 * u * t * (p2.y - p1.y) + 3 * t * t * (p3.y - p2.y),
    };
  }

  // ─── Road curve with adjustable "intensity" (1 = brief default) ────
  // Returns a fn(t) → {x,y,heading}. Curve intensity scales lateral offset
  // of control points relative to the straight line between endpoints.
  function makeRoad(p0, p3, sideOffset, intensity) {
    const I = intensity == null ? 1 : intensity;
    const dx = p3.x - p0.x, dy = p3.y - p0.y;
    const len = Math.hypot(dx, dy) || 1;
    // Perpendicular unit (left-hand of forward dir)
    const nx = -dy / len, ny = dx / len;
    const so = sideOffset * I;
    // Control points pushed laterally + forward to make a smooth S/arc
    const p1 = { x: p0.x + dx * 0.30 + nx * so, y: p0.y + dy * 0.30 + ny * so };
    const p2 = { x: p0.x + dx * 0.70 + nx * so, y: p0.y + dy * 0.70 + ny * so };
    return {
      points: [p0, p1, p2, p3],
      at: (t) => bez(p0, p1, p2, p3, t),
      tangent: (t) => {
        const tg = bezTan(p0, p1, p2, p3, t);
        return { x: tg.x, y: tg.y, heading: Math.atan2(tg.x, tg.y) };
      },
      length: () => {
        let acc = 0, prev = p0;
        for (let i = 1; i <= 32; i++) {
          const pt = bez(p0, p1, p2, p3, i / 32);
          acc += Math.hypot(pt.x - prev.x, pt.y - prev.y);
          prev = pt;
        }
        return acc;
      },
    };
  }

  // ─── World data ───────────────────────────────────────────────────
  const SECTIONS = [
    { id: 'the_square',          label: 'The Square',           x:    0, y:    0, w: 220, h: 180, floor_color: '#1e1b30', walled: false, accent: 'octagon' },
    { id: 'frank_office',        label: "Frank's Office",       x: -390, y:  310, w: 160, h: 140, floor_color: '#1a1826', walled: true,  door: { side: 'south', width: 40 } },
    { id: 'max_writers',         label: "Max's Writers' Room",  x: -350, y:   50, w: 200, h: 120, floor_color: '#1c1a2a', walled: 'partial' },
    { id: 'florence_analysis',   label: "Florence's Analysis",  x:  390, y:    0, w: 160, h: 160, floor_color: '#181e28', walled: 'partial' },
    { id: 'pat_audit',           label: "Pat's Audit Corner",   x:  430, y:  330, w: 120, h: 120, floor_color: '#1a1a22', walled: true,  door: { side: 'south', width: 40 } },
    { id: 'boswell_desk',        label: "Boswell's Desk",       x:  225, y:    0, w: 100, h:  80, floor_color: '#201e2e', walled: false, raised: 6 },
    { id: 'design_studio',       label: 'Design Studio',        x:    0, y: -330, w: 240, h: 140, floor_color: '#1c1a28', walled: false, lshape: true },
  ];

  // Cast (from office_standup_replay.json) — assignments per brief §4
  const CAST = [
    { name: 'Frank',    role: 'foreman',  color: '#6db8ff', type: 'anchor',   spawn: 'frank_office' },
    { name: 'Max',      role: 'writer',   color: '#e0c46d', type: 'creative', spawn: 'max_writers' },
    { name: 'Florence', role: 'analyst',  color: '#ff7da6', type: 'thinker',  spawn: 'florence_analysis' },
    { name: 'Pat',      role: 'auditor',  color: '#79e5b8', type: 'anchor',   spawn: 'pat_audit' },
    { name: 'Boswell',  role: 'scribe',   color: '#ff9d6d', type: 'thinker',  spawn: 'boswell_desk' },
    { name: 'Design',   role: 'designer', color: '#c279ff', type: 'creative', spawn: 'design_studio' },
  ];

  // Stations — per brief
  const STATIONS = [
    { id: 'theater_station', x:    0, y: -1400, label: 'THE THEATER',     target_pack: 'theater', heading: Math.PI },     // facing south back to map
    { id: 'bar_station',     x: 1400, y:     0, label: 'THE BAR',         target_pack: 'bar',     heading: Math.PI / 2 }, // facing east
    { id: 'lab_station',     x: -900, y:   900, label: 'THE LAB + FIELD', target_pack: 'lab',     heading: -Math.PI * 0.25 },
  ];

  // Road pairs — outbound (map→station) + return (station→map).
  // sideOffset positive curves the outbound LEFT of the forward direction;
  // return curves the OTHER way, enclosing area between them.
  function buildRoads(intensity) {
    const I = intensity;
    return [
      // Theater — south
      {
        id: 'theater_road_out', direction: 'out',  destination: 'theater_station', width: 80, theme: 'warm',
        curve: makeRoad({ x:  60, y: -450 }, { x:   0, y: -1400 },  240, I),
      },
      {
        id: 'theater_road_back', direction: 'back', destination: 'theater_station', width: 80, theme: 'warm',
        curve: makeRoad({ x:   0, y: -1400 }, { x: -60, y:  -450 },  240, I),
      },
      // Bar — east
      {
        id: 'bar_road_out', direction: 'out', destination: 'bar_station', width: 80, theme: 'amber',
        curve: makeRoad({ x:  550, y:  60 }, { x: 1400, y:    0 },  240, I),
      },
      {
        id: 'bar_road_back', direction: 'back', destination: 'bar_station', width: 80, theme: 'amber',
        curve: makeRoad({ x: 1400, y:   0 }, { x:  550, y:  -60 },  240, I),
      },
      // Lab — NW diagonal
      {
        id: 'lab_road_out', direction: 'out', destination: 'lab_station', width: 80, theme: 'cyan',
        curve: makeRoad({ x: -440, y:  460 }, { x: -900, y:  900 },  220, I),
      },
      {
        id: 'lab_road_back', direction: 'back', destination: 'lab_station', width: 80, theme: 'cyan',
        curve: makeRoad({ x: -900, y:  900 }, { x: -460, y:  430 },  220, I),
      },
    ];
  }

  // Stops along outbound roads (return roads stay light — scenery only)
  // POI types + lighting per stop are deliberately varied across roads.
  const STOPS = [
    // Theater Road — warm/gold palette
    { id: 'theater_road_stop_1', road: 'theater_road_out', t: 0.25, poi: 'notice_board',     lighting: { color: '#f5b86b', intensity: 0.9, type: 'steady' },     audio: 'wind_low' },
    { id: 'theater_road_stop_2', road: 'theater_road_out', t: 0.55, poi: 'bench_cluster',    lighting: { color: '#ffd28a', intensity: 1.0, type: 'pool' },       audio: 'distant_chatter' },
    { id: 'theater_road_stop_3', road: 'theater_road_out', t: 0.85, poi: 'road_marker',      lighting: { color: '#f59a4a', intensity: 0.7, type: 'flicker' },    audio: 'transformer_hum' },
    // Bar Road — red/amber palette
    { id: 'bar_road_stop_1',     road: 'bar_road_out',     t: 0.25, poi: 'vendor_table',     lighting: { color: '#ff7d4a', intensity: 0.9, type: 'steady' },     audio: 'crate_creak' },
    { id: 'bar_road_stop_2',     road: 'bar_road_out',     t: 0.50, poi: 'parked_vehicle',   lighting: { color: '#ff8b3a', intensity: 0.8, type: 'flicker' },    audio: 'engine_idle' },
    { id: 'bar_road_stop_3',     road: 'bar_road_out',     t: 0.85, poi: 'viewing_platform', lighting: { color: '#e84a3c', intensity: 1.1, type: 'pool' },       audio: 'wind_high' },
    // Lab Road — cyan/cool palette
    { id: 'lab_road_stop_1',     road: 'lab_road_out',     t: 0.25, poi: 'rock_bench',       lighting: { color: '#6dd8ff', intensity: 0.8, type: 'steady' },     audio: 'insect_chirps' },
    { id: 'lab_road_stop_2',     road: 'lab_road_out',     t: 0.50, poi: 'observation_post', lighting: { color: '#9ae8ff', intensity: 0.9, type: 'pulse' },      audio: 'sensor_ping' },
    { id: 'lab_road_stop_3',     road: 'lab_road_out',     t: 0.85, poi: 'covered_alcove',   lighting: { color: '#46d9c5', intensity: 1.0, type: 'steady' },     audio: 'wind_reeds' },
  ];

  const GHOST_PACKS = [
    { id: 'theater_ghost', x:  800, y: -800, w: 350, h: 200, color: '#1a1a2e', kind: 'theater' },
    { id: 'field_ghost',   x:    0, y: 1100, w: 400, h: 300, color: '#181e1a', kind: 'field' },
    { id: 'bar_ghost',     x: -1200, y: -350, w: 300, h: 200, color: '#1e1a1a', kind: 'bar' },
  ];

  const BOUNDARY = { north: 1600, south: -1600, east: 1600, west: -1600 };
  const EGGS = [
    { id: 'egg_north', x:     0, y:  1600, face: 'north' },
    { id: 'egg_south', x:     0, y: -1600, face: 'south' },
    { id: 'egg_east',  x:  1600, y:     0, face: 'east'  },
    { id: 'egg_west',  x: -1600, y:     0, face: 'west'  },
  ];

  // Ring road — circle of given radius. Width 60. Crosses station roads
  // at 6 points (out + back for each of the 3 destinations).
  function ringIntersections(roads, radius) {
    const out = [];
    for (const road of roads) {
      // Sample road; find closest point to ring radius
      let best = null;
      for (let i = 0; i <= 200; i++) {
        const t = i / 200;
        const p = road.curve.at(t);
        const r = Math.hypot(p.x, p.y);
        const d = Math.abs(r - radius);
        if (!best || d < best.d) {
          best = { d, t, x: p.x, y: p.y };
        }
      }
      out.push({
        id: 'ix_' + road.id,
        road_id: road.id,
        t: best.t,
        x: best.x,
        y: best.y,
        angle: Math.atan2(best.x, best.y), // angle around ring (0 = north)
      });
    }
    return out;
  }

  // ─── Exported JSON (matches §5 format in the brief) ───────────────
  function toJSONSpec(state) {
    const I = state.curveIntensity;
    const R = state.ringRadius;
    const roads = buildRoads(I);
    const intersections = ringIntersections(roads, R);
    return {
      canvas: { width: 4000, height: 4000 },
      sections: SECTIONS.map(s => ({
        id: s.id, label: s.label,
        global_x: s.x, global_y: s.y,
        width: s.w, height: s.h,
        flags: {
          walled: !!s.walled,
          floor_color: s.floor_color,
          pack: 'demo_floor',
          ...(s.raised ? { raised: s.raised } : {}),
        },
      })),
      roads: roads.map(r => ({
        id: r.id, direction: r.direction, destination: r.destination,
        width: r.width, theme: r.theme,
        bezier: r.curve.points,
        length: Math.round(r.curve.length()),
      })),
      ring_road: {
        id: 'ring_road',
        radius: R,
        width: 60,
        intersections: intersections.map(ix => ({
          id: ix.id, road_id: ix.road_id, x: Math.round(ix.x), y: Math.round(ix.y),
          traffic_light: true,
        })),
      },
      stops: STOPS.map(s => ({
        id: s.id, road: s.road, t: s.t, poi: s.poi,
        lighting: s.lighting, audio: s.audio,
      })),
      stations: STATIONS.map(s => ({
        id: s.id, position: { x: s.x, y: s.y },
        target_pack: s.target_pack, label: s.label,
      })),
      ghost_packs: GHOST_PACKS,
      easter_eggs: EGGS.map(e => ({ id: e.id, position: { x: e.x, y: e.y } })),
      boundary: BOUNDARY,
      cast: CAST,
    };
  }

  // Expose
  window.SIMUTUM_WORLD = {
    SECTIONS, CAST, STATIONS, STOPS, GHOST_PACKS, BOUNDARY, EGGS,
    buildRoads, ringIntersections, toJSONSpec,
    bez, bezTan, makeRoad,
  };
})();
