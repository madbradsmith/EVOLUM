/* =====================================================================
   EVOLUM — Shared Room shell with dock orchestration
   Each room provides:
     - ROOM_CONFIG.activeTool      ('script' | 'pitch' | null = workspace overview)
     - ROOM_CONFIG.crumb           (e.g. "Script")
     - ROOM_CONFIG.project         (project record from PROJECTS)
     - ROOM_CONFIG.panels          ({ id: { mode, zone, rect?, meta:{title,icon,sub} } })
     - ROOM_CONFIG.renderPanel(id) → React node
     - ROOM_CONFIG.statusItems     (array of {lbl,num})
     - ROOM_CONFIG.statusRight     (React node)
     - ROOM_CONFIG.menuExtras      (React node, optional)
   ===================================================================== */
const { useState: uSh, useEffect: uEh, useRef: uRh, useMemo: uMh, useCallback: uCh } = React;

const ZONES_SH = ['main', 'right', 'bottom'];

function computeRectsSh(canvas, rightW, bottomH, panels) {
  const pad = 4;
  const hasRight = Object.values(panels).some(p => p.mode === 'docked' && p.zone === 'right');
  const hasBottom = Object.values(panels).some(p => p.mode === 'docked' && p.zone === 'bottom');
  const rW = hasRight ? rightW : 0;
  const bH = hasBottom ? bottomH : 0;
  const mainW = canvas.w - (hasRight ? rW + pad : 0);
  const mainH = canvas.h - (hasBottom ? bH + pad : 0);
  const zoneRects = {
    main:   { x: 0, y: 0, w: mainW, h: mainH },
    right:  { x: canvas.w - rW, y: 0, w: rW, h: canvas.h },
    bottom: { x: 0, y: canvas.h - bH, w: mainW, h: bH },
  };
  const byZone = { main: [], right: [], bottom: [] };
  for (const [id, st] of Object.entries(panels)) {
    if (st.mode === 'docked') byZone[st.zone].push(id);
  }
  const out = {};
  for (const zone of ZONES_SH) {
    const ids = byZone[zone];
    const z = zoneRects[zone];
    const n = ids.length;
    if (!n) continue;
    ids.forEach((id, i) => {
      out[id] = {
        x: z.x,
        y: z.y + Math.round((z.h / n) * i),
        w: z.w,
        h: Math.round(z.h / n) - (i < n - 1 ? 1 : 0),
      };
    });
  }
  return out;
}

const Room = ({ config }) => {
  const PANEL_META = Object.fromEntries(Object.entries(config.panels).map(([id, p]) => [id, p.meta]));

  /* canvas size */
  const canvasRef = uRh(null);
  const [canvas, setCanvas] = uSh({ w: 1200, h: 700 });
  uEh(() => {
    const ro = new ResizeObserver(() => {
      const el = canvasRef.current; if (!el) return;
      const r = el.getBoundingClientRect();
      setCanvas({ w: Math.floor(r.width), h: Math.floor(r.height) });
    });
    if (canvasRef.current) ro.observe(canvasRef.current);
    return () => ro.disconnect();
  }, []);

  /* splitter sizes */
  const [rightW, setRightW] = uSh(config.rightW || 320);
  const [bottomH, setBottomH] = uSh(config.bottomH || 200);

  /* panel states (clone from config) */
  const initialPanelStates = () => {
    const o = {};
    for (const [id, p] of Object.entries(config.panels)) {
      o[id] = { mode: p.mode, zone: p.zone, rect: p.rect || null, z: 1, _wasFloat: p.mode === 'floating' };
    }
    return o;
  };
  const [panels, setPanels] = uSh(initialPanelStates);
  const [focusId, setFocusId] = uSh(Object.keys(config.panels)[0]);
  const zCounter = uRh(10);

  /* drag-to-dock */
  const [hoverZone, setHoverZone] = uSh(null);
  const [activeDrag, setActiveDrag] = uSh(null);

  /* derived */
  const dockedRects = uMh(() => computeRectsSh(canvas, rightW, bottomH, panels), [canvas, rightW, bottomH, panels]);

  /* initial position for floating panels that had no rect */
  uEh(() => {
    if (canvas.w < 100) return;
    setPanels(p => {
      const next = { ...p };
      let changed = false;
      for (const id of Object.keys(next)) {
        if (next[id].mode === 'floating' && (!next[id].rect || next[id].rect.x === 0)) {
          const cfg = config.panels[id];
          const w = cfg.rect?.w || 340, h = cfg.rect?.h || 360;
          next[id] = { ...next[id], rect: {
            x: Math.max(60, canvas.w - rightW - w - 20),
            y: Math.max(40, canvas.h - bottomH - h - 20),
            w, h
          }};
          changed = true;
        }
      }
      return changed ? next : p;
    });
    // eslint-disable-next-line
  }, [canvas.w, canvas.h]);

  const bringToFront = uCh((id) => {
    zCounter.current += 1;
    setPanels(p => ({ ...p, [id]: { ...p[id], z: zCounter.current } }));
    setFocusId(id);
  }, []);

  const minimize = (id) => setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'minimized' } }));
  const close    = (id) => setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'closed' } }));
  const undock   = (id) => setPanels(p => {
    const cur = p[id];
    const r = dockedRects[id] || { x: 80, y: 60, w: 380, h: 360 };
    const popped = {
      x: Math.max(8, r.x + 24),
      y: Math.max(8, r.y + 24),
      w: Math.min(canvas.w - 60, Math.max(320, Math.floor(r.w * 0.7))),
      h: Math.min(canvas.h - 60, Math.max(240, Math.floor(r.h * 0.7))),
    };
    zCounter.current += 1;
    return { ...p, [id]: { ...cur, mode: 'floating', rect: popped, z: zCounter.current, _wasFloat: true } };
  });
  const dock = (id) => setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'docked', _wasFloat: false } }));

  const onPanelChange = (id, patch, drag) => {
    setPanels(p => {
      const cur = p[id];
      const next = { ...cur, ...patch };
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
        if (x > canvas.w - 80) zone = 'right';
        else if (y > canvas.h - 60) zone = 'bottom';
        setHoverZone(zone); setActiveDrag(id);
      } else if (drag.commit) {
        if (hoverZone) setPanels(p => ({ ...p, [id]: { ...p[id], mode: 'docked', zone: hoverZone, _wasFloat: false } }));
        setHoverZone(null); setActiveDrag(null);
      }
    }
  };

  const recallAll = () => {
    setPanels(initialPanelStates());
    setRightW(config.rightW || 320); setBottomH(config.bottomH || 200);
  };

  const splitV = (e) => {
    e.preventDefault();
    const start = e.clientX, startW = rightW;
    const onMove = (ev) => setRightW(Math.max(220, Math.min(560, startW - (ev.clientX - start))));
    const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
  };
  const splitH = (e) => {
    e.preventDefault();
    const start = e.clientY, startH = bottomH;
    const onMove = (ev) => setBottomH(Math.max(120, Math.min(canvas.h - 160, startH - (ev.clientY - start))));
    const onUp = () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
    window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
  };

  /* timecode */
  const [now, setNow] = uSh(new Date());
  uEh(() => { const t = setInterval(()=>setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  const tc = now.toTimeString().slice(0, 8);

  /* panel content + rect */
  const rectFor = (id) => {
    const st = panels[id];
    if (st.mode === 'floating') return st.rect || { x: 80, y: 80, w: 360, h: 320 };
    if (st.mode === 'docked')   return dockedRects[id] || { x: 0, y: 0, w: 0, h: 0 };
    return { x: 0, y: 0, w: 0, h: 0 };
  };

  const minimizedIds = Object.entries(panels).filter(([_,s])=>s.mode==='minimized').map(([id])=>id);
  const closedIds = Object.entries(panels).filter(([_,s])=>s.mode==='closed').map(([id])=>id);
  const showVSplit = Object.values(panels).some(p=>p.mode==='docked' && p.zone==='right');
  const showHSplit = Object.values(panels).some(p=>p.mode==='docked' && p.zone==='bottom');

  const project = config.project;

  return (
    <React.Fragment>
      {/* Title bar */}
      <div className="titlebar">
        <div className="tl-lights"><span className="r"/><span className="y"/><span className="g"/></div>
        <div className="tl-brand">
          <span className="badge">EV</span>
          <span>EVOLUM</span>
        </div>
        <div className="tl-crumbs">
          <a href="/studio" style={{color:'var(--text-3)', textDecoration:'none'}}>Workspace</a>
          <span className="sep">/</span>
          {project ? <strong>{project.title}</strong> : <strong>All Projects</strong>}
          <span className="sep">/</span>
          <span style={{color:'var(--accent)'}}>{config.crumb || 'Overview'}</span>
        </div>
        <div className="tl-spacer"/>
        <div className="tl-meta">
          <span className="dot"/>
          <span>SYNC OK</span>
          <span style={{color:'var(--line-3)'}}>·</span>
          <span>{tc}</span>
        </div>
      </div>

      {/* Menu bar */}
      <div className="menubar">
        <button>File</button>
        <button>Edit</button>
        <button>View</button>
        <button>Project</button>
        <button>Window</button>
        <button>Help</button>
        <span className="mb-spacer"/>
        {config.menuExtras}
        <span className="layout-name">LAYOUT · {config.crumb?.toUpperCase() || 'WORKSPACE'}</span>
        <button className="recall-btn" onClick={recallAll}>{(minimizedIds.length||closedIds.length) ? 'RECALL ALL' : 'RESET LAYOUT'}</button>
      </div>

      {/* Canvas */}
      <div className="workspace-canvas">
        <ToolRail active={config.activeTool} onPick={()=>{}}/>
        <div ref={canvasRef} style={{ position:'absolute', top:0, left:'var(--tool-rail-w)', right:0, bottom:0 }}>
          {activeDrag && (
            <React.Fragment>
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

          {showVSplit && <div onMouseDown={splitV} style={{ position:'absolute', top:0, bottom:0, width:5, left: canvas.w - rightW - 2, cursor:'ew-resize', zIndex:10 }}/>}
          {showHSplit && <div onMouseDown={splitH} style={{ position:'absolute', left:0, right: showVSplit ? rightW + 4 : 0, height:5, top: canvas.h - bottomH - 2, cursor:'ns-resize', zIndex:10 }}/>}

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

      {/* Status bar */}
      <div className="statusbar">
        {(config.statusItems || []).map((s,i) => (
          <div key={i} className="stat"><span className="lbl">{s.lbl}</span><span className="num">{s.num}</span></div>
        ))}
        <div className="sb-spacer"/>
        <div className="sb-right">
          {config.statusRight || (
            <React.Fragment>
              <span><span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:'var(--ok)',marginRight:5,verticalAlign:'middle',boxShadow:'0 0 6px var(--ok-glow)'}}/>online</span>
              <span>evolumstudio@gmail.com</span>
              <span>EN · v1.4.0</span>
              <span><strong>{tc}</strong></span>
            </React.Fragment>
          )}
        </div>
      </div>
    </React.Fragment>
  );
};

Object.assign(window, { Room });
