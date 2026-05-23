/* =====================================================================
   EVOLUM — Sizzle Room
   Hitchcock chat (main) + long-scroll Reel builder (right)
   ===================================================================== */
const SIZZLE_ASSETS = [
  { id:'logline',    label:'LOGLINE',       on:true },
  { id:'treatment',  label:'TREATMENT',     on:true },
  { id:'world',      label:'WORLD IMAGE',   on:true },
  { id:'characters', label:'CHARACTERS',    on:true },
  { id:'existing',   label:'EXISTING REEL', on:false },
];

const SIZZLE_MSGS_INIT = [
  { who:'hitch', t:'2:48p', text:"You\u2019ve got something real here. The moment Ethan reaches down and touches the strap of his backpack \u2014 just to make sure it\u2019s there \u2014 that\u2019s your whole film in one gesture.\n\nI\u2019m Hitchcock. I cut sizzle reels. Let\u2019s make yours land.\n\nYou\u2019ve got 27 seconds on the plan right now, and five of those slots have no image locked yet. Before I start suggesting frames, I need to know one thing:\n\nThat opening \u2014 Danny crossing the courthouse plaza alone, work boots, clean shirt, the only thing he could control \u2014 is that where you want the reel to begin? Or do you want to start quieter, in the neighborhood, before anyone knows what\u2019s coming?" },
];

/* 8 frames, 27s total — matches the user's reference */
const SIZZLE_FRAMES = [
  { id:'f1', n:1, caption:'EVOLUM STUDIO PRESENTS',                           dur: 2,  hasImage:true,  tone:'black' },
  { id:'f2', n:2, caption:'(no text)',                                        dur: 3,  hasImage:true,  tone:'amber' },
  { id:'f3', n:3, caption:'MANDATORY REPORTER',                               dur: 3,  hasImage:true,  tone:'gold'  },
  { id:'f4', n:4, caption:'In a suburb where neighbors mow their\u2026',      dur: 4,  hasImage:true,  tone:'cool'  },
  { id:'f5', n:5, caption:'(no text)',                                        dur: 3,  hasImage:false, tone:'mono'  },
  { id:'f6', n:6, caption:'with the machinery of child protective s\u2026',   dur: 4,  hasImage:false, tone:'mono'  },
  { id:'f7', n:7, caption:'For those who believe in stories that ma\u2026',   dur: 3,  hasImage:false, tone:'amber' },
  { id:'f8', n:8, caption:'evolumstudio.com',                                 dur: 5,  hasImage:false, tone:'black' },
];

const fmtSec = (s) => `${s}s`;

/* ---------- Main: Hitchcock chat ---------- */
const SizzleChat = ({ msgs, setMsgs }) => {
  const [val, setVal] = React.useState('');
  const scrollRef = React.useRef(null);
  React.useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight; }, [msgs]);
  const send = () => {
    if (!val.trim()) return;
    setMsgs(m => [...m, { who:'you', t: new Date().toTimeString().slice(0,5), text: val }]);
    const q = val; setVal('');
    setTimeout(() => {
      setMsgs(m => [...m, { who:'hitch', t: new Date().toTimeString().slice(0,5), text: `Locked. \u201C${q}\u201D \u2014 I\u2019ll fold that into the cut and rebuild any frame that drifts off it. Use the Frame Builder on the right to commit a credit when you\u2019re ready.` }]);
    }, 700);
  };
  return (
    <div className="sizzle-stage">
      <div className="sizzle-head">
        <div>
          <div className="ic-title">Sizzle Room</div>
          <div className="ic-sub">Tell Hitchcock the feeling, the scale, the one image you want people to remember. He\u2019ll cut the reel frame by frame on the right.</div>
        </div>
        <div className="ic-room"><span className="d"/><span>1 person here</span></div>
      </div>

      <div className="ic-stream sizzle-chat" ref={scrollRef}>
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
        <div className="ic-input" style={{maxWidth:'none'}}>
          <input value={val} onChange={e=>setVal(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter') send(); }} placeholder="Talk to Hitchcock\u2026"/>
          <button title="Voice"><Icon name="sizzle" size={13}/></button>
          <button className="send" onClick={send}>Send</button>
        </div>
        <div className="ic-foot">EVOLUM \u2014 POWERED BY DEVELOPUM AI ENGINE \u00b7 INTEGRITY STATEMENT</div>
      </div>
    </div>
  );
};

/* ---------- Right: long-scroll reel builder ---------- */
const SizzleBuilder = ({ frames, setFrames, assets, setAssets, prompts, setPrompts, builderPrompt, setBuilderPrompt, terms, setTerms, musicFile, setMusicFile, ready, onGenerate3, onCut, onUploadTrack, generating, cutting }) => {
  const totalDur = frames.reduce((a,f) => a + f.dur, 0);
  const framesWithImages = frames.filter(f => f.hasImage).length;
  const canUploadTrack = terms;
  const canCut = ready && terms !== false;
  return (
    <div className="sizzle-builder">
      {/* THE PROJECT */}
      <div className="sb-section">
        <div className="sb-label">The Project</div>
        <div style={{fontFamily:'Georgia, serif', fontSize:18, fontWeight:700, fontStyle:'italic', color:'var(--text-1)', marginBottom:6}}>Mandatory Reporter</div>
        <div style={{fontFamily:'Georgia, serif', fontStyle:'italic', fontSize:11.5, color:'var(--text-2)', lineHeight:1.5, borderLeft:'2px solid var(--accent)', paddingLeft:10}}>
          In a suburb where neighbors mow their lawns through hard times and never ask for help, one family\u2019s collision with the machinery of child protective services exposes how systems built to protect children can quietly destroy them instead.
        </div>
      </div>

      {/* AVAILABLE ASSETS */}
      <div className="sb-section">
        <div className="sb-label">Available Assets</div>
        <div className="asset-grid">
          {assets.map((a, i) => (
            <button key={a.id} className={`asset-chip ${a.on?'on':''}`} onClick={()=>setAssets(prev => prev.map((x,idx) => idx===i ? { ...x, on: !x.on } : x))}>
              <span className="ac-name">{a.label}</span>
              {a.on && <span className="ac-check"><Icon name="check" size={9}/></span>}
            </button>
          ))}
        </div>
      </div>

      {/* REEL PROMPTS */}
      <div className="sb-section">
        <div className="sb-label">Reel Prompts <span className="sb-hint">\u2014 Hitchcock fills these or you can</span></div>
        <div style={{display:'flex', flexDirection:'column', gap:8}}>
          <div>
            <div className="field-label" style={{fontSize:9, marginBottom:3}}>Feeling / Mood</div>
            <input className="field" placeholder="tension and wonder, melancholy, hope\u2026" value={prompts.mood} onChange={e=>setPrompts(p=>({...p, mood:e.target.value}))}/>
          </div>
          <div>
            <div className="field-label" style={{fontSize:9, marginBottom:3}}>Scale</div>
            <input className="field" placeholder="intimate, epic, claustrophobic\u2026" value={prompts.scale} onChange={e=>setPrompts(p=>({...p, scale:e.target.value}))}/>
          </div>
          <div>
            <div className="field-label" style={{fontSize:9, marginBottom:3}}>Key Visual</div>
            <input className="field" placeholder="the image you want people to remember\u2026" value={prompts.visual} onChange={e=>setPrompts(p=>({...p, visual:e.target.value}))}/>
          </div>
        </div>
      </div>

      {/* PREVIEW — frame list */}
      <div className="sb-section">
        <div className="sb-label">
          Preview <span className="sb-hint">\u2014 the cut, frame by frame \u00b7 click <Icon name="undock" size={9}/> to refresh</span>
          <button className="sb-refresh" title="Refresh preview"><Icon name="undock" size={11}/></button>
        </div>
        <div className="frame-list">
          {frames.map((f, i) => (
            <div key={f.id} className="frame-row">
              <span className="fr-n">{f.n}</span>
              <div className={`fr-thumb tone-${f.tone} ${!f.hasImage?'empty':''}`}>
                {!f.hasImage && <Icon name="plus" size={12}/>}
              </div>
              <span className={`fr-caption ${!f.hasImage?'no-img':''}`} style={{ fontStyle: f.caption.startsWith('(') ? 'italic' : 'normal' }}>{f.caption}</span>
              <span className="fr-dur">{fmtSec(f.dur)}</span>
            </div>
          ))}
        </div>
        <div className="frame-list-totals">
          <span>{frames.length} FRAMES \u00b7 {totalDur}S TOTAL</span>
          <span style={{color: musicFile ? 'var(--ok)' : 'var(--text-3)'}}>\u00b7 {musicFile ? `MUSIC: ${musicFile}` : 'NO MUSIC BED'}</span>
        </div>
      </div>

      {/* FRAME BUILDER */}
      <div className="sb-section">
        <div className="sb-label">Frame Builder <span className="sb-hint">\u2014 generate 3, lock in the ones you want</span></div>
        <textarea className="field area" placeholder="A cinematic still: setting, light, mood, lens. Specific." value={builderPrompt} onChange={e=>setBuilderPrompt(e.target.value)} style={{minHeight:62}}/>
        <button className="btn primary" style={{ width:'100%', marginTop:6 }} disabled={generating} onClick={onGenerate3}>
          <Icon name="sparkle" size={11}/> {generating ? 'Generating\u2026' : 'Generate 3'}
        </button>
      </div>

      {/* MUSIC BED */}
      <div className="sb-section">
        <div className="sb-label">Music Bed <span className="sb-hint">(optional)</span></div>
        <button className="upload-zone">
          <Icon name="folder" size={14}/>
          <span>CLICK TO UPLOAD TRACK</span>
        </button>
        <label className="terms-row">
          <input type="checkbox" checked={terms} onChange={e=>setTerms(e.target.checked)}/>
          <span>I own this music or have a valid license. I accept full responsibility for any copyright claims. EVOLUM is not liable for my music choices.</span>
        </label>
        <button className="btn primary" style={{ width:'100%' }} disabled={!canUploadTrack} onClick={onUploadTrack}>
          <Icon name="folder" size={11}/> Upload Track
        </button>
      </div>

      {/* SIZZLE REEL READY */}
      <div className={`sb-section sb-ready ${ready?'is-ready':''}`}>
        <div className="sb-label" style={{ color: ready ? 'var(--ok)' : 'var(--text-3)'}}>
          {ready ? '\u2713 Sizzle Reel Ready' : 'Sizzle Reel Pending'}
        </div>
        <button className={`btn primary`} style={{ width:'100%' }} disabled={!ready}>
          <Icon name="folder" size={11}/> Download MP4
        </button>
        <div style={{fontSize:9.5, color:'var(--text-3)', textAlign:'center', marginTop:6, fontFamily:'var(--font-mono)', letterSpacing:'.08em'}}>
          UPLOAD TO YOUTUBE \u2192 PASTE URL BACK IN YOUR PROJECT
        </div>
        <button className={`btn primary`} style={{ width:'100%', marginTop:8 }} disabled={!canCut || cutting} onClick={onCut}>
          {cutting ? 'CUTTING\u2026' : 'CUT'}
        </button>
        <div style={{fontSize:9.5, color:'var(--text-3)', textAlign:'center', marginTop:4, fontFamily:'var(--font-mono)', letterSpacing:'.06em'}}>
          {ready ? 'Re-cut with any prompt or music change.' : `${framesWithImages} / ${frames.length} frames locked \u00b7 cut when ready`}
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { SizzleChat, SizzleBuilder, SIZZLE_ASSETS, SIZZLE_MSGS_INIT, SIZZLE_FRAMES });
