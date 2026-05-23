/* =====================================================================
   Icons — small inline SVG set, matched to a 14px Premiere-ish line style
   ===================================================================== */
const Icon = ({ name, size = 14, stroke = 1.5, className = '' }) => {
  const s = size;
  const common = {
    width: s, height: s, viewBox: '0 0 24 24',
    fill: 'none', stroke: 'currentColor',
    strokeWidth: stroke, strokeLinecap: 'round', strokeLinejoin: 'round',
    className
  };
  switch (name) {
    case 'idea':
      return (<svg {...common}><path d="M9 18h6"/><path d="M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/></svg>);
    case 'script':
      return (<svg {...common}><path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/><path d="M9 12h7"/><path d="M9 16h7"/><path d="M9 8h3"/></svg>);
    case 'poster':
      return (<svg {...common}><rect x="5" y="3" width="14" height="18" rx="1"/><circle cx="12" cy="9" r="2.5"/><path d="M7 19l3.5-5 3 3.5L16 14l1 5"/></svg>);
    case 'pitch':
      return (<svg {...common}><rect x="3" y="4" width="18" height="12" rx="1"/><path d="M8 20h8"/><path d="M12 16v4"/><path d="M7 8l3 3 7-7" strokeWidth={stroke+0.3}/></svg>);
    case 'sizzle':
      return (<svg {...common}><circle cx="12" cy="12" r="9"/><path d="M10 8.5v7l6-3.5z" fill="currentColor"/></svg>);
    case 'casting':
      return (<svg {...common}><circle cx="9" cy="9" r="3.5"/><path d="M3 19c0-3 2.7-5 6-5s6 2 6 5"/><circle cx="17" cy="7" r="2.5"/><path d="M15 14.5c2.5 0 4.5 1.6 4.5 4"/></svg>);
    case 'invest':
      return (<svg {...common}><path d="M4 19V8"/><path d="M9 19V5"/><path d="M14 19v-9"/><path d="M19 19v-5"/><path d="M3 22h18"/></svg>);
    case 'deliver':
      return (<svg {...common}><path d="M3 7l9-4 9 4-9 4-9-4z"/><path d="M3 12l9 4 9-4"/><path d="M3 17l9 4 9-4"/></svg>);

    case 'search':
      return (<svg {...common}><circle cx="11" cy="11" r="6.5"/><path d="M20 20l-3.5-3.5"/></svg>);
    case 'filter':
      return (<svg {...common}><path d="M4 5h16l-6 8v6l-4-2v-4z"/></svg>);
    case 'sort':
      return (<svg {...common}><path d="M7 4v16"/><path d="M4 7l3-3 3 3"/><path d="M17 20V4"/><path d="M14 17l3 3 3-3"/></svg>);
    case 'grid':
      return (<svg {...common}><rect x="4" y="4" width="7" height="7"/><rect x="13" y="4" width="7" height="7"/><rect x="4" y="13" width="7" height="7"/><rect x="13" y="13" width="7" height="7"/></svg>);
    case 'list':
      return (<svg {...common}><path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/><circle cx="6" cy="6" r="0.4" fill="currentColor"/></svg>);
    case 'plus':
      return (<svg {...common}><path d="M12 5v14"/><path d="M5 12h14"/></svg>);
    case 'star':
      return (<svg {...common}><path d="M12 3l2.7 5.7 6.3.9-4.5 4.4 1 6.3L12 17.5 6.5 20.3l1-6.3L3 9.6l6.3-.9z"/></svg>);

    case 'minimize':
      return (<svg {...common}><path d="M5 17h14"/></svg>);
    case 'maximize':
      return (<svg {...common}><rect x="5" y="5" width="14" height="14"/></svg>);
    case 'undock':
      return (<svg {...common}><path d="M10 14l10-10"/><path d="M14 4h6v6"/><path d="M19 13v6H5V5h6"/></svg>);
    case 'dock':
      return (<svg {...common}><rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 9h18"/></svg>);
    case 'close':
      return (<svg {...common}><path d="M6 6l12 12"/><path d="M6 18L18 6"/></svg>);
    case 'drag':
      return (<svg {...common}><circle cx="9" cy="6" r="1" fill="currentColor"/><circle cx="9" cy="12" r="1" fill="currentColor"/><circle cx="9" cy="18" r="1" fill="currentColor"/><circle cx="15" cy="6" r="1" fill="currentColor"/><circle cx="15" cy="12" r="1" fill="currentColor"/><circle cx="15" cy="18" r="1" fill="currentColor"/></svg>);

    case 'folder':
      return (<svg {...common}><path d="M3 7a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/></svg>);
    case 'film':
      return (<svg {...common}><rect x="3" y="4" width="18" height="16" rx="1"/><path d="M7 4v16"/><path d="M17 4v16"/><path d="M3 12h18"/><path d="M3 8h4"/><path d="M3 16h4"/><path d="M17 8h4"/><path d="M17 16h4"/></svg>);
    case 'clock':
      return (<svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>);
    case 'bell':
      return (<svg {...common}><path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2H4.5z"/><path d="M10 21h4"/></svg>);
    case 'people':
      return (<svg {...common}><circle cx="9" cy="9" r="3"/><path d="M3 19c0-3 2.7-5 6-5s6 2 6 5"/><circle cx="17" cy="8" r="2.5"/><path d="M15 15c2.5 0 4.5 1.4 4.5 4"/></svg>);
    case 'send':
      return (<svg {...common}><path d="M21 3L3 11l7 2 2 7z"/><path d="M21 3l-11 11"/></svg>);
    case 'check':
      return (<svg {...common}><path d="M4 12l5 5L20 6"/></svg>);
    case 'chevron':
      return (<svg {...common}><path d="M9 6l6 6-6 6"/></svg>);
    case 'sparkle':
      return (<svg {...common}><path d="M12 3v6"/><path d="M12 15v6"/><path d="M3 12h6"/><path d="M15 12h6"/><path d="M6 6l3 3"/><path d="M15 15l3 3"/><path d="M18 6l-3 3"/><path d="M9 15l-3 3"/></svg>);
    case 'settings':
      return (<svg {...common}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .4 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.4 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.4l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .4-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.4-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.4H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.4l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.4 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>);
    default:
      return (<svg {...common}><circle cx="12" cy="12" r="9"/></svg>);
  }
};

/* =====================================================================
   Panel — generic dockable / floatable container
   props:
     id, title, sub, icon, dockZone (default), defaultRect, focused,
     onFocus, onChange (rect/state), state ({zone, rect, mode, z}),
     children
   ===================================================================== */
const Panel = ({ id, title, sub, icon, state, onChange, onFocus, focused, onMinimize, onClose, onUndock, onDock, children }) => {
  const ref = React.useRef(null);
  const dragRef = React.useRef(null);

  const startDrag = (e) => {
    if (state.mode === 'docked') return; // docked panels move only via undock
    e.preventDefault();
    onFocus && onFocus(id);
    const startX = e.clientX, startY = e.clientY;
    const startRect = { ...state.rect };
    dragRef.current = { dragging: true };
    const onMove = (ev) => {
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;
      onChange(id, { rect: { ...startRect, x: startRect.x + dx, y: startRect.y + dy } }, { dragging: true, x: ev.clientX, y: ev.clientY });
    };
    const onUp = (ev) => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      onChange(id, {}, { dragging: false, x: ev.clientX, y: ev.clientY, commit: true });
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  const startResize = (e) => {
    e.preventDefault();
    e.stopPropagation();
    onFocus && onFocus(id);
    const startX = e.clientX, startY = e.clientY;
    const startRect = { ...state.rect };
    const onMove = (ev) => {
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;
      onChange(id, { rect: { ...startRect, w: Math.max(220, startRect.w + dx), h: Math.max(80, startRect.h + dy) } });
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  if (state.mode === 'closed') return null;

  const isFloat = state.mode === 'floating';
  const isMini = state.mode === 'minimized';

  const style = isFloat
    ? { left: state.rect.x, top: state.rect.y, width: state.rect.w, height: state.rect.h, zIndex: state.z || 50 }
    : { left: state.rect.x, top: state.rect.y, width: state.rect.w, height: state.rect.h };

  return (
    <div
      ref={ref}
      className={`panel ${isFloat ? 'floating' : ''} ${isMini ? 'minimized' : ''} ${focused ? 'focused' : ''}`}
      style={style}
      onMouseDown={() => onFocus && onFocus(id)}
    >
      <div className="ph">
        <div className="ph-grip" onMouseDown={startDrag} onDoubleClick={() => onChange(id, { mode: isMini ? (isFloat ? 'floating' : 'docked') : 'minimized' })}>
          {icon ? <span className="ic"><Icon name={icon} size={13}/></span> : null}
          <span className="title">{title}</span>
          {sub ? <span className="sub">{sub}</span> : null}
        </div>
        <div className="ph-actions">
          {isFloat ? (
            <button className="ph-btn" title="Dock" onClick={(e)=>{ e.stopPropagation(); onDock && onDock(id); }}><Icon name="dock" size={12}/></button>
          ) : (
            <button className="ph-btn" title="Undock" onClick={(e)=>{ e.stopPropagation(); onUndock && onUndock(id); }}><Icon name="undock" size={12}/></button>
          )}
          <button className="ph-btn" title="Minimize" onClick={(e)=>{ e.stopPropagation(); onMinimize && onMinimize(id); }}><Icon name="minimize" size={12}/></button>
          <button className="ph-btn danger" title="Close" onClick={(e)=>{ e.stopPropagation(); onClose && onClose(id); }}><Icon name="close" size={12}/></button>
        </div>
      </div>
      <div className="panel-body">{children}</div>
      {isFloat && !isMini ? <div className="resize-handle" onMouseDown={startResize}/> : null}
    </div>
  );
};

/* Expose to other babel scripts */
Object.assign(window, { Icon, Panel });
