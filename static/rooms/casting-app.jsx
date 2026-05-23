/* =====================================================================
   EVOLUM Self-Tape — simple actor recording room
   (4 docks: Sides | Studio | Backgrounds | Takes)
   No Evie, no RUN SCENE, no ROLES — just record and submit.
   ===================================================================== */
const CastingApp = () => {
  const project = PROJECTS.find(p => p.id === 'p01');
  const [bgId, setBgId] = React.useState('void');
  const [takes, setTakes] = React.useState([]);
  const [activeTakeId, setActiveTakeId] = React.useState(null);
  const [recording, setRecording] = React.useState(false);
  const [ready, setReady] = React.useState({ cam: false, mic: false, frame: false, audio: true });

  const addTake = (t) => setTakes(arr => [...arr, t]);
  const deleteTake = (id) => {
    setTakes(arr => arr.filter(t => {
      if (t.id === id) { try { URL.revokeObjectURL(t.url); } catch(e){} return false; }
      return true;
    }));
    if (activeTakeId === id) setActiveTakeId(null);
  };

  const config = {
    project,
    roomName: 'Self-Tape',
    panels: {
      sides:       { meta: { title: 'Sides', icon: 'script',  sub: SIDES.role } },
      studio:      { meta: { title: 'Self-Tape Studio', icon: 'film', sub: recording ? 'RECORDING' : 'Ready' } },
      backgrounds: { meta: { title: 'Backgrounds', icon: 'poster', sub: BACKGROUNDS.length + ' presets' } },
      takes:       { meta: { title: 'My Takes', icon: 'sizzle', sub: takes.length + (takes.length === 1 ? ' clip' : ' clips') } },
    },
    renderPanel: (id) => {
      switch (id) {
        case 'sides':       return <SidesPanel simple={true}/>;
        case 'studio':      return <TapeStudio bgId={bgId} takes={takes} addTake={addTake} recording={recording} setRecording={setRecording} ready={ready} setReady={setReady} takeNum={takes.length + 1}/>;
        case 'backgrounds': return <BackgroundPanel bgId={bgId} setBgId={setBgId}/>;
        case 'takes':       return <TakesStrip takes={takes} activeTakeId={activeTakeId} setActiveTakeId={setActiveTakeId} deleteTake={deleteTake}/>;
        default: return null;
      }
    },
    statusItems: [
      { lbl:'ROLE',  num: SIDES.role },
      { lbl:'SCENE', num: '01' },
      { lbl:'TAKES', num: takes.length },
      { lbl:'BG',    num: bgId.toUpperCase() },
    ],
    statusRight: (
      <React.Fragment>
        <span><span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:recording?'#ff3344':'var(--ok)',marginRight:5,verticalAlign:'middle',boxShadow:recording?'0 0 6px #ff3344':'0 0 6px var(--ok-glow)'}}/>{recording ? 'RECORDING' : 'Studio ready'}</span>
        <span>Powered by Claude · ElevenLabs · FAL</span>
        <span>v1.4.0</span>
      </React.Fragment>
    ),
  };

  return <CastingRoom config={config}/>;
};

const CastingRoom = ({ config }) => {
  const PANEL_META = Object.fromEntries(Object.entries(config.panels).map(([id, p]) => [id, p.meta]));
  const canvasRef = React.useRef(null);
  const [canvas, setCanvas] = React.useState({ w: 1200, h: 700 });
  React.useEffect(() => {
    const ro = new ResizeObserver(() => {
      const el = canvasRef.current; if (!el) return;
      const r = el.getBoundingClientRect();
      setCanvas({ w: Math.floor(r.width), h: Math.floor(r.height) });
    });
    if (canvasRef.current) ro.observe(canvasRef.current);
    return () => ro.disconnect();
  }, []);

  const [leftW, setLeftW] = React.useState(280);
  const [rightW, setRightW] = React.useState(260);
  const [bottomH, setBottomH] = React.useState(180);

  const [panels, setPanels] = React.useState(() => ({
    sides:       { mode: 'docked', zone: 'left',   rect: null, z: 1 },
    studio:      { mode: 'docked', zone: 'main',   rect: null, z: 1 },
    backgrounds: { mode: 'docked', zone: 'right',  rect: null, z: 1 },
    takes:       { mode: 'docked', zone: 'bottom', rect: null, z: 1 },
  }));
  const [focusId, setFocusId] = React.useState('studio');
  const zCounter = React.useRef(10);
  const [hoverZone, setHoverZone] = React.useState(null);
  const [activeDrag, setActiveDrag] = React.useState(null);

  const dockedRects = React.useMemo(() => {
    const hasLeft   = Object.values(panels).some(p => p.mode === 'docked' && p.zone === 'left');
    const hasRight  = Object.values(panels).some(p => p.mode === 'docked' && p.zone === 'right');
    const hasBottom = Object.values(panels).some(p => p.mode === 'docked' && p.zone === 'bottom');
    const lW = hasLeft ? leftW : 0;
    const rW = hasRight ? rightW : 0;
    const bH = hasBottom ? bottomH : 0;
    const pad = 4;
    const mainX = hasLeft ? lW + pad : 0;
    const mainW = canvas.w - mainX - (hasRight ? rW + pad : 0);
    const mainH = canvas.h - (hasBottom ? bH + pad : 0);
    const rects = {
      left:   { x: 0, y: 0, w: lW, h: canvas.h },
      main:   { x: mainX, y: 0, w: mainW, h: mainH },
      right:  { x: canvas.w - rW, y: 0, w: rW, h: canvas.h },
      bottom: { x: mainX, y: canvas.h - bH, w: mainW, h: bH },
    };
    const out = {};
    for (const [id, st] of Object.entries(panels)) if (st.mode === 'docked') out[id] = rects[st.zone];
    return out;
  }, [canvas, leftW, rightW, bottomH, panels]);

  const bringToFront = (id) => { zCounter.current += 1; setPanels(p => ({ ...p, [id]: { ...p[id], z: zCounter.current } })); setFocusId(id); };
  const minimize = (id) => setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'minimized' } }));
  const close    = (id) => setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'closed' } }));
  const undock = (id) => {
    const r = dockedRects[id] || { x: 80, y: 60, w: 380, h: 360 };
    const popped = { x: Math.max(8, r.x + 24), y: Math.max(8, r.y + 24),
                     w: Math.min(canvas.w - 60, Math.max(320, Math.floor(r.w * 0.7))),
                     h: Math.min(canvas.h - 60, Math.max(240, Math.floor(r.h * 0.7))) };
    zCounter.current += 1;
    setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'floating', rect: popped, z: zCounter.current, _wasFloat: true } }));
  };
  const dock = (id) => setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'docked', _wasFloat: false } }));

  const onPanelChange = (id, patch, drag) => {
    setPanels(p => {
      const cur = p[id]; const next = { ...cur, ...patch };
      if (patch.rect) next.rect = patch.rect;
      return { ...p, [id]: next };
    });
    if (drag) {
      if (drag.dragging && panels[id].mode === 'floating') {
        const canvasRect = canvasRef.current?.getBoundingClientRect();
        if (!canvasRect) return;
        const x = drag.x - canvasRect.left;
        const y = drag.y - canvasRect.top;
        let zone = null;
        if (x < 80) zone = 'left';
        else if (x > canvas.w - 80) zone = 'right';
        else if (y > canvas.h - 60) zone = 'bottom';
        setHoverZone(zone); setActiveDrag(id);
      } else if (drag.commit) {
        if (hoverZone) setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'docked', zone: hoverZone, _wasFloat: false } }));
        setHoverZone(null); setActiveDrag(null);
      }
    }
  };

  const recallAll = () => {
    setPanels({
      sides:       { mode: 'docked', zone: 'left', rect: null, z: 1 },
      studio:      { mode: 'docked', zone: 'main', rect: null, z: 1 },
      backgrounds: { mode: 'docked', zone: 'right', rect: null, z: 1 },
      takes:       { mode: 'docked', zone: 'bottom', rect: null, z: 1 },
    });
    setLeftW(280); setRightW(260); setBottomH(180);
  };

  const splitL = (e) => {
    e.preventDefault();
    const start = e.clientX, startW = leftW;
    const onMove = (ev) => setLeftW(Math.max(220, Math.min(440, startW + (ev.clientX - start))));
    const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
  };
  const splitR = (e) => {
    e.preventDefault();
    const start = e.clientX, startW = rightW;
    const onMove = (ev) => setRightW(Math.max(220, Math.min(420, startW - (ev.clientX - start))));
    const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
  };
  const splitB = (e) => {
    e.preventDefault();
    const start = e.clientY, startH = bottomH;
    const onMove = (ev) => setBottomH(Math.max(120, Math.min(canvas.h - 200, startH - (ev.clientY - start))));
    const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
  };

  const [now, setNow] = React.useState(new Date());
  React.useEffect(() => { const t = setInterval(()=>setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  const tc = now.toTimeString().slice(0, 8);

  const rectFor = (id) => {
    const st = panels[id];
    if (st.mode === 'floating') return st.rect || { x: 80, y: 80, w: 360, h: 320 };
    if (st.mode === 'docked')   return dockedRects[id] || { x: 0, y: 0, w: 0, h: 0 };
    return { x: 0, y: 0, w: 0, h: 0 };
  };
  const minimizedIds = Object.entries(panels).filter(([_,s])=>s.mode==='minimized').map(([id])=>id);
  const closedIds = Object.entries(panels).filter(([_,s])=>s.mode==='closed').map(([id])=>id);
  const showLSplit = panels.sides.mode === 'docked';
  const showRSplit = panels.backgrounds.mode === 'docked';
  const showBSplit = panels.takes.mode === 'docked';
  const project = config.project;

  return (
    <React.Fragment>
      <div className="titlebar">
        <div className="tl-lights"><span className="r"/><span className="y"/><span className="g"/></div>
        <div className="tl-brand"><span className="badge">EV</span><span>EVOLUM</span></div>
        <div className="tl-crumbs">
          <a href="/studio" style={{color:'var(--text-3)', textDecoration:'none'}}>Workspace</a>
          <span className="sep">/</span>
          <strong>{project.title}</strong>
          <span className="sep">/</span>
          <span style={{color:'var(--accent)'}}>{config.roomName || 'Self-Tape'}</span>
        </div>
        <div className="tl-spacer"/>
        <div className="tl-meta"><span className="dot"/><span>SYNC OK</span><span style={{color:'var(--line-3)'}}>·</span><span>{tc}</span></div>
      </div>

      <div className="menubar">
        <button>File</button><button>Edit</button><button>View</button><button>Camera</button><button>Window</button><button>Help</button>
        <span className="mb-spacer"/>
        <a className="recall-btn" href="/studio/audition" style={{ marginRight:6, textDecoration:'none' }}><Icon name="sparkle" size={11} className=""/> Switch to Audition</a>
        <span className="layout-name">LAYOUT · STUDIO</span>
        <button className="recall-btn" onClick={recallAll}>{(minimizedIds.length||closedIds.length) ? 'RECALL ALL' : 'RESET LAYOUT'}</button>
      </div>

      <div className="workspace-canvas">
        <ToolRail active="casting" onPick={()=>{}}/>
        <div ref={canvasRef} style={{ position:'absolute', top:0, left:'var(--tool-rail-w)', right:0, bottom:0 }}>
          {activeDrag && (
            <React.Fragment>
              <div className={`dz ${hoverZone==='left'?'active':''}`}   style={{ left:0, top:0, width:80, height:'100%' }}>DOCK LEFT</div>
              <div className={`dz ${hoverZone==='right'?'active':''}`}  style={{ right:0, top:0, width:80, height:'100%' }}>DOCK RIGHT</div>
              <div className={`dz ${hoverZone==='bottom'?'active':''}`} style={{ left:0, right:0, bottom:0, height:60 }}>DOCK BOTTOM</div>
            </React.Fragment>
          )}

          {Object.entries(panels).filter(([_,s])=>s.mode==='docked').map(([id, s]) => (
            <Panel key={id} id={id}
              title={PANEL_META[id].title} icon={PANEL_META[id].icon} sub={PANEL_META[id].sub}
              state={{ ...s, rect: rectFor(id), z: s.z }}
              focused={focusId===id}
              onFocus={bringToFront} onChange={onPanelChange}
              onMinimize={minimize} onClose={close} onUndock={undock} onDock={dock}>
              {config.renderPanel(id)}
            </Panel>
          ))}

          {showLSplit && <div onMouseDown={splitL} style={{ position:'absolute', top:0, bottom:0, width:5, left: leftW - 2, cursor:'ew-resize', zIndex:10 }}/>}
          {showRSplit && <div onMouseDown={splitR} style={{ position:'absolute', top:0, bottom:0, width:5, left: canvas.w - rightW - 2, cursor:'ew-resize', zIndex:10 }}/>}
          {showBSplit && <div onMouseDown={splitB} style={{ position:'absolute', left: showLSplit ? leftW + 4 : 0, right: showRSplit ? rightW + 4 : 0, height:5, top: canvas.h - bottomH - 2, cursor:'ns-resize', zIndex:10 }}/>}

          {Object.entries(panels).filter(([_,s])=>s.mode==='floating').map(([id, s]) => (
            <Panel key={id} id={id}
              title={PANEL_META[id].title} icon={PANEL_META[id].icon} sub={PANEL_META[id].sub}
              state={{ ...s, rect: rectFor(id), z: s.z }}
              focused={focusId===id}
              onFocus={bringToFront} onChange={onPanelChange}
              onMinimize={minimize} onClose={close} onUndock={undock} onDock={dock}>
              {config.renderPanel(id)}
            </Panel>
          ))}

          {minimizedIds.length > 0 && (
            <div className="dock-tray">
              {minimizedIds.map(id => (
                <button key={id} className="tab" onClick={()=>{
                  setPanels(p => ({ ...p, [id]: { ...p[id], mode: p[id]._wasFloat ? 'floating' : 'docked' } }));
                  bringToFront(id);
                }}>
                  <span className="ic"><Icon name={PANEL_META[id].icon} size={12}/></span>
                  {PANEL_META[id].title}
                </button>
              ))}
            </div>
          )}

          {closedIds.length > 0 && (
            <div style={{ position:'absolute', top:8, right: 12, zIndex:50, display:'flex', gap:6 }}>
              {closedIds.map(id => (
                <button key={id} className="dock-tray tab" style={{ position:'static' }}
                  onClick={()=>{ setPanels(p => ({ ...p, [id]: { ...p[id], mode: p[id]._wasFloat ? 'floating' : 'docked' } })); bringToFront(id); }}>
                  <Icon name="plus" size={11}/>
                  {PANEL_META[id].title}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="statusbar">
        {(config.statusItems || []).map((s,i) => (
          <div key={i} className="stat"><span className="lbl">{s.lbl}</span><span className="num">{s.num}</span></div>
        ))}
        <div className="sb-spacer"/>
        <div className="sb-right">{config.statusRight}</div>
      </div>
    </React.Fragment>
  );
};

ReactDOM.createRoot(document.getElementById('app')).render(<CastingApp/>);
