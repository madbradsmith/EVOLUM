/* =====================================================================
   EVOLUM Deliverables — 4-zone dock
   ===================================================================== */
const DeliverablesApp = () => {
  const project = PROJECTS.find(p => p.id === 'p01');
  const [activeCat, setActiveCat] = React.useState('all');
  const [selectedId, setSelectedId] = React.useState('d01');

  /* live document statuses + per-doc progress + build queue */
  const initialStatuses = () => {
    const o = {}; for (const d of DOCS) o[d.id] = d.status; return o;
  };
  const [docStatuses, setDocStatuses] = React.useState(initialStatuses);
  const [progress, setProgress] = React.useState({});
  const [queueItems, setQueueItems] = React.useState(BUILD_QUEUE);
  const [generating, setGenerating] = React.useState(false);
  const cancelRef = React.useRef(false);

  const nowStamp = () => new Date().toTimeString().slice(0, 8);

  /* generate a single doc — animate progress + push to queue */
  const generateOne = (docId) => new Promise((resolve) => {
    const doc = DOCS.find(x => x.id === docId);
    if (!doc) return resolve();
    setDocStatuses(s => ({ ...s, [docId]: 'generating' }));
    setProgress(p => ({ ...p, [docId]: 0 }));
    /* queue entry */
    setQueueItems(q => [
      { t: nowStamp(), who:'System', what:`Generating ${doc.name}\u2026`, tag: doc.cat === 'deal' ? 'invest' : (doc.cat === 'press' ? 'invest' : (doc.cat === 'production' ? 'deliver' : doc.cat)), state:'in-progress', pct: 0, docId },
      ...q
    ]);
    let pct = 0;
    const tick = () => {
      if (cancelRef.current) { resolve(); return; }
      pct = Math.min(100, pct + Math.round(8 + Math.random() * 14));
      setProgress(p => ({ ...p, [docId]: pct }));
      setQueueItems(q => q.map(it => it.docId === docId && it.state === 'in-progress' ? { ...it, pct } : it));
      if (pct < 100) {
        setTimeout(tick, 110);
      } else {
        setTimeout(() => {
          setDocStatuses(s => ({ ...s, [docId]: doc.status === 'configure' ? 'configure' : (doc.status === 'always' ? 'always' : 'ready') }));
          setProgress(p => { const c = { ...p }; delete c[docId]; return c; });
          setQueueItems(q => q.map(it => it.docId === docId ? { ...it, what:`${doc.name} \u00b7 ready`, state:'done', pct:100 } : it));
          resolve();
        }, 120);
      }
    };
    setTimeout(tick, 120);
  });

  const onGenerate = async (docId) => {
    cancelRef.current = false;
    await generateOne(docId);
  };

  const onGenerateAll = async () => {
    cancelRef.current = false;
    setGenerating(true);
    const pending = DOCS.filter(d => (docStatuses[d.id] === 'pending'));
    for (const d of pending) {
      if (cancelRef.current) break;
      await generateOne(d.id);
    }
    setGenerating(false);
  };

  const onReset = () => {
    cancelRef.current = true;
    setTimeout(() => {
      cancelRef.current = false;
      setDocStatuses(() => {
        const o = {};
        for (const d of DOCS) o[d.id] = d.status === 'configure' ? 'configure' : (d.status === 'always' ? 'always' : 'pending');
        return o;
      });
      setProgress({});
      setQueueItems([]);
      setGenerating(false);
    }, 200);
  };

  const readyCount = DOCS.filter(d => isReady(docStatuses[d.id])).length;
  const dealCount  = DOCS.filter(d => d.cat === 'deal').length;
  const buildingCount = Object.values(docStatuses).filter(s => s === 'generating').length;

  const totalMb = Math.round(DOCS.filter(d=>isReady(docStatuses[d.id])).reduce((acc,d)=>{
    const v = parseFloat(d.size); if (!v) return acc;
    return acc + (d.size?.includes('MB') ? v : v/1024);
  }, 0) * 10) / 10;

  const config = {
    project,
    roomName: 'Deliverables',
    panels: {
      categories: { meta: { title: 'Suites', icon: 'folder',  sub: D_CATS.length + ' categories' } },
      docs:       { meta: { title: 'Documents', icon: 'film', sub: readyCount + ' / ' + DOCS.length + ' ready' } },
      inspector:  { meta: { title: 'Inspector', icon: 'settings', sub: '' } },
      queue:      { meta: { title: 'Build Queue', icon: 'clock',   sub: buildingCount > 0
        ? <span><span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:'var(--accent)',marginRight:5,verticalAlign:'middle',boxShadow:'0 0 6px var(--accent-glow)'}}/>{buildingCount} BUILDING</span>
        : <span><span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:'var(--ok)',marginRight:5,verticalAlign:'middle',boxShadow:'0 0 6px var(--ok-glow)'}}/>IDLE</span>
      } },
    },
    renderPanel: (id) => {
      switch (id) {
        case 'categories': return <CategoriesPanel activeCat={activeCat} setActiveCat={setActiveCat} docStatuses={docStatuses}/>;
        case 'docs':       return <DocsTable project={project} activeCat={activeCat} selectedId={selectedId} setSelectedId={setSelectedId} docStatuses={docStatuses} progress={progress} generating={generating} onGenerate={onGenerate} onGenerateAll={onGenerateAll} onReset={onReset}/>;
        case 'inspector':  return <DocInspector selectedId={selectedId} docStatuses={docStatuses} progress={progress} onGenerate={onGenerate}/>;
        case 'queue':      return <BuildQueue items={queueItems}/>;
        default: return null;
      }
    },
    statusItems: [
      { lbl:'READY',   num: readyCount + '/' + DOCS.length },
      { lbl:'BUILD',   num: buildingCount },
      { lbl:'DEAL',    num: DOCS.filter(d=>d.cat==='deal' && isReady(docStatuses[d.id])).length + '/' + dealCount },
      { lbl:'TOTAL',   num: totalMb + ' MB' },
    ],
    statusRight: (
      <React.Fragment>
        <span>
          <span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background: buildingCount > 0 ? 'var(--accent)' : 'var(--ok)', marginRight:5,verticalAlign:'middle',boxShadow: buildingCount > 0 ? '0 0 6px var(--accent-glow)' : '0 0 6px var(--ok-glow)'}}/>
          {buildingCount > 0 ? `${buildingCount} building` : (readyCount === DOCS.length ? 'All complete' : 'Idle')}
        </span>
        <span>$1013.85 / $18.75 wk</span>
        <span>v1.4.0</span>
      </React.Fragment>
    ),
    /* expose actions for menu bar */
    _onGenerateAll: onGenerateAll,
    _onReset: onReset,
    _generating: generating,
    _readyCount: readyCount,
    _total: DOCS.length,
  };

  return <DeliverablesRoom config={config}/>;
};

const DeliverablesRoom = ({ config }) => {
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

  const [leftW, setLeftW] = React.useState(240);
  const [rightW, setRightW] = React.useState(340);
  const [bottomH, setBottomH] = React.useState(180);

  const [panels, setPanels] = React.useState(() => ({
    categories: { mode: 'docked', zone: 'left',   rect: null, z: 1 },
    docs:       { mode: 'docked', zone: 'main',   rect: null, z: 1 },
    inspector:  { mode: 'docked', zone: 'right',  rect: null, z: 1 },
    queue:      { mode: 'docked', zone: 'bottom', rect: null, z: 1 },
  }));
  const [focusId, setFocusId] = React.useState('docs');
  const zCounter = React.useRef(10);
  const [hoverZone, setHoverZone] = React.useState(null);
  const [activeDrag, setActiveDrag] = React.useState(null);

  const dockedRects = React.useMemo(() => {
    const zones = new Set(Object.values(panels).filter(p => p.mode === 'docked').map(p => p.zone));
    const hasLeft   = zones.has('left');
    const hasRight  = zones.has('right');
    const hasBottom = zones.has('bottom');
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
      categories: { mode: 'docked', zone: 'left',   rect: null, z: 1 },
      docs:       { mode: 'docked', zone: 'main',   rect: null, z: 1 },
      inspector:  { mode: 'docked', zone: 'right',  rect: null, z: 1 },
      queue:      { mode: 'docked', zone: 'bottom', rect: null, z: 1 },
    });
    setLeftW(240); setRightW(340); setBottomH(180);
  };

  const splitL = (e) => {
    e.preventDefault();
    const start = e.clientX, startW = leftW;
    const onMove = (ev) => setLeftW(Math.max(200, Math.min(360, startW + (ev.clientX - start))));
    const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
  };
  const splitR = (e) => {
    e.preventDefault();
    const start = e.clientX, startW = rightW;
    const onMove = (ev) => setRightW(Math.max(260, Math.min(520, startW - (ev.clientX - start))));
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
  const showLSplit = panels.categories.mode === 'docked';
  const showRSplit = panels.inspector.mode === 'docked';
  const showBSplit = panels.queue.mode === 'docked';
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
        <button>File</button><button>Edit</button><button>View</button><button>Generate</button><button>Window</button><button>Help</button>
        <span className="mb-spacer"/>
        {config._readyCount < config._total ? (
          <button className="btn primary" style={{padding:'3px 10px', marginRight:6}} disabled={config._generating} onClick={config._onGenerateAll}>
            <Icon name="sparkle" size={11}/> {config._generating ? 'Generating\u2026' : `Generate All (${config._total - config._readyCount} pending)`}
          </button>
        ) : (
          <button className="btn primary" style={{padding:'3px 10px', marginRight:6}}><Icon name="send" size={11}/> Send Pitch Package</button>
        )}
        <button className="recall-btn" style={{marginRight:6}} onClick={config._onReset}><Icon name="undock" size={11}/> Reset</button>
        <span className="layout-name">LAYOUT · DELIVERABLES</span>
        <button className="recall-btn" onClick={recallAll}>{(minimizedIds.length||closedIds.length) ? 'RECALL ALL' : 'RESET LAYOUT'}</button>
      </div>

      <div className="workspace-canvas">
        <ToolRail active="deliver" onPick={()=>{}}/>
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

ReactDOM.createRoot(document.getElementById('app')).render(<DeliverablesApp/>);
