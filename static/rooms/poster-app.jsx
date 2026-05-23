/* =====================================================================
   EVOLUM Poster / Design — 2-zone dock (Chat | Poster preview)
   ===================================================================== */
const PosterApp = () => {
  const project = PROJECTS.find(p => p.id === 'p01');
  const [msgs, setMsgs] = React.useState(POSTER_MSGS_INIT);
  const [activeId, setActiveId] = React.useState('pv1');
  const [variants, setVariants] = React.useState(POSTER_VARIANTS);
  const [generating, setGenerating] = React.useState(false);

  const onGenerate = () => {
    setGenerating(true);
    setTimeout(() => setGenerating(false), 2200);
  };

  const config = {
    project,
    roomName: 'Poster · Design',
    panels: {
      chat:   { meta: { title: 'Design Director', icon: 'sparkle', sub: 'Hitchcock \u00b7 FAL' } },
      poster: { meta: { title: 'Poster Preview',  icon: 'poster',  sub: variants.find(v => v.id === activeId)?.label } },
    },
    renderPanel: (id) => {
      switch (id) {
        case 'chat':   return <DesignChat msgs={msgs} setMsgs={setMsgs} onGenerate={onGenerate}/>;
        case 'poster': return <PosterPanel activeId={activeId} setActiveId={setActiveId} variants={variants} generating={generating}/>;
        default: return null;
      }
    },
    statusItems: [
      { lbl:'VARIANTS', num: variants.length },
      { lbl:'ACTIVE',   num: variants.find(v => v.id === activeId)?.tone?.toUpperCase() || '—' },
      { lbl:'CREDITS',  num: '3 / 5 USED' },
    ],
    statusRight: (
      <React.Fragment>
        <span><span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:generating?'var(--accent)':'var(--ok)',marginRight:5,verticalAlign:'middle',boxShadow:generating?'0 0 6px var(--accent-glow)':'0 0 6px var(--ok-glow)'}}/>{generating ? 'FAL rendering\u2026' : 'FAL ready'}</span>
        <span>$1013.85 / $18.75 wk</span>
        <span>v1.4.0</span>
      </React.Fragment>
    ),
  };

  return <PosterRoom config={config}/>;
};

const PosterRoom = ({ config }) => {
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

  const [rightW, setRightW] = React.useState(440);

  const [panels, setPanels] = React.useState(() => ({
    chat:   { mode: 'docked', zone: 'main',  rect: null, z: 1 },
    poster: { mode: 'docked', zone: 'right', rect: null, z: 1 },
  }));
  const [focusId, setFocusId] = React.useState('chat');
  const zCounter = React.useRef(10);
  const [hoverZone, setHoverZone] = React.useState(null);
  const [activeDrag, setActiveDrag] = React.useState(null);

  const dockedRects = React.useMemo(() => {
    const hasRight = panels.poster.mode === 'docked';
    const rW = hasRight ? rightW : 0;
    const pad = 4;
    const mainW = canvas.w - (hasRight ? rW + pad : 0);
    const rects = {
      main:  { x: 0, y: 0, w: mainW, h: canvas.h },
      right: { x: canvas.w - rW, y: 0, w: rW, h: canvas.h },
    };
    const out = {};
    for (const [id, st] of Object.entries(panels)) if (st.mode === 'docked') out[id] = rects[st.zone];
    return out;
  }, [canvas, rightW, panels]);

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
        let zone = null;
        if (x > canvas.w - 80) zone = 'right';
        else if (x < 80) zone = 'main';
        setHoverZone(zone); setActiveDrag(id);
      } else if (drag.commit) {
        if (hoverZone) setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'docked', zone: hoverZone, _wasFloat: false } }));
        setHoverZone(null); setActiveDrag(null);
      }
    }
  };

  const recallAll = () => {
    setPanels({
      chat:   { mode: 'docked', zone: 'main',  rect: null, z: 1 },
      poster: { mode: 'docked', zone: 'right', rect: null, z: 1 },
    });
    setRightW(440);
  };

  const splitR = (e) => {
    e.preventDefault();
    const start = e.clientX, startW = rightW;
    const onMove = (ev) => setRightW(Math.max(300, Math.min(640, startW - (ev.clientX - start))));
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
  const showRSplit = panels.poster.mode === 'docked';
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
          <span style={{color:'var(--accent)'}}>{config.roomName}</span>
        </div>
        <div className="tl-spacer"/>
        <div className="tl-meta"><span className="dot"/><span>SYNC OK</span><span style={{color:'var(--line-3)'}}>·</span><span>{tc}</span></div>
      </div>

      <div className="menubar">
        <button>File</button><button>Edit</button><button>View</button><button>Render</button><button>Window</button><button>Help</button>
        <span className="mb-spacer"/>
        <a className="recall-btn" href="/studio/pitch" style={{marginRight:6, textDecoration:'none'}}><Icon name="pitch" size={11}/> Apply to Pitch Deck</a>
        <span className="layout-name">LAYOUT · DESIGN</span>
        <button className="recall-btn" onClick={recallAll}>{(minimizedIds.length||closedIds.length) ? 'RECALL ALL' : 'RESET LAYOUT'}</button>
      </div>

      <div className="workspace-canvas">
        <ToolRail active="poster" onPick={()=>{}}/>
        <div ref={canvasRef} style={{ position:'absolute', top:0, left:'var(--tool-rail-w)', right:0, bottom:0 }}>
          {activeDrag && (
            <React.Fragment>
              <div className={`dz ${hoverZone==='main'?'active':''}`}  style={{ left:0, top:0, width:80, height:'100%' }}>DOCK LEFT</div>
              <div className={`dz ${hoverZone==='right'?'active':''}`} style={{ right:0, top:0, width:80, height:'100%' }}>DOCK RIGHT</div>
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

          {showRSplit && <div onMouseDown={splitR} style={{ position:'absolute', top:0, bottom:0, width:5, left: canvas.w - rightW - 2, cursor:'ew-resize', zIndex:10 }}/>}

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

ReactDOM.createRoot(document.getElementById('app')).render(<PosterApp/>);
