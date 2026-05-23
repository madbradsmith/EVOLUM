/* =====================================================================
   EVOLUM — Pitch room (slide deck editor)
   ===================================================================== */
const { useState: uSp, useRef: uRp } = React;

const SLIDES = [
  { id:'s01', n:1,  tag:'TITLE',      title:'MANDATORY REPORTER',                             accent:'orange', body:'A FEATURE FILM BY EVOLUM STUDIO\n\nWRITTEN AND DIRECTED BY E. WALKER' },
  { id:'s02', n:2,  tag:'HOOK',       title:'One Moment.\nOne Report.\nEverything at Stake.',  accent:'orange', body:'When a teacher files a report she didn\u2019t mean to file, a single father has 72 hours to prove he\u2019s the parent he says he is — before the system decides for him.' },
  { id:'s03', n:3,  tag:'WORLD',      title:'What This Film\nIs Really About',                  accent:'orange', active:true, body:'A system designed to protect children nearly destroys one. Not because anyone is evil. Because institutions optimize for procedure — not people. Three people did everything right. One family almost didn\u2019t survive it.' },
  { id:'s04', n:4,  tag:'SETUP',      title:'The Story',                                       accent:'mint',   body:'Danny Walker, 38, raises his son alone since his wife\u2019s death. A teacher misreads a bruise. The report goes upstream. A social worker has 48 hours to assess. The assessment becomes a case. The case becomes a hearing.' },
  { id:'s05', n:5,  tag:'CHARACTERS', title:'Who You\u2019ll Follow',                          accent:'mint',   body:'DANNY (38) — a man who has rebuilt himself once already, and isn\u2019t sure he has another rebuild left.\nETHAN (8) — quiet, watchful, the reason for everything.\nREBECCA (40s) — a teacher who knows she made a mistake, and won\u2019t look away.' },
  { id:'s06', n:6,  tag:'ACT I',      title:'Act One —\nThe Ordinary World',                   accent:'mint',   body:'We learn the shape of Danny\u2019s life: the routine, the rituals, the love. We meet Ethan in his world and Danny in his. We see the small bruise that will change everything.' },
  { id:'s07', n:7,  tag:'ACT II',     title:'Act Two —\nThe Unraveling',                       accent:'mint',   body:'Procedure takes over. Each step is reasonable. Each step is wrong. Danny fights inside a system that responds best to people who don\u2019t need to fight.' },
  { id:'s08', n:8,  tag:'ACT III',    title:'Act Three —\nThe Reckoning',                      accent:'mint',   body:'A hearing. A truth told plainly, without strategy. A small kindness from a stranger. And a father and son in a pickup truck, driving toward a morning that finally feels like theirs.' },
  { id:'s09', n:9,  tag:'TONE',       title:'Tone & Texture',                                  accent:'blue',   body:'Restrained. Observational. The camera as a witness, not a judge. Long takes for the bureaucratic scenes. Handheld only when love is in the room.' },
  { id:'s10', n:10, tag:'COMPS',      title:'Films We\u2019re In\nConversation With',          accent:'blue',   body:'The deliberate humanism of CAPERNAUM. The procedural patience of A SEPARATION. The American specificity of WINTER\u2019S BONE. Domestic stakes told with feature-film grammar.' },
  { id:'s11', n:11, tag:'AUDIENCE',   title:'Who This Reaches',                                accent:'blue',   body:'Adults 25–54 who watch one prestige drama a week. The Sundance/SXSW circuit. Streamers building libraries with a conscience. Parents. Teachers. Anyone who has ever been mis-read by a stranger.' },
  { id:'s12', n:12, tag:'MARKET',     title:'Where It Lives',                                  accent:'blue',   body:'Festival premiere → limited theatrical → streamer acquisition. Sister-territory deals in the UK, Canada, Australia. Educational and institutional licensing as a long tail.' },
  { id:'s13', n:13, tag:'BUDGET',     title:'Budget Top Sheet',                                accent:'gold',   body:'$1.8M production · $250K post · $150K marketing & festival.\n4-week shoot, one primary location, 6 supporting. SAG modified low. Below-the-line department in place.' },
  { id:'s14', n:14, tag:'TEAM',       title:'Who\u2019s Making It',                            accent:'gold',   body:'Director — E. Walker (EVOLUM)\nProducer — M. Reyes (NORTH LIGHT FILMS)\nDP — T. Kapoor (placeholder, in conversation)\nEditor — A. Holt' },
  { id:'s15', n:15, tag:'ATTACHMENTS',title:'Attached Talent &\nDepartment',                   accent:'gold',   body:'Lead role under offer — top choice attached, second-position confirmed. Production designer signed. Casting director attached. Composer in early discussion.' },
  { id:'s16', n:16, tag:'ASK',        title:'The Ask',                                         accent:'orange', body:'$500,000 equity raise to close production financing. 12% IRR projected over 5 years. Hard floor at $250k for greenlight; ceiling at $750k to fund festival run end-to-end.' },
  { id:'s17', n:17, tag:'CONTACT',    title:'Let\u2019s Make This.',                           accent:'orange', body:'EVOLUM STUDIO\nevolumstudio@gmail.com\nevolumstudio.com / project / mandatory-reporter\n\nNDA + full deck available on request.' },
];

/* ---------- Slide list (left panel) ---------- */
const SlideList = ({ activeSlide, setActiveSlide }) => {
  return (
    <React.Fragment>
      <div style={{padding:'8px 10px', borderBottom:'1px solid var(--line-1)', display:'flex', alignItems:'center', gap:8, flexShrink:0}}>
        <span style={{fontSize:9.5, letterSpacing:'.14em', textTransform:'uppercase', color:'var(--text-3)', fontFamily:'var(--font-mono)', flex:1}}>Slides</span>
        <span style={{fontSize:10.5, color:'var(--text-2)', fontFamily:'var(--font-mono)'}}>{SLIDES.length}</span>
        <button className="chip" style={{padding:'2px 6px'}}><Icon name="plus" size={11}/></button>
      </div>
      <div style={{flex:1, overflowY:'auto', padding:'8px 10px', display:'flex', flexDirection:'column', gap:8}}>
        {SLIDES.map(s => (
          <div key={s.id} className={`slide-thumb ${activeSlide===s.id?'active':''}`} onClick={()=>setActiveSlide(s.id)}>
            <div className={`st-frame accent-${s.accent}`}>
              <span className="st-tag">{s.tag}</span>
              <span className="st-title">{s.title.length > 32 ? s.title.slice(0,30)+'\u2026' : s.title}</span>
            </div>
            <div className="st-meta">
              <span className="st-n">{String(s.n).padStart(2,'0')}</span>
              <span className="st-name">{s.tag}</span>
            </div>
          </div>
        ))}
      </div>
    </React.Fragment>
  );
};

/* ---------- Slide preview (center) ---------- */
const SlideStage = ({ activeSlide, setActiveSlide }) => {
  const idx = SLIDES.findIndex(s => s.id === activeSlide);
  const slide = SLIDES[idx];
  const go = (d) => {
    const next = SLIDES[Math.max(0, Math.min(SLIDES.length-1, idx + d))];
    if (next) setActiveSlide(next.id);
  };
  /* Title-slide treatment differs from content-slide treatment */
  const isTitleSlide  = slide.tag === 'TITLE';
  const isContact     = slide.tag === 'CONTACT';
  const isAsk         = slide.tag === 'ASK';
  return (
    <React.Fragment>
      <div className="deck-toolbar">
        <div className="dt-left">
          <span className="dt-counter">Slide <strong>{idx+1}</strong> of {SLIDES.length}</span>
          <span className={`accent-${slide.accent}-bg`} style={{padding:'2px 7px', borderRadius:2, textTransform:'uppercase', letterSpacing:'.1em', fontSize:10, fontWeight:700}}>{slide.tag}</span>
        </div>
        <div className="grow"/>
        <button className="st-btn"><Icon name="folder" size={11}/> Preview</button>
        <button className="st-btn"><Icon name="sparkle" size={11}/> Refine</button>
        <button className="st-btn"><Icon name="sparkle" size={11}/> Regenerate</button>
        <button className="st-btn"><Icon name="sizzle" size={11}/> Present</button>
        <button className="st-btn">PDF</button>
        <button className="st-btn primary">PPTX</button>
        <span className="dt-credits">0 / 5 BUSINESS INFO CREDITS</span>
      </div>

      <div className="deck-stage">
        <button className="deck-arrow l" onClick={()=>go(-1)} disabled={idx===0}><Icon name="chevron" size={14} className="flip"/></button>
        <div className={`slide accent-${slide.accent} ${isTitleSlide?'is-title':''}`} key={slide.id}>
          <div className="slide-thumb-strip">
            {SLIDES.map(s => (
              <div key={s.id} className={`sts ${s.id===activeSlide?'on':''}`}/>
            ))}
          </div>

          {/* full-bleed image placeholder */}
          <div className={`slide-img tone-${slide.accent}`}>
            <span className="img-label">{slide.tag} \u2014 16:9 \u2014 drop hero still / generate</span>
            <div className="img-stripes"/>
          </div>

          {/* slide content overlay */}
          <div className="slide-overlay">
            <span className="ov-tag">{slide.tag}</span>
            <h1 className="ov-title">
              {slide.title.split('\n').map((line, i) => (
                <React.Fragment key={i}>{line}{i < slide.title.split('\n').length - 1 ? <br/> : null}</React.Fragment>
              ))}
            </h1>
            <div className="ov-body">
              {slide.body.split('\n').map((line, i) => (
                <p key={i} style={{ margin: 0 }}>{line || '\u00a0'}</p>
              ))}
            </div>
          </div>

          <div className="slide-stamp">EV-001 / S{String(slide.n).padStart(2,'0')}</div>
        </div>
        <button className="deck-arrow r" onClick={()=>go(1)} disabled={idx===SLIDES.length-1}><Icon name="chevron" size={14}/></button>
      </div>
    </React.Fragment>
  );
};

/* ---------- Right panel: Refine controls + Media ---------- */
const SlideInspector = ({ activeSlide }) => {
  const [tab, setTab] = uSp('content');
  const slide = SLIDES.find(s => s.id === activeSlide);
  return (
    <React.Fragment>
      <div className="tabs">
        <button className={tab==='content'?'on':''} onClick={()=>setTab('content')}>CONTENT</button>
        <button className={tab==='design'?'on':''} onClick={()=>setTab('design')}>DESIGN</button>
        <button className={tab==='media'?'on':''} onClick={()=>setTab('media')}>MEDIA</button>
        <button className={tab==='ai'?'on':''} onClick={()=>setTab('ai')}>AI</button>
      </div>

      <div style={{ flex:1, overflowY:'auto', padding:'10px 12px', display:'flex', flexDirection:'column', gap:12 }}>
        {tab==='content' && (
          <React.Fragment>
            <div>
              <div className="field-label">SECTION TAG</div>
              <input className="field" defaultValue={slide.tag}/>
            </div>
            <div>
              <div className="field-label">HEADLINE</div>
              <textarea className="field area" defaultValue="WHAT THIS FILM IS REALLY ABOUT"/>
            </div>
            <div>
              <div className="field-label">BODY</div>
              <textarea className="field area tall" defaultValue="A system designed to protect children nearly destroys one. Not because anyone is evil. Because institutions optimize for procedure — not people. Three people did everything right. One family almost didn't survive it."/>
            </div>
            <div>
              <div className="field-label">FOOTER STAMP</div>
              <input className="field" defaultValue="EV-001 / S03"/>
            </div>
            <button className="btn primary"><Icon name="check" size={11}/> Save Slide</button>
          </React.Fragment>
        )}

        {tab==='design' && (
          <React.Fragment>
            <div>
              <div className="field-label">LAYOUT</div>
              <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:6}}>
                {['Full Image','Split','Quote','Stat','Grid','Title'].map((l,i) => (
                  <div key={l} className={`layout-thumb ${i===0?'on':''}`}>
                    <div className="lt-frame"/>
                    <span>{l}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="field-label">ACCENT</div>
              <div style={{display:'flex', gap:6}}>
                {['orange','mint','blue','gold'].map(c => (
                  <div key={c} className={`accent-swatch accent-${c}-bg`}/>
                ))}
              </div>
            </div>
            <div>
              <div className="field-label">TYPE</div>
              <div style={{display:'flex', flexDirection:'column', gap:5}}>
                <div className="type-row on"><span className="tn">Editorial Serif</span><span className="ts">DISPLAY</span></div>
                <div className="type-row"><span className="tn">Industrial Sans</span><span className="ts">DISPLAY</span></div>
                <div className="type-row"><span className="tn">Editorial Sans</span><span className="ts">DISPLAY</span></div>
              </div>
            </div>
            <div>
              <div className="field-label">TEXT TREATMENT</div>
              <div style={{display:'flex', gap:6, flexWrap:'wrap'}}>
                {['UPPERCASE','Title Case','Letterspaced','Outlined'].map(t => (
                  <span key={t} className="char-chip"><span className="d"/>{t}</span>
                ))}
              </div>
            </div>
          </React.Fragment>
        )}

        {tab==='media' && (
          <React.Fragment>
            <div>
              <div className="field-label">HERO IMAGE</div>
              <div className="media-drop">
                <Icon name="folder" size={16}/>
                <span>Drop image, or</span>
                <button className="btn" style={{padding:'4px 8px'}}>Upload</button>
                <button className="btn primary" style={{padding:'4px 8px'}}><Icon name="sparkle" size={11}/> Generate</button>
              </div>
            </div>
            <div>
              <div className="field-label">RECENT</div>
              <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6}}>
                {[1,2,3,4].map(i => (
                  <div key={i} className="recent-media">
                    <span>IMG-{String(i).padStart(2,'0')}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="field-label">OVERLAY</div>
              <div style={{display:'flex', gap:6}}>
                {['None','Light','Heavy','Vignette'].map(o => (
                  <span key={o} className={`char-chip ${o==='Heavy'?'on':''}`}><span className="d"/>{o}</span>
                ))}
              </div>
            </div>
          </React.Fragment>
        )}

        {tab==='ai' && (
          <React.Fragment>
            <div style={{ fontSize:11, color:'var(--text-2)' }}>
              Generate this slide from the project bible. Pitch will pull from script + beat sheet + character notes.
            </div>
            <div>
              <div className="field-label">PROMPT</div>
              <textarea className="field area tall" defaultValue="Open Act II with the moment of intervention. Lean cinematic, restrained. No clichés."/>
            </div>
            <div>
              <div className="field-label">STYLE</div>
              <div style={{display:'flex', gap:6, flexWrap:'wrap'}}>
                {['Editorial','Cinematic','Festival','Streamer'].map(s => (
                  <span key={s} className={`char-chip ${s==='Cinematic'?'on':''}`}><span className="d"/>{s}</span>
                ))}
              </div>
            </div>
            <button className="btn primary"><Icon name="sparkle" size={11}/> Regenerate Slide</button>
            <div style={{ fontSize:10, color:'var(--text-3)', textAlign:'center' }}>Uses 1 of 5 weekly credits</div>
          </React.Fragment>
        )}
      </div>
    </React.Fragment>
  );
};

Object.assign(window, { SlideList, SlideStage, SlideInspector, SLIDES });
