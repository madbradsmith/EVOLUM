// editor-map.jsx — 2D canvas + inspector for the Map Editor tab.
//
// SVG-based, Figma-style: scroll to zoom, space+drag (or middle-drag) to pan.
// Click empty space to deselect; click an element to select; drag to move.
//
// Roads are rendered as cubic Bezier paths with two draggable midpoint handles
// (these adjust sideOffset/intensity visually). Endpoints are draggable too.
//
// All mutations route through window.EDITOR_STATE.update().

const { useState, useEffect, useRef, useCallback, useMemo } = React;

function MapEditor() {
  const [state, setState] = useState(window.EDITOR_STATE.get());
  const [size, setSize] = useState({ w: 1200, h: 800 });
  const [spaceDown, setSpaceDown] = useState(false);
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const dragRef = useRef(null);

  // ── Subscribe to state ──
  useEffect(() => {
    return window.EDITOR_STATE.subscribe((s) => setState({ ...s }));
  }, []);

  // ── Track container size for SVG viewport ──
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver(() => {
      const r = containerRef.current.getBoundingClientRect();
      setSize({ w: r.width, h: r.height });
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // ── Keyboard: space for pan, delete for delete ──
  useEffect(() => {
    const down = (e) => {
      if (e.code === 'Space' && !e.target.matches('input, textarea')) { setSpaceDown(true); e.preventDefault(); }
      if ((e.code === 'Backspace' || e.code === 'Delete') && !e.target.matches('input, textarea')) {
        const sel = state.editor.selection;
        if (sel) deleteSelected(sel);
      }
      if (e.code === 'Escape') window.EDITOR_STATE.clearSelection();
    };
    const up = (e) => { if (e.code === 'Space') setSpaceDown(false); };
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    return () => { window.removeEventListener('keydown', down); window.removeEventListener('keyup', up); };
  }, [state.editor.selection]);

  // ── Coord transforms ──
  const cam = state.editor.camera;
  const W = size.w, H = size.h;
  const tx = W / 2 + cam.x;
  const ty = H / 2 + cam.y;
  const z = cam.zoom;

  // screen → world
  const screenToWorld = useCallback((sx, sy) => {
    const r = svgRef.current.getBoundingClientRect();
    const lx = sx - r.left, ly = sy - r.top;
    const wx = (lx - tx) / z;
    const wy = -(ly - ty) / z; // flip Y
    return { x: wx, y: wy };
  }, [tx, ty, z]);

  // ── Pan/zoom handlers ──
  const wheelRef = useRef(null);
  useEffect(() => {
    const el = svgRef.current; if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      const factor = Math.exp(-e.deltaY * 0.0015);
      const newZ = Math.max(0.08, Math.min(4, cam.zoom * factor));
      // zoom toward cursor
      const r = el.getBoundingClientRect();
      const cx = e.clientX - r.left - W / 2;
      const cy = e.clientY - r.top - H / 2;
      const wx = (cx - cam.x) / cam.zoom;
      const wy = (cy - cam.y) / cam.zoom;
      const nx = cx - wx * newZ;
      const ny = cy - wy * newZ;
      window.EDITOR_STATE.update(s => {
        s.editor.camera = { x: nx, y: ny, zoom: newZ };
      }, 'camera');
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [cam.x, cam.y, cam.zoom, W, H]);

  // ── Pointer (pan vs drag-select) ──
  const onPointerDown = useCallback((e) => {
    if (e.target === svgRef.current || e.target.classList.contains('bg-grid') || spaceDown) {
      // pan
      const startX = e.clientX, startY = e.clientY;
      const startCam = { ...cam };
      const move = (ev) => {
        window.EDITOR_STATE.update(s => {
          s.editor.camera = { ...startCam, x: startCam.x + (ev.clientX - startX), y: startCam.y + (ev.clientY - startY) };
        }, 'camera');
      };
      const up = () => {
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', up);
      };
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', up);
      // deselect on plain click (not pan)
      if (!spaceDown) {
        const downAt = performance.now();
        const upOnce = () => {
          if (performance.now() - downAt < 200) window.EDITOR_STATE.clearSelection();
          window.removeEventListener('pointerup', upOnce);
        };
        window.addEventListener('pointerup', upOnce);
      }
    }
  }, [cam, spaceDown]);

  // ── Generic element drag ──
  const beginDrag = useCallback((startEvent, onMove, onEnd) => {
    startEvent.stopPropagation();
    const startX = startEvent.clientX, startY = startEvent.clientY;
    const startWorld = screenToWorld(startX, startY);
    const move = (ev) => {
      const w = screenToWorld(ev.clientX, ev.clientY);
      onMove(w, { dx: w.x - startWorld.x, dy: w.y - startWorld.y });
    };
    const up = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      if (onEnd) onEnd();
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  }, [screenToWorld]);

  // ── World→screen helpers for SVG drawing ──
  const w2s = useCallback((wx, wy) => ({ x: wx * z + tx, y: -wy * z + ty }), [tx, ty, z]);
  const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

  // ── Snap helper ──
  const snap = (v) => Math.round(v / state.editor.gridSize) * state.editor.gridSize;

  // ── Selection helpers ──
  const select = (kind, id) => window.EDITOR_STATE.select(kind, id);
  const sel = state.editor.selection;

  const isSelected = (kind, id) => sel && sel.kind === kind && sel.id === id;

  // ── Bezier path string for a road ──
  const roadPath = (r) => {
    const pts = window.EDITOR_EXPORT.makeCurve(r.p0, r.p3, r.sideOffset, r.intensity);
    const p = pts.map(pt => w2s(pt.x, pt.y));
    return `M ${p[0].x},${p[0].y} C ${p[1].x},${p[1].y} ${p[2].x},${p[2].y} ${p[3].x},${p[3].y}`;
  };
  const roadBackPath = (r) => {
    const dx = r.p3.x - r.p0.x, dy = r.p3.y - r.p0.y;
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len, ny = dx / len;
    const back_p0 = r.p3;
    const back_p3 = { x: r.p0.x - nx * 120, y: r.p0.y - ny * 120 };
    const pts = window.EDITOR_EXPORT.makeCurve(back_p0, back_p3, r.sideOffset, r.intensity);
    const p = pts.map(pt => w2s(pt.x, pt.y));
    return `M ${p[0].x},${p[0].y} C ${p[1].x},${p[1].y} ${p[2].x},${p[2].y} ${p[3].x},${p[3].y}`;
  };

  // ── Add operations ──
  const addSection = () => {
    window.EDITOR_STATE.update(s => {
      const id = window.EDITOR_STATE.uid('sec');
      s.sections.push({
        id, label: 'New Section',
        x: snap(-cam.x / z), y: snap(cam.y / z),
        w: 160, h: 120,
        floor_color: '#1c1a28', walled: false, rotation: 0, raised: 0,
      });
      s.editor.selection = { kind: 'section', id };
    }, 'geometry');
  };
  const addRoad = () => {
    window.EDITOR_STATE.update(s => {
      const id = window.EDITOR_STATE.uid('road');
      const cx = -cam.x / z, cy = cam.y / z;
      s.roads.push({
        id, label: 'New Road', destination: id + '_station', theme: 'warm', width: 80,
        p0: { x: snap(cx - 50), y: snap(cy - 200) },
        p3: { x: snap(cx + 50), y: snap(cy - 800) },
        sideOffset: 200, intensity: 1.0,
      });
      // auto-create station at the road's terminus
      s.stations.push({
        id: id + '_station', x: snap(cx + 50), y: snap(cy - 800),
        label: 'STATION', target_pack: 'custom', road: id,
      });
      s.editor.selection = { kind: 'road', id };
    }, 'geometry');
  };
  const addGhost = () => {
    window.EDITOR_STATE.update(s => {
      const id = window.EDITOR_STATE.uid('ghost');
      s.ghostPacks.push({
        id, x: snap(-cam.x / z + 300), y: snap(cam.y / z + 300),
        w: 300, h: 200, color: '#1a1a2a', kind: 'theater',
      });
      s.editor.selection = { kind: 'ghost', id };
    }, 'geometry');
  };
  const addStop = () => {
    const state2 = window.EDITOR_STATE.get();
    const road = state2.roads.find(r => r.id === (sel && sel.kind === 'road' ? sel.id : (state2.roads[0] && state2.roads[0].id)));
    if (!road) { alert('Add a road first.'); return; }
    const existing = state2.stops.filter(s => s.road === road.id);
    if (existing.length >= 3) { alert('Max 3 stops per road.'); return; }
    window.EDITOR_STATE.update(s => {
      const id = window.EDITOR_STATE.uid('stop');
      s.stops.push({
        id, road: road.id, t: 0.5, poi: 'bench_cluster',
        lighting: { color: '#ffd28a', intensity: 1.0, type: 'steady' },
        audio: 'wind_low',
      });
      s.editor.selection = { kind: 'stop', id };
    }, 'geometry');
  };

  const deleteSelected = (sel2) => {
    const s2 = sel2 || state.editor.selection;
    if (!s2) return;
    window.EDITOR_STATE.update(s => {
      if (s2.kind === 'section') {
        s.sections = s.sections.filter(x => x.id !== s2.id);
      } else if (s2.kind === 'road') {
        s.roads = s.roads.filter(x => x.id !== s2.id);
        s.stops = s.stops.filter(x => x.road !== s2.id);
        s.stations = s.stations.filter(x => x.road !== s2.id);
      } else if (s2.kind === 'stop') {
        s.stops = s.stops.filter(x => x.id !== s2.id);
      } else if (s2.kind === 'station') {
        s.stations = s.stations.filter(x => x.id !== s2.id);
      } else if (s2.kind === 'ghost') {
        s.ghostPacks = s.ghostPacks.filter(x => x.id !== s2.id);
      }
      s.editor.selection = null;
    }, 'geometry');
  };

  // ── Selected for inspector ──
  const selected = window.EDITOR_STATE.findSelected(state);

  // ── Grid lines ──
  const gridLines = useMemo(() => {
    const lines = [];
    const step = z > 0.5 ? 100 : z > 0.25 ? 200 : 500;
    const left = (-cam.x - W / 2) / z;
    const right = (-cam.x + W / 2) / z;
    const top = -(-cam.y - H / 2) / z;
    const bot = -(-cam.y + H / 2) / z;
    const sx = Math.floor(left / step) * step;
    const ex = Math.ceil(right / step) * step;
    const sy = Math.floor(bot / step) * step;
    const ey = Math.ceil(top / step) * step;
    for (let x = sx; x <= ex; x += step) {
      const a = w2s(x, sy), b = w2s(x, ey);
      lines.push(<line key={'gx' + x} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
        stroke={x === 0 ? 'rgba(70,217,197,0.18)' : 'rgba(184,196,224,0.06)'} strokeWidth={x === 0 ? 0.8 : 0.5} />);
    }
    for (let y = sy; y <= ey; y += step) {
      const a = w2s(sx, y), b = w2s(ex, y);
      lines.push(<line key={'gy' + y} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
        stroke={y === 0 ? 'rgba(70,217,197,0.18)' : 'rgba(184,196,224,0.06)'} strokeWidth={y === 0 ? 0.8 : 0.5} />);
    }
    return lines;
  }, [cam.x, cam.y, z, W, H]);

  // ── Render ──
  return (
    <div className="canvas-pane" ref={containerRef}>
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        onPointerDown={onPointerDown}
        style={{ cursor: spaceDown ? 'grab' : 'default', display: 'block' }}
      >
        {/* grid */}
        <rect className="bg-grid" x="0" y="0" width={W} height={H} fill="#06070b" pointerEvents="all" />
        {gridLines}

        {/* boundary */}
        <BoundaryFrame state={state} w2s={w2s} />

        {/* ring road */}
        {state.ringRoad.enabled && <RingRoadGuide state={state} w2s={w2s} z={z} />}

        {/* roads */}
        {state.roads.map(r => (
          <RoadElement key={r.id} road={r}
            roadPath={roadPath} backPath={roadBackPath}
            selected={isSelected('road', r.id)}
            onSelect={() => select('road', r.id)}
            beginDrag={beginDrag}
            snap={snap}
            w2s={w2s}
            z={z}
          />
        ))}

        {/* ghost packs */}
        {state.ghostPacks.map(g => (
          <GhostPackElement key={g.id} ghost={g}
            selected={isSelected('ghost', g.id)}
            onSelect={() => select('ghost', g.id)}
            beginDrag={beginDrag} snap={snap} w2s={w2s} z={z}
          />
        ))}

        {/* sections */}
        {state.sections.map(s => (
          <SectionElement key={s.id} section={s}
            selected={isSelected('section', s.id)}
            onSelect={() => select('section', s.id)}
            beginDrag={beginDrag} snap={snap} w2s={w2s} z={z}
          />
        ))}

        {/* stations */}
        {state.stations.map(st => (
          <StationElement key={st.id} station={st}
            selected={isSelected('station', st.id)}
            onSelect={() => select('station', st.id)}
            beginDrag={beginDrag} snap={snap} w2s={w2s} z={z}
          />
        ))}

        {/* stops */}
        {state.stops.map(stp => (
          <StopElement key={stp.id} stop={stp} state={state}
            selected={isSelected('stop', stp.id)}
            onSelect={() => select('stop', stp.id)}
            w2s={w2s} z={z}
          />
        ))}

        {/* eggs */}
        <EggsLayer state={state} w2s={w2s} z={z} />

        {/* cast (small dots at spawn positions) */}
        {state.cast.map((c, i) => {
          const sec = state.sections.find(s => s.id === c.spawn);
          if (!sec) return null;
          const p = w2s(sec.x, sec.y);
          return (
            <g key={'cast' + i}>
              <circle cx={p.x} cy={p.y} r={5} fill={c.color} stroke="#06070b" strokeWidth={1.5} />
            </g>
          );
        })}
      </svg>

      <CanvasToolbar
        addSection={addSection}
        addRoad={addRoad}
        addStop={addStop}
        addGhost={addGhost}
      />

      <CanvasInfo cam={cam} state={state} />

      <Inspector selected={selected} state={state} onDelete={() => deleteSelected()} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Element components
// ─────────────────────────────────────────────────────────────────────

function SectionElement({ section: s, selected, onSelect, beginDrag, snap, w2s, z }) {
  const p = w2s(s.x, s.y);
  const halfW = s.w * z / 2, halfH = s.h * z / 2;
  const onPointerDown = (e) => {
    onSelect();
    beginDrag(e, (_, delta) => {
      window.EDITOR_STATE.update(st => {
        const t = st.sections.find(x => x.id === s.id);
        if (t) { t.x = snap(s.x + delta.dx); t.y = snap(s.y + delta.dy); }
      }, 'geometry');
    });
  };
  const onResize = (corner) => (e) => {
    e.stopPropagation();
    const startW = s.w, startH = s.h, startX = s.x, startY = s.y;
    beginDrag(e, (_, delta) => {
      window.EDITOR_STATE.update(st => {
        const t = st.sections.find(x => x.id === s.id);
        if (!t) return;
        if (corner.includes('e')) t.w = Math.max(40, snap(startW + delta.dx * 2));
        if (corner.includes('w')) { t.w = Math.max(40, snap(startW - delta.dx * 2)); }
        if (corner.includes('n')) t.h = Math.max(40, snap(startH + delta.dy * 2));
        if (corner.includes('s')) t.h = Math.max(40, snap(startH - delta.dy * 2));
      }, 'geometry');
    });
  };

  return (
    <g transform={`translate(${p.x},${p.y}) rotate(${-(s.rotation || 0)})`}>
      <rect x={-halfW} y={-halfH} width={halfW * 2} height={halfH * 2}
        fill={s.floor_color || '#1c1a28'}
        fillOpacity={selected ? 0.9 : 0.75}
        stroke={selected ? '#46d9c5' : 'rgba(184,196,224,0.35)'}
        strokeWidth={selected ? 1.5 : 1}
        onPointerDown={onPointerDown}
        style={{ cursor: 'move' }}
      />
      {s.walled && (
        <rect x={-halfW} y={-halfH} width={halfW * 2} height={halfH * 2}
          fill="none" stroke="rgba(184,196,224,0.6)" strokeWidth={2.2}
          pointerEvents="none"
          strokeDasharray={s.walled === 'partial' ? '4 4' : 'none'}
        />
      )}
      <text x={0} y={-halfH - 6 / z * z}
        textAnchor="middle"
        fontFamily="ui-monospace, Menlo, monospace"
        fontSize={10}
        fill={selected ? '#46d9c5' : 'rgba(184,196,224,0.7)'}
        pointerEvents="none">
        {s.label.toUpperCase()}
      </text>
      {selected && (
        <g>
          <circle cx={halfW} cy={halfH} r={5} fill="#46d9c5" stroke="#06070b" strokeWidth={1.5}
            onPointerDown={onResize('se')} style={{ cursor: 'nwse-resize' }} />
          <circle cx={-halfW} cy={-halfH} r={5} fill="#46d9c5" stroke="#06070b" strokeWidth={1.5}
            onPointerDown={onResize('nw')} style={{ cursor: 'nwse-resize' }} />
          <circle cx={halfW} cy={-halfH} r={5} fill="#46d9c5" stroke="#06070b" strokeWidth={1.5}
            onPointerDown={onResize('ne')} style={{ cursor: 'nesw-resize' }} />
          <circle cx={-halfW} cy={halfH} r={5} fill="#46d9c5" stroke="#06070b" strokeWidth={1.5}
            onPointerDown={onResize('sw')} style={{ cursor: 'nesw-resize' }} />
        </g>
      )}
    </g>
  );
}

function RoadElement({ road: r, roadPath, backPath, selected, onSelect, beginDrag, snap, w2s, z }) {
  const themeColor = { warm: '#f5b86b', amber: '#ff9d6d', cyan: '#6dd8ff', purple: '#c279ff', white: '#e8edf8' }[r.theme] || '#f5b86b';
  const p0s = w2s(r.p0.x, r.p0.y), p3s = w2s(r.p3.x, r.p3.y);
  const pts = window.EDITOR_EXPORT.makeCurve(r.p0, r.p3, r.sideOffset, r.intensity);
  const c1s = w2s(pts[1].x, pts[1].y), c2s = w2s(pts[2].x, pts[2].y);

  const moveEndpoint = (which) => (e) => {
    e.stopPropagation();
    onSelect();
    beginDrag(e, (w) => {
      window.EDITOR_STATE.update(st => {
        const t = st.roads.find(x => x.id === r.id);
        if (!t) return;
        if (which === 'p0') { t.p0 = { x: snap(w.x), y: snap(w.y) }; }
        else { t.p3 = { x: snap(w.x), y: snap(w.y) }; }
      }, 'geometry');
    });
  };

  // Drag the curve midpoint to adjust sideOffset (perpendicular displacement)
  const dragCurve = (e) => {
    e.stopPropagation();
    onSelect();
    const dx = r.p3.x - r.p0.x, dy = r.p3.y - r.p0.y;
    const len = Math.hypot(dx, dy) || 1;
    const nx = -dy / len, ny = dx / len;
    const midX = (r.p0.x + r.p3.x) / 2, midY = (r.p0.y + r.p3.y) / 2;
    const startOff = r.sideOffset;
    beginDrag(e, (w) => {
      // project (w - mid) onto normal
      const dxw = w.x - midX, dyw = w.y - midY;
      const dot = dxw * nx + dyw * ny;
      window.EDITOR_STATE.update(st => {
        const t = st.roads.find(x => x.id === r.id);
        if (t) t.sideOffset = Math.max(-600, Math.min(600, dot));
      }, 'geometry');
    });
  };

  return (
    <g>
      <path d={roadPath(r)} fill="none" stroke="#1a1a22" strokeWidth={r.width * z}
        strokeLinecap="round" onPointerDown={(e) => { e.stopPropagation(); onSelect(); dragCurve(e); }}
        style={{ cursor: selected ? 'move' : 'pointer' }} />
      <path d={roadPath(r)} fill="none" stroke={themeColor} strokeWidth={2}
        opacity={selected ? 1 : 0.7} pointerEvents="none" />
      {/* return road, dimmer */}
      <path d={backPath(r)} fill="none" stroke="#1a1a22" strokeWidth={r.width * z}
        strokeLinecap="round" pointerEvents="none" opacity={0.65} />
      <path d={backPath(r)} fill="none" stroke={themeColor} strokeWidth={1.5}
        opacity={selected ? 0.7 : 0.4} pointerEvents="none" strokeDasharray="4 6" />
      {/* endpoints */}
      <circle cx={p0s.x} cy={p0s.y} r={6} fill={selected ? '#46d9c5' : themeColor} stroke="#06070b" strokeWidth={1.5}
        onPointerDown={moveEndpoint('p0')} style={{ cursor: 'move' }} />
      <circle cx={p3s.x} cy={p3s.y} r={6} fill={selected ? '#46d9c5' : themeColor} stroke="#06070b" strokeWidth={1.5}
        onPointerDown={moveEndpoint('p3')} style={{ cursor: 'move' }} />
      {/* bezier control handles when selected */}
      {selected && (
        <g pointerEvents="none">
          <line x1={p0s.x} y1={p0s.y} x2={c1s.x} y2={c1s.y} stroke="rgba(70,217,197,0.5)" strokeDasharray="2 3" />
          <line x1={p3s.x} y1={p3s.y} x2={c2s.x} y2={c2s.y} stroke="rgba(70,217,197,0.5)" strokeDasharray="2 3" />
          <circle cx={c1s.x} cy={c1s.y} r={3.5} fill="rgba(70,217,197,0.7)" />
          <circle cx={c2s.x} cy={c2s.y} r={3.5} fill="rgba(70,217,197,0.7)" />
        </g>
      )}
    </g>
  );
}

function StopElement({ stop: stp, state, selected, onSelect, w2s, z }) {
  const road = state.roads.find(r => r.id === stp.road);
  if (!road) return null;
  const pts = window.EDITOR_EXPORT.makeCurve(road.p0, road.p3, road.sideOffset, road.intensity);
  const p = window.EDITOR_EXPORT.bez(pts[0], pts[1], pts[2], pts[3], stp.t);
  const tg = (function () {
    const u = 1 - stp.t;
    return {
      x: 3*u*u*(pts[1].x - pts[0].x) + 6*u*stp.t*(pts[2].x - pts[1].x) + 3*stp.t*stp.t*(pts[3].x - pts[2].x),
      y: 3*u*u*(pts[1].y - pts[0].y) + 6*u*stp.t*(pts[2].y - pts[1].y) + 3*stp.t*stp.t*(pts[3].y - pts[2].y),
    };
  })();
  const tl = Math.hypot(tg.x, tg.y) || 1;
  const nx = -tg.y / tl, ny = tg.x / tl;
  const px = p.x + nx * 70, py = p.y + ny * 70;
  const sp = w2s(px, py);

  return (
    <g onPointerDown={(e) => { e.stopPropagation(); onSelect(); }} style={{ cursor: 'pointer' }}>
      <circle cx={sp.x} cy={sp.y} r={selected ? 12 : 9}
        fill={stp.lighting.color}
        fillOpacity={0.18}
        stroke={selected ? '#46d9c5' : stp.lighting.color}
        strokeWidth={selected ? 2 : 1.2}
      />
      <circle cx={sp.x} cy={sp.y} r={3.5} fill={stp.lighting.color} />
    </g>
  );
}

function StationElement({ station: st, selected, onSelect, beginDrag, snap, w2s, z }) {
  const p = w2s(st.x, st.y);
  const half = 18;
  const onPD = (e) => {
    onSelect();
    beginDrag(e, (_, delta) => {
      window.EDITOR_STATE.update(s => {
        const t = s.stations.find(x => x.id === st.id);
        if (t) { t.x = snap(st.x + delta.dx); t.y = snap(st.y + delta.dy); }
      }, 'geometry');
    });
  };
  return (
    <g onPointerDown={onPD} style={{ cursor: 'move' }}>
      <rect x={p.x - half} y={p.y - half} width={half * 2} height={half * 2}
        fill="#0e1018" stroke={selected ? '#46d9c5' : '#46d9c5'} strokeWidth={selected ? 2 : 1} />
      <text x={p.x} y={p.y - half - 5} textAnchor="middle"
        fontFamily="ui-monospace, Menlo, monospace" fontSize={9}
        fill="#46d9c5" pointerEvents="none">{st.label}</text>
    </g>
  );
}

function GhostPackElement({ ghost: g, selected, onSelect, beginDrag, snap, w2s, z }) {
  const p = w2s(g.x, g.y);
  const halfW = g.w * z / 2, halfH = g.h * z / 2;
  const onPD = (e) => {
    onSelect();
    beginDrag(e, (_, delta) => {
      window.EDITOR_STATE.update(s => {
        const t = s.ghostPacks.find(x => x.id === g.id);
        if (t) { t.x = snap(g.x + delta.dx); t.y = snap(g.y + delta.dy); }
      }, 'geometry');
    });
  };
  return (
    <g onPointerDown={onPD} style={{ cursor: 'move' }}>
      <rect x={p.x - halfW} y={p.y - halfH} width={halfW * 2} height={halfH * 2}
        fill={g.color} fillOpacity={0.6}
        stroke={selected ? '#46d9c5' : 'rgba(184,196,224,0.18)'}
        strokeWidth={selected ? 1.5 : 0.8}
        strokeDasharray="3 4"
      />
      <text x={p.x} y={p.y + 4} textAnchor="middle"
        fontFamily="ui-monospace, Menlo, monospace" fontSize={9}
        fill="rgba(184,196,224,0.5)" pointerEvents="none">{(g.kind || 'pack').toUpperCase()}</text>
    </g>
  );
}

function BoundaryFrame({ state, w2s }) {
  const b = state.boundary;
  const tl = w2s(b.west, b.north), tr = w2s(b.east, b.north);
  const br = w2s(b.east, b.south), bl = w2s(b.west, b.south);
  return (
    <g pointerEvents="none">
      <polygon points={`${tl.x},${tl.y} ${tr.x},${tr.y} ${br.x},${br.y} ${bl.x},${bl.y}`}
        fill="none" stroke="rgba(70,217,197,0.18)" strokeWidth={1} strokeDasharray="8 6" />
      {[tl, tr, br, bl].map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r={4} fill="rgba(70,217,197,0.4)" />
        </g>
      ))}
      <text x={(tl.x + tr.x) / 2} y={tl.y - 10} textAnchor="middle"
        fontFamily="ui-monospace, Menlo, monospace" fontSize={9}
        fill="rgba(70,217,197,0.55)">STARGATE BOUNDARY</text>
    </g>
  );
}

function RingRoadGuide({ state, w2s, z }) {
  const c = w2s(0, 0);
  const r = state.ringRoad.radius * z;
  return (
    <g pointerEvents="none">
      <circle cx={c.x} cy={c.y} r={r} fill="none"
        stroke="rgba(184,196,224,0.18)" strokeWidth={state.ringRoad.width * z}
      />
      <circle cx={c.x} cy={c.y} r={r} fill="none"
        stroke="rgba(70,217,197,0.5)" strokeWidth={1}
      />
    </g>
  );
}

function EggsLayer({ state, w2s, z }) {
  const eggs = [];
  if (state.eggs.north) eggs.push({ x: 0, y: state.boundary.north });
  if (state.eggs.south) eggs.push({ x: 0, y: state.boundary.south });
  if (state.eggs.east)  eggs.push({ x: state.boundary.east, y: 0 });
  if (state.eggs.west)  eggs.push({ x: state.boundary.west, y: 0 });
  return (
    <g pointerEvents="none">
      {eggs.map((e, i) => {
        const p = w2s(e.x, e.y);
        return (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={9} fill="rgba(0,255,65,0.18)" />
            <circle cx={p.x} cy={p.y} r={3.5} fill="#00ff41" />
          </g>
        );
      })}
    </g>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Toolbar / info / inspector
// ─────────────────────────────────────────────────────────────────────

function CanvasToolbar({ addSection, addRoad, addStop, addGhost }) {
  return (
    <div className="canvas-toolbar">
      <button className="btn primary" onClick={addSection}>+ Section</button>
      <button className="btn" onClick={addRoad}>+ Road</button>
      <button className="btn" onClick={addStop}>+ Stop</button>
      <button className="btn" onClick={addGhost}>+ Ghost</button>
    </div>
  );
}

function CanvasInfo({ cam, state }) {
  const counts = [
    state.sections.length + ' sections',
    state.roads.length + ' roads',
    state.stops.length + ' stops',
    state.stations.length + ' stations',
    state.ghostPacks.length + ' ghosts',
    state.cast.length + ' entities',
  ].join(' · ');
  return (
    <div className="canvas-info">
      {counts} · zoom {cam.zoom.toFixed(2)}× ·{' '}
      <kbd>space+drag</kbd> pan · <kbd>scroll</kbd> zoom · <kbd>del</kbd> remove
    </div>
  );
}

// Inspector and per-kind editors live in a separate file (editor-inspector.jsx)
// to keep this file under the line cap.

window.MapEditor = MapEditor;
