// app.jsx — Tweaks panel + entity feed.
// React lives only in the chrome overlay; the 3D scene is vanilla Babylon.

const { useState, useEffect, useRef } = React;

// Defaults persisted to disk via the host's __edit_mode_set_keys flow.
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "curveIntensity": 1.0,
  "ringRadius": 900,
  "lightingPalette": "destination",
  "trafficCycleSec": 8,
  "entitySpeed": 1.0,
  "showOverlay": true,
  "showLabels": true,
  "showFog": true,
  "sound": true
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [feed, setFeed] = useState([]);
  const [cameraMode, setCameraMode] = useState('top');

  // Push tweak values into the runtime state
  useEffect(() => {
    const S = window.SIMUTUM_STATE;
    if (!S) return;
    S.set('curveIntensity', t.curveIntensity);
    S.set('ringRadius', t.ringRadius);
    S.set('lightingPalette', t.lightingPalette);
    S.set('trafficCycleSec', t.trafficCycleSec);
    S.set('entitySpeed', t.entitySpeed);
    S.set('showOverlay', t.showOverlay);
    S.set('showLabels', t.showLabels);
    S.set('showFog', t.showFog);
    S.set('sound', t.sound);
  }, [t]);

  // Poll agents for their latest thoughts
  useEffect(() => {
    const id = setInterval(() => {
      const R = window.SIMUTUM_RUNTIME;
      if (!R) return;
      const agents = R.getAgents();
      const lines = [];
      for (const ag of agents) {
        const last = ag.thoughts[ag.thoughts.length - 1];
        if (last) {
          lines.push({ name: ag.name, color: ag.color, thought: last.thought, t: last.t });
        }
      }
      lines.sort((a, b) => b.t - a.t);
      setFeed(lines.slice(0, 6));
    }, 600);
    return () => clearInterval(id);
  }, []);

  const switchCam = (mode) => {
    setCameraMode(mode);
    window.SIMUTUM_RUNTIME.setCameraMode(mode);
  };

  return (
    <React.Fragment>
      {/* Camera controls — floating top-right */}
      <div style={camPillStyle}>
        <button onClick={() => switchCam('top')} style={camBtn(cameraMode === 'top')}>TOP DOWN</button>
        <button onClick={() => switchCam('fly')} style={camBtn(cameraMode === 'fly')}>FREE FLY</button>
        <button onClick={() => window.SIMUTUM_RUNTIME.exportJSON()} style={exportBtn}>↓ EXPORT JSON</button>
      </div>

      {/* Live entity feed — top-left */}
      <div style={feedStyle}>
        <div style={feedHead}>
          <span style={{ color: '#46d9c5' }}>● LIVE</span>
          <span> · ENTITIES ARE NOT ON A PROGRAM</span>
        </div>
        {feed.map((line, i) => (
          <div key={i} style={feedRow}>
            <span style={{ color: line.color, fontWeight: 700 }}>{line.name.toUpperCase()}</span>
            <span style={{ color: 'rgba(216,221,233,0.85)' }}> · {line.thought}</span>
          </div>
        ))}
        {feed.length === 0 && (
          <div style={{ ...feedRow, color: 'rgba(184,196,224,0.5)' }}>booting agents…</div>
        )}
      </div>

      {/* Tweaks panel */}
      <TweaksPanel>
        <TweakSection label="World" />
        <TweakSlider
          label="Curve intensity"
          value={t.curveIntensity}
          min={0} max={2} step={0.05}
          onChange={(v) => setTweak('curveIntensity', v)}
        />
        <TweakSlider
          label="Ring radius"
          value={t.ringRadius}
          min={700} max={1300} step={20} unit="u"
          onChange={(v) => setTweak('ringRadius', v)}
        />
        <TweakSlider
          label="Traffic cycle"
          value={t.trafficCycleSec}
          min={3} max={20} step={1} unit="s"
          onChange={(v) => setTweak('trafficCycleSec', v)}
        />
        <TweakSlider
          label="Entity speed"
          value={t.entitySpeed}
          min={0.2} max={3} step={0.1} unit="×"
          onChange={(v) => setTweak('entitySpeed', v)}
        />

        <TweakSection label="View" />
        <TweakToggle label="Top-down overlay"
          value={t.showOverlay} onChange={(v) => setTweak('showOverlay', v)} />
        <TweakToggle label="Section labels"
          value={t.showLabels} onChange={(v) => setTweak('showLabels', v)} />
        <TweakToggle label="Distance fog"
          value={t.showFog} onChange={(v) => setTweak('showFog', v)} />
        <TweakToggle label="Ambient sound"
          value={t.sound} onChange={(v) => setTweak('sound', v)} />
      </TweaksPanel>
    </React.Fragment>
  );
}

// ─── Styles ─────────────────────────────────────────────────────────
const camPillStyle = {
  position: 'fixed', top: 12, right: 12, zIndex: 50,
  display: 'flex', gap: 0,
  background: 'rgba(10,12,18,0.78)',
  backdropFilter: 'blur(8px)',
  border: '1px solid rgba(184,196,224,0.18)',
  borderRadius: 6,
  overflow: 'hidden',
  fontFamily: 'ui-monospace, Menlo, monospace',
};
const camBtn = (active) => ({
  border: 0,
  background: active ? 'rgba(70,217,197,0.18)' : 'transparent',
  color: active ? '#46d9c5' : '#b9c4e0',
  padding: '7px 12px',
  fontSize: 10.5,
  letterSpacing: '0.10em',
  textTransform: 'uppercase',
  cursor: 'pointer',
  borderRight: '1px solid rgba(184,196,224,0.12)',
  fontFamily: 'ui-monospace, Menlo, monospace',
});
const exportBtn = {
  border: 0,
  background: 'transparent',
  color: '#46d9c5',
  padding: '7px 12px',
  fontSize: 10.5,
  letterSpacing: '0.10em',
  textTransform: 'uppercase',
  cursor: 'pointer',
  fontFamily: 'ui-monospace, Menlo, monospace',
};
const feedStyle = {
  position: 'fixed', top: 64, left: 16, zIndex: 50,
  width: 360,
  background: 'rgba(10,12,18,0.78)',
  backdropFilter: 'blur(8px)',
  border: '1px solid rgba(184,196,224,0.18)',
  borderRadius: 6,
  padding: '10px 12px 8px',
  fontFamily: 'ui-monospace, Menlo, monospace',
  fontSize: 11,
  lineHeight: 1.55,
  color: '#d8dde9',
};
const feedHead = {
  fontSize: 9.5,
  letterSpacing: '0.10em',
  textTransform: 'uppercase',
  color: 'rgba(184,196,224,0.65)',
  marginBottom: 6,
  paddingBottom: 6,
  borderBottom: '1px solid rgba(184,196,224,0.12)',
};
const feedRow = {
  fontSize: 11,
  paddingTop: 3,
};

ReactDOM.createRoot(document.getElementById('app-root')).render(<App />);
