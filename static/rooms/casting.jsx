/* =====================================================================
   EVOLUM — Casting / Self-Tape Studio (Actor view)
   ===================================================================== */
const { useState: uSc, useEffect: uEc, useRef: uRc } = React;

/* Backgrounds catalog */
const BACKGROUNDS = [
  { id:'void',     name:'VOID',         tone:'void',     hint:'pure black' },
  { id:'studio',   name:'STUDIO',       tone:'studio',   hint:'neutral gray' },
  { id:'cream',    name:'CREAM',        tone:'cream',    hint:'warm white' },
  { id:'ember',    name:'EMBER',        tone:'ember',    hint:'firelight' },
  { id:'midnight', name:'MIDNIGHT',     tone:'midnight', hint:'deep blue night' },
  { id:'deep',     name:'DEEP BLUE',    tone:'deep',     hint:'blue gradient' },
  { id:'hospital', name:'HOSPITAL',     tone:'hospital', hint:'cool clinical' },
  { id:'jail',     name:'JAIL',         tone:'jail',     hint:'concrete + bars' },
  { id:'court',    name:'COURTROOM',    tone:'court',    hint:'wood + marble' },
  { id:'exec',     name:'EXEC OFFICE',  tone:'exec',     hint:'warm corporate' },
  { id:'police',   name:'POLICE CAR',   tone:'police',   hint:'flashing red/blue' },
  { id:'bar',      name:'DIVE BAR',     tone:'bar',      hint:'amber neon' },
  { id:'alley',    name:'ALLEY NIGHT',  tone:'alley',    hint:'sodium streetlight' },
  { id:'hotel',    name:'HOTEL SUITE',  tone:'hotel',    hint:'gold + cream' },
  { id:'warehouse',name:'WAREHOUSE',    tone:'warehouse',hint:'concrete + dust' },
  { id:'whitecyc', name:'WHITE CYC',    tone:'whitecyc', hint:'seamless white' },
];

/* The audition / sides — Scene 1, Mandatory Reporter */
const SIDES = {
  project: 'MANDATORY REPORTER',
  role: 'DANNY',
  roleLabel: 'LEAD',
  pages: 1,
  scenes: [
    {
      n: 1,
      slug: "INT. DANNY'S HOUSE - FRONT DOOR / DRIVEWAY - MORNING",
      notes: 'Lean restrained. The morning routine is muscle memory. He is paying close attention to the small things because the big things are too heavy.',
      lines: [
        { kind:'action', text:'Danny grabs Ethan\u2019s backpack and lunch.' },
        { kind:'action', text:'He checks the house automatically \u2014 lights off, lunch packed, keys, wallet.' },
        { kind:'action', text:'Before opening the door, Ethan glances back at the photo on the fridge.' },
        { kind:'action', text:'Danny notices.' },
        { kind:'char',   role:'me',   text:'DANNY' },
        { kind:'dialog', role:'me',   text:'Come on, bud. We\u2019ll be late.' },
        { kind:'action', text:'Ethan follows him out.' },
        { kind:'char',   role:'them', text:'ETHAN' },
        { kind:'paren',  text:'(small voice)' },
        { kind:'dialog', role:'them', text:'Is it picture day still?' },
        { kind:'char',   role:'me',   text:'DANNY' },
        { kind:'dialog', role:'me',   text:'It\u2019s picture day still.' },
        { kind:'paren',  text:'(beat)' },
        { kind:'dialog', role:'me',   text:'Smile with your eyes. That\u2019s what your mom used to say.' },
        { kind:'action', text:'Ethan nods, the way kids do when they\u2019re memorizing something.' },
      ]
    }
  ],
};

const fmtTime = (s) => {
  const m = Math.floor(s / 60);
  const r = Math.floor(s % 60);
  return `${String(m).padStart(2,'0')}:${String(r).padStart(2,'0')}`;
};

/* ---------- Center: Camera + Sides overlay + Controls ---------- */
const TapeStudio = ({ bgId, takes, addTake, recording, setRecording, ready, setReady, takeNum }) => {
  const videoRef = uRc(null);
  const streamRef = uRc(null);
  const recorderRef = uRc(null);
  const chunksRef = uRc([]);
  const [camOK, setCamOK] = uSc(null);
  const [elapsed, setElapsed] = uSc(0);
  const timerRef = uRc(null);
  const [showSides, setShowSides] = uSc(false);
  const [mute, setMute] = uSc(false);

  uEc(() => {
    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720, facingMode: 'user' }, audio: true });
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(()=>{});
        }
        setCamOK(true);
        setReady(r => ({ ...r, cam: true, mic: true, frame: true }));
      } catch (e) {
        if (!cancelled) setCamOK(false);
      }
    })();
    return () => {
      cancelled = true;
      if (streamRef.current) { streamRef.current.getTracks().forEach(t => t.stop()); }
    };
  }, []);

  const startRec = () => {
    if (!streamRef.current || recording) return;
    chunksRef.current = [];
    try {
      const mr = new MediaRecorder(streamRef.current, { mimeType: 'video/webm;codecs=vp8,opus' });
      mr.ondataavailable = (e) => { if (e.data && e.data.size) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        const dur = elapsed;
        addTake({ id: 'tk-' + Date.now(), url, duration: dur, t: new Date(), bg: bgId });
      };
      mr.start();
      recorderRef.current = mr;
      setRecording(true);
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
    } catch (e) {
      console.warn('recorder failed', e);
    }
  };
  const stopRec = () => {
    if (recorderRef.current && recording) {
      recorderRef.current.stop();
      recorderRef.current = null;
      setRecording(false);
      clearInterval(timerRef.current);
    }
  };
  const toggleRec = () => recording ? stopRec() : startRec();

  uEc(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.code === 'Space') { e.preventDefault(); toggleRec(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line
  }, [recording]);

  const bgClass = bgId ? `tape-bg-${bgId}` : '';
  const scene = SIDES.scenes[0];

  return (
    <div className="tape-stage">
      <div className={`tape-viewport ${bgClass}`}>
        {/* slate top-left */}
        <div className="tape-slate">
          <span>PROJECT</span><span className="sep"/><span style={{color:'#fff'}}>{SIDES.project}</span>
          <span className="sep"/>
          <span>ROLE</span><span className="role">{SIDES.role}</span>
          <span className="sep"/>
          <span>TAKE</span><span style={{color:'#fff'}}>{String(takeNum).padStart(2,'0')}</span>
        </div>

        {/* ready indicators top-right */}
        <div className="tape-ready">
          <div className={`rd ${ready.cam?'on':''}`}><span className="d"/>CAM</div>
          <div className={`rd ${ready.mic?'on':''}`}><span className="d"/>MIC</div>
          <div className={`rd ${ready.frame?'on':''}`}><span className="d"/>FRAME</div>
          <div className={`rd ${ready.audio?'on':''}`}><span className="d"/>AUDIO</div>
        </div>

        {/* rec pill below ready indicators */}
        <div className={`tape-rec-pill ${recording?'recording':''}`}>
          <span className="dot"/>
          <span>{recording ? 'REC' : 'STBY'}</span>
        </div>

        {camOK === true ? (
          <video ref={videoRef} className="tape-video mirror" playsInline muted/>
        ) : camOK === false ? (
          <div className="tape-no-cam">
            <div className="lens"/>
            <div>CAMERA PERMISSION DENIED</div>
            <div style={{fontSize:10, color:'var(--text-3)', letterSpacing:'.06em', textTransform:'none', maxWidth:280}}>Allow camera + mic in your browser to record your self-tape. Refresh after granting.</div>
          </div>
        ) : (
          <div className="tape-no-cam"><div className="lens"/><div>REQUESTING CAMERA\u2026</div></div>
        )}

        {/* eye-line marker */}
        <div className="eyeline">EYE-LINE \u00B7 CAMERA</div>

        {showSides && (
          <div className="sides-overlay">
            <div className="so-head">
              <span className="role">{SIDES.role}</span>
              <span>\u00b7 SCENE {scene.n}</span>
              <span style={{marginLeft:'auto', color:'rgba(255,255,255,0.4)'}}>{scene.slug}</span>
            </div>
            {scene.lines.map((l, i) => {
              if (l.kind === 'action') return <div key={i} className="so-line them">{l.text}</div>;
              if (l.kind === 'paren')  return <div key={i} className="so-paren">{l.text}</div>;
              if (l.kind === 'char')   return <div key={i} className={`so-char ${l.role==='me'?'me':'them'}`}>{l.text}</div>;
              if (l.kind === 'dialog') return <div key={i} className={`so-line ${l.role==='me'?'me':'them'}`}>{l.text}</div>;
              return null;
            })}
          </div>
        )}
      </div>

      <div className="tape-controls">
        <button className="tape-iconbtn" title={showSides ? 'Hide sides overlay' : 'Show sides overlay'} onClick={()=>setShowSides(s=>!s)}>
          <Icon name={showSides ? 'close' : 'script'} size={16}/>
        </button>
        <button className={`tape-iconbtn ${mute?'on':''}`} title={mute?'Unmute mic':'Mute mic'} onClick={()=>{
          setMute(m=>!m);
          if (streamRef.current) streamRef.current.getAudioTracks().forEach(t => t.enabled = mute);
        }}>
          <span style={{fontSize:13, fontWeight:700}}>{mute?'\uD83D\uDD07':'\uD83C\uDF99'}</span>
        </button>
        <button className={`rec-btn ${recording?'recording':''}`} onClick={toggleRec} disabled={camOK!==true} title="Record / Stop (Space)">
          <span className="rec-dot"/>
        </button>
        <span className={`tape-timer ${recording?'recording':''}`}>{fmtTime(elapsed)}</span>
        <button className="tape-iconbtn" title="Reset timer" onClick={()=>{ stopRec(); setElapsed(0); }}>
          <Icon name="undock" size={14}/>
        </button>
        <span className="tape-hint">
          {camOK===true && !recording && <React.Fragment>Press <kbd>SPACE</kbd> to record \u00b7 TAKE {String(takeNum).padStart(2,'0')} READY</React.Fragment>}
          {recording && <React.Fragment>RECORDING \u00b7 Press <kbd>SPACE</kbd> to stop</React.Fragment>}
          {camOK===false && <React.Fragment>Camera blocked</React.Fragment>}
        </span>
      </div>
    </div>
  );
};

/* ---------- Right: Background chooser ---------- */
const BackgroundPanel = ({ bgId, setBgId }) => {
  const [aiPrompt, setAiPrompt] = uSc('rooftop at night, city lights, soft rim');
  return (
    <div style={{ flex:1, overflowY:'auto', padding:'12px 12px 14px' }}>
      <div className="field-label">Background</div>
      <div className="bg-grid">
        {BACKGROUNDS.map(b => (
          <button key={b.id} className={`bg-tile tile-${b.tone} ${bgId===b.id?'on':''}`} onClick={()=>setBgId(b.id)} title={b.hint}>
            <span className="bg-name">{b.name}</span>
          </button>
        ))}
      </div>

      <div className="field-label" style={{marginTop:14}}>Generate with AI</div>
      <div style={{display:'flex', gap:6}}>
        <input className="field" placeholder="rooftop at night, city lights\u2026" value={aiPrompt} onChange={e=>setAiPrompt(e.target.value)}/>
        <button className="btn primary" style={{padding:'6px 10px'}}><Icon name="sparkle" size={11}/> Gen</button>
      </div>
      <div style={{fontSize:10, color:'var(--text-3)', marginTop:6, fontFamily:'var(--font-mono)', letterSpacing:'.06em'}}>Uses 1 of 5 weekly credits \u00b7 FAL</div>
    </div>
  );
};

/* ---------- Left: Sides panel ---------- */
const SidesPanel = ({ simple }) => {
  const [tab, setTab] = uSc('sides');
  const [intent, setIntent] = uSc('');
  const [beat, setBeat] = uSc('');
  const [note, setNote] = uSc('');
  const scene = SIDES.scenes[0];
  return (
    <div className="sides-panel">
      <div className="sp-head">
        <div className="sp-title">{SIDES.role}</div>
        <div className="sp-sub">{SIDES.project} \u00b7 {SIDES.roleLabel} \u00b7 {SIDES.pages} PG</div>
      </div>

      {!simple && (
        <div className="tabs">
          <button className={tab==='sides'?'on':''} onClick={()=>setTab('sides')}>SIDES</button>
          <button className={tab==='run'?'on':''} onClick={()=>setTab('run')}>RUN SCENE</button>
          <button className={tab==='roles'?'on':''} onClick={()=>setTab('roles')}>ROLES</button>
        </div>
      )}

      {tab==='sides' && (
        <React.Fragment>
          {!simple && (
            <div className="sp-fields">
              <input className="sp-field" placeholder="Intent" value={intent} onChange={e=>setIntent(e.target.value)}/>
              <input className="sp-field" placeholder="Beat"   value={beat}   onChange={e=>setBeat(e.target.value)}/>
              <input className="sp-field" placeholder="Note"   value={note}   onChange={e=>setNote(e.target.value)}/>
            </div>
          )}
          <div className="sp-script">
            <div className="sp-scene-row">
              <span className="sp-scene-n">SCENE {scene.n}</span>
              <span className="sp-scene-slug">{scene.slug}</span>
            </div>
            {scene.notes && (
              <div className="sp-direction">{scene.notes}</div>
            )}
            {scene.lines.map((l, i) => {
              if (l.kind === 'action') return <div key={i} className="sp-line action">{l.text}</div>;
              if (l.kind === 'paren')  return <div key={i} className="sp-line paren">{l.text}</div>;
              if (l.kind === 'char')   return <div key={i} className={`sp-line char ${l.role==='me'?'me':'them'}`}>{l.text}</div>;
              if (l.kind === 'dialog') return <div key={i} className={`sp-line dial ${l.role==='me'?'me':'them'}`}>{l.text}</div>;
              return null;
            })}
          </div>
        </React.Fragment>
      )}

      {tab==='run' && (
        <div style={{ flex:1, padding:'12px 14px', overflowY:'auto', display:'flex', flexDirection:'column', gap:10, fontSize:11.5, color:'var(--text-2)' }}>
          <div style={{display:'flex', alignItems:'center', gap:8}}>
            <span className="dot" style={{width:8,height:8,borderRadius:'50%',background:'var(--ok)',boxShadow:'0 0 6px var(--ok-glow)'}}/>
            <span style={{fontFamily:'var(--font-mono)', fontSize:10, letterSpacing:'.1em', textTransform:'uppercase', color:'var(--text-1)'}}>Coach mode enabled</span>
          </div>
          <p style={{lineHeight:1.5, margin:0}}>Evie will read the <strong style={{color:'var(--accent)'}}>other character\u2019s lines</strong> in the scene with you. Hit record and start when you\u2019re ready. She\u2019ll pause for your dialogue automatically.</p>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6}}>
            <div className="char-chip on" style={{justifyContent:'center'}}><span className="d"/>Ethan</div>
            <div className="char-chip" style={{justifyContent:'center'}}><span className="d"/>Off-screen</div>
          </div>
          <div className="field-label">VOICE</div>
          <div style={{display:'flex', flexDirection:'column', gap:5}}>
            {['Child · Boy, 6-8','Child · Boy, 8-10','Custom (ElevenLabs)'].map((v,i) => (
              <div key={v} className={`type-row ${i===0?'on':''}`}><span className="tn" style={{fontFamily:'var(--font-ui)', fontSize:11.5}}>{v}</span><span className="ts">{i===2?'AI':'PRESET'}</span></div>
            ))}
          </div>
          <button className="btn primary" style={{ marginTop:6 }}><Icon name="sparkle" size={11}/> Run Scene With Evie</button>
        </div>
      )}

      {tab==='roles' && (
        <div style={{ flex:1, padding:'10px 14px', overflowY:'auto', display:'flex', flexDirection:'column', gap:6 }}>
          {[
            { name:'DANNY',   project:'MANDATORY REPORTER', tag:'LEAD',       current:true },
            { name:'NOAH',    project:'COURT JESTER',        tag:'SUPPORTING', current:false },
            { name:'PETER',   project:'WHO INVITED YOU?',    tag:'GUEST',      current:false },
            { name:'CALEB',   project:'TAX SEASON',          tag:'CO-LEAD',    current:false },
          ].map((r,i) => (
            <div key={i} className={`role-row ${r.current?'on':''}`}>
              <div>
                <div className="rr-name">{r.name}</div>
                <div className="rr-proj">{r.project}</div>
              </div>
              <span className="rr-tag">{r.tag}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/* ---------- Right (bottom): Evie AI coach ---------- */
const Evie = ({ ready }) => {
  const [val, setVal] = uSc('');
  const [msgs, setMsgs] = uSc([
    { who:'evie', text:"You\u2019re playing DANNY. I\u2019ll read the other character\u2019s lines. Enable your camera, then hit record \u2014 or press SPACE." },
    { who:'evie', text:"This morning, Danny is holding himself together with routine. Don\u2019t play the grief. Let the small things carry it." },
  ]);
  const send = () => {
    if (!val.trim()) return;
    setMsgs(m => [...m, { who:'you', text: val }]);
    const q = val;
    setVal('');
    setTimeout(() => {
      setMsgs(m => [...m, { who:'evie', text: `Try one more take with: \u201C${q}\u201D. I\u2019ll watch for it.` }]);
    }, 600);
  };
  return (
    <div className="warren" style={{ flex:1 }}>
      <div className="evie-head">
        <div className="evie-avt">E</div>
        <div>
          <div className="evie-name">Evie</div>
          <div className="evie-mode"><span className="d"/>READY \u00b7 COACH MODE</div>
        </div>
      </div>
      <div className="stream">
        {msgs.map((m,i) => (
          <div key={i} className={`msg ${m.who==='you'?'you':''}`}>
            <div className="avt">{m.who==='you' ? 'A' : 'E'}</div>
            <div className="body">
              <div className="who">{m.who==='you' ? 'Actor' : 'Evie \u00b7 Self-Tape Coach'}</div>
              <div>{m.text}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="input-row">
        <input type="text" value={val} onChange={e=>setVal(e.target.value)} onKeyDown={e=>{ if(e.key==='Enter') send(); }} placeholder="Ask Evie\u2026"/>
        <button className="send" onClick={send}><Icon name="send" size={11}/></button>
      </div>
    </div>
  );
};

/* ---------- Bottom: Takes strip ---------- */
const TakesStrip = ({ takes, activeTakeId, setActiveTakeId, deleteTake }) => {
  return (
    <div className="takes-strip">
      <div className="ts-head">
        <span className="ts-title">My Takes</span>
        <span className="ts-count">{takes.length}</span>
        <div className="grow"/>
        {takes.length > 0 && (
          <React.Fragment>
            <button className="btn">Download All</button>
            <button className="btn primary"><Icon name="send" size={11}/> Submit Best Take</button>
          </React.Fragment>
        )}
      </div>
      {takes.length === 0 ? (
        <div className="ts-empty">
          No takes yet. Hit <kbd>SPACE</kbd> to record your first.
        </div>
      ) : (
        <div className="ts-list">
          {takes.map((t, i) => (
            <div key={t.id} className={`take ${activeTakeId===t.id?'active':''}`} onClick={()=>setActiveTakeId(t.id)}>
              <video src={t.url} className="take-thumb" muted preload="metadata"/>
              <div className="take-meta">
                <span className="tm-n">TAKE {String(i+1).padStart(2,'0')}</span>
                <span className="tm-dur">{fmtTime(t.duration)}</span>
              </div>
              <div className="take-actions">
                <button title="Play" onClick={(e)=>{ e.stopPropagation(); const v = e.currentTarget.closest('.take').querySelector('video'); if (v.paused) v.play(); else v.pause(); }}><Icon name="sizzle" size={10}/></button>
                <button title="Delete" onClick={(e)=>{ e.stopPropagation(); deleteTake(t.id); }}><Icon name="close" size={10}/></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

Object.assign(window, { TapeStudio, BackgroundPanel, SidesPanel, Evie, TakesStrip, BACKGROUNDS, SIDES });
