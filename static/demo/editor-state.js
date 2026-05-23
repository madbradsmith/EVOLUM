// editor-state.js — central state model.
//
// Single mutable store with subscriber + localStorage auto-save. Editor UI
// reads via window.EDITOR_STATE.get(), mutates via window.EDITOR_STATE.update(...),
// and reacts via window.EDITOR_STATE.subscribe(fn).
//
// The state schema is a superset of the Game World JSON spec — it stores
// the raw editing model (e.g. road as a single config that auto-mirrors into
// out+back), and editor-export.js folds it into the final spec.

(function () {
  'use strict';

  const STORAGE_KEY = 'simutum_editor_world_v1';

  // ── Default empty world (shown if no localStorage) ──
  const EMPTY_WORLD = () => ({
    meta: {
      name: 'Untitled World',
      createdAt: Date.now(),
      version: 1,
    },
    sections: [],
    roads: [],      // each: { id, label, destination, theme, width, p0, p3, sideOffset, intensity }
    ringRoad: { enabled: true, radius: 900, width: 60 },
    stops: [],      // each: { id, road, t, poi, lighting: {color, intensity, type}, audio }
    stations: [],   // each: { id, x, y, label, target_pack, road }
    ghostPacks: [],
    boundary: { north: 1600, south: -1600, east: 1600, west: -1600 },
    eggs: { north: true, south: true, east: true, west: true },
    cast: [],
    editor: {
      activeTab: 'wizard',      // wizard | map | entities | play
      selection: null,          // { kind: 'section'|'road'|'stop'|... , id }
      camera: { x: 0, y: 0, zoom: 1 }, // canvas viewport
      gridSize: 10,
      previewPlay: true,
      wizardDone: false,
    },
  });

  // ── Example world (loaded from simutum_demo_world.json on demand) ──
  // The example is the Game World demo as a starting template.
  const EXAMPLE_WORLD = {
    meta: { name: 'Open Office (Example)', createdAt: 0, version: 1 },
    sections: [
      { id: 'the_square',        label: 'The Square',          x:    0, y:    0, w: 220, h: 180, floor_color: '#1e1b30', walled: false,     rotation: 0, raised: 0 },
      { id: 'frank_office',      label: "Frank's Office",      x: -390, y:  310, w: 160, h: 140, floor_color: '#1a1826', walled: true,      rotation: 0, raised: 0 },
      { id: 'max_writers',       label: "Max's Writers' Room", x: -350, y:   50, w: 200, h: 120, floor_color: '#1c1a2a', walled: 'partial', rotation: 0, raised: 0 },
      { id: 'florence_analysis', label: "Florence's Analysis", x:  390, y:    0, w: 160, h: 160, floor_color: '#181e28', walled: 'partial', rotation: 0, raised: 0 },
      { id: 'pat_audit',         label: "Pat's Audit Corner",  x:  430, y:  330, w: 120, h: 120, floor_color: '#1a1a22', walled: true,      rotation: 0, raised: 0 },
      { id: 'boswell_desk',      label: "Boswell's Desk",      x:  225, y:    0, w: 100, h:  80, floor_color: '#201e2e', walled: false,     rotation: 0, raised: 6 },
      { id: 'design_studio',     label: 'Design Studio',       x:    0, y: -330, w: 240, h: 140, floor_color: '#1c1a28', walled: false,     rotation: 0, raised: 0 },
    ],
    roads: [
      { id: 'road_theater', label: 'Theater Road', destination: 'theater_station', theme: 'warm',  width: 80,
        p0: { x:  60, y: -450 }, p3: { x:    0, y: -1400 }, sideOffset: 240, intensity: 1.0 },
      { id: 'road_bar',     label: 'Bar Road',     destination: 'bar_station',     theme: 'amber', width: 80,
        p0: { x: 550, y:   60 }, p3: { x: 1400, y:     0 }, sideOffset: 240, intensity: 1.0 },
      { id: 'road_lab',     label: 'Lab Road',     destination: 'lab_station',     theme: 'cyan',  width: 80,
        p0: { x:-440, y:  460 }, p3: { x: -900, y:   900 }, sideOffset: 220, intensity: 1.0 },
    ],
    ringRoad: { enabled: true, radius: 900, width: 60 },
    stops: [
      { id: 'theater_road_stop_1', road: 'road_theater', t: 0.25, poi: 'notice_board',     lighting: { color: '#f5b86b', intensity: 0.9, type: 'steady'  }, audio: 'wind_low' },
      { id: 'theater_road_stop_2', road: 'road_theater', t: 0.55, poi: 'bench_cluster',    lighting: { color: '#ffd28a', intensity: 1.0, type: 'pool'    }, audio: 'distant_chatter' },
      { id: 'theater_road_stop_3', road: 'road_theater', t: 0.85, poi: 'road_marker',      lighting: { color: '#f59a4a', intensity: 0.7, type: 'flicker' }, audio: 'transformer_hum' },
      { id: 'bar_road_stop_1',     road: 'road_bar',     t: 0.25, poi: 'vendor_table',     lighting: { color: '#ff7d4a', intensity: 0.9, type: 'steady'  }, audio: 'crate_creak' },
      { id: 'bar_road_stop_2',     road: 'road_bar',     t: 0.50, poi: 'parked_vehicle',   lighting: { color: '#ff8b3a', intensity: 0.8, type: 'flicker' }, audio: 'engine_idle' },
      { id: 'bar_road_stop_3',     road: 'road_bar',     t: 0.85, poi: 'viewing_platform', lighting: { color: '#e84a3c', intensity: 1.1, type: 'pool'    }, audio: 'wind_high' },
      { id: 'lab_road_stop_1',     road: 'road_lab',     t: 0.25, poi: 'rock_bench',       lighting: { color: '#6dd8ff', intensity: 0.8, type: 'steady'  }, audio: 'insect_chirps' },
      { id: 'lab_road_stop_2',     road: 'road_lab',     t: 0.50, poi: 'observation_post', lighting: { color: '#9ae8ff', intensity: 0.9, type: 'pulse'   }, audio: 'sensor_ping' },
      { id: 'lab_road_stop_3',     road: 'road_lab',     t: 0.85, poi: 'covered_alcove',   lighting: { color: '#46d9c5', intensity: 1.0, type: 'steady'  }, audio: 'wind_reeds' },
    ],
    stations: [
      { id: 'theater_station', x:    0, y: -1400, label: 'THE THEATER',     target_pack: 'theater', road: 'road_theater' },
      { id: 'bar_station',     x: 1400, y:    0,  label: 'THE BAR',         target_pack: 'bar',     road: 'road_bar' },
      { id: 'lab_station',     x: -900, y:  900,  label: 'THE LAB + FIELD', target_pack: 'lab',     road: 'road_lab' },
    ],
    ghostPacks: [
      { id: 'theater_ghost', x:   800, y: -800, w: 350, h: 200, color: '#1a1a2e', kind: 'theater' },
      { id: 'field_ghost',   x:     0, y: 1100, w: 400, h: 300, color: '#181e1a', kind: 'field' },
      { id: 'bar_ghost',     x: -1200, y: -350, w: 300, h: 200, color: '#1e1a1a', kind: 'bar' },
    ],
    boundary: { north: 1600, south: -1600, east: 1600, west: -1600 },
    eggs: { north: true, south: true, east: true, west: true },
    cast: [
      { name: 'Frank',    role: 'foreman',  color: '#6db8ff', type: 'anchor',   spawn: 'frank_office',       agenda: { office: 0.20, square: 0.45, stop: 0.15, intersection: 0.15, boundary: 0.05 } },
      { name: 'Max',      role: 'writer',   color: '#e0c46d', type: 'creative', spawn: 'max_writers',        agenda: { office: 0.30, square: 0.30, stop: 0.30, intersection: 0.05, boundary: 0.05 } },
      { name: 'Florence', role: 'analyst',  color: '#ff7da6', type: 'thinker',  spawn: 'florence_analysis',  agenda: { office: 0.30, square: 0.10, stop: 0.40, intersection: 0.10, boundary: 0.10 } },
      { name: 'Pat',      role: 'auditor',  color: '#79e5b8', type: 'anchor',   spawn: 'pat_audit',          agenda: { office: 0.20, square: 0.10, stop: 0.10, intersection: 0.20, boundary: 0.40 } },
      { name: 'Boswell',  role: 'scribe',   color: '#ff9d6d', type: 'thinker',  spawn: 'boswell_desk',       agenda: { office: 0.20, square: 0.25, stop: 0.40, intersection: 0.10, boundary: 0.05 } },
      { name: 'Design',   role: 'designer', color: '#c279ff', type: 'creative', spawn: 'design_studio',      agenda: { office: 0.35, square: 0.30, stop: 0.20, intersection: 0.10, boundary: 0.05 } },
    ],
    editor: { activeTab: 'map', selection: null, camera: { x: 0, y: 0, zoom: 1 }, gridSize: 10, previewPlay: true, wizardDone: true },
  };

  // ── Store ──
  const subs = new Set();
  let state = null;
  let saveTimer = null;

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return EMPTY_WORLD();
      const parsed = JSON.parse(raw);
      // Merge with defaults so new keys survive
      return Object.assign(EMPTY_WORLD(), parsed, {
        editor: Object.assign(EMPTY_WORLD().editor, parsed.editor || {}),
      });
    } catch (e) {
      console.warn('editor state load failed', e);
      return EMPTY_WORLD();
    }
  }

  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      } catch (e) {
        console.warn('editor state save failed', e);
      }
    }, 250);
  }

  function notify(changeKind) {
    subs.forEach(fn => { try { fn(state, changeKind); } catch (e) { console.error(e); } });
  }

  function get() { return state; }
  function subscribe(fn) { subs.add(fn); return () => subs.delete(fn); }

  // Mutate state with a producer fn that receives a mutable draft.
  // Pass a kind string so subscribers can filter (e.g. 'select' vs 'geometry').
  function update(producer, kind) {
    producer(state);
    save();
    notify(kind || 'change');
  }

  // Replace whole state (load JSON, reset, wizard finish)
  function replace(newState, kind) {
    state = Object.assign(EMPTY_WORLD(), newState);
    save();
    notify(kind || 'replace');
  }

  function reset(toExample) {
    if (toExample) replace(JSON.parse(JSON.stringify(EXAMPLE_WORLD)), 'reset');
    else replace(EMPTY_WORLD(), 'reset');
  }

  // ── Helpers: ID generation, selection, etc. ──
  function uid(prefix) {
    return prefix + '_' + Math.random().toString(36).slice(2, 8);
  }

  function select(kind, id) {
    update(s => { s.editor.selection = id ? { kind, id } : null; }, 'select');
  }
  function clearSelection() { select(null, null); }

  function findSelected(s) {
    s = s || state;
    if (!s || !s.editor.selection) return null;
    const sel = s.editor.selection;
    const list = {
      section: s.sections, road: s.roads, stop: s.stops,
      station: s.stations, ghost: s.ghostPacks,
    }[sel.kind];
    if (!list) return null;
    return list.find(x => x.id === sel.id) || null;
  }

  // ── Boot ──
  state = load();

  // Expose
  window.EDITOR_STATE = {
    get, subscribe, update, replace, reset, select, clearSelection, findSelected,
    uid, EMPTY_WORLD, EXAMPLE_WORLD,
    STORAGE_KEY,
  };
})();
