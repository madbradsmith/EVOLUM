/* =====================================================================
   EVOLUM — Idea / Story Development room
   ===================================================================== */
const DEV_CHECKLIST = [
  { id:'shared',    label:'Idea shared',           done:true,  count:'' },
  { id:'world',     label:'World built',           done:true,  count:'' },
  { id:'worldviz',  label:'World visualized',      done:true,  count:'' },
  { id:'charsbib',  label:'Characters in Show Bible', done:true, count:'15 characters' },
  { id:'charsviz',  label:'Characters visualized', done:false, count:'14 / 15' },
  { id:'logline',   label:'Logline locked',        done:true,  count:'' },
  { id:'beats',     label:'Beat sheet built',      done:true,  count:'15 beats' },
  { id:'treat1',    label:'Treatment \u2014 Act 1', done:true,  count:'' },
  { id:'treat2',    label:'Treatment \u2014 Act 2', done:true,  count:'' },
  { id:'treat3',    label:'Treatment \u2014 Act 3', done:true,  count:'' },
  { id:'bible',     label:'Show Bible synced',     done:true,  count:'' },
];

const IDEA_CHARACTERS = [
  { id:'danny',   n:1, name:'DANNY',          tag:'PROTAGONIST', desc:'38, widowed father. A man who has rebuilt himself once already.' },
  { id:'ethan',   n:2, name:'ETHAN',          tag:'SUPPORTING',  desc:'8, quiet, watchful, the reason for everything.' },
  { id:'tony',    n:3, name:'TONY',           tag:'SUPPORTING',  desc:'Danny\u2019s brother. The kind of man who shows up.' },
  { id:'angela',  n:4, name:'ANGELA BROOKS',  tag:'SUPPORTING',  desc:'Caseworker. Believes in procedure because she has to.' },
  { id:'rebecca', n:5, name:'REBECCA KELLER', tag:'SUPPORTING',  desc:'Teacher. Knows she made a mistake. Won\u2019t look away.' },
  { id:'judge',   n:6, name:'JUDGE WHITAKER', tag:'SUPPORTING',  desc:'Family court. Tired of being lied to.' },
  { id:'davis',   n:7, name:'COUNSELOR DAVIS',tag:'BIT',         desc:'Court-appointed for Ethan. Two-line scene that lands hard.' },
];

const IDEA_MSGS_INIT = [
  { who:'hitch', t:'2:30p', text:"Hey! How\u2019s the pitch deck looking?" },
  { who:'you',   t:'2:31p', text:"I guess the only way to talk to you is on dictation" },
  { who:'hitch', t:'2:31p', text:"Ha \u2014 no, you can type too. Dictation just happens to be how you roll. Either way works for me. What are we doing \u2014 reviewing the deck or building something else?" },
  { who:'you',   t:'2:33p', text:"I want to break Act II open. The middle is too quiet." },
  { who:'hitch', t:'2:33p', text:"Yeah. We have 6 scenes between Catalyst and Midpoint and 4 of them are Danny + Rebecca in courthouses. The system feels small. Want me to draft three scene possibilities that move us into the world \u2014 Tony\u2019s shop, Ethan\u2019s school, the caseworker\u2019s POV?" },
];

/* ---------- Center: Hitchcock chat ---------- */
const IdeaChat = ({ msgs, setMsgs }) => {
  const [val, setVal] = React.useState('');
  const scrollRef = React.useRef(null);
  React.useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [msgs]);
  const send = () => {
    if (!val.trim()) return;
    setMsgs(m => [...m, { who:'you', t: new Date().toTimeString().slice(0,5), text: val }]);
    const q = val; setVal('');
    setTimeout(() => {
      setMsgs(m => [...m, { who:'hitch', t: new Date().toTimeString().slice(0,5), text: `Working on \u201C${q}\u201D. Give me a beat \u2014 I\u2019ll come back with options that map to the beat sheet.` }]);
    }, 700);
  };
  return (
    <div className="idea-chat">
      <div className="ic-head">
        <div>
          <div className="ic-title">Story Development</div>
          <div className="ic-sub">Develop your concept with Hitchcock. Talk freely \u2014 the Elements panel builds as you go.</div>
        </div>
        <div className="ic-room">
          <span className="d"/>
          <span>1 person here</span>
        </div>
      </div>

      <div className="ic-stream" ref={scrollRef}>
        {msgs.map((m, i) => (
          <div key={i} className={`ic-msg ${m.who==='you'?'you':'hitch'}`}>
            <div className="ic-who">
              <span className="avt">{m.who==='you'?'You':'Hitchcock'}</span>
              <span className="t">{m.t}</span>
            </div>
            <div className="ic-body">{m.text}</div>
            {m.who==='hitch' && (
              <div className="ic-actions">
                <button title="Replay as voice"><Icon name="sizzle" size={11}/></button>
                <button title="Copy"><Icon name="folder" size={11}/></button>
                <button title="Bookmark"><Icon name="star" size={11}/></button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="ic-input-row">
        <div className="ic-quick">
          <button className="chip"><Icon name="sparkle" size={11}/> Generate Loglines</button>
          <button className="chip"><Icon name="sparkle" size={11}/> Generate Treatment</button>
          <button className="chip"><Icon name="folder" size={11}/> Sync Bible \u2192</button>
        </div>
        <div className="ic-input">
          <input value={val} onChange={e=>setVal(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter') send(); }} placeholder="Tell me your idea, or respond to the question above\u2026"/>
          <button title="Attach"><Icon name="folder" size={13}/></button>
          <button title="Voice"><Icon name="sizzle" size={13}/></button>
          <button className="send" onClick={send}>Send</button>
        </div>
        <div className="ic-foot">EVOLUM \u2014 POWERED BY DEVELOPUM AI ENGINE \u00b7 INTEGRITY STATEMENT</div>
      </div>
    </div>
  );
};

/* ---------- Right top: Development progress ring + checklist ---------- */
const DevPanel = () => {
  const done = DEV_CHECKLIST.filter(c => c.done).length;
  const pct = Math.round((done / DEV_CHECKLIST.length) * 100);
  const C = 2 * Math.PI * 24; // radius 24
  const offset = C * (1 - pct / 100);
  return (
    <div className="dev-panel">
      <div className="dev-head">
        <div className="dev-ring">
          <svg width="64" height="64" viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="24" fill="none" stroke="var(--bg-3)" strokeWidth="6"/>
            <circle cx="32" cy="32" r="24" fill="none" stroke="var(--accent)" strokeWidth="6" strokeDasharray={C} strokeDashoffset={offset} strokeLinecap="round" transform="rotate(-90 32 32)"/>
          </svg>
          <span className="dev-pct">{pct}%</span>
        </div>
        <div>
          <div className="dev-tag">DEVELOPMENT</div>
          <div className="dev-state"><Icon name="star" size={12}/> {pct >= 100 ? 'Complete' : 'In progress'}</div>
        </div>
      </div>
      <div className="dev-list">
        {DEV_CHECKLIST.map(c => (
          <div key={c.id} className={`dev-row ${c.done?'done':''}`}>
            <span className="dev-check">{c.done ? <Icon name="check" size={11}/> : null}</span>
            <span className="dev-label">{c.label}</span>
            {c.count && <span className="dev-count">{c.count}</span>}
          </div>
        ))}
      </div>
    </div>
  );
};

/* ---------- Right bottom: Elements (characters/script/files) ---------- */
const ElementsPanel = () => {
  const [tab, setTab] = React.useState('characters');
  return (
    <React.Fragment>
      <div className="tabs">
        <button className={tab==='characters'?'on':''} onClick={()=>setTab('characters')}>ELEMENTS</button>
        <button className={tab==='script'?'on':''} onClick={()=>setTab('script')}>SCRIPT</button>
        <button className={tab==='files'?'on':''} onClick={()=>setTab('files')}>FILES</button>
      </div>
      {tab==='characters' && (
        <div className="elements-list">
          <div className="el-section">CHARACTERS</div>
          {IDEA_CHARACTERS.map(c => (
            <div key={c.id} className={`el-row ${c.tag==='PROTAGONIST'?'lead':''}`}>
              <span className="el-n">#{c.n}</span>
              <div className="el-body">
                <div className="el-name">{c.name}</div>
                <div className="el-desc">{c.desc}</div>
              </div>
              <span className={`el-tag tag-${c.tag.toLowerCase()}`}>{c.tag}</span>
            </div>
          ))}
          <button className="btn" style={{ margin:'10px 12px', width:'calc(100% - 24px)'}}><Icon name="plus" size={11}/> Add Character</button>
        </div>
      )}
      {tab==='script' && (
        <div className="elements-list">
          <div className="el-section">PAGES / SCENES</div>
          {[
            { n:'p. 1-7',   label:'Opening Sequence', done:true },
            { n:'p. 8-22',  label:'Setup',            done:true },
            { n:'p. 23-30', label:'Catalyst',         done:true },
            { n:'p. 31-58', label:'Act II',           done:false },
            { n:'p. 59-90', label:'Bad Guys Close In',done:false },
            { n:'p. 91-114',label:'Climax & Resolution', done:false },
          ].map((s,i) => (
            <div key={i} className="el-row">
              <span className="el-n" style={{fontSize:9.5, color:'var(--accent)'}}>{s.n}</span>
              <div className="el-body"><div className="el-name">{s.label}</div></div>
              {s.done ? <span className="el-tag tag-supporting" style={{color:'var(--ok)'}}>LOCKED</span> : <span className="el-tag" style={{color:'var(--text-3)'}}>DRAFT</span>}
            </div>
          ))}
        </div>
      )}
      {tab==='files' && (
        <div className="elements-list">
          <div className="el-section">PROJECT FILES</div>
          {['MR_treatment_v8.pdf','MR_bible_v3.pdf','character_arcs.md','tone_refs.zip','locations.kml'].map(f => (
            <div key={f} className="el-row" style={{gridTemplateColumns:'auto 1fr auto'}}>
              <span className="ic" style={{color:'var(--text-3)'}}><Icon name="folder" size={12}/></span>
              <div className="el-body"><div className="el-name" style={{fontFamily:'var(--font-mono)', fontSize:11}}>{f}</div></div>
              <span style={{color:'var(--text-3)', fontFamily:'var(--font-mono)', fontSize:10}}>{Math.floor(Math.random()*400+10)}kb</span>
            </div>
          ))}
        </div>
      )}
    </React.Fragment>
  );
};

Object.assign(window, { IdeaChat, DevPanel, ElementsPanel, DEV_CHECKLIST, IDEA_CHARACTERS, IDEA_MSGS_INIT });
