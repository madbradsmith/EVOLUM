/* =====================================================================
   EVOLUM — Outreach Hub (cross-project library)
   ===================================================================== */
const OUTREACH_ITEMS = [
  /* PRESS */
  { id:'o01', project:'Mandatory Reporter', kind:'press', type:'Press Release', headline:'Developum AI Brings EVOLUM Portal Live for Independent Film and Television', date:'today 12:14p', status:'sent', recipients:'Variety, IndieWire, Deadline', engagement:'24 opens' },
  { id:'o02', project:'Court Jester',       kind:'press', type:'Pitch Memo',     headline:'Court Jester locks director, raises $325K seed', date:'yesterday', status:'queued', recipients:'12 outlets', engagement:'—' },
  { id:'o03', project:'Mandatory Reporter', kind:'press', type:'Filmmaker Bio',  headline:'Bradley Smith — first-time feature director, 30 years in the AD chair', date:'2d ago', status:'draft', recipients:'—', engagement:'—' },
  { id:'o04', project:'Tax Season',         kind:'press', type:'Query Letter',   headline:'Tax Season — feature submission to Sundance Labs', date:'3d ago', status:'sent', recipients:'Sundance Institute', engagement:'1 reply' },
  { id:'o05', project:'Who Invited You?',   kind:'press', type:'EPK',            headline:'Who Invited You? — Electronic Press Kit v2', date:'1w ago', status:'sent', recipients:'8 outlets', engagement:'3 opens' },
  /* SOCIAL */
  { id:'o06', project:'Mandatory Reporter', kind:'social', type:'LinkedIn',  headline:'MANDATORY REPORTER — locked production budget. A widowed father has 72 hours…', date:'today 11:14a', status:'live', recipients:'LinkedIn', engagement:'128 likes · 14 reposts' },
  { id:'o07', project:'Mandatory Reporter', kind:'social', type:'X',         headline:'4 investors in on MANDATORY REPORTER. $345K committed against an $826K raise.', date:'today 9:30a', status:'live', recipients:'X (Twitter)', engagement:'432 views · 18 likes' },
  { id:'o08', project:'Court Jester',       kind:'social', type:'Instagram', headline:'Day 14 of pre-production on Court Jester. Three locations down, one to go.', date:'today 8:00a', status:'scheduled', recipients:'Instagram', engagement:'—' },
  { id:'o09', project:'Tax Season',         kind:'social', type:'TikTok',    headline:'Hook: "A teacher misread a bruise." Tone reel for Tax Season.', date:'yesterday', status:'live', recipients:'TikTok', engagement:'2.1K views' },
  { id:'o10', project:'Mandatory Reporter', kind:'social', type:'LinkedIn',  headline:'Open call: DANNY (38) lead, widowed father. Self-tapes by May 31.', date:'2d ago', status:'live', recipients:'LinkedIn', engagement:'62 likes · 8 comments' },
  { id:'o11', project:'Bone Music',         kind:'social', type:'YouTube',   headline:'BONE MUSIC — 90-second sizzle reel. Festival cut.', date:'3d ago', status:'live', recipients:'YouTube', engagement:'1.3K views · 88 likes' },
  { id:'o12', project:'Hollow Crown',       kind:'social', type:'LinkedIn',  headline:'Series pilot Hollow Crown — script lock celebration.', date:'4d ago', status:'live', recipients:'LinkedIn', engagement:'94 likes' },
  /* DISTRIBUTE */
  { id:'o13', project:'Eastbound',          kind:'distribute', type:'Festival', headline:'Eastbound — submitted to SXSW 2026 shorts.', date:'today 10:08a', status:'submitted', recipients:'SXSW', engagement:'pending' },
  { id:'o14', project:'Court Jester',       kind:'distribute', type:'Streamer', headline:'Court Jester — query sent to A24 acquisitions.', date:'yesterday', status:'sent', recipients:'A24', engagement:'opened' },
  { id:'o15', project:'Mandatory Reporter', kind:'distribute', type:'Sales Rep',headline:'Mandatory Reporter — represented by Boutique Sales.', date:'2d ago', status:'active', recipients:'Boutique Sales', engagement:'in conversation' },
];

const STATUS_COLORS_OH = {
  sent:      'var(--st-script)',
  live:      'var(--ok)',
  scheduled: 'var(--accent)',
  queued:    'var(--text-3)',
  draft:     'var(--text-3)',
  submitted: 'var(--accent)',
  active:    'var(--ok)',
};

const OutreachApp = () => {
  const [tab, setTab] = React.useState('library');
  const [q, setQ] = React.useState('evolumstudio@gmail.com');
  const [filter, setFilter] = React.useState('all');

  const filtered = OUTREACH_ITEMS.filter(it => {
    if (tab === 'press'      && it.kind !== 'press')      return false;
    if (tab === 'social'     && it.kind !== 'social')     return false;
    if (tab === 'distribute' && it.kind !== 'distribute') return false;
    if (filter === 'press'  && it.kind !== 'press')  return false;
    if (filter === 'social' && it.kind !== 'social') return false;
    return true;
  });

  const counts = {
    library:    OUTREACH_ITEMS.length,
    press:      OUTREACH_ITEMS.filter(x=>x.kind==='press').length,
    social:     OUTREACH_ITEMS.filter(x=>x.kind==='social').length,
    distribute: OUTREACH_ITEMS.filter(x=>x.kind==='distribute').length,
  };

  const project = PROJECTS.find(p => p.id === 'p01');
  const [now, setNow] = React.useState(new Date());
  React.useEffect(() => { const t = setInterval(()=>setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  const tc = now.toTimeString().slice(0, 8);

  return (
    <React.Fragment>
      <div className="titlebar">
        <div className="tl-lights"><span className="r"/><span className="y"/><span className="g"/></div>
        <div className="tl-brand"><span className="badge">EV</span><span>EVOLUM</span></div>
        <div className="tl-crumbs">
          <a href="/studio" style={{color:'var(--text-3)', textDecoration:'none'}}>Workspace</a>
          <span className="sep">/</span>
          <strong>All Projects</strong>
          <span className="sep">/</span>
          <span style={{color:'var(--accent)'}}>Outreach Hub</span>
        </div>
        <div className="tl-spacer"/>
        <div className="tl-meta"><span className="dot"/><span>SYNC OK</span><span style={{color:'var(--line-3)'}}>·</span><span>{tc}</span></div>
      </div>

      <div className="menubar">
        <button>File</button><button>Edit</button><button>View</button><button>Library</button><button>Window</button><button>Help</button>
        <span className="mb-spacer"/>
        <a className="recall-btn" href="/studio/admin" style={{marginRight:6, textDecoration:'none'}}><Icon name="settings" size={11}/> Admin</a>
        <a className="recall-btn" href="/studio/press" style={{marginRight:6, textDecoration:'none'}}><Icon name="send" size={11}/> Per-Project Press</a>
        <span className="layout-name">LAYOUT · OUTREACH</span>
      </div>

      <div className="workspace-canvas" style={{overflow:'hidden'}}>
        <ToolRail active="press" onPick={()=>{}}/>
        <div style={{ position:'absolute', top:0, left:'var(--tool-rail-w)', right:0, bottom:0, display:'flex', flexDirection:'column' }}>
          <div className="outreach-hero">
            <div>
              <div className="dh-tag">FOUNDER \u00b7 ALL PROJECTS</div>
              <div className="dh-title" style={{fontSize:26, marginBottom:4}}>Outreach Hub</div>
              <div style={{fontSize:11.5, color:'var(--text-2)'}}>Everything you\u2019ve sent, scheduled, or drafted across your slate. Buffer + outlet status, in one place.</div>
            </div>
            <div className="oh-stat-row">
              <div className="dh-stat"><div className="lbl">LIBRARY</div><div className="big"><strong>{OUTREACH_ITEMS.length}</strong></div></div>
              <div className="dh-stat"><div className="lbl">QUEUED</div><div className="big"><strong>{OUTREACH_ITEMS.filter(x=>x.status==='queued' || x.status==='scheduled').length}</strong></div></div>
              <div className="dh-stat"><div className="lbl">LIVE</div><div className="big" style={{color:'var(--ok)'}}><strong>{OUTREACH_ITEMS.filter(x=>x.status==='live' || x.status==='active').length}</strong></div></div>
            </div>
          </div>

          <div className="outreach-tabs">
            <button className={`oh-tab ${tab==='library'?'on':''}`} onClick={()=>setTab('library')}>LIBRARY <span className="n">{counts.library}</span></button>
            <button className={`oh-tab ${tab==='press'?'on':''}`} onClick={()=>setTab('press')}>PRESS <span className="n">{counts.press}</span></button>
            <button className={`oh-tab ${tab==='social'?'on':''}`} onClick={()=>setTab('social')}>SOCIAL <span className="n">{counts.social}</span></button>
            <button className={`oh-tab ${tab==='distribute'?'on':''}`} onClick={()=>setTab('distribute')}>DISTRIBUTE <span className="n">{counts.distribute}</span></button>
          </div>

          <div className="outreach-status">
            <span style={{color:'var(--ok)'}}><Icon name="check" size={11}/></span>
            <span>Last run: 0 of 15 posts queued \u00b7 1 day ago</span>
            <button className="oh-detail">details</button>
            <button className="ph-btn"><Icon name="close" size={11}/></button>
          </div>

          <div className="outreach-filter">
            <button className={`chip ${filter==='all'?'on':''}`} onClick={()=>setFilter('all')}>All</button>
            <button className={`chip ${filter==='press'?'on':''}`} onClick={()=>setFilter('press')}>Press only</button>
            <button className={`chip ${filter==='social'?'on':''}`} onClick={()=>setFilter('social')}>Social only</button>
            <input className="field" placeholder="evolumstudio@gmail.com" value={q} onChange={e=>setQ(e.target.value)} style={{flex:1, maxWidth:420}}/>
            <span style={{fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-3)', letterSpacing:'.08em'}}>{filtered.length} OF {OUTREACH_ITEMS.length}</span>
          </div>

          <div style={{flex:1, overflowY:'auto', padding:'0 18px 24px'}}>
            <div className="outreach-list">
              <div className="ol-head">
                <span/>
                <span>Project</span>
                <span>Type</span>
                <span>Headline</span>
                <span>Recipients</span>
                <span>Status</span>
                <span>Engagement</span>
                <span>Date</span>
              </div>
              {filtered.length === 0 ? (
                <div style={{padding:'40px 12px', textAlign:'center', fontStyle:'italic', color:'var(--text-3)'}}>No matches for that filter.</div>
              ) : filtered.map((it,i) => (
                <div key={it.id} className="ol-row">
                  <span className="ol-n">{String(i+1).padStart(2,'0')}</span>
                  <span className="ol-proj">{it.project}</span>
                  <span className="ol-type">{it.type}</span>
                  <span className="ol-head-text">{it.headline}</span>
                  <span className="ol-recipients">{it.recipients}</span>
                  <span>
                    <span className="status-pill" style={{ color: STATUS_COLORS_OH[it.status], background: 'rgba(255,255,255,0.04)' }}>
                      <span className="d" style={{ background: STATUS_COLORS_OH[it.status] }}/>{it.status.toUpperCase()}
                    </span>
                  </span>
                  <span className="ol-engagement">{it.engagement}</span>
                  <span className="ol-date">{it.date}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="statusbar">
        <div className="stat"><span className="lbl">TOTAL</span><span className="num">{OUTREACH_ITEMS.length}</span></div>
        <div className="stat"><span className="lbl">LIVE</span><span className="num">{OUTREACH_ITEMS.filter(x=>x.status==='live'||x.status==='active').length}</span></div>
        <div className="stat"><span className="lbl">SENT</span><span className="num">{OUTREACH_ITEMS.filter(x=>x.status==='sent'||x.status==='submitted').length}</span></div>
        <div className="stat"><span className="lbl">QUEUE</span><span className="num">{OUTREACH_ITEMS.filter(x=>x.status==='queued'||x.status==='scheduled').length}</span></div>
        <div className="sb-spacer"/>
        <div className="sb-right">
          <span><span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:'var(--ok)',marginRight:5,verticalAlign:'middle',boxShadow:'0 0 6px var(--ok-glow)'}}/>Buffer connected</span>
          <span>{tc}</span>
        </div>
      </div>
    </React.Fragment>
  );
};

ReactDOM.createRoot(document.getElementById('app')).render(<OutreachApp/>);
