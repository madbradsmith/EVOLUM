/* =====================================================================
   EVOLUM — Script room (Hitchcock + Beat Sheet + Editor)
   ===================================================================== */
const { useState: uS, useEffect: uE, useRef: uR, useMemo: uM, useCallback: uC } = React;

/* ---------- SCRIPT DATA ---------- */

const BEATS = [
  { act: 'ACT I', items: [
    { id:'b1',  name:'Opening Image',     done:true,  desc:'Danny loads a drowsy Ethan into a worn pickup truck in the blue-gray quiet of dawn.', scenes:[1,2,3] },
    { id:'b2',  name:'Theme Stated',      done:true,  desc:'In the school parking lot, Rebecca Keller watches Danny deliver two sharp swats…', scenes:[9,10,11,12,13] },
    { id:'b3',  name:'Setup',             done:true,  desc:"We see Danny's world in full: the practiced dinner routine, the homework…", scenes:[4,6,7] },
    { id:'b4',  name:'Catalyst',          done:false, desc:'The visit from the social worker arrives without warning.', scenes:[14,15] },
    { id:'b5',  name:'Debate',            done:false, desc:'Danny weighs whether to fight the report or cooperate.', scenes:[16,17,18] },
    { id:'b6',  name:'Break Into Two',    done:false, desc:'He hires a lawyer he cannot afford.', scenes:[19] },
  ]},
  { act: 'ACT II', items: [
    { id:'b7',  name:'B Story',           done:false, desc:'Rebecca becomes an unlikely ally.', scenes:[20,21] },
    { id:'b8',  name:'Fun & Games',       done:false, desc:'The promise of the premise: a single father fighting the system.', scenes:[22,23,24,25] },
    { id:'b9',  name:'Midpoint',          done:false, desc:'A win that turns out to be a setup.', scenes:[26] },
    { id:'b10', name:'Bad Guys Close In', done:false, desc:'CPS escalates. Ethan is removed.', scenes:[27,28,29] },
    { id:'b11', name:'All Is Lost',       done:false, desc:'Danny loses custody at the preliminary hearing.', scenes:[30] },
    { id:'b12', name:'Dark Night',        done:false, desc:'He drinks for the first time in eight years.', scenes:[31,32] },
  ]},
  { act: 'ACT III', items: [
    { id:'b13', name:'Break Into Three',  done:false, desc:'Rebecca finds the missing report.', scenes:[33] },
    { id:'b14', name:'Finale',            done:false, desc:'Hearing day. Danny tells the truth in his own words.', scenes:[34,35,36] },
    { id:'b15', name:'Final Image',       done:false, desc:'Father and son in the truck again. New light.', scenes:[37] },
  ]},
];

const SCENES = [
  { n:1,  slug:'EXT. WALKER HOUSE - DAWN',          beat:'b1' },
  { n:2,  slug:'EXT. COUNTY COURTHOUSE - MORNING', beat:'b1', active:true },
  { n:3,  slug:'INT. PICKUP TRUCK - MORNING',       beat:'b1' },
  { n:4,  slug:'INT. WALKER HOUSE - KITCHEN - NIGHT', beat:'b3' },
  { n:5,  slug:'INT. ETHAN\'S BEDROOM - NIGHT',     beat:'b3' },
  { n:6,  slug:'INT. WALKER HOUSE - LIVING ROOM - NIGHT', beat:'b3' },
  { n:7,  slug:'EXT. WALKER HOUSE - MORNING',       beat:'b3' },
  { n:8,  slug:'INT. SCHOOL HALLWAY - DAY',         beat:'b2' },
  { n:9,  slug:'EXT. SCHOOL PARKING LOT - DAY',     beat:'b2' },
  { n:10, slug:'INT. CLASSROOM - DAY',              beat:'b2' },
];

/* The full script page being viewed */
const SCRIPT_PAGE = [
  { kind:'scene',     text:'EXT. COUNTY COURTHOUSE - MORNING' },
  { kind:'action',    text:'The flag at the top of the pole barely moves.' },
  { kind:'action',    text:'DANNY WALKER (38) crosses the plaza alone. Work boots. Clean shirt. A man who dressed carefully this morning because it was the only thing he could control.' },
  { kind:'action',    text:'He reaches the steps. Looks up at the building.' },
  { kind:'action',    text:'Then he climbs.' },
  { kind:'scene',     text:'INT. COUNTY COURTHOUSE - LOBBY - CONTINUOUS' },
  { kind:'action',    text:'Echoes. Footsteps. The cathedral hush of marble and bureaucracy.' },
  { kind:'action',    text:'Danny passes through the metal detector. Removes his belt. Puts it back on. Routine he did not expect to learn.' },
  { kind:'action',    text:'REBECCA KELLER (40s, sharp coat, sharper eyes) is already waiting at the elevators. She doesn\u2019t wave. She just nods.' },
  { kind:'char',      text:'REBECCA' },
  { kind:'paren',     text:'(quiet)' },
  { kind:'dialogue',  text:'You sleep?' },
  { kind:'char',      text:'DANNY' },
  { kind:'dialogue',  text:'A little.' },
  { kind:'char',      text:'REBECCA' },
  { kind:'dialogue',  text:'Liar.' },
  { kind:'action',    text:'The elevator opens. They get on.' },
  { kind:'transition',text:'CUT TO:' },
  { kind:'scene',     text:'INT. FAMILY COURT - HALLWAY - LATER' },
  { kind:'action',    text:'A row of plastic chairs. Other parents. Other lawyers. Other children whose lives are about to be sorted.' },
  { kind:'action',    text:'Danny sits. Pulls a folded photo from his wallet. Ethan, age six, in a Halloween cape that is mostly bedsheet.' },
  { kind:'action',    text:'He stares at it the way a sailor stares at a chart of unfamiliar waters.' },
];

const CHARACTERS = [
  { id:'nova',  name:'Nova',  lines: 142, color:'#5ed3a8' },
  { id:'sage',  name:'Sage',  lines: 88,  color:'#b189ff' },
  { id:'river', name:'River', lines: 56,  color:'#6aa3ff' },
  { id:'atlas', name:'Atlas', lines: 32,  color:'#f06292' },
  { id:'cole',  name:'Cole',  lines: 24,  color:'#ff8a3d', active:true },
];

const HITCHCOCK_MSGS = [
  { who:'hitch', text:"Looks like you're on \u201COpening Image\u201D. We're in the script now. 15 beats mapped \u2014 want to start from the top or jump to a specific beat?" },
  { who:'you',   text:"Tighten the courthouse arrival. Less internal, more visible." },
  { who:'hitch', text:"Suggest cutting the wallet beat \u2014 we already feel his isolation. Replace with a stranger glance: a clerk who looks twice, then looks away. Want me to draft it?" },
];

/* ---------- LEFT PANEL — Beat Sheet ---------- */
const BeatSheet = ({ activeBeat, setActiveBeat, activeScene, setActiveScene }) => {
  const [tab, setTab] = uS('beats');
  return (
    <React.Fragment>
      <div className="tabs">
        <button className={tab==='beats'?'on':''} onClick={()=>setTab('beats')}>BEATS</button>
        <button className={tab==='scenes'?'on':''} onClick={()=>setTab('scenes')}>SCENES</button>
        <button className={tab==='outline'?'on':''} onClick={()=>setTab('outline')}>OUTLINE</button>
      </div>
      <div style={{ flex:1, overflowY:'auto', padding: '6px 0' }}>
        {tab==='beats' && (
          <div className="beat-sheet">
            {BEATS.map(group => (
              <div key={group.act} className="beat-act">
                <div className="ba-head">{group.act}</div>
                {group.items.map(b => (
                  <div key={b.id} className={`beat ${activeBeat===b.id?'active':''} ${b.done?'done':''}`} onClick={()=>setActiveBeat(b.id)}>
                    <div className="b-row">
                      <span className="b-name">{b.name}</span>
                      {b.done ? <span className="b-check"><Icon name="check" size={10}/></span> : null}
                    </div>
                    <div className="b-desc">{b.desc}</div>
                    <div className="b-scenes">
                      {b.scenes.map(n => (
                        <span key={n} className={`scene-chip ${activeScene===n?'on':''}`} onClick={(e)=>{ e.stopPropagation(); setActiveScene(n); }}>Scene {n}</span>
                      ))}
                      <button className="add-scene" onClick={(e)=>e.stopPropagation()}><Icon name="plus" size={10}/> Write scene</button>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
        {tab==='scenes' && (
          <div className="scene-list">
            {SCENES.map(s => (
              <div key={s.n} className={`scene-row ${activeScene===s.n?'active':''}`} onClick={()=>setActiveScene(s.n)}>
                <span className="sr-n">{String(s.n).padStart(2,'0')}</span>
                <span className="sr-slug">{s.slug}</span>
                <button className="sr-del"><Icon name="close" size={10}/></button>
              </div>
            ))}
          </div>
        )}
        {tab==='outline' && (
          <div style={{ padding: 12, color: 'var(--text-3)', fontSize:11 }}>Outline view coming soon.</div>
        )}
      </div>
    </React.Fragment>
  );
};

/* ---------- CENTER — Script Editor ---------- */
const ScriptEditor = ({ activeScene }) => {
  const [tool, setTool] = uS('action');
  const tools = [
    { id:'action',     label:'Action',     k:'1' },
    { id:'char',       label:'Character',  k:'2' },
    { id:'dialogue',   label:'Dialogue',   k:'3' },
    { id:'paren',      label:'(Paren)',    k:'4' },
    { id:'transition', label:'Transition', k:'5' },
  ];
  return (
    <React.Fragment>
      <div className="script-toolbar">
        <button className="st-btn"><Icon name="chevron" size={11} className="flip"/> Undo</button>
        <button className="st-btn"><Icon name="chevron" size={11}/> Redo</button>
        <div className="sep"/>
        {tools.map(t => (
          <button key={t.id} className={`st-tool ${tool===t.id?'on':''}`} onClick={()=>setTool(t.id)}>
            {t.label}
            <span className="k">{t.k}</span>
          </button>
        ))}
        <div className="grow"/>
        <span className="saved-tag"><span className="dot"/>All changes saved</span>
        <button className="st-btn">Full Script</button>
        <button className="st-btn">History</button>
        <button className="st-btn">Save Version</button>
        <button className="st-btn primary"><Icon name="pitch" size={11}/> Generate Deck</button>
      </div>

      <div className="script-stage">
        <div className="script-page">
          <div className="sp-head">
            <span>SCENE {String(activeScene).padStart(2,'0')} \u2014 EXT. COUNTY COURTHOUSE - MORNING</span>
            <span className="pp">PAGE 7 / 114</span>
          </div>
          <div className="sp-body">
            {SCRIPT_PAGE.map((blk, i) => {
              if (blk.kind === 'scene')      return <div key={i} className="line scene"><span className="gutter">SCN</span><span className="text">{blk.text}</span></div>;
              if (blk.kind === 'action')     return <div key={i} className="line action"><span className="gutter">ACT</span><span className="text">{blk.text}</span></div>;
              if (blk.kind === 'char')       return <div key={i} className="line char"><span className="gutter">CHR</span><span className="text">{blk.text}</span></div>;
              if (blk.kind === 'paren')      return <div key={i} className="line paren"><span className="gutter">(P)</span><span className="text">{blk.text}</span></div>;
              if (blk.kind === 'dialogue')   return <div key={i} className="line dial"><span className="gutter">DLG</span><span className="text">{blk.text}</span></div>;
              if (blk.kind === 'transition') return <div key={i} className="line trans"><span className="gutter">TRN</span><span className="text">{blk.text}</span></div>;
              return null;
            })}
            <div className="caret-line"><span className="gutter">ACT</span><span className="text"><span className="caret"/></span></div>
          </div>
        </div>
      </div>
    </React.Fragment>
  );
};

/* ---------- RIGHT — Hitchcock AI ---------- */
const Hitchcock = ({ activeBeat }) => {
  const [tab, setTab] = uS('hitch');
  const [val, setVal] = uS('');
  const [msgs, setMsgs] = uS(HITCHCOCK_MSGS);
  const beat = BEATS.flatMap(g => g.items).find(b => b.id === activeBeat);
  const send = () => {
    if (!val.trim()) return;
    setMsgs(m => [...m, { who:'you', text: val }]);
    const q = val;
    setVal('');
    setTimeout(() => {
      setMsgs(m => [...m, { who:'hitch', text: `Working on it. Pass: \u201C${q}\u201D. Want me to apply directly to the scene?` }]);
    }, 600);
  };
  return (
    <React.Fragment>
      <div className="tabs">
        <button className={tab==='rewrite'?'on':''} onClick={()=>setTab('rewrite')}>AI REWRITE</button>
        <button className={tab==='map'?'on':''} onClick={()=>setTab('map')}>STORY MAP</button>
        <button className={tab==='hitch'?'on':''} onClick={()=>setTab('hitch')}>HITCHCOCK</button>
      </div>
      <div className="hitch-chars">
        {CHARACTERS.map(c => (
          <span key={c.id} className={`char-chip ${c.active?'on':''}`} style={{ '--cc': c.color }}>
            <span className="d"/>{c.name}
          </span>
        ))}
      </div>
      {tab==='hitch' && (
        <React.Fragment>
          <div className="hitch-beat">
            <span className="lbl">Beat</span>
            <span className="val">{beat?.name || 'Opening Image'}</span>
          </div>
          <div className="warren" style={{ flex: 1 }}>
            <div className="stream">
              {msgs.map((m, i) => (
                <div key={i} className={`msg ${m.who==='you'?'you':''}`}>
                  <div className="avt">{m.who==='you' ? 'E' : 'H'}</div>
                  <div className="body">
                    <div className="who">{m.who==='you' ? 'You' : 'Hitchcock · Script Room'}</div>
                    <div>{m.text}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="input-row">
              <input type="text" value={val} onChange={e=>setVal(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter') send(); }} placeholder="Ask Hitchcock to tighten, expand, restructure…"/>
              <button className="send" onClick={send}><Icon name="send" size={11}/></button>
            </div>
          </div>
        </React.Fragment>
      )}
      {tab==='rewrite' && (
        <div style={{ padding: 12, fontSize: 11, color:'var(--text-2)', flex:1, overflow:'auto' }}>
          <div style={{color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'.08em', fontSize:10, marginBottom:6}}>Tone</div>
          <div style={{display:'flex', gap:6, flexWrap:'wrap', marginBottom: 12}}>
            {['Tighter','Punchier','More Cinematic','More Vulnerable','Less Internal'].map(t => (
              <span key={t} className="char-chip"><span className="d"/>{t}</span>
            ))}
          </div>
          <div style={{color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'.08em', fontSize:10, marginBottom:6}}>Scope</div>
          <div style={{display:'flex', gap:6, flexWrap:'wrap', marginBottom: 12}}>
            {['Selection','Scene 2','Whole beat','Act I'].map(t => (
              <span key={t} className="char-chip"><span className="d"/>{t}</span>
            ))}
          </div>
          <button className="btn primary" style={{ width:'100%' }}><Icon name="sparkle" size={11}/> Rewrite</button>
        </div>
      )}
      {tab==='map' && (
        <div className="story-map">
          {BEATS.map((g, gi) => (
            <div key={gi} className="sm-act">
              <div className="sm-act-name">{g.act}</div>
              <div className="sm-row">
                {g.items.map(b => (
                  <span key={b.id} className={`sm-dot ${b.done?'done':''} ${b.id===activeBeat?'on':''}`} title={b.name}/>
                ))}
              </div>
            </div>
          ))}
          <div style={{padding: 10, fontSize:11, color:'var(--text-3)'}}>{BEATS.flatMap(g=>g.items).filter(b=>b.done).length} of {BEATS.flatMap(g=>g.items).length} beats locked.</div>
        </div>
      )}
    </React.Fragment>
  );
};

Object.assign(window, { BeatSheet, ScriptEditor, Hitchcock, BEATS, SCENES, CHARACTERS, HITCHCOCK_MSGS });
