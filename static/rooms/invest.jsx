/* =====================================================================
   EVOLUM — Investor Portal room
   ===================================================================== */
const INVEST_SECTIONS = [
  { id:'setup',     name:'Status & Deal',  icon:'invest' },
  { id:'content',   name:'Portal Content', icon:'script' },
  { id:'pipeline',  name:'Pipeline',       icon:'people' },
  { id:'nda',       name:'NDA & Legal',    icon:'folder' },
  { id:'activity',  name:'Activity',       icon:'clock' },
];

const INVESTORS = [
  { id:'i01', name:'Hollow Brook Capital',  contact:'L. Marquez',     status:'committed', amount: 150000, nda:true,  visits: 12, last:'today 12:14p' },
  { id:'i02', name:'North Star Films',       contact:'D. Chen',        status:'committed', amount: 100000, nda:true,  visits: 8,  last:'yesterday' },
  { id:'i03', name:'M. Reyes (angel)',       contact:'M. Reyes',       status:'committed', amount: 50000,  nda:true,  visits: 18, last:'today 2:08p' },
  { id:'i04', name:'Pacific Ridge Partners', contact:'A. Whitford',    status:'review',    amount: 200000, nda:true,  visits: 5,  last:'today 11:30a' },
  { id:'i05', name:'L. Patel',               contact:'L. Patel',       status:'review',    amount: 75000,  nda:true,  visits: 3,  last:'2d ago' },
  { id:'i06', name:'Beacon Equity',          contact:'S. Adeyemi',     status:'nda',       amount: null,   nda:true,  visits: 4,  last:'3d ago' },
  { id:'i07', name:'Aspen + Co.',            contact:'R. Tanaka',      status:'nda',       amount: null,   nda:true,  visits: 2,  last:'4d ago' },
  { id:'i08', name:'C. Linde',               contact:'C. Linde',       status:'invited',   amount: null,   nda:false, visits: 1,  last:'1w ago' },
  { id:'i09', name:'Greenline Studios',      contact:'P. Ortega',      status:'invited',   amount: null,   nda:false, visits: 1,  last:'1w ago' },
  { id:'i10', name:'A. Holt (advisor)',      contact:'A. Holt',        status:'declined',  amount: null,   nda:true,  visits: 6,  last:'2w ago' },
];

const INVEST_ACTIVITY = [
  { t:'14:32:08', who:'L. Marquez',  what:'Visited portal · viewed slide 7 + 12 + 17',    proj:'EV-001', tag:'invest' },
  { t:'14:14:02', who:'M. Reyes',     what:'Wired commitment confirmation \u2014 $50,000',  proj:'EV-001', tag:'invest' },
  { t:'14:08:31', who:'A. Whitford',  what:'Downloaded Investor Brief PDF',                proj:'EV-001', tag:'invest' },
  { t:'13:50:33', who:'D. Chen',      what:'Signed NDA \u00b7 enabled portal access',      proj:'EV-001', tag:'invest' },
  { t:'13:41:18', who:'L. Patel',     what:'Visited portal \u2014 first visit',            proj:'EV-001', tag:'invest' },
  { t:'12:55:00', who:'You',          what:'Updated funding goal to $826,000',             proj:'EV-001', tag:'invest' },
  { t:'12:30:44', who:'S. Adeyemi',   what:'Signed NDA',                                   proj:'EV-001', tag:'invest' },
  { t:'11:48:09', who:'You',          what:'Published portal in LIVE mode',                proj:'EV-001', tag:'invest' },
  { t:'10:15:00', who:'You',          what:'Generated synopsis from script',               proj:'EV-001', tag:'invest' },
];

const STATUS_LABEL = {
  committed: { label:'Committed',     color:'var(--ok)',      bg:'rgba(94,211,168,0.10)' },
  review:    { label:'In Review',     color:'var(--accent)',  bg:'rgba(255,138,61,0.10)' },
  nda:       { label:'NDA Signed',    color:'var(--st-script)', bg:'rgba(106,163,255,0.08)' },
  invited:   { label:'Invited',       color:'var(--text-3)',  bg:'rgba(255,255,255,0.04)' },
  declined:  { label:'Declined',      color:'#c83a4a',        bg:'rgba(200,58,74,0.10)' },
};

/* ---------- Left: Sections nav ---------- */
const InvestSectionsPanel = ({ active, setActive }) => {
  const stats = {
    setup:    null,
    content:  null,
    pipeline: INVESTORS.length,
    nda:      INVESTORS.filter(i => i.nda).length + '/' + INVESTORS.length,
    activity: INVEST_ACTIVITY.length,
  };
  return (
    <React.Fragment>
      <div style={{ padding:'12px 14px 10px', borderBottom:'1px solid var(--line-1)', flexShrink:0 }}>
        <div style={{fontSize:9.5, letterSpacing:'.14em', textTransform:'uppercase', color:'var(--text-3)', fontFamily:'var(--font-mono)', marginBottom:4}}>Funding Goal</div>
        <div style={{ display:'flex', alignItems:'baseline', gap:6 }}>
          <span style={{ fontSize:24, fontFamily:'Georgia, serif', fontWeight:700, color:'var(--accent)' }}>$826K</span>
        </div>
        <div className="bar" style={{ height:5, background:'var(--bg-3)', borderRadius:2, overflow:'hidden', marginTop:6 }}>
          <span style={{ display:'block', width:'42%', height:'100%', background:'var(--accent)' }}/>
        </div>
        <div style={{fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-3)', marginTop:4, letterSpacing:'.06em'}}>$345K raised \u00b7 42% to goal</div>
      </div>
      <div style={{ flex:1, overflowY:'auto', padding:'6px 0' }}>
        {INVEST_SECTIONS.map(s => (
          <button key={s.id} className={`cat-row ${active===s.id?'active':''}`} onClick={()=>setActive(s.id)}>
            <span className="ic"><Icon name={s.icon} size={14}/></span>
            <span className="name">{s.name}</span>
            {stats[s.id] && <span className="ratio">{stats[s.id]}</span>}
          </button>
        ))}
      </div>
      <div style={{ padding:'10px 12px', borderTop:'1px solid var(--line-1)', flexShrink:0 }}>
        <div style={{display:'flex', alignItems:'center', gap:6, marginBottom:8}}>
          <span style={{width:8,height:8,borderRadius:'50%',background:'var(--ok)',boxShadow:'0 0 8px var(--ok-glow)'}}/>
          <span style={{fontFamily:'var(--font-mono)', fontSize:10, letterSpacing:'.14em', color:'var(--ok)'}}>PORTAL LIVE</span>
        </div>
        <button className="btn primary" style={{width:'100%'}}><Icon name="send" size={11}/> Invite Investor</button>
      </div>
    </React.Fragment>
  );
};

/* ---------- Main: Section detail ---------- */
const InvestDetail = ({ active }) => {
  const [status, setStatus] = React.useState('live');
  const [welcome, setWelcome] = React.useState("You\u2019re the first one in. That means something.\n\nMandatory Reporter is the story of Danny Walker \u2014 a widowed father, a seven-year-old boy with a dinosaur backpack, and one moment outside an elementary school that a well-meaning teacher misread. What follows isn\u2019t a villain story. It\u2019s something harder than that. A good man fighting a system that was never designed to be wrong.");
  const [synopsis, setSynopsis] = React.useState("A widowed father has 72 hours to prove he\u2019s the parent he says he is \u2014 before the system decides for him.");

  if (active === 'setup') return (
    <div className="invest-detail">
      <div className="id-section">
        <div className="id-head">
          <div className="id-h-title">Portal Status</div>
          <div className="id-h-sub">Control who sees your project and track funding commitments.</div>
        </div>

        <div className="status-switcher">
          {[
            { id:'private',  label:'Private',  icon:'\uD83D\uDD12', hint:'Only you can see it.' },
            { id:'pitching', label:'Pitching', icon:'\uD83C\uDFAF', hint:'Invited investors only.' },
            { id:'live',     label:'Live',     icon:'\u2022',       hint:'Public, anyone with the link.' },
          ].map(s => (
            <button key={s.id} className={`status-btn ${status===s.id?'on':''}`} onClick={()=>setStatus(s.id)}>
              <span className="ic">{s.icon}</span>
              <span className="lbl">{s.label}</span>
              <span className="hint">{s.hint}</span>
            </button>
          ))}
        </div>

        <div className="portal-url">
          <span className="lbl">PUBLIC URL</span>
          <code>https://evolumstudio.com/invest/mandatory-reporter</code>
          <button className="btn"><Icon name="folder" size={11}/> Copy</button>
          <button className="btn"><Icon name="undock" size={11}/> Open</button>
        </div>

        <div className="form-row two">
          <div>
            <div className="field-label">Funding Goal</div>
            <div className="field-with-prefix">
              <span className="prefix">$</span>
              <input className="field" defaultValue="826,000"/>
            </div>
          </div>
          <div>
            <div className="field-label">Deal Type</div>
            <select className="field">
              <option>Revenue Share</option>
              <option>Equity</option>
              <option>SAFE (post-money)</option>
              <option>Convertible Note</option>
            </select>
          </div>
          <div>
            <div className="field-label">Closing</div>
            <input className="field" placeholder="e.g. Jul 15" defaultValue="Aug 30, 2026"/>
          </div>
          <div>
            <div className="field-label">Minimum Check</div>
            <div className="field-with-prefix">
              <span className="prefix">$</span>
              <input className="field" defaultValue="25,000"/>
            </div>
          </div>
        </div>
      </div>

      <div className="id-section">
        <div className="id-head"><div className="id-h-title">Portal Content</div><div className="id-h-sub">Everything investors see, in the order they see it.</div></div>

        <div className="form-row">
          <div className="content-photo">
            <div className="cp-frame">
              <div className="cp-init">E</div>
            </div>
            <div>
              <div className="field-label">Your Photo</div>
              <div style={{display:'flex', gap:6, marginTop:6}}>
                <button className="btn"><Icon name="folder" size={11}/> Upload</button>
                <button className="btn"><Icon name="sparkle" size={11}/> Generate</button>
              </div>
              <div style={{fontSize:10, color:'var(--text-3)', marginTop:4, fontFamily:'var(--font-mono)', letterSpacing:'.06em'}}>JPG or PNG \u00b7 max 2 MB</div>
            </div>
          </div>
        </div>

        <div>
          <div className="field-row">
            <div className="field-label">Welcome Message</div>
            <button className="chip" style={{padding:'3px 8px'}}><Icon name="sparkle" size={11}/> Gen from Script</button>
          </div>
          <textarea className="field area" style={{minHeight:120}} value={welcome} onChange={e=>setWelcome(e.target.value)}/>
        </div>

        <div>
          <div className="field-row">
            <div className="field-label">Synopsis <span style={{color:'var(--text-3)',textTransform:'none',letterSpacing:'.04em',marginLeft:6,fontFamily:'var(--font-ui)'}}>(shown before the investor signs the NDA)</span></div>
            <button className="chip" style={{padding:'3px 8px'}}><Icon name="sparkle" size={11}/> Gen from Script</button>
          </div>
          <textarea className="field area" style={{minHeight:70}} value={synopsis} onChange={e=>setSynopsis(e.target.value)}/>
        </div>
      </div>
    </div>
  );

  if (active === 'pipeline') return (
    <div className="invest-detail">
      <div className="id-section">
        <div className="id-head">
          <div className="id-h-title">Investor Pipeline</div>
          <div className="id-h-sub">{INVESTORS.length} investors tracked \u00b7 {INVESTORS.filter(i=>i.status==='committed').length} committed.</div>
        </div>
        <div className="investor-table">
          <div className="iv-head">
            <span/>
            <span>Name</span>
            <span>Status</span>
            <span>Commitment</span>
            <span>NDA</span>
            <span>Visits</span>
            <span>Last Seen</span>
            <span/>
          </div>
          {INVESTORS.map((i, idx) => {
            const sl = STATUS_LABEL[i.status];
            return (
              <div key={i.id} className="iv-row">
                <span className="iv-n">{String(idx+1).padStart(2,'0')}</span>
                <span className="iv-name">
                  <div>{i.name}</div>
                  <div className="iv-contact">{i.contact}</div>
                </span>
                <span><span className="status-pill" style={{ color: sl.color, background: sl.bg }}><span className="d" style={{ background: sl.color }}/>{sl.label}</span></span>
                <span className="iv-amount">{i.amount ? '$' + i.amount.toLocaleString() : '—'}</span>
                <span className="iv-nda">{i.nda ? <span className="iv-check"><Icon name="check" size={10}/></span> : <span style={{color:'var(--text-3)', fontFamily:'var(--font-mono)', fontSize:10}}>—</span>}</span>
                <span className="iv-visits">{i.visits}</span>
                <span className="iv-last">{i.last}</span>
                <span className="iv-actions">
                  <button className="btn"><Icon name="send" size={10}/></button>
                  <button className="btn"><Icon name="folder" size={10}/></button>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  if (active === 'nda') return (
    <div className="invest-detail">
      <div className="id-section">
        <div className="id-head">
          <div className="id-h-title">NDA & Legal</div>
          <div className="id-h-sub">Auto-issued to every investor on portal entry. Customize once and forget.</div>
        </div>
        <div className="kv">
          <span className="k">NDA Template</span><span className="v">Standard mutual NDA · v2026.1</span>
          <span className="k">Auto-issue</span><span className="v" style={{color:'var(--ok)'}}>Enabled</span>
          <span className="k">Signers</span><span className="v">{INVESTORS.filter(i=>i.nda).length} / {INVESTORS.length}</span>
          <span className="k">Storage</span><span className="v">DocuSign · Supabase mirror</span>
        </div>
        <div style={{display:'flex', gap:6, marginTop:8}}>
          <button className="btn primary"><Icon name="folder" size={11}/> Preview NDA</button>
          <button className="btn">Edit Template</button>
          <button className="btn">Download Signed Set</button>
        </div>
      </div>
    </div>
  );

  if (active === 'activity') return (
    <div className="invest-detail" style={{padding:0}}>
      <div className="id-section" style={{borderBottom:'1px solid var(--line-1)', paddingBottom:0}}>
        <div className="id-head">
          <div className="id-h-title">Portal Activity</div>
          <div className="id-h-sub">Every page view, NDA, download, and commitment as it happens.</div>
        </div>
      </div>
      <Activity/>
    </div>
  );

  if (active === 'content') return (
    <div className="invest-detail">
      <div className="id-section">
        <div className="id-head"><div className="id-h-title">Portal Content</div><div className="id-h-sub">Same as Status panel \u2014 use that view to edit content alongside the live preview.</div></div>
        <button className="btn primary"><Icon name="chevron" size={11}/> Edit content in Status panel</button>
      </div>
    </div>
  );

  return null;
};

/* ---------- Right: Live preview ---------- */
const PortalPreview = () => {
  return (
    <div className="portal-preview">
      <div className="pp-bar">
        <span className="pp-dot pp-r"/><span className="pp-dot pp-y"/><span className="pp-dot pp-g"/>
        <span className="pp-url">evolumstudio.com/invest/mandatory-reporter</span>
      </div>
      <div className="pp-page">
        <div className="ppp-hero">
          <div className="ppp-eyebrow">A FEATURE FILM \u00b7 INVESTOR PORTAL</div>
          <div className="ppp-title">Mandatory Reporter</div>
          <div className="ppp-logline">A widowed father has 72 hours to prove he\u2019s the parent he says he is — before the system decides for him.</div>
        </div>
        <div className="ppp-block">
          <div className="ppp-photo">
            <div className="ppp-init">E</div>
          </div>
          <div className="ppp-welcome">You\u2019re the first one in. That means something. Mandatory Reporter is the story of Danny Walker — a widowed father, a seven-year-old boy with a dinosaur backpack, and one moment outside an elementary school that a well-meaning teacher misread\u2026</div>
        </div>
        <div className="ppp-stat-row">
          <div className="ppp-stat"><div className="lbl">FUNDING GOAL</div><div className="big">$826K</div></div>
          <div className="ppp-stat"><div className="lbl">RAISED</div><div className="big">$345K</div></div>
          <div className="ppp-stat"><div className="lbl">DEAL</div><div className="big" style={{fontSize:14}}>Rev Share</div></div>
        </div>
        <button className="ppp-cta">Sign NDA to Continue \u2192</button>
      </div>
    </div>
  );
};

Object.assign(window, { InvestSectionsPanel, InvestDetail, PortalPreview, INVEST_SECTIONS, INVESTORS, INVEST_ACTIVITY });
