// editor-inspector.jsx — property panel for the selected element.
// Rendered inside MapEditor as <Inspector selected={...} ...>.

(function () {
  const { useEffect, useState } = React;

  function Inspector({ selected, state, onDelete }) {
    if (!selected) {
      return <GlobalInspector state={state} />;
    }
    const sel = state.editor.selection;
    return (
      <div className="inspector">
        <div className="inspector__head">
          <span>{sel.kind.toUpperCase()}</span>
          <span className="id">{sel.id}</span>
        </div>
        <div className="inspector__body">
          {sel.kind === 'section' && <SectionInspector item={selected} />}
          {sel.kind === 'road' && <RoadInspector item={selected} state={state} />}
          {sel.kind === 'stop' && <StopInspector item={selected} />}
          {sel.kind === 'station' && <StationInspector item={selected} state={state} />}
          {sel.kind === 'ghost' && <GhostInspector item={selected} />}
          <button className="btn-del" onClick={onDelete}>Delete {sel.kind}</button>
        </div>
      </div>
    );
  }

  // ── Field components ─────────────────────────────────────
  function Field({ label, children }) {
    return (
      <div className="field">
        <label>{label}</label>
        {children}
      </div>
    );
  }
  function TextField({ label, value, onChange }) {
    return (
      <Field label={label}>
        <input type="text" value={value || ''} onChange={(e) => onChange(e.target.value)} />
      </Field>
    );
  }
  function NumField({ label, value, onChange, min, max, step }) {
    return (
      <Field label={label}>
        <input type="number" value={value} step={step || 1} min={min} max={max}
          onChange={(e) => onChange(parseFloat(e.target.value) || 0)} />
      </Field>
    );
  }
  function Slider({ label, value, onChange, min, max, step, unit }) {
    return (
      <div className="field">
        <label>{label}</label>
        <div className="slider-row">
          <input type="range" min={min} max={max} step={step}
            value={value} onChange={(e) => onChange(parseFloat(e.target.value))} />
          <span className="val">{Math.round(value * 100) / 100}{unit || ''}</span>
        </div>
      </div>
    );
  }
  function Segs({ label, value, options, onChange }) {
    return (
      <div className="field">
        <label>{label}</label>
        <div className="segs">
          {options.map(o => (
            <button key={o.value || o} className={value === (o.value || o) ? 'active' : ''}
              onClick={() => onChange(o.value || o)}>{o.label || o}</button>
          ))}
        </div>
      </div>
    );
  }
  function Toggle({ label, value, onChange }) {
    return (
      <div className="field-inline">
        <label>{label}</label>
        <div className={'toggle' + (value ? ' on' : '')} onClick={() => onChange(!value)}>
          <div className="toggle__dot" />
        </div>
      </div>
    );
  }
  function SwatchRow({ label, value, options, onChange }) {
    return (
      <div className="field">
        <label>{label}</label>
        <div className="swatch-row">
          {options.map(c => (
            <div key={c} className={'swatch' + (value === c ? ' active' : '')}
              style={{ background: c }} onClick={() => onChange(c)} />
          ))}
        </div>
      </div>
    );
  }

  // ── Per-kind inspectors ───────────────────────────────────
  function SectionInspector({ item: s }) {
    const update = (fn) => window.EDITOR_STATE.update(st => {
      const t = st.sections.find(x => x.id === s.id);
      if (t) fn(t);
    }, 'geometry');
    return (
      <>
        <TextField label="Label" value={s.label} onChange={(v) => update(t => t.label = v)} />
        <div className="field-row">
          <NumField label="X" value={s.x} step={10} onChange={(v) => update(t => t.x = v)} />
          <NumField label="Y" value={s.y} step={10} onChange={(v) => update(t => t.y = v)} />
        </div>
        <div className="field-row">
          <NumField label="Width" value={s.w} step={10} onChange={(v) => update(t => t.w = Math.max(40, v))} />
          <NumField label="Height" value={s.h} step={10} onChange={(v) => update(t => t.h = Math.max(40, v))} />
        </div>
        <Slider label="Rotation" value={s.rotation || 0} min={-180} max={180} step={5}
          unit="°" onChange={(v) => update(t => t.rotation = v)} />
        <SwatchRow label="Floor color" value={s.floor_color}
          options={['#1e1b30', '#1a1826', '#1c1a2a', '#181e28', '#1a1a22', '#201e2e', '#1c1a28']}
          onChange={(v) => update(t => t.floor_color = v)} />
        <Segs label="Walls" value={s.walled === true ? 'full' : (s.walled === 'partial' ? 'partial' : 'none')}
          options={[{value:'none',label:'None'},{value:'partial',label:'Partial'},{value:'full',label:'Full'}]}
          onChange={(v) => update(t => t.walled = (v === 'full' ? true : v === 'partial' ? 'partial' : false))} />
        <Slider label="Raised platform" value={s.raised || 0} min={0} max={20} step={1}
          unit="u" onChange={(v) => update(t => t.raised = v)} />
      </>
    );
  }

  function RoadInspector({ item: r, state }) {
    const update = (fn) => window.EDITOR_STATE.update(st => {
      const t = st.roads.find(x => x.id === r.id);
      if (t) fn(t);
    }, 'geometry');
    return (
      <>
        <TextField label="Label" value={r.label} onChange={(v) => update(t => t.label = v)} />
        <TextField label="Destination ID" value={r.destination}
          onChange={(v) => update(t => t.destination = v)} />
        <Segs label="Theme" value={r.theme}
          options={['warm', 'amber', 'cyan', 'purple', 'white']}
          onChange={(v) => update(t => t.theme = v)} />
        <Slider label="Width" value={r.width} min={40} max={120} step={4}
          unit="u" onChange={(v) => update(t => t.width = v)} />
        <Slider label="Curve intensity" value={r.intensity} min={0} max={2} step={0.05}
          onChange={(v) => update(t => t.intensity = v)} />
        <Slider label="Side offset" value={r.sideOffset} min={-400} max={400} step={20}
          unit="u" onChange={(v) => update(t => t.sideOffset = v)} />
        <div className="section-header">Start point (P0)</div>
        <div className="field-row">
          <NumField label="X" value={r.p0.x} step={10} onChange={(v) => update(t => t.p0 = { ...t.p0, x: v })} />
          <NumField label="Y" value={r.p0.y} step={10} onChange={(v) => update(t => t.p0 = { ...t.p0, y: v })} />
        </div>
        <div className="section-header">End point (P3)</div>
        <div className="field-row">
          <NumField label="X" value={r.p3.x} step={10} onChange={(v) => update(t => t.p3 = { ...t.p3, x: v })} />
          <NumField label="Y" value={r.p3.y} step={10} onChange={(v) => update(t => t.p3 = { ...t.p3, y: v })} />
        </div>
      </>
    );
  }

  function StopInspector({ item: stp }) {
    const update = (fn) => window.EDITOR_STATE.update(st => {
      const t = st.stops.find(x => x.id === stp.id);
      if (t) fn(t);
    }, 'geometry');
    return (
      <>
        <TextField label="POI" value={stp.poi} onChange={(v) => update(t => t.poi = v)} />
        <Slider label="Position along road" value={stp.t} min={0.05} max={0.95} step={0.01}
          onChange={(v) => update(t => t.t = v)} />
        <div className="section-header">Lighting</div>
        <SwatchRow label="Color" value={stp.lighting.color}
          options={['#f5b86b', '#ffd28a', '#f59a4a', '#ff7d4a', '#ff8b3a', '#e84a3c',
                    '#6dd8ff', '#9ae8ff', '#46d9c5', '#c279ff', '#ff7da6']}
          onChange={(v) => update(t => t.lighting = { ...t.lighting, color: v })} />
        <Slider label="Intensity" value={stp.lighting.intensity} min={0.2} max={2} step={0.1}
          onChange={(v) => update(t => t.lighting = { ...t.lighting, intensity: v })} />
        <Segs label="Type" value={stp.lighting.type}
          options={['steady', 'flicker', 'pulse', 'pool']}
          onChange={(v) => update(t => t.lighting = { ...t.lighting, type: v })} />
        <div className="section-header">Audio</div>
        <Segs label="Loop" value={stp.audio}
          options={['wind_low', 'wind_high', 'wind_reeds', 'transformer_hum', 'distant_chatter',
                    'crate_creak', 'engine_idle', 'insect_chirps', 'sensor_ping']}
          onChange={(v) => update(t => t.audio = v)} />
      </>
    );
  }

  function StationInspector({ item: st, state }) {
    const update = (fn) => window.EDITOR_STATE.update(s => {
      const t = s.stations.find(x => x.id === st.id);
      if (t) fn(t);
    }, 'geometry');
    return (
      <>
        <TextField label="Label" value={st.label} onChange={(v) => update(t => t.label = v)} />
        <TextField label="Target pack" value={st.target_pack}
          onChange={(v) => update(t => t.target_pack = v)} />
        <div className="field-row">
          <NumField label="X" value={st.x} step={10} onChange={(v) => update(t => t.x = v)} />
          <NumField label="Y" value={st.y} step={10} onChange={(v) => update(t => t.y = v)} />
        </div>
      </>
    );
  }

  function GhostInspector({ item: g }) {
    const update = (fn) => window.EDITOR_STATE.update(s => {
      const t = s.ghostPacks.find(x => x.id === g.id);
      if (t) fn(t);
    }, 'geometry');
    return (
      <>
        <Segs label="Kind" value={g.kind}
          options={['theater', 'bar', 'field', 'lab', 'custom']}
          onChange={(v) => update(t => t.kind = v)} />
        <div className="field-row">
          <NumField label="X" value={g.x} step={20} onChange={(v) => update(t => t.x = v)} />
          <NumField label="Y" value={g.y} step={20} onChange={(v) => update(t => t.y = v)} />
        </div>
        <div className="field-row">
          <NumField label="Width" value={g.w} step={20} onChange={(v) => update(t => t.w = Math.max(50, v))} />
          <NumField label="Height" value={g.h} step={20} onChange={(v) => update(t => t.h = Math.max(50, v))} />
        </div>
        <SwatchRow label="Color" value={g.color}
          options={['#1a1a2e', '#181e1a', '#1e1a1a', '#1a1a22', '#1c1c1c']}
          onChange={(v) => update(t => t.color = v)} />
      </>
    );
  }

  // ── Global inspector (when nothing is selected) ──────────
  function GlobalInspector({ state }) {
    const update = (fn) => window.EDITOR_STATE.update(s => fn(s), 'geometry');
    return (
      <div className="inspector empty">
        <div className="inspector__head">
          <span>WORLD</span>
          <span className="id">{state.meta.name}</span>
        </div>
        <div className="inspector__body">
          <TextField label="World name" value={state.meta.name}
            onChange={(v) => update(s => s.meta.name = v)} />

          <div className="section-header">Ring road</div>
          <Toggle label="Enabled" value={state.ringRoad.enabled}
            onChange={(v) => update(s => s.ringRoad.enabled = v)} />
          <Slider label="Radius" value={state.ringRoad.radius} min={400} max={1400} step={20}
            unit="u" onChange={(v) => update(s => s.ringRoad.radius = v)} />
          <Slider label="Width" value={state.ringRoad.width} min={30} max={120} step={5}
            unit="u" onChange={(v) => update(s => s.ringRoad.width = v)} />

          <div className="section-header">Boundary</div>
          <div className="field-row">
            <NumField label="North" value={state.boundary.north} step={50}
              onChange={(v) => update(s => s.boundary.north = v)} />
            <NumField label="South" value={state.boundary.south} step={50}
              onChange={(v) => update(s => s.boundary.south = v)} />
          </div>
          <div className="field-row">
            <NumField label="East" value={state.boundary.east} step={50}
              onChange={(v) => update(s => s.boundary.east = v)} />
            <NumField label="West" value={state.boundary.west} step={50}
              onChange={(v) => update(s => s.boundary.west = v)} />
          </div>

          <div className="section-header">Easter eggs</div>
          <Toggle label="North wall" value={state.eggs.north}
            onChange={(v) => update(s => s.eggs.north = v)} />
          <Toggle label="South wall" value={state.eggs.south}
            onChange={(v) => update(s => s.eggs.south = v)} />
          <Toggle label="East wall" value={state.eggs.east}
            onChange={(v) => update(s => s.eggs.east = v)} />
          <Toggle label="West wall" value={state.eggs.west}
            onChange={(v) => update(s => s.eggs.west = v)} />

          <div className="section-header">Editor</div>
          <Slider label="Grid size" value={state.editor.gridSize} min={5} max={50} step={5}
            unit="u" onChange={(v) => update(s => s.editor.gridSize = v)} />
        </div>
      </div>
    );
  }

  window.Inspector = Inspector;
})();
