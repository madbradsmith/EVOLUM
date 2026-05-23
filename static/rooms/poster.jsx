/* =====================================================================
   EVOLUM — Poster / Design room
   ===================================================================== */
const POSTER_VARIANTS = [
  { id:'pv1', tone:'embers',   label:'Embers · Festival',   title:'MANDATORY REPORTER', tag:'THE BATTLE FOR ETHAN\u2019S FUTURE', current:true,
    bg: 'linear-gradient(180deg, #2a1208 0%, #5a2818 40%, #c84818 60%, #1a0805 100%)' },
  { id:'pv2', tone:'midnight', label:'Midnight · Streamer', title:'MANDATORY REPORTER', tag:'WHEN THE SYSTEM CAN\u2019T LISTEN',
    bg: 'linear-gradient(180deg, #04081a 0%, #1a2a4a 40%, #244668 70%, #05080e 100%)' },
  { id:'pv3', tone:'concrete', label:'Concrete · Indie',    title:'MANDATORY REPORTER', tag:'A FATHER\u2019S FIGHT',
    bg: 'linear-gradient(180deg, #1a1a1a 0%, #3a3a3a 50%, #1a1a1a 100%)' },
  { id:'pv4', tone:'paper',    label:'Paper · Boutique',    title:'MANDATORY REPORTER', tag:'A FAMILY ON THE EDGE',
    bg: 'linear-gradient(180deg, #f0e6cf 0%, #d4c39c 50%, #8a7d5e 100%)', light:true },
  { id:'pv5', tone:'crimson',  label:'Crimson · Tense',     title:'MANDATORY REPORTER', tag:'PROCEDURE WILL CONSUME YOU',
    bg: 'linear-gradient(180deg, #1a0408 0%, #4a0a14 50%, #14040a 100%)' },
];

const POSTER_MSGS_INIT = [
  { who:'hitch', t:'2:42p', text:"Describe your vision. I\u2019ll build the prompt with you. We\u2019ll generate three at a time, you pick what to push further. What\u2019s the moment you want on the wall?" },
  { who:'you',   t:'2:44p', text:"A father and a young boy framed in the doorway of a school, late afternoon light. Behind them the world is on fire \u2014 not literally, but emotionally. Tone of A SEPARATION meets WINTER\u2019S BONE." },
  { who:'hitch', t:'2:45p', text:"Good \u2014 emotional fire, not literal. Two reads: an EMBERS direction (gold light, smoke, fire-tinted backlight) and a CONCRETE direction (slate sky, cool morning, gray school facade). I\u2019ll render both. Want a third \u2014 something more poster-poetic?" },
  { who:'you',   t:'2:46p', text:"Yeah. Something on white. Sparse." },
  { who:'hitch', t:'2:46p', text:"Done. Generating 3 variants now \u2014 PAPER, EMBERS, CONCRETE. ~25s each." },
];

/* ---------- Center: Design chat ---------- */
const DesignChat = ({ msgs, setMsgs, onGenerate }) => {
  const [val, setVal] = React.useState('');
  const scrollRef = React.useRef(null);
  React.useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [msgs]);
  const send = () => {
    if (!val.trim()) return;
    setMsgs(m => [...m, { who:'you', t: new Date().toTimeString().slice(0,5), text: val }]);
    const q = val; setVal('');
    setTimeout(() => {
      setMsgs(m => [...m, { who:'hitch', t: new Date().toTimeString().slice(0,5), text: `On it. Reading \u201C${q}\u201D as a tone direction. I\u2019ll build the prompt and queue a render \u2014 use Generate when you want to commit a credit.` }]);
    }, 600);
  };
  return (
    <div className="idea-chat">
      <div className="ic-head">
        <div>
          <div className="ic-title">Hitchcock \u2014 Design Director</div>
          <div className="ic-sub">Describe your vision. He\u2019ll build the prompt with you. You\u2019ll generate the poster.</div>
        </div>
        <div className="ic-room">
          <span className="d"/>
          <span>FAL \u00b7 connected</span>
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
          </div>
        ))}
      </div>

      <div className="ic-input-row">
        <div className="ic-quick">
          <button className="chip" onClick={() => onGenerate()}><Icon name="sparkle" size={11}/> Generate 3 Variants</button>
          <button className="chip"><Icon name="folder" size={11}/> Reference Image</button>
          <button className="chip"><Icon name="poster" size={11}/> Apply To Pitch Deck</button>
        </div>
        <div className="ic-input">
          <input value={val} onChange={e=>setVal(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter') send(); }} placeholder="Describe the image you want \u2014 mood, light, what\u2019s in frame\u2026"/>
          <button title="Voice"><Icon name="sizzle" size={13}/></button>
          <button className="send" onClick={send}>Send</button>
        </div>
        <div className="ic-foot">POWERED BY FAL \u00b7 1 CREDIT PER VARIANT \u00b7 $1013.85 / $18.75 wk</div>
      </div>
    </div>
  );
};

/* ---------- Right: Poster preview + variants ---------- */
const PosterPanel = ({ activeId, setActiveId, variants, generating }) => {
  const v = variants.find(x => x.id === activeId) || variants[0];
  return (
    <div className="poster-panel">
      <div className="pp-stage">
        <div className="poster-frame" style={{ background: v.bg }}>
          <div className="poster-grain"/>
          {v.tone === 'embers' && (
            <React.Fragment>
              <div className="poster-fig"/>
              <div className="poster-fire"/>
            </React.Fragment>
          )}
          {v.tone === 'midnight' && (
            <React.Fragment>
              <div className="poster-fig" style={{ filter:'brightness(0.7)' }}/>
              <div className="poster-light"/>
            </React.Fragment>
          )}
          {v.tone === 'concrete' && (
            <div className="poster-fig"/>
          )}
          {v.tone === 'paper' && (
            <div className="poster-paper-line"/>
          )}
          {v.tone === 'crimson' && (
            <React.Fragment>
              <div className="poster-fig" style={{ filter:'brightness(0.5) sepia(1) hue-rotate(-20deg)' }}/>
              <div className="poster-shadow"/>
            </React.Fragment>
          )}

          <div className={`poster-text ${v.light?'light':''}`}>
            <div className="poster-tag">{v.tag}</div>
            <div className="poster-title">{v.title.split(' ').map((w,i) => <div key={i}>{w}</div>)}</div>
            <div className="poster-credit">A FEATURE FILM BY EVOLUM STUDIO</div>
          </div>

          {generating && (
            <div className="poster-loading">
              <div className="poster-loading-bar"><span/></div>
              <div>GENERATING\u2026</div>
            </div>
          )}
        </div>
        <div className="pp-meta">
          <div>
            <div className="pp-meta-lbl">VARIANT</div>
            <div className="pp-meta-val">{v.label}</div>
          </div>
          <div style={{flex:1}}/>
          <div style={{display:'flex', gap:6}}>
            <button className="btn" title="Previous"><Icon name="chevron" size={11} className="flip"/></button>
            <button className="btn" title="Next"><Icon name="chevron" size={11}/></button>
            <button className="btn"><Icon name="folder" size={11}/> Download</button>
            <button className="btn primary"><Icon name="check" size={11}/> Use This</button>
          </div>
        </div>
      </div>

      <div className="pp-variants">
        <div className="field-label" style={{padding:'8px 14px 4px'}}>Variants</div>
        <div className="pv-strip">
          {variants.map(x => (
            <button key={x.id} className={`pv-thumb ${activeId===x.id?'on':''}`} onClick={()=>setActiveId(x.id)} style={{ background: x.bg }}>
              <span className="pv-label">{x.label.split(' \u00b7 ')[0]}</span>
            </button>
          ))}
          <button className="pv-thumb pv-empty">
            <Icon name="plus" size={18}/>
            <span style={{fontSize:9.5, letterSpacing:'.1em', marginTop:4}}>NEW VARIANT</span>
          </button>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { DesignChat, PosterPanel, POSTER_VARIANTS, POSTER_MSGS_INIT });
