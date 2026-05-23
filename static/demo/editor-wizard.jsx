// editor-wizard.jsx — 3-screen onboarding wizard.
//
// On finish: builds a starter world, switches to Map Editor.

const { useState, useEffect } = React;

const VIBES = {
  'Open Office': { square: '#1e1b30', wall: '#2a2438', accent: '#46d9c5', sections: ['#1a1826','#1c1a2a','#181e28','#1a1a22','#201e2e','#1c1a28'] },
  'War Room':    { square: '#2a1a1a', wall: '#3a1c1c', accent: '#ff7d4a', sections: ['#2a1a1a','#1f1414','#2c1818','#231414','#2a1818','#1c1010'] },
  'Studio':      { square: '#1a1f2a', wall: '#262e3a', accent: '#9ae8ff', sections: ['#1a1f2a','#1a1d28','#1c1d2a','#181d24','#1d2030','#181d28'] },
};

const ROAD_THEMES = ['warm', 'amber', 'cyan', 'purple', 'white'];

function Wizard({ onFinish }) {
  const initial = window.EDITOR_STATE.get();
  const [step, setStep] = useState(0);
  const [data, setData] = useState({
    worldName: initial.meta.name === 'Untitled World' ? '' : initial.meta.name,
    homeName: 'The Square',
    teamSize: 4,
    vibe: 'Open Office',
    destinations: [
      { name: 'Theater', theme: 'warm',  enabled: true, hasStop: true },
      { name: 'Bar',     theme: 'amber', enabled: true, hasStop: true },
      { name: 'Lab',     theme: 'cyan',  enabled: true, hasStop: false },
    ],
    entities: Array.from({ length: 4 }, (_, i) => ({
      name: 'Entity ' + (i + 1),
      type: ['anchor','thinker','creative','anchor'][i] || 'anchor',
      color: ['#6db8ff','#ff7da6','#c279ff','#79e5b8'][i] || '#46d9c5',
      preset: ['Coordinator','Analyst','Designer','Friend Maker'][i] || 'Friend Maker',
    })),
  });

  // Keep entities array in sync with teamSize
  useEffect(() => {
    setData(d => {
      if (d.entities.length === d.teamSize) return d;
      const copy = { ...d };
      while (copy.entities.length < d.teamSize) {
        const i = copy.entities.length;
        copy.entities.push({
          name: 'Entity ' + (i + 1), type: 'anchor',
          color: ['#6db8ff','#e0c46d','#ff7da6','#79e5b8','#ff9d6d','#c279ff','#46d9c5','#ffd86d'][i] || '#46d9c5',
          preset: 'Friend Maker',
        });
      }
      copy.entities = copy.entities.slice(0, d.teamSize);
      return copy;
    });
  }, [data.teamSize]);

  const set = (key, val) => setData(d => ({ ...d, [key]: val }));
  const setEntity = (i, fn) => setData(d => {
    const copy = { ...d, entities: d.entities.slice() };
    copy.entities[i] = fn({ ...copy.entities[i] });
    return copy;
  });
  const setDest = (i, fn) => setData(d => {
    const copy = { ...d, destinations: d.destinations.slice() };
    copy.destinations[i] = fn({ ...copy.destinations[i] });
    return copy;
  });

  const finish = () => {
    const world = generateWorld(data);
    window.EDITOR_STATE.replace(world, 'wizard-finish');
    if (onFinish) onFinish();
  };

  return (
    <div className="wizard">
      <div className="wizard__card">
        <div className="wizard__step">Step {step + 1} of 3</div>
        {step === 0 && <Step1 data={data} set={set} />}
        {step === 1 && <Step2 data={data} setDest={setDest} />}
        {step === 2 && <Step3 data={data} setEntity={setEntity} />}
        <Nav step={step} setStep={setStep} finish={finish} canAdvance={canAdvance(step, data)} />
      </div>
    </div>
  );
}

function canAdvance(step, data) {
  if (step === 0) return data.worldName.trim().length > 0 && data.teamSize >= 2;
  if (step === 1) return data.destinations.some(d => d.enabled);
  if (step === 2) return data.entities.every(e => e.name.trim().length > 0);
  return true;
}

function Step1({ data, set }) {
  return (
    <>
      <h1 className="wizard__title">Name your world.</h1>
      <p className="wizard__sub">
        Tell us about the place. Who's there, what's it called, what's the vibe?
        We'll generate a starter map you can shape from there.
      </p>

      <div className="wizard__group">
        <label>What do you call this world?</label>
        <input type="text" autoFocus placeholder="Open Office, The Studio, HQ…"
          value={data.worldName} onChange={(e) => set('worldName', e.target.value)} />
      </div>

      <div className="wizard__group">
        <label>What do you call your team's home base?</label>
        <input type="text" placeholder="The Square"
          value={data.homeName} onChange={(e) => set('homeName', e.target.value)} />
      </div>

      <div className="wizard__group">
        <label>How many people?</label>
        <div className="wizard__options">
          {[2,3,4,5,6,7,8].map(n => (
            <button key={n}
              className={'wizard__opt' + (data.teamSize === n ? ' active' : '')}
              onClick={() => set('teamSize', n)}>
              {n}<small>entit{n===1?'y':'ies'}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="wizard__group">
        <label>What's the vibe?</label>
        <div className="wizard__options">
          {Object.entries(VIBES).map(([name, vibe]) => (
            <button key={name}
              className={'wizard__opt' + (data.vibe === name ? ' active' : '')}
              onClick={() => { set('vibe', name); }}>
              <span style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
                <span style={{ width: 14, height: 14, background: vibe.square, borderRadius: 3 }} />
                <span style={{ width: 14, height: 14, background: vibe.wall, borderRadius: 3 }} />
                <span style={{ width: 14, height: 14, background: vibe.accent, borderRadius: 3 }} />
              </span>
              {name}
              <small>{name === 'Open Office' ? 'loft, creative, dark indigo' :
                       name === 'War Room' ? 'urgent, focused, deep red' :
                       'precise, technical, cool steel'}</small>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}

function Step2({ data, setDest }) {
  return (
    <>
      <h1 className="wizard__title">Where do people go?</h1>
      <p className="wizard__sub">
        Each destination becomes a road out of the home base, with a station at the end.
        Leave a slot blank if you don't want one — you can always add more later.
      </p>

      <div className="wizard__group">
        <label>Destinations</label>
        {data.destinations.map((dest, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 8,
            padding: 12, border: '1px solid var(--s-border)', borderRadius: 6,
            background: 'rgba(6,7,11,0.4)' }}>
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <div className={'toggle' + (dest.enabled ? ' on' : '')}
                onClick={() => setDest(i, t => ({ ...t, enabled: !t.enabled }))}>
                <div className="toggle__dot" />
              </div>
              <input type="text" placeholder={'Destination ' + (i + 1)}
                disabled={!dest.enabled}
                style={{ flex: 1, fontSize: 13, opacity: dest.enabled ? 1 : 0.5 }}
                value={dest.name}
                onChange={(e) => setDest(i, t => ({ ...t, name: e.target.value }))} />
              <select disabled={!dest.enabled} value={dest.theme}
                onChange={(e) => setDest(i, t => ({ ...t, theme: e.target.value }))}
                style={{ opacity: dest.enabled ? 1 : 0.5 }}>
                {ROAD_THEMES.map(th => <option key={th} value={th}>{th}</option>)}
              </select>
            </div>
            <div className="field-inline" style={{ paddingLeft: 38, opacity: dest.enabled ? 1 : 0.4 }}>
              <label style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10,
                letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--s-text-3)' }}>
                Add a stop along the way
              </label>
              <div className={'toggle' + (dest.hasStop ? ' on' : '')}
                onClick={() => dest.enabled && setDest(i, t => ({ ...t, hasStop: !t.hasStop }))}>
                <div className="toggle__dot" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 10.5,
        color: 'var(--s-text-3)', lineHeight: 1.55,
        padding: '10px 14px', background: 'rgba(70,217,197,0.05)',
        border: '1px solid rgba(70,217,197,0.18)', borderRadius: 6 }}>
        Each road auto-generates an outbound + return pair (mirrored curves).
        Stops give your entities a reason to leave the home base.
      </div>
    </>
  );
}

function Step3({ data, setEntity }) {
  const presetNames = ['Coordinator','Explorer','Analyst','Scribe','Designer','Auditor','Friend Maker'];
  return (
    <>
      <h1 className="wizard__title">Who's in the room?</h1>
      <p className="wizard__sub">
        Name everyone. Pick how they show up (silhouette) and what their personality leans toward.
        These aren't roles — they're tendencies. Entities still pick their own moves.
      </p>

      <div className="wizard__group">
        <label>Cast</label>
        {data.entities.map((e, i) => (
          <div key={i} className="wizard__entity-row">
            <span className="num">{String(i+1).padStart(2,'0')}</span>
            <input type="text" value={e.name} placeholder="Name"
              onChange={(ev) => setEntity(i, t => ({ ...t, name: ev.target.value }))} />
            <select value={e.preset}
              onChange={(ev) => setEntity(i, t => ({ ...t, preset: ev.target.value }))}>
              {presetNames.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <div className="segs" style={{ minWidth: 130 }}>
                {['anchor','thinker','creative'].map(t => (
                  <button key={t} className={e.type === t ? 'active' : ''}
                    onClick={() => setEntity(i, x => ({ ...x, type: t }))}>{t.slice(0,1)}</button>
                ))}
              </div>
              <div className="swatch" style={{ background: e.color, cursor: 'pointer' }}
                onClick={() => {
                  const palette = ['#6db8ff','#e0c46d','#ff7da6','#79e5b8','#ff9d6d','#c279ff','#46d9c5','#ffd86d','#9ae8ff','#ff5e8a'];
                  const idx = palette.indexOf(e.color);
                  const next = palette[(idx + 1) % palette.length];
                  setEntity(i, t => ({ ...t, color: next }));
                }} />
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function Nav({ step, setStep, finish, canAdvance }) {
  return (
    <div className="wizard__nav">
      <div className="wizard__dots">
        {[0,1,2].map(i => <div key={i} className={'wizard__dot' + (i <= step ? ' active' : '')} />)}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {step > 0 && <button className="btn" onClick={() => setStep(step - 1)}>← Back</button>}
        {step < 2 && <button className="btn primary" disabled={!canAdvance}
          onClick={() => setStep(step + 1)}>Next →</button>}
        {step === 2 && <button className="btn primary" disabled={!canAdvance}
          onClick={finish}>Generate World →</button>}
      </div>
    </div>
  );
}

// ── World generation ─────────────────────────────────────────────────
function generateWorld(data) {
  const empty = window.EDITOR_STATE.EMPTY_WORLD();
  const palette = VIBES[data.vibe];

  empty.meta = { name: data.worldName, createdAt: Date.now(), version: 1 };

  // ── Sections ────────────────────────────────────────────
  // Center square + N satellite zones around it
  empty.sections.push({
    id: 'home_square', label: data.homeName,
    x: 0, y: 0, w: 220, h: 180,
    floor_color: palette.square,
    walled: false, rotation: 0, raised: 0,
  });
  const ringR = 320;
  const angles = ringAngles(data.teamSize);
  for (let i = 0; i < data.teamSize; i++) {
    const a = angles[i];
    const x = Math.round(Math.cos(a) * ringR / 10) * 10;
    const y = Math.round(Math.sin(a) * ringR / 10) * 10;
    const e = data.entities[i];
    empty.sections.push({
      id: 'sec_' + i,
      label: (e ? e.name : 'Zone ' + (i + 1)) + "'s spot",
      x, y, w: 140, h: 120,
      floor_color: palette.sections[i % palette.sections.length],
      walled: (i % 3 === 0) ? true : (i % 3 === 1 ? 'partial' : false),
      rotation: 0, raised: 0,
    });
  }

  // ── Roads (3 destinations) ──────────────────────────────
  const dests = data.destinations.filter(d => d.enabled);
  const destDirs = [
    { angle: -Math.PI / 2, label: 'south' },
    { angle: 0,             label: 'east' },
    { angle: Math.PI * 3/4, label: 'nw' },
  ];
  dests.forEach((d, i) => {
    const dir = destDirs[i] || { angle: Math.PI * (i + 1) / dests.length };
    const start = { x: Math.cos(dir.angle) * 460, y: Math.sin(dir.angle) * 460 };
    const end   = { x: Math.cos(dir.angle) * 1400, y: Math.sin(dir.angle) * 1400 };
    const id = 'road_' + d.name.toLowerCase().replace(/[^a-z0-9]/g, '_');
    const stationId = id + '_station';
    empty.roads.push({
      id, label: d.name + ' Road',
      destination: stationId,
      theme: d.theme, width: 80,
      p0: { x: Math.round(start.x / 10) * 10, y: Math.round(start.y / 10) * 10 },
      p3: { x: Math.round(end.x / 10) * 10,   y: Math.round(end.y / 10) * 10 },
      sideOffset: 240, intensity: 1.0,
    });
    empty.stations.push({
      id: stationId,
      x: Math.round(end.x / 10) * 10, y: Math.round(end.y / 10) * 10,
      label: ('THE ' + d.name).toUpperCase(),
      target_pack: d.name.toLowerCase(), road: id,
    });
    if (d.hasStop) {
      const themeColor = ({ warm: '#ffd28a', amber: '#ff8b3a', cyan: '#6dd8ff', purple: '#c279ff', white: '#e8edf8' })[d.theme] || '#ffd28a';
      empty.stops.push({
        id: id + '_stop_1',
        road: id, t: 0.55, poi: 'bench_cluster',
        lighting: { color: themeColor, intensity: 1.0, type: 'pool' },
        audio: 'distant_chatter',
      });
    }
  });

  // ── Cast (from wizard entities) ─────────────────────────
  empty.cast = data.entities.map((e, i) => ({
    name: e.name,
    role: e.preset.toLowerCase(),
    color: e.color,
    type: e.type,
    spawn: 'sec_' + i,
    agenda: window.AGENT_PRESETS ? { ...window.AGENT_PRESETS[e.preset] } :
      { office: 0.20, square: 0.30, stop: 0.25, intersection: 0.15, boundary: 0.10 },
  }));

  // ── Sensible defaults for everything else ───────────────
  empty.ringRoad = { enabled: true, radius: 900, width: 60 };
  empty.boundary = { north: 1600, south: -1600, east: 1600, west: -1600 };
  empty.eggs = { north: true, south: true, east: true, west: true };
  empty.ghostPacks = [];

  empty.editor = { activeTab: 'map', selection: null, camera: { x: 0, y: 0, zoom: 0.4 },
    gridSize: 10, previewPlay: true, wizardDone: true };

  return empty;
}

function ringAngles(n) {
  const out = [];
  for (let i = 0; i < n; i++) out.push((i / n) * Math.PI * 2 + Math.PI / 2);
  return out;
}

window.Wizard = Wizard;
