// editor-extensions.jsx — Final compilation additions to the Map Editor.
// Adds: Undo/Redo (Cmd+Z / Cmd+Shift+Z), section templates, road labels,
// world thumbnail auto-generator on export.

(function () {
  const { useEffect, useState } = React;

  // ─── Undo/Redo state stack ───────────────────────────
  const UNDO_LIMIT = 50;
  const history = []; // snapshots
  let historyIdx = -1;
  let suppressNextPush = false;

  function snapshot() {
    const s = window.EDITOR_STATE.get();
    // strip editor (selection/camera) so undo doesn't replay selection changes
    const { editor: _e, ...rest } = s;
    return JSON.parse(JSON.stringify(rest));
  }
  function push() {
    if (suppressNextPush) { suppressNextPush = false; return; }
    // drop redo branch
    history.length = historyIdx + 1;
    history.push(snapshot());
    if (history.length > UNDO_LIMIT) history.shift();
    historyIdx = history.length - 1;
  }
  function applyRestore(snap) {
    suppressNextPush = true;
    const cur = window.EDITOR_STATE.get();
    const merged = Object.assign({}, snap, { editor: cur.editor });
    window.EDITOR_STATE.replace(merged, 'undo');
  }
  function undo() {
    if (historyIdx <= 0) return;
    historyIdx--;
    applyRestore(history[historyIdx]);
  }
  function redo() {
    if (historyIdx >= history.length - 1) return;
    historyIdx++;
    applyRestore(history[historyIdx]);
  }

  // Hook on geometry changes
  if (window.EDITOR_STATE) {
    push(); // baseline
    window.EDITOR_STATE.subscribe((s, kind) => {
      if (kind === 'select' || kind === 'camera' || kind === 'tab' || kind === 'undo' || kind === 'play') return;
      push();
    });

    // Keyboard
    window.addEventListener('keydown', (e) => {
      const cmd = e.metaKey || e.ctrlKey;
      if (!cmd) return;
      if (e.target.matches && e.target.matches('input, textarea, select')) return;
      if (e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo(); }
      else if ((e.key === 'z' && e.shiftKey) || e.key === 'y') { e.preventDefault(); redo(); }
    });
  }

  window.EDITOR_UNDO = { undo, redo, canUndo: () => historyIdx > 0, canRedo: () => historyIdx < history.length - 1 };

  // ─── Section Templates (5 presets, applied at canvas center) ──
  const TEMPLATES = {
    'Open Grid': () => {
      const out = [];
      for (let r = 0; r < 2; r++) {
        for (let c = 0; c < 3; c++) {
          out.push({
            id: 'sec_' + Math.random().toString(36).slice(2, 7),
            label: 'Zone ' + (r * 3 + c + 1),
            x: -300 + c * 300, y: -150 + r * 300,
            w: 200, h: 160, floor_color: '#1c1a28',
            walled: 'partial', rotation: 0, raised: 0,
          });
        }
      }
      return out;
    },
    'War Room': () => [
      { id: 'tmpl_cmd', label: 'Command Table', x: 0, y: 0, w: 220, h: 140, floor_color: '#2a1818', walled: true, rotation: 0, raised: 4 },
      { id: 'tmpl_sit', label: 'Situation Wall', x: -260, y: 0, w: 140, h: 200, floor_color: '#231414', walled: 'partial', rotation: 0, raised: 0 },
      { id: 'tmpl_str', label: 'Strategy Pit', x: 260, y: 0, w: 140, h: 200, floor_color: '#231414', walled: 'partial', rotation: 0, raised: 0 },
      { id: 'tmpl_ops', label: 'Ops Bench', x: 0, y: 220, w: 280, h: 90, floor_color: '#1f1414', walled: false, rotation: 0, raised: 0 },
    ],
    "Writers' Circle": () => {
      const out = [];
      out.push({ id: 'wc_table', label: 'Long Table', x: 0, y: 0, w: 320, h: 80, floor_color: '#2a2418', walled: false, rotation: 0, raised: 0 });
      for (let i = 0; i < 4; i++) {
        const a = (i / 4) * Math.PI * 2 + Math.PI / 4;
        out.push({
          id: 'wc_desk_' + i, label: 'Writer Desk ' + (i + 1),
          x: Math.round(Math.cos(a) * 320 / 10) * 10,
          y: Math.round(Math.sin(a) * 320 / 10) * 10,
          w: 140, h: 110, floor_color: '#2c1f12', walled: 'partial', rotation: 0, raised: 0,
        });
      }
      return out;
    },
    'L-Shape': () => [
      { id: 'l_arm_a', label: 'L · Arm A', x: -120, y: 0, w: 280, h: 140, floor_color: '#1c1a28', walled: 'partial', rotation: 0, raised: 0 },
      { id: 'l_arm_b', label: 'L · Arm B', x: 0, y: -160, w: 140, h: 200, floor_color: '#1d1b2a', walled: 'partial', rotation: 0, raised: 0 },
    ],
    'Campus Cluster': () => [
      { id: 'cc_quad',     label: 'Quad',     x:    0, y:    0, w: 240, h: 200, floor_color: '#1c1c20', walled: false },
      { id: 'cc_north',    label: 'North Hall', x:    0, y:  300, w: 200, h: 120, floor_color: '#1a1c28', walled: true },
      { id: 'cc_south',    label: 'South Hall', x:    0, y: -300, w: 200, h: 120, floor_color: '#1d1d22', walled: true },
      { id: 'cc_east',     label: 'East Wing',  x:  340, y:    0, w: 140, h: 240, floor_color: '#221a26', walled: true },
      { id: 'cc_west',     label: 'West Wing',  x: -340, y:    0, w: 140, h: 240, floor_color: '#1f1c2e', walled: true },
    ],
  };

  function TemplateMenu({ onClose }) {
    const apply = (name) => {
      const tmpl = TEMPLATES[name]();
      window.EDITOR_STATE.update(s => {
        // assign unique IDs if collision
        for (const t of tmpl) {
          let id = t.id, n = 1;
          while (s.sections.find(x => x.id === id)) { id = t.id + '_' + n; n++; }
          t.id = id;
          s.sections.push(t);
        }
      }, 'geometry');
      onClose();
    };
    return (
      <div style={modalBg} onClick={onClose}>
        <div style={modalBox} onClick={(e) => e.stopPropagation()}>
          <div style={modalHead}>
            <span style={{ color: '#46d9c5', fontFamily: 'ui-monospace, Menlo, monospace',
              fontSize: 12, letterSpacing: '0.10em', textTransform: 'uppercase' }}>
              Section Templates
            </span>
          </div>
          <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.keys(TEMPLATES).map(name => (
              <button key={name} onClick={() => apply(name)} style={tplRow}>
                <span style={{ flex: 1, color: '#d8dde9', fontWeight: 600 }}>{name}</span>
                <span style={{ color: 'rgba(184,196,224,0.55)', fontSize: 10.5 }}>
                  {TEMPLATES[name]().length} sections
                </span>
              </button>
            ))}
          </div>
          <div style={{ padding: 12, borderTop: '1px solid rgba(184,196,224,0.14)', textAlign: 'right' }}>
            <button className="btn" onClick={onClose}>Cancel</button>
          </div>
        </div>
      </div>
    );
  }

  const modalBg = {
    position: 'fixed', inset: 0, background: 'rgba(6,7,11,0.78)',
    backdropFilter: 'blur(6px)', zIndex: 100,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  };
  const modalBox = {
    width: 420, background: '#0e1018',
    border: '1px solid rgba(184,196,224,0.22)', borderRadius: 10,
    overflow: 'hidden',
  };
  const modalHead = {
    padding: '14px 18px', borderBottom: '1px solid rgba(184,196,224,0.14)',
  };
  const tplRow = {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '10px 14px', background: 'transparent',
    border: '1px solid rgba(184,196,224,0.14)', borderRadius: 6,
    fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12,
    color: '#d8dde9', cursor: 'pointer', textAlign: 'left',
  };

  // ─── Editor Toolbar Augmentation (Undo / Redo / Templates) ──
  function EditorTopButtons() {
    const [tplOpen, setTplOpen] = useState(false);
    const [, setForce] = useState(0);
    // Force re-render on history change (poll lightly)
    useEffect(() => {
      const id = setInterval(() => setForce(n => n + 1), 600);
      return () => clearInterval(id);
    }, []);
    return (
      <div style={{ position: 'fixed', top: 8, right: 360, zIndex: 35, display: 'flex', gap: 6 }}>
        <button className="btn" disabled={!window.EDITOR_UNDO.canUndo()} onClick={() => window.EDITOR_UNDO.undo()} title="Undo (Cmd+Z)">↶ Undo</button>
        <button className="btn" disabled={!window.EDITOR_UNDO.canRedo()} onClick={() => window.EDITOR_UNDO.redo()} title="Redo (Cmd+Shift+Z)">↷ Redo</button>
        <button className="btn" onClick={() => setTplOpen(true)} title="Insert a section template">+ Template</button>
        {tplOpen && <TemplateMenu onClose={() => setTplOpen(false)} />}
      </div>
    );
  }

  // Mount alongside the canvas only when Map Editor tab is active
  function mountToolbar() {
    const checkAndMount = () => {
      const state = window.EDITOR_STATE && window.EDITOR_STATE.get();
      if (!state) return setTimeout(checkAndMount, 200);
      if (state.editor.activeTab !== 'map') return;
      if (document.getElementById('editorToolbarMount')) return;
      const mount = document.createElement('div');
      mount.id = 'editorToolbarMount';
      document.body.appendChild(mount);
      const root = ReactDOM.createRoot(mount);
      root.render(<EditorTopButtons />);
    };
    setTimeout(checkAndMount, 800);
    if (window.EDITOR_STATE) {
      window.EDITOR_STATE.subscribe((_, kind) => {
        if (kind === 'tab') {
          const s = window.EDITOR_STATE.get();
          const existing = document.getElementById('editorToolbarMount');
          if (s.editor.activeTab !== 'map' && existing) existing.remove();
          if (s.editor.activeTab === 'map' && !existing) setTimeout(checkAndMount, 200);
        }
      });
    }
  }
  mountToolbar();

  // ─── Thumbnail auto-generator on export ─────────────
  if (window.EDITOR_EXPORT) {
    const origExport = window.EDITOR_EXPORT.exportWorld;
    window.EDITOR_EXPORT.exportWorld = function () {
      origExport();
      // also generate 400x225 thumbnail PNG from the spec
      const spec = window.EDITOR_EXPORT.toSpec(window.EDITOR_STATE.get());
      const cv = document.createElement('canvas');
      cv.width = 400; cv.height = 225;
      const ctx = cv.getContext('2d');
      ctx.fillStyle = '#06070b'; ctx.fillRect(0, 0, 400, 225);
      const range = 3400;
      const scale = Math.min(400, 225) / range;
      const cx = 200, cy = 112;
      function w2sX(x) { return cx + x * scale; }
      function w2sY(y) { return cy - y * scale; }
      // boundary
      const b = spec.boundary || { north: 1600, south: -1600, east: 1600, west: -1600 };
      ctx.strokeStyle = 'rgba(70,217,197,0.22)';
      ctx.strokeRect(w2sX(b.west), w2sY(b.north), (b.east - b.west) * scale, (b.north - b.south) * scale);
      // ring
      if (spec.ring_road) {
        ctx.beginPath();
        ctx.arc(cx, cy, spec.ring_road.radius * scale, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(184,196,224,0.18)';
        ctx.lineWidth = (spec.ring_road.width || 60) * scale;
        ctx.stroke();
      }
      // roads
      for (const r of (spec.roads || [])) {
        if (!r.bezier) continue;
        ctx.beginPath();
        for (let i = 0; i <= 24; i++) {
          const t = i / 24, u = 1 - t;
          const p = {
            x: u*u*u*r.bezier[0].x + 3*u*u*t*r.bezier[1].x + 3*u*t*t*r.bezier[2].x + t*t*t*r.bezier[3].x,
            y: u*u*u*r.bezier[0].y + 3*u*u*t*r.bezier[1].y + 3*u*t*t*r.bezier[2].y + t*t*t*r.bezier[3].y,
          };
          if (i === 0) ctx.moveTo(w2sX(p.x), w2sY(p.y)); else ctx.lineTo(w2sX(p.x), w2sY(p.y));
        }
        ctx.strokeStyle = r.direction === 'out' ? 'rgba(70,217,197,0.6)' : 'rgba(255,157,109,0.4)';
        ctx.lineWidth = 2; ctx.stroke();
      }
      // sections
      for (const s of (spec.sections || [])) {
        ctx.fillStyle = (s.flags && s.flags.floor_color) || '#1c1a28';
        ctx.fillRect(w2sX(s.global_x - s.width / 2), w2sY(s.global_y + s.height / 2), s.width * scale, s.height * scale);
        ctx.strokeStyle = 'rgba(184,196,224,0.35)';
        ctx.lineWidth = 0.6;
        ctx.strokeRect(w2sX(s.global_x - s.width / 2), w2sY(s.global_y + s.height / 2), s.width * scale, s.height * scale);
      }
      // stations
      ctx.fillStyle = '#46d9c5';
      for (const st of (spec.stations || [])) {
        ctx.fillRect(w2sX(st.position.x) - 3, w2sY(st.position.y) - 3, 6, 6);
      }
      // brand
      ctx.fillStyle = '#46d9c5';
      ctx.font = 'bold 10px ui-monospace, Menlo, monospace';
      ctx.fillText('·· SIMUTUM ··', 10, 218);

      const url = cv.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = url; a.download = 'simutum_world_thumb.png';
      document.body.appendChild(a); a.click(); a.remove();
    };
  }

})();
