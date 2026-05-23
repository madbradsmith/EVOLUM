/* =====================================================================
   Sample data — film projects on Evolum
   ===================================================================== */
const STAGES = {
  idea:    { label: 'Idea',         color: 'var(--st-idea)' },
  script:  { label: 'Script',       color: 'var(--st-script)' },
  poster:  { label: 'Poster',       color: 'var(--st-poster)' },
  pitch:   { label: 'Pitch',        color: 'var(--st-pitch)' },
  sizzle:  { label: 'Sizzle',       color: 'var(--st-sizzle)' },
  casting: { label: 'Casting',      color: 'var(--st-casting)' },
  invest:  { label: 'Invest',       color: 'var(--st-invest)' },
  deliver: { label: 'Deliverables', color: 'var(--st-deliver)' },
};

const PROJECTS = [
  { id:'p01', code:'EV-001', title:'Mandatory Reporter', kind:'Feature',      stage:'invest',  pages:114, runtime:'01:52:00', updated:'today 3:24p', owner:'You',         team:['EV','MR','TK'],       progress:{ script:100, pitch:100, poster:100, casting:78, invest:64, deliver:0 }, c1:'#3a2820', c2:'#1f140d', glyph:'MR' },
  { id:'p02', code:'EV-002', title:'Court Jester',       kind:'Feature',      stage:'invest',  pages:108, runtime:'01:46:00', updated:'today 1:08p', owner:'You',         team:['EV','MR','AH'],       progress:{ script:100, pitch:100, poster:100, casting:90, invest:55, deliver:0 }, c1:'#3a2418', c2:'#22120a', glyph:'CJ' },
  { id:'p03', code:'EV-003', title:'Tax Season',         kind:'Feature',      stage:'pitch',   pages:96,  runtime:'01:34:00', updated:'yesterday',   owner:'M. Reyes',    team:['EV','MR','TK','AH'],  progress:{ script:100, pitch:72, poster:100, casting:18, invest:0, deliver:0 }, c1:'#3a2e1a', c2:'#1e1709', glyph:'TS' },
  { id:'p04', code:'EV-004', title:'Who Invited You?',   kind:'Feature',      stage:'pitch',   pages:88,  runtime:'01:28:00', updated:'2d ago',      owner:'You',         team:['EV','JN'],            progress:{ script:100, pitch:55, poster:80, casting:0, invest:0, deliver:0 }, c1:'#2a1f3a', c2:'#161024', glyph:'WI' },
  { id:'p05', code:'EV-005', title:'House Of Echoes',    kind:'Series Pilot', stage:'pitch',   pages:62,  runtime:'00:54:00', updated:'3d ago',      owner:'T. Kapoor',   team:['EV','TK','MR'],       progress:{ script:100, pitch:48, poster:75, casting:0, invest:0, deliver:0 }, c1:'#2a3142', c2:'#161a26', glyph:'HE' },
  { id:'p06', code:'EV-006', title:'Just Walk In',       kind:'Short',        stage:'pitch',   pages:24,  runtime:'00:18:30', updated:'4d ago',      owner:'A. Holt',     team:['EV','AH','JN'],       progress:{ script:100, pitch:60, poster:90, casting:30, invest:0, deliver:0 }, c1:'#3a221f', c2:'#221311', glyph:'JW' },
  { id:'p07', code:'EV-007', title:'Like You Belong',    kind:'Feature',      stage:'pitch',   pages:92,  runtime:'01:30:00', updated:'5d ago',      owner:'You',         team:['EV','MR'],            progress:{ script:100, pitch:42, poster:65, casting:0, invest:0, deliver:0 }, c1:'#2c1f30', c2:'#19121c', glyph:'LY' },
  { id:'p08', code:'EV-008', title:'Hollow Crown',       kind:'Series Pilot', stage:'script',  pages:58,  runtime:'00:54:00', updated:'1w ago',      owner:'You',         team:['EV','MR','TK','AH','JN'], progress:{ script:64, pitch:0, poster:0, casting:0, invest:0, deliver:0 }, c1:'#3a2a2a', c2:'#211616', glyph:'HC' },
  { id:'p09', code:'EV-009', title:'Quiet War',          kind:'Feature',      stage:'casting', pages:104, runtime:'01:42:00', updated:'1w ago',      owner:'You',         team:['EV','TK'],            progress:{ script:100, pitch:100, poster:100, casting:55, invest:24, deliver:0 }, c1:'#23323a', c2:'#14202a', glyph:'QW' },
  { id:'p10', code:'EV-010', title:'Eastbound',          kind:'Short',        stage:'deliver', pages:24,  runtime:'00:18:30', updated:'2w ago',      owner:'A. Holt',     team:['EV','AH','JN'],       progress:{ script:100, pitch:100, poster:100, casting:100, invest:100, deliver:78 }, c1:'#1c3a2e', c2:'#0f251c', glyph:'EB' },
  { id:'p11', code:'EV-011', title:'Soft Static',        kind:'Short',        stage:'poster',  pages:22,  runtime:'00:14:00', updated:'3w ago',      owner:'M. Reyes',    team:['EV','MR'],            progress:{ script:100, pitch:30, poster:62, casting:0, invest:0, deliver:0 }, c1:'#202a2c', c2:'#10181a', glyph:'SS' },
  { id:'p12', code:'EV-012', title:'North Light',        kind:'Documentary',  stage:'idea',    pages:0,   runtime:'00:00:00', updated:'1mo ago',     owner:'You',         team:['EV'],                 progress:{ script:14, pitch:0, poster:0, casting:0, invest:0, deliver:0 }, c1:'#1f2c3a', c2:'#0f1822', glyph:'NL' },
  { id:'p13', code:'EV-013', title:'Bone Music',         kind:'Short',        stage:'sizzle',  pages:31,  runtime:'00:24:00', updated:'1mo ago',     owner:'J. Naidu',    team:['EV','JN'],            progress:{ script:100, pitch:80, poster:75, casting:100, invest:0, deliver:30 }, c1:'#2a1f3a', c2:'#190f24', glyph:'BM' },
  { id:'p14', code:'EV-014', title:'Halo Of Wires',      kind:'Series Pilot', stage:'idea',    pages:0,   runtime:'00:00:00', updated:'1mo ago',     owner:'M. Reyes',    team:['MR'],                 progress:{ script:8, pitch:0, poster:0, casting:0, invest:0, deliver:0 }, c1:'#2a2e3a', c2:'#171a24', glyph:'HW' },
  { id:'p15', code:'EV-015', title:'Mercy Lane',         kind:'Feature',      stage:'idea',    pages:0,   runtime:'00:00:00', updated:'1mo ago',     owner:'T. Kapoor',   team:['TK'],                 progress:{ script:0, pitch:0, poster:0, casting:0, invest:0, deliver:0 }, c1:'#2c2030', c2:'#19121c', glyph:'ML' },
  { id:'p16', code:'EV-016', title:'The Calling',        kind:'Feature',      stage:'idea',    pages:0,   runtime:'00:00:00', updated:'2mo ago',     owner:'A. Holt',     team:['EV','AH'],            progress:{ script:0, pitch:0, poster:0, casting:0, invest:0, deliver:0 }, c1:'#3a3220', c2:'#241e10', glyph:'TC' },
];

const TOOLS = [
  { id:'idea',    label:'Idea',    icon:'idea',    n:9 },
  { id:'script',  label:'Script',  icon:'script',  n:4 },
  { id:'poster',  label:'Poster',  icon:'poster',  n:2 },
  { id:'pitch',   label:'Pitch',   icon:'pitch',   n:3 },
  { id:'sizzle',  label:'Sizzle',  icon:'sizzle',  n:1 },
  { id:'casting', label:'Casting', icon:'casting', n:1 },
  { id:'invest',  label:'Invest',  icon:'invest',  n:2 },
  { id:'deliver', label:'Deliver', icon:'deliver', n:1 },
];

const ACTIVITY = [
  { t:'14:32:08', who:'Warren',     tag:'script',  what:'Drafted Act II scene outline for Big Sanitation',     proj:'EV-001' },
  { t:'14:28:51', who:'You',        tag:'invest',  what:'Set funding goal to $500,000',                         proj:'EV-001' },
  { t:'14:14:02', who:'M. Reyes',   tag:'poster',  what:'Uploaded poster_v3.png',                                proj:'EV-001' },
  { t:'13:50:33', who:'Warren',     tag:'pitch',   what:'Generated 2 new title slide variations',               proj:'EV-007' },
  { t:'13:41:18', who:'T. Kapoor',  tag:'casting', what:'Shortlisted 6 actors for the role of Naomi',           proj:'EV-005' },
  { t:'12:55:00', who:'You',        tag:'script',  what:'Approved revision pass on pp. 48–62',                  proj:'EV-002' },
  { t:'12:30:44', who:'A. Holt',    tag:'deliver', what:'Exported ProRes master + DCP for Eastbound',           proj:'EV-006' },
  { t:'11:48:09', who:'Warren',     tag:'idea',    what:'Found 3 reference films matching tone of Hollow Crown',proj:'EV-004' },
  { t:'11:22:51', who:'J. Naidu',   tag:'sizzle',  what:'Cut sizzle reel v2 — 1:46',                            proj:'EV-008' },
  { t:'10:15:00', who:'You',        tag:'invest',  what:'Published investor portal (Pitching mode)',            proj:'EV-001' },
  { t:'09:55:21', who:'M. Reyes',   tag:'script',  what:'Locked Act I for Tundra',                              proj:'EV-003' },
  { t:'09:30:00', who:'System',     tag:'deliver', what:'Backup completed — 47 GB',                             proj:'—'      },
];

const WARREN_MESSAGES = [
  { who:'warren', text:"I'm here. What are we working on — welcome message, synopsis, strategy?" },
  { who:'you',    text:"Pull up Big Sanitation. Where are we on the investor side?" },
  { who:'warren', text:"Portal is in Pitching mode, $500k goal, equity deal. 4 of 12 investors have signed the NDA. Want me to draft the next outreach?" },
];

/* =====================================================================
   Tool rail — navigates between rooms via href
   ===================================================================== */
const TOOL_HREFS = {
  idea:    'Evolum Idea.html',
  script:  'Evolum Script.html',
  poster:  'Evolum Poster.html',
  pitch:   'Evolum Pitch.html',
  sizzle:  'Evolum Sizzle.html',
  casting: 'Evolum Self-Tape.html',
  invest:  'Evolum Investor.html',
  deliver: 'Evolum Deliverables.html',
};

const ToolRail = ({ active, onPick }) => (
  <div className="tool-rail">
    <div className="tr-head">TOOLS</div>
    <a className={`tool-btn home-btn ${active==='workspace'?'active':''}`} href="/studio" title="Workspace · All Projects">
      <span className="ic"><Icon name="folder" size={20}/></span>
      <span className="lbl">All</span>
    </a>
    <div className="tool-divider"/>
    <div className="tr-list">
      {TOOLS.slice(0, 4).map(t => {
        const href = TOOL_HREFS[t.id];
        const Tag = href ? 'a' : 'button';
        const props = href ? { href } : { onClick: () => onPick(t.id) };
        return (
          <Tag key={t.id} className={`tool-btn ${active===t.id?'active':''}`} {...props} title={t.label}>
            <span className="ic"><Icon name={t.icon} size={20}/></span>
            <span className="lbl">{t.label}</span>
            {t.n ? <span className="badge-n">{t.n}</span> : null}
          </Tag>
        );
      })}
      <div className="tool-divider"/>
      {TOOLS.slice(4).map(t => {
        const href = TOOL_HREFS[t.id];
        const Tag = href ? 'a' : 'button';
        const props = href ? { href } : { onClick: () => onPick(t.id) };
        return (
          <Tag key={t.id} className={`tool-btn ${active===t.id?'active':''}`} {...props} title={t.label}>
            <span className="ic"><Icon name={t.icon} size={20}/></span>
            <span className="lbl">{t.label}</span>
            {t.n ? <span className="badge-n">{t.n}</span> : null}
          </Tag>
        );
      })}
    </div>
    <div className="tr-foot">
      <button className="tool-btn" title="Settings"><span className="ic"><Icon name="settings" size={18}/></span></button>
      <div className="av">E</div>
    </div>
  </div>
);

/* =====================================================================
   Projects panel content
   ===================================================================== */
const ProjectCard = ({ p, selected, onClick }) => (
  <div className={`proj-card ${selected?'selected':''}`}
       style={{'--c1':p.c1,'--c2':p.c2}}
       onClick={onClick}>
    <div className="proj-thumb">
      <span className="pt-tag">{p.code}</span>
      <span className="pt-glyph">{p.glyph}</span>
      <span className="pt-stage" style={{ color: STAGES[p.stage].color }}>{STAGES[p.stage].label}</span>
      <span className="pt-tc">{p.runtime}</span>
    </div>
    <div className="proj-card-meta">
      <div className="ttl">{p.title}</div>
      <div className="sub">
        <span>{p.kind}</span>
        <span className="dot"/>
        <span>{p.pages ? `${p.pages} pp` : 'no script'}</span>
        <span className="dot"/>
        <span>{p.updated}</span>
      </div>
    </div>
    <div className="proj-card-bar">
      {Object.entries(p.progress).map(([k,v]) => (
        <span key={k} style={{ background: STAGES[k]?.color || '#444', opacity: v ? 0.35 + (v/100)*0.65 : 0.08 }} title={`${k} ${v}%`}/>
      ))}
    </div>
  </div>
);

const ProjectsView = ({ selected, setSelected, view, setView }) => {
  const [q, setQ] = React.useState('');
  const [filter, setFilter] = React.useState('all');
  const filtered = PROJECTS.filter(p =>
    (filter==='all' ? true : filter==='mine' ? p.owner==='You' : p.stage===filter)
    && (q==='' || p.title.toLowerCase().includes(q.toLowerCase()) || p.code.toLowerCase().includes(q.toLowerCase()))
  );
  const showHero = filter === 'all' && q === '' && view === 'grid';
  const live    = filtered.filter(p => p.stage === 'invest' || p.stage === 'deliver');
  const pitching = filtered.filter(p => p.stage === 'pitch');
  const inScript = filtered.filter(p => p.stage === 'script' || p.stage === 'poster' || p.stage === 'sizzle' || p.stage === 'casting');
  const ideas   = filtered.filter(p => p.stage === 'idea');

  const liveCount = PROJECTS.filter(p => p.stage === 'invest' || p.stage === 'deliver').length;

  return (
    <React.Fragment>
      <div className="proj-toolbar">
        <div className="search">
          <Icon name="search" size={12}/>
          <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search projects, codes, owners…"/>
          {q ? <button onClick={()=>setQ('')} style={{color:'var(--text-3)'}}><Icon name="close" size={11}/></button> : null}
        </div>
        <button className={`chip ${filter==='all'?'on':''}`} onClick={()=>setFilter('all')}>All <span style={{color:'var(--text-3)',marginLeft:4,fontFamily:'var(--font-mono)'}}>{PROJECTS.length}</span></button>
        <button className={`chip ${filter==='mine'?'on':''}`} onClick={()=>setFilter('mine')}>Mine</button>
        <button className={`chip ${filter==='script'?'on':''}`} onClick={()=>setFilter('script')}>In Script</button>
        <button className={`chip ${filter==='pitch'?'on':''}`} onClick={()=>setFilter('pitch')}>Pitching</button>
        <button className={`chip ${filter==='invest'?'on':''}`} onClick={()=>setFilter('invest')}>Investing</button>
        <div className="grow"/>
        <button className="chip" title="Sort"><Icon name="sort" size={12}/> Updated</button>
        <div className="view-toggle">
          <button className={view==='grid'?'on':''} onClick={()=>setView('grid')} title="Grid"><Icon name="grid" size={12}/></button>
          <button className={view==='list'?'on':''} onClick={()=>setView('list')} title="List"><Icon name="list" size={12}/></button>
        </div>
        <button className="chip" style={{color:'var(--accent)',borderColor:'var(--line-2)'}}><Icon name="plus" size={12}/> New</button>
      </div>

      {view==='grid' ? (
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {showHero && (
            <div className="proj-hero">
              <div>
                <div className="greet">Welcome back, evolumstudio</div>
                <div className="num-headline"><em>{PROJECTS.length}</em> good ideas.</div>
              </div>
              <div className="sub">{PROJECTS.length} projects · {liveCount} live · {PROJECTS.filter(p=>p.stage==='pitch').length} pitching</div>
            </div>
          )}

          {showHero ? (
            <React.Fragment>
              {live.length > 0 && (
                <React.Fragment>
                  <div className="proj-section-head">Live <span className="badge">{live.length}</span></div>
                  <div className="proj-grid">{live.map(p => <ProjectCard key={p.id} p={p} selected={selected===p.id} onClick={()=>setSelected(p.id)}/>)}</div>
                </React.Fragment>
              )}
              {pitching.length > 0 && (
                <React.Fragment>
                  <div className="proj-section-head">Pitching <span className="badge">{pitching.length}</span></div>
                  <div className="proj-grid">{pitching.map(p => <ProjectCard key={p.id} p={p} selected={selected===p.id} onClick={()=>setSelected(p.id)}/>)}</div>
                </React.Fragment>
              )}
              {inScript.length > 0 && (
                <React.Fragment>
                  <div className="proj-section-head">In Development <span className="badge">{inScript.length}</span></div>
                  <div className="proj-grid">{inScript.map(p => <ProjectCard key={p.id} p={p} selected={selected===p.id} onClick={()=>setSelected(p.id)}/>)}</div>
                </React.Fragment>
              )}
              {ideas.length > 0 && (
                <React.Fragment>
                  <div className="proj-section-head">Ideas <span className="badge">{ideas.length}</span></div>
                  <div className="proj-grid">{ideas.map(p => <ProjectCard key={p.id} p={p} selected={selected===p.id} onClick={()=>setSelected(p.id)}/>)}</div>
                </React.Fragment>
              )}
            </React.Fragment>
          ) : (
            <div className="proj-grid">
              {filtered.map(p => (
                <ProjectCard key={p.id} p={p} selected={selected===p.id} onClick={()=>setSelected(p.id)}/>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="proj-list">
          <div className="pl-row pl-head">
            <span/>
            <span>Title</span>
            <span>Kind</span>
            <span>Stage</span>
            <span>Updated</span>
            <span style={{textAlign:'right'}}>Pages</span>
          </div>
          {filtered.map(p => (
            <div key={p.id} className={`pl-row ${selected===p.id?'selected':''}`} onClick={()=>setSelected(p.id)}>
              <span className="ic"><Icon name="film" size={12}/></span>
              <span className="ttl">{p.title} <span style={{color:'var(--text-3)',marginLeft:6,fontSize:10}}>{p.code}</span></span>
              <span>{p.kind}</span>
              <span className="stage" style={{ color: STAGES[p.stage].color, background:'rgba(255,255,255,0.04)' }}>{STAGES[p.stage].label}</span>
              <span>{p.updated}</span>
              <span className="num" style={{textAlign:'right'}}>{p.pages||'—'}</span>
            </div>
          ))}
        </div>
      )}
    </React.Fragment>
  );
};

/* =====================================================================
   Inspector panel content
   ===================================================================== */
const Inspector = ({ project }) => {
  const [tab, setTab] = React.useState('details');
  if (!project) {
    return (
      <div style={{padding:14, color:'var(--text-3)', fontSize:11}}>Select a project to inspect.</div>
    );
  }
  return (
    <React.Fragment>
      <div className="tabs">
        {['details','team','files','activity'].map(t => (
          <button key={t} className={tab===t?'on':''} onClick={()=>setTab(t)}>{t.toUpperCase()}</button>
        ))}
      </div>
      <div className="insp">
        <div className="ins-hero" style={{'--c1':project.c1,'--c2':project.c2}}>
          <span className="tag">{project.code} · {project.kind.toUpperCase()}</span>
          <span className="glyph">{project.glyph}</span>
        </div>
        <div>
          <h3>{project.title}</h3>
          <div className="sub">{project.code} · UPDATED {project.updated.toUpperCase()}</div>
        </div>

        {tab==='details' && (
          <React.Fragment>
            <div className="kv">
              <span className="k">Stage</span>
              <span className="v">
                <span className="stage-pill" style={{ color: STAGES[project.stage].color, background:'rgba(255,255,255,0.04)' }}>
                  <span className="d" style={{ background: STAGES[project.stage].color }}/>
                  {STAGES[project.stage].label}
                </span>
              </span>
              <span className="k">Kind</span><span className="v">{project.kind}</span>
              <span className="k">Owner</span><span className="v">{project.owner}</span>
              <span className="k">Pages</span><span className="v mono">{project.pages || '—'}</span>
              <span className="k">Runtime</span><span className="v mono">{project.runtime}</span>
              <span className="k">Team</span>
              <span className="v">
                <div className="team">
                  {project.team.map(t => <div key={t} className="avt">{t}</div>)}
                  <span className="more">{project.team.length} members</span>
                </div>
              </span>
            </div>

            <div style={{borderTop:'1px solid var(--line-1)', paddingTop:10}}>
              <div style={{fontSize:9.5, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:7}}>Pipeline</div>
              <div className="progress">
                {Object.entries(project.progress).map(([k,v]) => (
                  <div key={k} className="pr-row">
                    <span className="lbl">{STAGES[k]?.label || k}</span>
                    <span className="bar"><span style={{ width:`${v}%`, background: STAGES[k]?.color || '#666' }}/></span>
                    <span className="pct">{v}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="actions">
              <button className="btn primary"><Icon name="chevron" size={11}/> Open</button>
              <button className="btn"><Icon name="sparkle" size={11}/> Ask Warren</button>
            </div>
          </React.Fragment>
        )}

        {tab==='team' && (
          <div style={{display:'flex',flexDirection:'column',gap:6, fontSize:11}}>
            {project.team.map(t => (
              <div key={t} style={{display:'flex',alignItems:'center',gap:8, padding:'6px 8px', background:'var(--bg-2)', border:'1px solid var(--line-1)', borderRadius:3}}>
                <div className="avt" style={{width:24,height:24,borderRadius:'50%',background:'var(--bg-4)',display:'flex',alignItems:'center',justifyContent:'center',fontSize:10,fontWeight:700,border:'1px solid var(--line-2)'}}>{t}</div>
                <div>
                  <div style={{color:'var(--text-1)'}}>{t==='EV'?'You':t==='MR'?'M. Reyes':t==='TK'?'T. Kapoor':t==='AH'?'A. Holt':'J. Naidu'}</div>
                  <div style={{color:'var(--text-3)', fontSize:10}}>Editor</div>
                </div>
              </div>
            ))}
          </div>
        )}
        {tab==='files' && (
          <div style={{fontFamily:'var(--font-mono)', fontSize:10.5, color:'var(--text-2)'}}>
            {['script_v14.fdx','poster_v3.png','pitch_deck_v8.pptx','synopsis.md','budget_top_sheet.xlsx','sizzle_v2.mp4'].map(f => (
              <div key={f} style={{display:'flex',gap:8,alignItems:'center',padding:'4px 4px',borderBottom:'1px solid var(--line-1)'}}>
                <Icon name="folder" size={12}/>
                <span style={{flex:1, color:'var(--text-1)'}}>{f}</span>
                <span style={{color:'var(--text-3)'}}>{Math.floor(Math.random()*400+10)}kb</span>
              </div>
            ))}
          </div>
        )}
        {tab==='activity' && (
          <div style={{fontFamily:'var(--font-mono)', fontSize:10.5, color:'var(--text-2)'}}>
            {ACTIVITY.filter(a => a.proj===project.code).slice(0,8).map((a,i) => (
              <div key={i} style={{padding:'5px 0', borderBottom:'1px solid var(--line-1)'}}>
                <div style={{color:'var(--text-3)', fontSize:10}}>{a.t} · {a.who}</div>
                <div style={{color:'var(--text-1)', fontFamily:'var(--font-ui)', fontSize:11}}>{a.what}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </React.Fragment>
  );
};

/* =====================================================================
   Activity panel content
   ===================================================================== */
const Activity = () => (
  <div className="act">
    <div className="row head">
      <span>TIME</span>
      <span>WHO</span>
      <span>TOOL</span>
      <span>EVENT</span>
      <span>PROJECT</span>
    </div>
    {ACTIVITY.map((a,i) => (
      <div key={i} className="row">
        <span>{a.t}</span>
        <span className="who">{a.who}</span>
        <span className="tag" style={{ color: STAGES[a.tag]?.color, background:'rgba(255,255,255,0.04)' }}>{STAGES[a.tag]?.label || a.tag}</span>
        <span className="what">{a.what}</span>
        <span>{a.proj}</span>
      </div>
    ))}
  </div>
);

/* =====================================================================
   Warren assistant panel content
   ===================================================================== */
const Warren = () => {
  const [msgs, setMsgs] = React.useState(WARREN_MESSAGES);
  const [val, setVal] = React.useState('');
  const send = () => {
    if (!val.trim()) return;
    setMsgs(m => [...m, { who:'you', text: val }]);
    const q = val;
    setVal('');
    setTimeout(() => {
      setMsgs(m => [...m, { who:'warren', text: `On it. Pulling that up now — “${q}”` }]);
    }, 600);
  };
  return (
    <div className="warren">
      <div className="stream">
        {msgs.map((m,i) => (
          <div key={i} className={`msg ${m.who==='you'?'you':''}`}>
            <div className="avt">{m.who==='you' ? 'E' : 'W'}</div>
            <div className="body">
              <div className="who">{m.who==='you'?'You':'Warren · Investor Room'}</div>
              <div>{m.text}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="input-row">
        <input type="text" value={val} onChange={e=>setVal(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter') send(); }} placeholder="Talk to Warren…"/>
        <button className="send" onClick={send}>Send</button>
      </div>
    </div>
  );
};

Object.assign(window, { ToolRail, ProjectsView, Inspector, Activity, Warren, PROJECTS, ACTIVITY, STAGES });
