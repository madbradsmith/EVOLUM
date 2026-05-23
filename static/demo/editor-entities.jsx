// editor-entities.jsx — Entity Editor tab.
//
// Grid of cast cards. Each card has: name, role, avatar type, color,
// spawn section, agenda sliders, preset buttons, and a rotating avatar preview.

const { useState, useEffect } = React;

const AGENT_PRESETS = {
  'Coordinator':   { office: 0.20, square: 0.45, stop: 0.15, intersection: 0.15, boundary: 0.05 },
  'Explorer':      { office: 0.15, square: 0.15, stop: 0.15, intersection: 0.15, boundary: 0.40 },
  'Analyst':       { office: 0.30, square: 0.10, stop: 0.40, intersection: 0.10, boundary: 0.10 },
  'Scribe':        { office: 0.20, square: 0.25, stop: 0.40, intersection: 0.10, boundary: 0.05 },
  'Designer':      { office: 0.40, square: 0.30, stop: 0.20, intersection: 0.05, boundary: 0.05 },
  'Auditor':       { office: 0.15, square: 0.10, stop: 0.15, intersection: 0.25, boundary: 0.35 },
  'Friend Maker':  { office: 0.20, square: 0.40, stop: 0.30, intersection: 0.05, boundary: 0.05 },
};

const ENTITY_COLORS = [
  '#6db8ff', '#e0c46d', '#ff7da6', '#79e5b8', '#ff9d6d', '#c279ff',
  '#46d9c5', '#ffd86d', '#9ae8ff', '#ff5e8a', '#a4e36d', '#d8a26d',
];

function EntityEditor() {
  const [state, setState] = useState(window.EDITOR_STATE.get());
  const [rosterOpen, setRosterOpen] = useState(false);
  const [roster, setRoster] = useState([]);

  useEffect(() => window.EDITOR_STATE.subscribe((s) => setState({ ...s })), []);

  const addEntity = () => {
    if (state.cast.length >= 8) return;
    window.EDITOR_STATE.update(s => {
      const i = s.cast.length;
      s.cast.push({
        name: 'Entity ' + (i + 1),
        role: 'role',
        color: ENTITY_COLORS[i % ENTITY_COLORS.length],
        type: 'anchor',
        spawn: s.sections[0] ? s.sections[0].id : '',
        agenda: AGENT_PRESETS['Friend Maker'],
      });
    }, 'cast');
  };

  const loadRoster = () => {
    if (roster.length) { setRosterOpen(true); return; }
    fetch('simutum_cast_roster.json').then(r => r.json()).then(list => {
      setRoster(list); setRosterOpen(true);
    }).catch(e => alert('Roster load failed: ' + e.message));
  };

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div className="entity-toolbar">
        <h2>Cast · {state.cast.length} / 8</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" onClick={loadRoster}>↑ Load from Roster</button>
          <button className="btn" onClick={() => window.EDITOR_EXPORT.exportCast()}>
            ↓ Export cast JSON
          </button>
          <button className="btn primary" disabled={state.cast.length >= 8} onClick={addEntity}>
            + Add Entity
          </button>
        </div>
      </div>
      <div className="entity-grid">
        {state.cast.map((c, i) => (
          <EntityCard key={i} cast={c} index={i} state={state} />
        ))}
        {state.cast.length === 0 && (
          <div style={{ gridColumn: '1 / -1', padding: 40, textAlign: 'center',
            color: 'rgba(184,196,224,0.45)', fontFamily: 'ui-monospace, Menlo, monospace',
            fontSize: 12, letterSpacing: '0.04em' }}>
            No entities yet. Click <strong style={{color:'#46d9c5'}}>+ Add Entity</strong> or <strong style={{color:'#46d9c5'}}>↑ Load from Roster</strong>.
          </div>
        )}
      </div>
      {rosterOpen && <RosterPicker roster={roster} state={state}
        onClose={() => setRosterOpen(false)} />}
    </div>
  );
}

function RosterPicker({ roster, state, onClose }) {
  const [picked, setPicked] = useState(new Set());
  const toggle = (name) => setPicked(p => {
    const c = new Set(p);
    if (c.has(name)) c.delete(name);
    else if (c.size + state.cast.length < 8) c.add(name);
    return c;
  });
  const confirm = () => {
    window.EDITOR_STATE.update(s => {
      for (const name of picked) {
        if (s.cast.length >= 8) break;
        const def = roster.find(r => r.name === name);
        if (!def) continue;
        s.cast.push({
          name: def.name, role: def.role, color: def.color, type: def.type,
          spawn: s.sections[0] ? s.sections[0].id : '',
          agenda: { ...def.agenda },
        });
      }
    }, 'cast');
    onClose();
  };
  return (
    <div style={modalBackdrop} onClick={onClose}>
      <div style={modalBox} onClick={(e) => e.stopPropagation()}>
        <div style={modalHead}>
          <span style={{ color: '#46d9c5', fontFamily: 'ui-monospace, Menlo, monospace',
            fontSize: 12, letterSpacing: '0.10em', textTransform: 'uppercase' }}>
            Cast Roster · {roster.length} characters
          </span>
          <span style={{ color: 'rgba(184,196,224,0.55)', fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10.5 }}>
            picked {picked.size} · slots open {Math.max(0, 8 - state.cast.length - picked.size)}
          </span>
        </div>
        <div style={modalBody}>
          {roster.map(r => (
            <div key={r.name} style={rosterRow(picked.has(r.name))}
              onClick={() => toggle(r.name)}>
              <div style={{ width: 14, height: 14, borderRadius: '50%', background: r.color, flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12,
                  color: '#d8dde9', fontWeight: 600 }}>{r.name}</div>
                <div style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
                  color: 'rgba(184,196,224,0.55)', letterSpacing: '0.04em' }}>
                  {r.role} · {r.type}
                </div>
              </div>
              <div style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 9,
                letterSpacing: '0.06em', color: 'rgba(184,196,224,0.4)',
                textTransform: 'uppercase', minWidth: 100, textAlign: 'right' }}>
                {topAgenda(r.agenda)}
              </div>
            </div>
          ))}
        </div>
        <div style={modalFoot}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" disabled={picked.size === 0} onClick={confirm}>
            Add {picked.size} to cast
          </button>
        </div>
      </div>
    </div>
  );
}

function topAgenda(a) {
  const entries = Object.entries(a).sort((x, y) => y[1] - x[1]);
  return entries[0][0] + ' ' + Math.round(entries[0][1] * 100) + '%';
}

const modalBackdrop = {
  position: 'fixed', inset: 0, background: 'rgba(6,7,11,0.78)',
  backdropFilter: 'blur(6px)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 100,
};
const modalBox = {
  width: 540, maxWidth: 'calc(100% - 40px)',
  maxHeight: 'calc(100% - 80px)',
  background: '#0e1018', border: '1px solid rgba(184,196,224,0.22)',
  borderRadius: 10, display: 'flex', flexDirection: 'column',
  overflow: 'hidden',
};
const modalHead = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '14px 18px', borderBottom: '1px solid rgba(184,196,224,0.14)',
};
const modalBody = {
  flex: 1, overflowY: 'auto', padding: '8px 12px',
  display: 'flex', flexDirection: 'column', gap: 4,
};
const modalFoot = {
  display: 'flex', justifyContent: 'flex-end', gap: 8,
  padding: 14, borderTop: '1px solid rgba(184,196,224,0.14)',
};
const rosterRow = (picked) => ({
  display: 'flex', alignItems: 'center', gap: 12,
  padding: '8px 12px',
  background: picked ? 'rgba(70,217,197,0.12)' : 'transparent',
  border: '1px solid ' + (picked ? '#46d9c5' : 'transparent'),
  borderRadius: 5,
  cursor: 'pointer',
});

function EntityCard({ cast: c, index, state }) {
  const update = (fn) => window.EDITOR_STATE.update(s => {
    if (s.cast[index]) fn(s.cast[index]);
  }, 'cast');

  const removeMe = () => {
    if (!confirm('Remove ' + c.name + '?')) return;
    window.EDITOR_STATE.update(s => { s.cast.splice(index, 1); }, 'cast');
  };

  const setPreset = (name) => {
    update(t => { t.agenda = { ...AGENT_PRESETS[name] }; });
  };

  // Identify which preset (if any) the agenda currently matches.
  const activePreset = (() => {
    const ag = c.agenda || {};
    for (const [name, preset] of Object.entries(AGENT_PRESETS)) {
      let close = true;
      for (const k of ['office','square','stop','intersection','boundary']) {
        if (Math.abs((ag[k] || 0) - (preset[k] || 0)) > 0.001) { close = false; break; }
      }
      if (close) return name;
    }
    return null;
  })();

  return (
    <div className="entity-card">
      <div className="entity-card__head">
        <AvatarPreview type={c.type} color={c.color} />
        <div className="entity-card__head__meta">
          <input type="text" value={c.name} onChange={(e) => update(t => t.name = e.target.value)} />
          <input type="text" className="role-input" value={c.role}
            placeholder="role" onChange={(e) => update(t => t.role = e.target.value)} />
        </div>
      </div>

      <div className="segs">
        {['anchor', 'thinker', 'creative'].map(typ => (
          <button key={typ} className={c.type === typ ? 'active' : ''}
            onClick={() => update(t => t.type = typ)}>{typ}</button>
        ))}
      </div>

      <div className="swatch-row">
        {ENTITY_COLORS.map(col => (
          <div key={col} className={'swatch' + (c.color === col ? ' active' : '')}
            style={{ background: col }}
            onClick={() => update(t => t.color = col)} />
        ))}
      </div>

      <div className="field">
        <label>Spawn section</label>
        <select value={c.spawn} onChange={(e) => update(t => t.spawn = e.target.value)}>
          <option value="">— pick a section —</option>
          {state.sections.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </div>

      <div className="section-header">Agenda presets</div>
      <div className="preset-row">
        {Object.keys(AGENT_PRESETS).map(name => (
          <button key={name} className={'preset-btn' + (activePreset === name ? ' active' : '')}
            onClick={() => setPreset(name)}>{name}</button>
        ))}
      </div>

      <div className="section-header">Agenda weights</div>
      <AgendaSliders agenda={c.agenda} update={update} />

      <button className="btn-del" onClick={removeMe}>Remove entity</button>
    </div>
  );
}

function AgendaSliders({ agenda, update }) {
  const keys = ['office','square','stop','intersection','boundary'];
  const ag = agenda || {};
  const total = keys.reduce((a, k) => a + (ag[k] || 0), 0) || 1;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      {keys.map(k => (
        <div className="slider-row" key={k} style={{ alignItems: 'center', gap: 8 }}>
          <span style={{ width: 70, fontSize: 9.5, letterSpacing: '0.06em',
            textTransform: 'uppercase', color: 'rgba(184,196,224,0.55)' }}>{k}</span>
          <input type="range" min={0} max={1} step={0.05} style={{ flex: 1, accentColor: '#46d9c5' }}
            value={ag[k] || 0}
            onChange={(e) => update(t => { t.agenda = { ...(t.agenda || {}), [k]: parseFloat(e.target.value) }; })} />
          <span className="val">{Math.round((ag[k] || 0) / total * 100)}%</span>
        </div>
      ))}
    </div>
  );
}

// SVG avatar preview — matches Game World runtime shapes.
function AvatarPreview({ type, color }) {
  const [angle, setAngle] = useState(0);
  useEffect(() => {
    let frame;
    const tick = () => {
      setAngle(a => a + 0.6);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, []);

  // body dimensions per type (mirror the runtime)
  const conf = type === 'thinker'
    ? { headW: 13, headH: 15, bodyW: 9, bodyH: 18, neckH: 7 }
    : type === 'anchor'
      ? { headW: 14, headH: 11, bodyW: 11, bodyH: 14, neckH: 5 }
      : { headW: 14, headH: 14, bodyW: 11, bodyH: 16, neckH: 6, torus: true };

  // SVG units → fit 80x110 viewBox. 1 world u = ~2 px.
  // Apply a slight 3D tilt via Y skew based on rotation angle.
  const r = (Math.sin(angle * Math.PI / 180) * 0.5 + 0.5); // 0..1
  const skew = (r - 0.5) * 0.4; // pseudo perspective

  return (
    <svg className="entity-card__preview" viewBox="-40 -10 80 110" preserveAspectRatio="xMidYMid meet">
      <defs>
        <radialGradient id={'pad' + color.slice(1)}>
          <stop offset="0" stopColor={color} stopOpacity="0.35" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </radialGradient>
      </defs>
      <ellipse cx="0" cy="94" rx="22" ry="6" fill={`url(#pad${color.slice(1)})`} />
      {/* body */}
      <ellipse cx={skew * 6} cy={94 - conf.bodyH / 2}
        rx={conf.bodyW / 2 * (1 + r * 0.04)}
        ry={conf.bodyH / 2}
        fill={darken(color, 0.4, 0.3)}
        opacity={0.92} />
      {/* torus (creative) */}
      {conf.torus && (
        <ellipse cx={skew * 6} cy={94 - conf.bodyH + 6}
          rx={(conf.bodyW / 2 + 1) * (1 + r * 0.04)} ry="1.5"
          fill={color} opacity="0.85" />
      )}
      {/* neck */}
      <rect x={skew * 6 - 2.4} y={94 - conf.bodyH - conf.neckH}
        width="4.8" height={conf.neckH}
        fill={darken(color, 0.4, 0.3)} />
      {/* head */}
      <ellipse cx={skew * 6} cy={94 - conf.bodyH - conf.neckH - conf.headH / 2}
        rx={conf.headW / 2} ry={conf.headH / 2}
        fill={color} />
    </svg>
  );
}

function darken(hex, satFac, lumFac) {
  const c = hex.replace('#', '');
  const R = parseInt(c.slice(0, 2), 16);
  const G = parseInt(c.slice(2, 4), 16);
  const B = parseInt(c.slice(4, 6), 16);
  const max = Math.max(R, G, B);
  const lum = max * (1 - lumFac);
  const avg = (R + G + B) / 3;
  const blend = (v) => Math.round(v * (1 - satFac) + avg * satFac) * (lum / (max || 1));
  const toHex = (v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0');
  return '#' + toHex(blend(R)) + toHex(blend(G)) + toHex(blend(B));
}

window.EntityEditor = EntityEditor;
