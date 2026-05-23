/* =====================================================================
   EVOLUM — Admin Dashboard (platform-level)
   ===================================================================== */
const ADMIN_TABS = [
  { id:'overview', name:'Overview' },
  { id:'users',    name:'Users' },
  { id:'projects', name:'Projects' },
  { id:'messages', name:'Messages' },
  { id:'visitors', name:'Visitors' },
  { id:'costs',    name:'Costs' },
  { id:'system',   name:'System' },
];

const ENV_CHECKS = [
  { name:'Supabase',             state:'ok',    val:'Connected' },
  { name:'ANTHROPIC_API_KEY',    state:'ok',    val:'Set' },
  { name:'FAL_API_KEY',          state:'ok',    val:'Set' },
  { name:'STRIPE_SECRET_KEY',    state:'ok',    val:'Set' },
  { name:'SUPABASE_URL',         state:'ok',    val:'Set' },
  { name:'SUPABASE_SERVICE_KEY', state:'ok',    val:'Set' },
  { name:'ELEVENLABS_API_KEY',   state:'ok',    val:'Set' },
  { name:'BUFFER_TOKEN',         state:'ok',    val:'Set' },
];

const DEBUG_LINKS = [
  { name:'Health Check',  desc:'App status JSON' },
  { name:'Build Status',  desc:'Pipeline state' },
  { name:'Supabase \u2197', desc:'Database + Auth + Storage' },
  { name:'Render Logs \u2197', desc:'Live server output' },
];

const ADMIN_USERS = [
  { id:'u01', email:'evolumstudio@gmail.com',   role:'Founder',   plan:'\u2014',       projects:16, joined:'2024-11-04', last:'today 5:14p' },
  { id:'u02', email:'m.reyes@northlight.films', role:'Filmmaker', plan:'Studio',   projects:4,  joined:'2025-01-22', last:'today 2:08p' },
  { id:'u03', email:'t.kapoor@filmmaker.io',    role:'Filmmaker', plan:'Indie',    projects:2,  joined:'2025-03-14', last:'today 1:30p' },
  { id:'u04', email:'a.holt@independent.tv',    role:'Filmmaker', plan:'Indie',    projects:3,  joined:'2025-04-02', last:'yesterday' },
  { id:'u05', email:'l.marquez@hollowbrook.vc', role:'Investor',  plan:'\u2014',       projects:0,  joined:'2025-08-12', last:'today 12:14p' },
  { id:'u06', email:'d.chen@northstarfilms.io', role:'Investor',  plan:'\u2014',       projects:0,  joined:'2025-09-04', last:'yesterday' },
  { id:'u07', email:'j.naidu@indie.studio',     role:'Filmmaker', plan:'Boutique', projects:5,  joined:'2025-02-19', last:'3d ago' },
  { id:'u08', email:'r.tanaka@aspenco.fund',    role:'Investor',  plan:'\u2014',       projects:0,  joined:'2025-11-01', last:'4d ago' },
];

const COSTS = [
  { name:'FAL AI Credits',  state:'warn', val:'[Errno -2] Name or service not known — check dashboard \u2197' },
  { name:'Anthropic (Claude)', state:'ok',  val:'No balance API — check console \u2197' },
  { name:'Stripe',          state:'ok',    val:'View dashboard \u2197' },
  { name:'Render Server',   state:'ok',    val:'View server costs \u2197' },
];

const BILLING_DASHBOARDS = [
  { name:'Stripe Dashboard \u2197',     desc:'Subscriptions, revenue, payouts' },
  { name:'Anthropic Console \u2197',    desc:'Claude API usage + billing' },
  { name:'FAL Dashboard \u2197',        desc:'Image generation credits' },
  { name:'Supabase Dashboard \u2197',   desc:'DB usage + auth + storage' },
  { name:'Render Dashboard \u2197',     desc:'Server costs + logs' },
];

const AdminApp = () => {
  const [tab, setTab] = React.useState('overview');
  const [now, setNow] = React.useState(new Date());
  React.useEffect(() => { const t = setInterval(()=>setNow(new Date()), 1000); return () => clearInterval(t); }, []);
  const tc = now.toTimeString().slice(0, 8);

  return (
    <React.Fragment>
      <div className="titlebar">
        <div className="tl-lights"><span className="r"/><span className="y"/><span className="g"/></div>
        <div className="tl-brand"><span className="badge">EV</span><span>EVOLUM</span></div>
        <div className="tl-crumbs">
          <a href="/studio" style={{color:'var(--text-3)', textDecoration:'none'}}>Platform</a>
          <span className="sep">/</span>
          <span style={{color:'var(--accent)'}}>Admin</span>
          <span className="sep">/</span>
          <span>{ADMIN_TABS.find(t=>t.id===tab)?.name}</span>
        </div>
        <div className="tl-spacer"/>
        <div className="tl-meta"><span className="dot"/><span>SYSTEM OK</span><span style={{color:'var(--line-3)'}}>·</span><span>{tc}</span></div>
      </div>

      <div className="menubar">
        <button>File</button><button>View</button><button>Tools</button><button>Window</button><button>Help</button>
        <span className="mb-spacer"/>
        <a className="recall-btn" href="/studio/outreach" style={{marginRight:6, textDecoration:'none'}}><Icon name="send" size={11}/> Outreach Hub</a>
        <a className="recall-btn" href="/studio" style={{marginRight:6, textDecoration:'none'}}><Icon name="folder" size={11}/> Studio</a>
        <span className="layout-name">V2 \u00b7 STUDIO PLATFORM</span>
      </div>

      <div className="workspace-canvas" style={{overflow:'hidden'}}>
        <ToolRail active="admin" onPick={()=>{}}/>
        <div style={{ position:'absolute', top:0, left:'var(--tool-rail-w)', right:0, bottom:0, display:'flex', flexDirection:'column' }}>
          <div className="admin-header">
            <div>
              <div className="admin-title">EVOLUM <span className="admin-tag">Admin</span></div>
              <div className="admin-sub">V2 \u00b7 STUDIO PLATFORM \u00b7 evolumstudio.com</div>
            </div>
            <div className="admin-actions">
              <button className="btn"><Icon name="check" size={11}/> Health</button>
              <button className="btn"><Icon name="undock" size={11}/> Sign Out</button>
            </div>
          </div>

          <div className="admin-tabs">
            {ADMIN_TABS.map(t => (
              <button key={t.id} className={`admin-tab ${tab===t.id?'on':''}`} onClick={()=>setTab(t.id)}>{t.name}</button>
            ))}
          </div>

          <div className="admin-body">
            {tab==='overview' && <AdminOverview/>}
            {tab==='users'    && <AdminUsers/>}
            {tab==='projects' && <AdminProjects/>}
            {tab==='messages' && <AdminMessages/>}
            {tab==='visitors' && <AdminVisitors/>}
            {tab==='costs'    && <AdminCosts/>}
            {tab==='system'   && <AdminSystem/>}
          </div>
        </div>
      </div>

      <div className="statusbar">
        <div className="stat"><span className="lbl">USERS</span><span className="num">{ADMIN_USERS.length}</span></div>
        <div className="stat"><span className="lbl">PROJECTS</span><span className="num">{PROJECTS.length}</span></div>
        <div className="stat"><span className="lbl">MRR</span><span className="num">$1013.85</span></div>
        <div className="stat"><span className="lbl">DEAL FLOW</span><span className="num">$8.1M</span></div>
        <div className="sb-spacer"/>
        <div className="sb-right">
          <span><span style={{display:'inline-block',width:6,height:6,borderRadius:'50%',background:'var(--ok)',marginRight:5,verticalAlign:'middle',boxShadow:'0 0 6px var(--ok-glow)'}}/>All systems healthy</span>
          <span>{tc}</span>
        </div>
      </div>
    </React.Fragment>
  );
};

const AdminOverview = () => (
  <React.Fragment>
    <div className="admin-section">
      <div className="admin-section-label">Platform Health</div>
      <div className="admin-card-row">
        <div className="admin-card"><div className="admin-card-head"><span className="dot ok"/>Supabase</div><div className="admin-card-value">Connected</div></div>
        <div className="admin-card"><div className="admin-card-head"><span className="dot ok"/>Anthropic API</div><div className="admin-card-value">Key configured</div></div>
        <div className="admin-card"><div className="admin-card-head"><span className="dot ok"/>FAL (Image Gen)</div><div className="admin-card-value">Key configured</div></div>
        <div className="admin-card"><div className="admin-card-head"><span className="dot ok"/>Stripe</div><div className="admin-card-value">Key configured</div></div>
      </div>
    </div>

    <div className="admin-section">
      <div className="admin-section-label">Showcase Bench (15 placeholder profiles)</div>
      <div className="admin-banner">
        <div>
          <div className="bn-title">5 Actors \u00b7 5 Supporters \u00b7 5 Investors</div>
          <div className="bn-sub">Idempotent \u2014 safe to click twice. Uses FAL credits (~15 image generations on first run; reuses existing avatars on subsequent runs).</div>
        </div>
        <div className="bn-actions">
          <button className="btn primary"><Icon name="sparkle" size={11}/> Seed / Refresh</button>
          <button className="btn">Check Status</button>
        </div>
      </div>
    </div>

    <div className="admin-section">
      <div className="admin-section-label">Investor Portal Content (bulk-edit + AI draft)</div>
      <div className="admin-banner">
        <div>
          <div className="bn-title">Welcome \u00b7 Synopsis \u00b7 Cherry-Breaker \u00b7 Stripe links \u2014 across every project</div>
          <div className="bn-sub">Bulk view + edit of welcome / synopsis / cherry-breaker / Stripe across every project. AI drafting lives on each project\u2019s own /invest-manage page now.</div>
        </div>
        <div className="bn-actions">
          <button className="btn primary">Open Bulk Editor \u2192</button>
        </div>
      </div>
    </div>

    <div className="admin-section">
      <div className="admin-section-label">Room Backgrounds (10 cinematic green-screen plates)</div>
      <div className="admin-banner">
        <div>
          <div className="bn-title">Hospital \u00b7 Jail \u00b7 Courtroom \u00b7 Office \u00b7 Police Car \u00b7 Dive Bar \u00b7 Alley \u00b7 Hotel \u00b7 Warehouse \u00b7 White Cyc</div>
          <div className="bn-sub">Uses FAL credits (~10 image generations). Backgrounds are saved to /static/backgrounds and used by the Actor Studio booth + Private Deal Room.</div>
        </div>
        <div className="bn-actions">
          <button className="btn primary">Seed</button>
          <button className="btn">Force Regen All</button>
          <button className="btn">Check Status</button>
        </div>
      </div>
    </div>
  </React.Fragment>
);

const AdminUsers = () => (
  <div className="admin-section">
    <div className="admin-section-label">All Users ({ADMIN_USERS.length})</div>
    <div className="investor-table">
      <div className="iv-head" style={{ gridTemplateColumns:'32px 2fr 0.8fr 0.8fr 0.7fr 1fr 1fr' }}>
        <span/><span>Email</span><span>Role</span><span>Plan</span><span>Projects</span><span>Joined</span><span>Last Seen</span>
      </div>
      {ADMIN_USERS.map((u, i) => (
        <div key={u.id} className="iv-row" style={{ gridTemplateColumns:'32px 2fr 0.8fr 0.8fr 0.7fr 1fr 1fr' }}>
          <span className="iv-n">{String(i+1).padStart(2,'0')}</span>
          <span className="iv-name"><div style={{fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-1)'}}>{u.email}</div></span>
          <span><span className="status-pill" style={{ background:'rgba(255,255,255,0.04)', color: u.role==='Founder'?'var(--accent)':(u.role==='Investor'?'var(--st-script)':'var(--ok)') }}>{u.role.toUpperCase()}</span></span>
          <span style={{fontFamily:'var(--font-mono)', fontSize:11}}>{u.plan}</span>
          <span style={{fontFamily:'var(--font-mono)', color:'var(--accent)'}}>{u.projects}</span>
          <span style={{fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-3)'}}>{u.joined}</span>
          <span style={{fontFamily:'var(--font-mono)', fontSize:11, color:'var(--text-3)'}}>{u.last}</span>
        </div>
      ))}
    </div>
  </div>
);

const AdminProjects = () => (
  <div className="admin-section">
    <div className="admin-section-label">All Projects ({PROJECTS.length}) \u00b7 $8.1M Active Deal Flow</div>
    <div className="proj-list">
      <div className="pl-row pl-head">
        <span/><span>Title</span><span>Kind</span><span>Stage</span><span>Updated</span><span style={{textAlign:'right'}}>Pages</span>
      </div>
      {PROJECTS.map(p => (
        <div key={p.id} className="pl-row">
          <span className="ic"><Icon name="film" size={12}/></span>
          <span className="ttl">{p.title} <span style={{color:'var(--text-3)',marginLeft:6,fontSize:10}}>{p.code}</span></span>
          <span>{p.kind}</span>
          <span className="stage" style={{ color: STAGES[p.stage].color, background:'rgba(255,255,255,0.04)' }}>{STAGES[p.stage].label}</span>
          <span>{p.updated}</span>
          <span className="num" style={{textAlign:'right'}}>{p.pages||'—'}</span>
        </div>
      ))}
    </div>
  </div>
);

const AdminMessages = () => (
  <div className="admin-section">
    <div className="admin-section-label">Recent Platform Messages</div>
    <div className="act">
      <div className="row head"><span>TIME</span><span>FROM</span><span>ROOM</span><span>MESSAGE</span><span>PROJECT</span></div>
      {ACTIVITY.slice(0, 8).map((a,i) => (
        <div key={i} className="row">
          <span>{a.t}</span><span className="who">{a.who}</span>
          <span className="tag" style={{ color: STAGES[a.tag]?.color, background:'rgba(255,255,255,0.04)' }}>{STAGES[a.tag]?.label || a.tag}</span>
          <span className="what">{a.what}</span><span>{a.proj}</span>
        </div>
      ))}
    </div>
  </div>
);

const AdminVisitors = () => (
  <React.Fragment>
    <div className="admin-section">
      <div className="admin-section-label">Visits (last 24h)</div>
      <div className="admin-card-row">
        <div className="admin-card"><div className="admin-card-head">SIGNED-IN VIEWS</div><div className="admin-card-value" style={{fontSize:24, color:'var(--accent)', fontFamily:'Georgia, serif', fontWeight:700}}>342</div></div>
        <div className="admin-card"><div className="admin-card-head">PORTAL VISITS</div><div className="admin-card-value" style={{fontSize:24, color:'var(--ok)', fontFamily:'Georgia, serif', fontWeight:700}}>1,432</div></div>
        <div className="admin-card"><div className="admin-card-head">NDA SIGNED</div><div className="admin-card-value" style={{fontSize:24, color:'var(--st-script)', fontFamily:'Georgia, serif', fontWeight:700}}>7</div></div>
        <div className="admin-card"><div className="admin-card-head">NEW LEADS</div><div className="admin-card-value" style={{fontSize:24, color:'var(--st-pitch)', fontFamily:'Georgia, serif', fontWeight:700}}>11</div></div>
      </div>
    </div>
  </React.Fragment>
);

const AdminCosts = () => (
  <React.Fragment>
    <div className="admin-section">
      <div className="admin-section-label">Live Balances</div>
      <div className="admin-card-row">
        {COSTS.map((c,i) => (
          <div key={i} className="admin-card">
            <div className="admin-card-head"><span className={`dot ${c.state==='warn' ? 'warn' : 'ok'}`}/>{c.name}</div>
            <div className="admin-card-value" style={{ color: c.state==='warn' ? '#c83a4a' : 'var(--text-2)' }}>{c.val}</div>
          </div>
        ))}
      </div>
    </div>
    <div className="admin-section">
      <div className="admin-section-label">Pricing Reference</div>
      <div className="admin-pricing">
        <div><strong>Claude Sonnet 4.6:</strong> $3.00/1M input \u00b7 $15.00/1M output \u00b7 $0.30/1M cache read \u00b7 $3.75/1M cache write</div>
        <div><strong>FAL Flux Schnell:</strong> ~$0.003 / image</div>
        <div><strong>ElevenLabs:</strong> Pro plan \u00b7 100k chars/mo</div>
        <div><strong>Supabase:</strong> Pro plan \u2014 <a style={{color:'var(--accent)'}}>check dashboard \u2197</a></div>
      </div>
    </div>
    <div className="admin-section">
      <div className="admin-section-label">Billing Dashboards</div>
      <div className="admin-card-row">
        {BILLING_DASHBOARDS.map((b,i) => (
          <div key={i} className="admin-card linkish">
            <div className="admin-card-head">{b.name}</div>
            <div className="admin-card-value">{b.desc}</div>
          </div>
        ))}
      </div>
    </div>
  </React.Fragment>
);

const AdminSystem = () => (
  <React.Fragment>
    <div className="admin-section">
      <div className="admin-section-label">Environment Checks</div>
      <div className="admin-card-row">
        {ENV_CHECKS.map((c,i) => (
          <div key={i} className="admin-card">
            <div className="admin-card-head"><span className={`dot ${c.state}`}/>{c.name}</div>
            <div className="admin-card-value">{c.val}</div>
          </div>
        ))}
      </div>
    </div>
    <div className="admin-section">
      <div className="admin-section-label">Debug Links</div>
      <div className="admin-card-row">
        {DEBUG_LINKS.map((d,i) => (
          <div key={i} className="admin-card linkish">
            <div className="admin-card-head">{d.name}</div>
            <div className="admin-card-value">{d.desc}</div>
          </div>
        ))}
      </div>
    </div>
  </React.Fragment>
);

ReactDOM.createRoot(document.getElementById('app')).render(<AdminApp/>);
