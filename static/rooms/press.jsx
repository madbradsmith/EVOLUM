/* =====================================================================
   EVOLUM — Press / Outreach room
   ===================================================================== */
const PRESS_SECTIONS = [
  { id:'social',  name:'Social Generator', icon:'sparkle' },
  { id:'public',  name:'Public Page',      icon:'undock' },
  { id:'press',   name:'Press List',       icon:'send' },
  { id:'queue',   name:'Buffer Queue',     icon:'clock' },
];

const PLATFORMS = [
  { id:'linkedin', name:'LinkedIn',           limit:3000, icon:'\uD83C\uDD41', tone:'professional' },
  { id:'twitter',  name:'X (Twitter)',        limit:280,  icon:'\u2715',       tone:'concise' },
  { id:'instagram',name:'Instagram caption',  limit:2200, icon:'\u25CE',       tone:'cinematic' },
  { id:'tiktok',   name:'TikTok / Reels hook',limit:150,  icon:'\u25B6',       tone:'punchy' },
  { id:'youtube',  name:'YouTube Short script',limit:600, icon:'\u25BA',       tone:'narrative' },
];

const ANGLES = [
  { id:'cherry',  name:'Cherry Breaker', desc:'Big news to plant a flag. Lead with the most undeniable thing about the project.' },
  { id:'milestone',name:'Milestone',     desc:'A specific win \u2014 cast, financing, festival, locked draft.' },
  { id:'bts',     name:'Behind Scenes',  desc:'Production photo or detail. Authentic and process-forward.' },
  { id:'casting', name:'Casting Open',   desc:'Call for actors with role notes. Filters at the bottom.' },
  { id:'personal',name:'Personal Story', desc:'The why. Director POV. The one-line motivation, told plainly.' },
  { id:'investor',name:'Investor Signal',desc:'Smart, restrained. Hints at traction without overselling.' },
];

const SAMPLE_POSTS = {
  linkedin: {
    cherry:   `MANDATORY REPORTER \u2014 a feature film I\u2019ve been writing for two years \u2014 just locked its production budget.\n\nIt\u2019s the story of a widowed father who has 72 hours to prove he\u2019s the parent he says he is, before the system decides for him. A good man fighting a system that was never designed to be wrong.\n\nWe\u2019re raising $826K. Four investors in. Eight more conversations open.\n\nIf you\u2019ve ever sat in a fluorescent-lit waiting room waiting for someone to tell you the obvious thing about your own life \u2014 you already know this story.\n\nDM if you want the deck.`,
    milestone:`Mandatory Reporter just crossed 42% of our raise. Halfway home.\n\nNext milestone: lead casting closed by end of month. Three offers out. One in second position.\n\nThank you to the investors already in. You\u2019re not just funding a movie \u2014 you\u2019re funding the first film I\u2019ll be proud to put my name on.\n\nMore soon.`,
    bts:      `Day 14 of pre-production on Mandatory Reporter.\n\nMy DP and I spent three hours yesterday in a real family-court hallway with a tape measure and a light meter. The architecture of these places does most of the work for you \u2014 narrow, fluorescent, full of people pretending to read magazines.\n\nWe shoot in 47 days.`,
  },
  twitter: {
    cherry:   `MANDATORY REPORTER \u2014 my next feature \u2014 just locked its $826K budget. A widowed father has 72 hours to prove he\u2019s the parent he says he is. DM for deck.`,
    milestone:`MANDATORY REPORTER is 42% funded. Lead casting closes this month. Three offers out.`,
    bts:      `Spent the morning in a real family-court hallway with a tape measure. Some buildings do the directing for you. \u2014 mandatory reporter, day 14 pre.`,
    casting:  `OPEN CALL \u2014 MANDATORY REPORTER \u00b7 Feature. DANNY (38) lead, widowed father. SAG modified low. Self-tapes by May 31. Link in bio.`,
    personal: `I started writing MANDATORY REPORTER the week a stranger misread my own kid\u2019s bruise from a soccer practice. It\u2019s not autobiographical. It\u2019s adjacent. Sometimes that\u2019s harder.`,
    investor: `Four investors in on MANDATORY REPORTER. $345K committed against an $826K raise. Three more in second position. Quietly building.`,
  },
  instagram: {
    cherry:   `MANDATORY REPORTER \u00b7 a feature\n\nA widowed father has 72 hours to prove he\u2019s the parent he says he is \u2014 before the system decides for him.\n\nWe\u2019re raising $826K. Four investors in. The full deck is at the link in bio.\n\n\u2014\n\n#independentfilm #filmfinancing #screenwriter`,
  },
  tiktok: {
    cherry:   `Hook: \u201CA teacher misread a bruise.\u201D\n\nText overlay: \u201CWhat happened next nearly destroyed a family.\u201D\n\nMy next film, MANDATORY REPORTER, is about a system that means well \u2014 and the people it consumes anyway. Link in bio.`,
    bts:      `Hook: \u201CHere\u2019s the courthouse hallway I\u2019m shooting in.\u201D\n\nPan camera. Show the bench, the magazines, the fluorescent flicker.\n\n\u201CSometimes the location IS the antagonist.\u201D\n\nMANDATORY REPORTER \u2014 47 days from now.`,
  },
  youtube: {
    cherry:   `[0:00] FATHER, mid-30s, holds a folded photo of his son.\n\nVO: \u201CA teacher misread a bruise. That\u2019s how it starts.\n\n[0:08] Cut to fluorescent-lit court hallway. Empty seats.\n\nVO: \u201CA week later, my son and I were strangers in a system that meant well.\n\n[0:18] Title card \u2014 MANDATORY REPORTER. Logline. CTA.`,
  },
};

const BUFFER_QUEUE = [
  { id:'b1', when:'Today \u00b7 3:00p', platform:'twitter', angle:'milestone', text:'MANDATORY REPORTER is 42% funded. Lead casting closes this month. Three offers out.', state:'scheduled' },
  { id:'b2', when:'Today \u00b7 6:00p', platform:'linkedin', angle:'bts',     text:'Day 14 of pre-production on Mandatory Reporter\u2026', state:'scheduled' },
  { id:'b3', when:'Tomorrow \u00b7 9:00a', platform:'instagram', angle:'cherry', text:'MANDATORY REPORTER \u00b7 a feature\u2026', state:'queued' },
  { id:'b4', when:'Tomorrow \u00b7 12:00p', platform:'tiktok', angle:'bts',   text:'Here\u2019s the courthouse hallway I\u2019m shooting in\u2026', state:'queued' },
  { id:'b5', when:'Today \u00b7 11:14a', platform:'twitter', angle:'investor', text:'Four investors in on MANDATORY REPORTER\u2026', state:'posted', engagement:'128 likes \u00b7 14 reposts' },
  { id:'b6', when:'Yesterday \u00b7 8:30a', platform:'linkedin', angle:'personal', text:'I started writing MANDATORY REPORTER the week\u2026', state:'posted', engagement:'62 likes \u00b7 8 comments' },
];

/* ---------- Left: Sections nav ---------- */
const PressSectionsPanel = ({ active, setActive }) => {
  return (
    <React.Fragment>
      <div style={{ padding:'12px 14px 10px', borderBottom:'1px solid var(--line-1)', flexShrink:0 }}>
        <div style={{fontSize:9.5, letterSpacing:'.14em', textTransform:'uppercase', color:'var(--text-3)', fontFamily:'var(--font-mono)', marginBottom:4}}>This Week</div>
        <div style={{display:'flex', alignItems:'baseline', gap:6}}>
          <span style={{fontSize:24, fontFamily:'Georgia, serif', fontWeight:700, color:'var(--accent)'}}>14</span>
          <span style={{fontSize:11.5, color:'var(--text-3)', fontFamily:'var(--font-mono)'}}>posts queued</span>
        </div>
        <div style={{fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-3)', marginTop:4, letterSpacing:'.06em'}}>4 today \u00b7 6 tomorrow \u00b7 4 later</div>
      </div>
      <div style={{flex:1, overflowY:'auto', padding:'6px 0'}}>
        {PRESS_SECTIONS.map(s => (
          <button key={s.id} className={`cat-row ${active===s.id?'active':''}`} onClick={()=>setActive(s.id)}>
            <span className="ic"><Icon name={s.icon} size={14}/></span>
            <span className="name">{s.name}</span>
            {s.id === 'queue' && <span className="ratio">{BUFFER_QUEUE.filter(b=>b.state!=='posted').length}</span>}
          </button>
        ))}
      </div>
      <div style={{ padding:'10px 12px', borderTop:'1px solid var(--line-1)', flexShrink:0 }}>
        <div style={{display:'flex', alignItems:'center', gap:6, marginBottom:8}}>
          <span style={{width:8,height:8,borderRadius:'50%',background:'var(--ok)',boxShadow:'0 0 8px var(--ok-glow)'}}/>
          <span style={{fontFamily:'var(--font-mono)', fontSize:10, letterSpacing:'.14em', color:'var(--ok)'}}>BUFFER CONNECTED</span>
        </div>
        <button className="btn primary" style={{width:'100%'}}><Icon name="send" size={11}/> Generate Batch (10)</button>
      </div>
    </React.Fragment>
  );
};

/* ---------- Main: Active section ---------- */
const PressDetail = ({ active, plat, setPlat, angle, setAngle, mention, setMention, post, generate, generating }) => {
  if (active === 'social') return (
    <div className="invest-detail">
      <div className="id-section">
        <div className="id-head">
          <div className="id-h-title">Social Generator</div>
          <div className="id-h-sub">Pick a platform and an angle. Hitchcock writes the post in your voice using the project bible.</div>
        </div>

        <div>
          <div className="field-label">Platform</div>
          <div className="press-grid">
            {PLATFORMS.map(p => (
              <button key={p.id} className={`press-tile ${plat===p.id?'on':''}`} onClick={()=>setPlat(p.id)}>
                <span className="pt-icon">{p.icon}</span>
                <div>
                  <div className="pt-name">{p.name}</div>
                  <div className="pt-limit">{p.limit} chars</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="field-label">Angle</div>
          <div className="press-grid">
            {ANGLES.map(a => (
              <button key={a.id} className={`press-tile angle-tile ${angle===a.id?'on':''}`} onClick={()=>setAngle(a.id)}>
                <div>
                  <div className="pt-name">{a.name}</div>
                  <div className="pt-desc">{a.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="field-label">Anything specific to mention? <span style={{color:'var(--text-3)',textTransform:'none',letterSpacing:'.02em',fontFamily:'var(--font-ui)'}}>(optional)</span></div>
          <textarea className="field area" placeholder="A specific number, a moment, a name \u2014 anything the generator wouldn\u2019t otherwise know." value={mention} onChange={e=>setMention(e.target.value)}/>
        </div>

        <div style={{display:'flex', gap:8}}>
          <button className="btn primary" style={{flex:1}} onClick={generate} disabled={generating}>
            <Icon name="sparkle" size={11}/> {generating ? 'Generating\u2026' : 'Generate Post'}
          </button>
          <button className="btn"><Icon name="folder" size={11}/> History</button>
        </div>
      </div>
    </div>
  );

  if (active === 'public') return (
    <div className="invest-detail">
      <div className="id-section">
        <div className="id-head">
          <div className="id-h-title">Public Page</div>
          <div className="id-h-sub">Publish a public-facing page anyone can visit \u2014 no login required. Visitors can support with one click or sign up free to see the full pitch.</div>
        </div>

        <div>
          <div className="field-label">Vanity URL</div>
          <div className="vanity-row">
            <span className="vanity-prefix">evolumstudio.com/film/</span>
            <input className="field" defaultValue="mandatory-reporter"/>
            <button className="btn"><Icon name="sparkle" size={11}/> Suggest</button>
          </div>
          <div style={{ fontSize:10.5, color:'var(--text-3)', marginTop:4 }}>Lowercase, dashes, no spaces. Must be unique across all projects.</div>
        </div>

        <div>
          <div className="field-label">Public Blurb</div>
          <textarea className="field area" style={{minHeight:90}} defaultValue="What you want the public to know. Keep it short and cinematic \u2014 this sits under the logline. A widowed father, a seven-year-old boy with a dinosaur backpack, and one moment outside an elementary school that a well-meaning teacher misread."/>
        </div>

        <div>
          <div className="field-label">Supporter Stripe Link</div>
          <input className="field" defaultValue="https://buy.stripe.com/14k6oybVa1nQ7Nm5kk"/>
          <div style={{ fontSize:10.5, color:'var(--text-3)', marginTop:4 }}>One-click donate / support. Visitors get sent directly here \u2014 no signup, no friction.</div>
        </div>

        <div className="form-row two">
          <div>
            <div className="field-label">Press Email</div>
            <input className="field" defaultValue="press@evolumstudio.com"/>
          </div>
          <div>
            <div className="field-label">Casting Link</div>
            <input className="field" defaultValue="https://evolumstudio.com/casting/mandatory-reporter"/>
          </div>
        </div>

        <div style={{display:'flex', alignItems:'center', gap:10}}>
          <label className="toggle">
            <input type="checkbox" defaultChecked/>
            <span className="toggle-slider"/>
          </label>
          <span style={{fontSize:12, color:'var(--text-1)'}}>Public page is live</span>
          <span style={{marginLeft:'auto', fontFamily:'var(--font-mono)', fontSize:10, color:'var(--ok)', letterSpacing:'.14em'}}>1,432 visits this week</span>
        </div>

        <div style={{display:'flex', gap:6}}>
          <button className="btn primary"><Icon name="check" size={11}/> Save</button>
          <button className="btn"><Icon name="undock" size={11}/> Preview</button>
        </div>
      </div>
    </div>
  );

  if (active === 'press') return (
    <div className="invest-detail">
      <div className="id-section">
        <div className="id-head">
          <div className="id-h-title">Press List</div>
          <div className="id-h-sub">Outlets, contacts, and personalized pitches \u2014 sent on a schedule.</div>
        </div>
        <div className="investor-table">
          <div className="iv-head">
            <span/>
            <span>Outlet</span>
            <span>Contact</span>
            <span>Status</span>
            <span>Angle</span>
            <span>Last</span>
            <span/>
          </div>
          {[
            { n:1, outlet:'Variety',                 contact:'A. Vaughn',  status:'sent',    angle:'Cherry Breaker', last:'today 12:14p' },
            { n:2, outlet:'IndieWire',               contact:'M. Donelly', status:'opened',  angle:'Personal Story',  last:'today 11:08a' },
            { n:3, outlet:'Filmmaker Magazine',      contact:'L. Park',    status:'replied', angle:'Behind Scenes',  last:'yesterday' },
            { n:4, outlet:'Deadline',                contact:'C. Wong',    status:'queued',  angle:'Cherry Breaker', last:'\u2014' },
            { n:5, outlet:'Hollywood Reporter',      contact:'S. Levin',   status:'queued',  angle:'Investor Signal', last:'\u2014' },
            { n:6, outlet:'No Film School',          contact:'J. Lo',      status:'sent',    angle:'Behind Scenes',  last:'2d ago' },
            { n:7, outlet:'Sundance Institute blog', contact:'K. Brooks',  status:'replied', angle:'Personal Story',  last:'3d ago' },
          ].map(p => {
            const colors = { sent:'var(--st-script)', opened:'var(--accent)', replied:'var(--ok)', queued:'var(--text-3)' };
            return (
              <div key={p.n} className="iv-row" style={{ gridTemplateColumns:'32px 1.4fr 1fr 0.9fr 1fr 0.9fr 60px' }}>
                <span className="iv-n">{String(p.n).padStart(2,'0')}</span>
                <span className="iv-name"><div>{p.outlet}</div></span>
                <span className="iv-contact">{p.contact}</span>
                <span><span className="status-pill" style={{ color: colors[p.status], background:'rgba(255,255,255,0.04)' }}><span className="d" style={{ background: colors[p.status] }}/>{p.status.toUpperCase()}</span></span>
                <span style={{fontSize:11, color:'var(--text-2)'}}>{p.angle}</span>
                <span className="iv-last">{p.last}</span>
                <span className="iv-actions"><button className="btn"><Icon name="send" size={10}/></button></span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  if (active === 'queue') return (
    <div className="invest-detail">
      <div className="id-section">
        <div className="id-head">
          <div className="id-h-title">Buffer Queue</div>
          <div className="id-h-sub">{BUFFER_QUEUE.filter(b=>b.state!=='posted').length} scheduled \u00b7 {BUFFER_QUEUE.filter(b=>b.state==='posted').length} posted this week. Connected via Buffer.</div>
        </div>
        <div className="buffer-list">
          {BUFFER_QUEUE.map(b => (
            <div key={b.id} className={`buf-row buf-${b.state}`}>
              <div className="buf-when">
                <div className="buf-time">{b.when}</div>
                <div className="buf-platform">{PLATFORMS.find(p=>p.id===b.platform)?.name || b.platform}</div>
              </div>
              <div className="buf-text">
                <div className="buf-angle">{ANGLES.find(a=>a.id===b.angle)?.name || b.angle}</div>
                <div className="buf-body">{b.text}</div>
                {b.engagement && <div className="buf-engagement">{b.engagement}</div>}
              </div>
              <div className="buf-state">
                <span className={`status-pill buf-pill-${b.state}`}><span className="d"/>{b.state.toUpperCase()}</span>
                <div className="buf-actions">
                  <button title="Edit"><Icon name="script" size={10}/></button>
                  <button title="Reschedule"><Icon name="clock" size={10}/></button>
                  <button title="Delete"><Icon name="close" size={10}/></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  return null;
};

/* ---------- Right: Post / Page preview ---------- */
const PressPreview = ({ active, plat, angle, post, generating, mention }) => {
  if (active === 'public') {
    return (
      <div className="portal-preview">
        <div className="pp-bar">
          <span className="pp-dot pp-r"/><span className="pp-dot pp-y"/><span className="pp-dot pp-g"/>
          <span className="pp-url">evolumstudio.com/film/mandatory-reporter</span>
        </div>
        <div className="pp-page">
          <div className="ppp-hero">
            <div className="ppp-eyebrow">A FEATURE FILM \u00b7 IN DEVELOPMENT</div>
            <div className="ppp-title">Mandatory Reporter</div>
            <div className="ppp-logline">A widowed father has 72 hours to prove he\u2019s the parent he says he is — before the system decides for him.</div>
          </div>
          <div className="ppp-block">
            <div className="ppp-photo"><div className="ppp-init">E</div></div>
            <div className="ppp-welcome">A widowed father, a seven-year-old boy with a dinosaur backpack, and one moment outside an elementary school that a well-meaning teacher misread.</div>
          </div>
          <div style={{display:'flex', gap:8}}>
            <button className="ppp-cta" style={{flex:1}}>Support \u2192</button>
            <button className="ppp-cta" style={{flex:1, background:'transparent', color:'#1c1a14', border:'1px solid #1c1a14'}}>Watch Sizzle</button>
          </div>
        </div>
      </div>
    );
  }

  const p = PLATFORMS.find(x => x.id === plat) || PLATFORMS[0];
  const a = ANGLES.find(x => x.id === angle) || ANGLES[0];
  return (
    <div className="post-preview">
      <div className="ppv-head">
        <div className="ppv-platform">{p.icon} {p.name}</div>
        <div className="ppv-angle">{a.name}</div>
      </div>
      <div className="ppv-stage">
        {generating ? (
          <div className="ppv-loading">
            <div className="poster-loading-bar"><span/></div>
            <div>WRITING\u2026</div>
          </div>
        ) : post ? (
          <div className={`ppv-card ppv-${plat}`}>
            <div className="ppv-card-head">
              <div className="ppv-avt">E</div>
              <div>
                <div className="ppv-handle">Evolum Studio</div>
                <div className="ppv-meta">@evolumstudio \u00b7 now</div>
              </div>
            </div>
            <div className="ppv-body">{post}</div>
            <div className="ppv-card-foot">
              <span>\u2661 0</span>
              <span>\u21BB 0</span>
              <span>\uD83D\uDCAC 0</span>
            </div>
          </div>
        ) : (
          <div className="ppv-empty">
            <div>Pick a platform + angle on the left and hit Generate.</div>
            <div style={{ color:'var(--text-3)', fontSize:11, marginTop:6 }}>Your latest post will appear here.</div>
          </div>
        )}
      </div>
      {post && !generating && (
        <div className="ppv-foot">
          <div className="ppv-foot-meta">{post.length} chars \u00b7 limit {p.limit}</div>
          <div className="ppv-foot-actions">
            <button className="btn"><Icon name="folder" size={11}/> Copy</button>
            <button className="btn"><Icon name="sparkle" size={11}/> Variants</button>
            <button className="btn primary"><Icon name="clock" size={11}/> Queue in Buffer</button>
          </div>
        </div>
      )}
    </div>
  );
};

Object.assign(window, { PressSectionsPanel, PressDetail, PressPreview, PRESS_SECTIONS, PLATFORMS, ANGLES, SAMPLE_POSTS, BUFFER_QUEUE });
