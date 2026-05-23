/* =====================================================================
   EVOLUM — Deliverables room
   ===================================================================== */
const { useState: uSd } = React;

const D_CATS = [
  { id:'core',       name:'Core Deliverables',   icon:'film' },
  { id:'pitch',      name:'Pitch Suite',         icon:'pitch' },
  { id:'script',     name:'Script Intelligence', icon:'script' },
  { id:'production', name:'Production Package',  icon:'people' },
  { id:'press',      name:'Investor & Press',    icon:'send' },
  { id:'deal',       name:'After the Handshake', icon:'invest' },
];

const DOCS = [
  /* Core (3) */
  { id:'d01', cat:'core', icon:'pitch',  name:'Pitch Deck',            desc:'Slides built from your script — comp titles, audience map, logline, and tone references.', status:'ready',  format:'PPTX', size:'4.2 MB', updated:'today 2:14p',  primary:'Preview & Refine', actions:[{ label:'Download PPTX', kind:'sec' }, { label:'Download PDF', kind:'sec' }] },
  { id:'d02', cat:'core', icon:'film',   name:'Script Analysis Report',desc:'Per-scene character function, market positioning, audience temperature, and comparable performance data.', status:'ready', format:'PDF', size:'1.8 MB', updated:'today 11:08a', primary:'View Report', actions:[{ label:'Download PDF', kind:'sec' }] },
  { id:'d03', cat:'core', icon:'script', name:'Script',                desc:'Download your original script, or send a watermarked copy to a collaborator.', status:'always', format:'FDX', size:'612 KB', updated:'today 9:42a',  primary:'Download Script', actions:[{ label:'Share (Watermarked)', kind:'sec' }, { label:'Download PDF', kind:'sec' }] },

  /* Pitch Suite (3) */
  { id:'d04', cat:'pitch', icon:'pitch',  name:'Title Slide Variants', desc:'Five title designs sampled from your project tone — light, dark, festival, streamer, gritty.', status:'ready', format:'PNG', size:'8.4 MB',  updated:'today 1:50p',  primary:'Preview', actions:[{ label:'Download Set', kind:'sec' }] },
  { id:'d05', cat:'pitch', icon:'poster', name:'Poster Concepts',      desc:'Three poster directions in 27×40 print-ready format.', status:'ready', format:'PNG', size:'24 MB',   updated:'today 11:30a', primary:'Preview', actions:[{ label:'Download Set', kind:'sec' }] },
  { id:'d06', cat:'pitch', icon:'sizzle', name:'Sizzle Reel · 90s',    desc:'Tone reel cut to your synopsis using reference footage and your script\u2019s emotional beats.', status:'ready', format:'MP4', size:'186 MB', updated:'today 9:15a',  primary:'Preview', actions:[{ label:'Download', kind:'sec' }] },

  /* Script Intelligence (3) */
  { id:'d07', cat:'script', icon:'script', name:'Beat Sheet',           desc:'Save the Cat structure mapped to your scenes. 15 beats, color-coded, exportable.', status:'ready', format:'PDF',  size:'420 KB', updated:'yesterday',  primary:'View', actions:[{ label:'Download', kind:'sec' }] },
  { id:'d08', cat:'script', icon:'people', name:'Character Breakdowns', desc:'Per-character arc, scenes in, dialogue count, comparable performers.', status:'ready', format:'PDF', size:'880 KB',  updated:'yesterday',  primary:'View', actions:[{ label:'Download', kind:'sec' }] },
  { id:'d09', cat:'script', icon:'clock',  name:'Coverage Report',      desc:'Industry-style coverage: logline, synopsis, comments, recommend / consider / pass.', status:'ready', format:'PDF', size:'560 KB', updated:'2d ago',     primary:'View', actions:[{ label:'Download', kind:'sec' }] },

  /* Production Package (2) */
  { id:'d10', cat:'production', icon:'invest', name:'Budget Top Sheet',         desc:'Line-by-line spend by department. Below-the-line modeled from your locations and scene count.', status:'ready', format:'XLSX', size:'160 KB', updated:'2d ago', primary:'View', actions:[{ label:'Download', kind:'sec' }] },
  { id:'d11', cat:'production', icon:'film',   name:'Shooting Schedule Draft', desc:'Stripboard estimate from your scene heading database.', status:'ready', format:'PDF', size:'320 KB', updated:'2d ago', primary:'View', actions:[{ label:'Download', kind:'sec' }] },

  /* Investor & Press (3) */
  { id:'d12', cat:'press', icon:'invest', name:'Investor Brief', desc:'Financial case — budget, ROI projections, and comparable box office performance.', status:'ready', format:'PDF',  size:'2.1 MB', updated:'today 2:30p', primary:'View', actions:[{ label:'Download PDF', kind:'sec' }] },
  { id:'d13', cat:'press', icon:'send',   name:'Query Letter',   desc:'Formatted letter to agents, producers, and studios. Professional and ready to send.', status:'ready', format:'DOCX', size:'48 KB',  updated:'today 2:00p', primary:'View', actions:[{ label:'Download PDF', kind:'sec' }] },
  { id:'d14', cat:'press', icon:'star',   name:'Press Kit',      desc:'Press release, full synopsis, production notes, and director statement.', status:'ready', format:'PDF',  size:'3.4 MB', updated:'today 1:14p', primary:'View', actions:[{ label:'Download PDF', kind:'sec' }] },

  /* Deal Docs (9) */
  { id:'d15', cat:'deal', icon:'invest', name:'Term Sheet',           desc:'Principal terms: investment amount, valuation cap, equity at conversion, founder commitments, governance.', status:'configure', actions:[{ label:'Configure to Generate', kind:'prim' }] },
  { id:'d16', cat:'deal', icon:'invest', name:'Use of Funds',         desc:'Line-by-line deployment of the raise across the 12-month operating window.',                                  status:'configure', actions:[{ label:'Configure to Generate', kind:'prim' }] },
  { id:'d17', cat:'deal', icon:'invest', name:'Cap Table',            desc:'Pre-investment, post-bridge (optional), and post-SAFE-conversion ownership scenarios.',                       status:'configure', actions:[{ label:'Configure to Generate', kind:'prim' }] },
  { id:'d18', cat:'deal', icon:'script', name:'SAFE Agreement',       desc:'Y Combinator-style SAFE customized with your project structure and equity terms.',                            status:'configure', actions:[{ label:'Configure to Generate', kind:'prim' }] },
  { id:'d19', cat:'deal', icon:'folder', name:'Disclosure Schedule',  desc:'Exceptions and required disclosures attached to the investment agreement.',                                   status:'configure', actions:[{ label:'Configure to Generate', kind:'prim' }] },
  { id:'d20', cat:'deal', icon:'check',  name:'Funding Milestones',   desc:'Tranche schedule with deliverables, dates, and release conditions.',                                          status:'configure', actions:[{ label:'Configure to Generate', kind:'prim' }] },
  { id:'d21', cat:'deal', icon:'people', name:'Investor Agreement',   desc:'Master purchase agreement for the equity round.',                                                             status:'configure', actions:[{ label:'Configure to Generate', kind:'prim' }] },
  { id:'d22', cat:'deal', icon:'send',   name:'Subscription Docs',    desc:'Per-investor subscription package: bio, signature pages, K-1 election.',                                      status:'configure', actions:[{ label:'Configure to Generate', kind:'prim' }] },
  { id:'d23', cat:'deal', icon:'star',   name:'Operating Agreement',  desc:'LLC operating agreement updated for new member admissions and governance.',                                   status:'configure', actions:[{ label:'Configure to Generate', kind:'prim' }] },
];

const BUILD_QUEUE = [
  { t:'14:32:08', who:'You',      what:'Regenerating Pitch Deck v4',           tag:'pitch',  state:'in-progress', pct:62 },
  { t:'14:14:02', who:'System',   what:'Press Kit · rebuilt 3 sections',       tag:'press',  state:'done',        pct:100 },
  { t:'13:50:33', who:'Hitchcock',what:'Script Analysis · v2 published',       tag:'script', state:'done',        pct:100 },
  { t:'13:41:18', who:'You',      what:'Investor Brief · ROI tables refreshed',tag:'invest', state:'done',        pct:100 },
  { t:'12:55:00', who:'System',   what:'Title Slide Variants · regenerated 5', tag:'pitch',  state:'done',        pct:100 },
  { t:'12:30:44', who:'You',      what:'Beat Sheet · locked Act II',           tag:'script', state:'done',        pct:100 },
  { t:'11:48:09', who:'System',   what:'Coverage Report · v1.4 ready',         tag:'script', state:'done',        pct:100 },
  { t:'10:15:00', who:'You',      what:'Sizzle Reel · cut to 1:30',            tag:'sizzle', state:'done',        pct:100 },
];

const fmtStatus = (s) => {
  switch (s) {
    case 'ready':      return 'Ready';
    case 'always':     return 'Always Available';
    case 'configure':  return 'Configure to Generate';
    case 'pending':    return 'Not Generated';
    case 'generating': return 'Generating…';
    default: return s;
  }
};

const isReady = (s) => s === 'ready' || s === 'always';
const getStatus = (doc, docStatuses) => docStatuses?.[doc.id] || doc.status;

/* ---------- Compact hero band (top of main panel) ---------- */
const DelivHero = ({ project, readyCount, totalCount, generating, onGenerateAll, onReset }) => {
  const pct = Math.round((readyCount / totalCount) * 100);
  const corePct = Math.round((readyCount / totalCount) * 100);
  return (
    <div className="deliv-hero">
      <div className="dh-left">
        <div className="dh-tag">FEATURE · DELIVERABLES</div>
        <div className="dh-title">{project.title}</div>
        <div className="dh-logline">
          In a suburb where neighbors mow their lawns through hard times and never ask for help, one family\u2019s collision with the machinery of child protective services exposes how systems built to protect children can quietly destroy them instead.
        </div>
      </div>
      <div className="dh-right">
        <div className="dh-stat">
          <div className="lbl">DOCS READY</div>
          <div className="big"><strong>{readyCount}</strong> <span>/ {totalCount}</span></div>
          <div className="bar"><span style={{ width: pct + '%' }}/></div>
        </div>
        <div className="dh-actions">
          {readyCount < totalCount ? (
            <button className="btn primary" style={{padding:'8px 14px', fontSize:12}} disabled={generating} onClick={onGenerateAll}>
              <Icon name="sparkle" size={12}/> {generating ? 'Generating\u2026' : 'Generate All'}
            </button>
          ) : (
            <button className="btn primary" style={{padding:'8px 14px', fontSize:12}}>
              <Icon name="send" size={12}/> Send Pitch Package
            </button>
          )}
          <button className="btn" style={{padding:'5px 10px', fontSize:11}} onClick={onReset}><Icon name="undock" size={11}/> Reset</button>
          <div className="dh-pct">{pct}% READY</div>
        </div>
      </div>
    </div>
  );
};

/* ---------- Left: Categories ---------- */
const CategoriesPanel = ({ activeCat, setActiveCat, docStatuses, onGenerateCat }) => {
  const allReady = DOCS.filter(d => isReady(getStatus(d, docStatuses))).length;
  return (
    <React.Fragment>
      <div style={{ padding:'10px 12px 6px', flexShrink:0, borderBottom:'1px solid var(--line-1)' }}>
        <div style={{ fontSize:9.5, letterSpacing:'.14em', textTransform:'uppercase', color:'var(--text-3)', fontFamily:'var(--font-mono)', marginBottom: 4 }}>Documents</div>
        <div style={{ display:'flex', alignItems:'baseline', gap:6 }}>
          <span style={{ fontSize:22, fontFamily:'Georgia, serif', fontWeight:700, color:'var(--accent)' }}>{allReady}</span>
          <span style={{ fontSize:13, color:'var(--text-3)', fontFamily:'var(--font-mono)' }}>/ {DOCS.length}</span>
          <span style={{ marginLeft:'auto', fontSize:9.5, letterSpacing:'.14em', color:'var(--ok)', fontFamily:'var(--font-mono)' }}>READY</span>
        </div>
      </div>
      <div style={{ flex:1, overflowY:'auto', padding: '6px 0' }}>
        <button className={`cat-row ${activeCat==='all'?'active':''}`} onClick={()=>setActiveCat('all')}>
          <span className="ic"><Icon name="folder" size={14}/></span>
          <span className="name">All Documents</span>
          <span className="n">{DOCS.length}</span>
        </button>
        <div style={{ height:1, background:'var(--line-1)', margin:'6px 12px' }}/>
        {D_CATS.map(c => {
          const docs = DOCS.filter(d => d.cat === c.id);
          const ready = docs.filter(d => isReady(getStatus(d, docStatuses))).length;
          return (
            <button key={c.id} className={`cat-row ${activeCat===c.id?'active':''}`} onClick={()=>setActiveCat(c.id)}>
              <span className="ic"><Icon name={c.icon} size={14}/></span>
              <span className="name">{c.name}</span>
              <span className="ratio">{ready}/{docs.length}</span>
            </button>
          );
        })}
      </div>
      <div style={{ padding:'10px 12px', borderTop:'1px solid var(--line-1)', flexShrink:0 }}>
        <button className="btn primary" style={{ width:'100%' }} disabled={allReady === 0}>
          <Icon name="folder" size={11}/> Download All as ZIP
        </button>
        <div style={{ fontSize:10, color:'var(--text-3)', textAlign:'center', marginTop:6, fontFamily:'var(--font-mono)', letterSpacing:'.08em' }}>{allReady} files \u00b7 {Math.round(DOCS.filter(d=>isReady(getStatus(d, docStatuses))).reduce((acc,d)=>{
          const v = parseFloat(d.size); if (!v) return acc;
          return acc + (d.size?.includes('MB') ? v : v/1024);
        }, 0) * 10) / 10} MB</div>
      </div>
    </React.Fragment>
  );
};

/* ---------- Center: Document table with hero ---------- */
const DocsTable = ({ project, activeCat, selectedId, setSelectedId, docStatuses, progress, generating, onGenerate, onGenerateAll, onReset }) => {
  const filtered = activeCat === 'all' ? DOCS : DOCS.filter(d => d.cat === activeCat);
  const grouped = activeCat === 'all'
    ? D_CATS.map(c => ({ cat: c, docs: DOCS.filter(d => d.cat === c.id) })).filter(g => g.docs.length)
    : [{ cat: D_CATS.find(c=>c.id===activeCat), docs: filtered }];

  const readyCount = DOCS.filter(d => isReady(getStatus(d, docStatuses))).length;

  return (
    <React.Fragment>
      <DelivHero project={project} readyCount={readyCount} totalCount={DOCS.length}
                 generating={generating} onGenerateAll={onGenerateAll} onReset={onReset}/>

      <div className="docs-table-wrap">
        <div className="docs-table-head">
          <span/>
          <span>Name</span>
          <span>Description</span>
          <span>Status</span>
          <span>Format</span>
          <span>Size</span>
          <span>Updated</span>
          <span/>
        </div>
        {grouped.map(g => {
          const catReady = g.docs.filter(d => isReady(getStatus(d, docStatuses))).length;
          return (
            <React.Fragment key={g.cat.id}>
              <div className="docs-section-head">
                <Icon name={g.cat.icon} size={11}/>
                <span className="name">{g.cat.name}</span>
                <span className="n">{g.docs.length} {g.docs.length === 1 ? 'document' : 'documents'}</span>
                <span className="ready">{catReady} ready</span>
              </div>
              {g.docs.map(d => {
                const st = getStatus(d, docStatuses);
                const pg = progress?.[d.id] || 0;
                return (
                  <div key={d.id} className={`doc-row ${selectedId===d.id?'selected':''} ${st==='generating'?'generating':''}`} onClick={()=>setSelectedId(d.id)}>
                    <span className="dc-icon"><Icon name={d.icon} size={14}/></span>
                    <span className="dc-name">{d.name}</span>
                    <span className="dc-desc">{d.desc}</span>
                    <span className="dc-status">
                      <span className={`status-pill st-${st}`}>
                        <span className="d"/>{fmtStatus(st)}
                      </span>
                    </span>
                    <span className="dc-format">{d.format || '—'}</span>
                    <span className="dc-size">{isReady(st) ? d.size : '—'}</span>
                    <span className="dc-updated">{isReady(st) ? d.updated : (st === 'generating' ? 'building\u2026' : '—')}</span>
                    <span className="dc-actions">
                      {st === 'pending' && (
                        <button className="btn primary" onClick={(e)=>{ e.stopPropagation(); onGenerate(d.id); }}>
                          <Icon name="sparkle" size={11}/> Generate
                        </button>
                      )}
                      {st === 'generating' && (
                        <div className="gen-progress">
                          <div className="gp-bar"><span style={{ width: pg + '%' }}/></div>
                          <span className="gp-pct">{pg}%</span>
                        </div>
                      )}
                      {isReady(st) && (
                        <button className="btn primary" onClick={(e)=>e.stopPropagation()}>
                          <Icon name="folder" size={11}/> Download
                        </button>
                      )}
                      {st === 'configure' && (
                        <button className="btn" onClick={(e)=>e.stopPropagation()}>Configure</button>
                      )}
                    </span>
                  </div>
                );
              })}
            </React.Fragment>
          );
        })}
      </div>
    </React.Fragment>
  );
};

/* ---------- Right: Inspector ---------- */
const DocInspector = ({ selectedId, docStatuses, progress, onGenerate }) => {
  const d = DOCS.find(x => x.id === selectedId);
  if (!d) return <div style={{ padding:14, color:'var(--text-3)', fontSize:11 }}>Select a document to inspect.</div>;
  const cat = D_CATS.find(c => c.id === d.cat);
  const st = getStatus(d, docStatuses);
  const pg = progress?.[d.id] || 0;
  return (
    <div className="insp" style={{ padding:'12px 14px 16px' }}>
      <div className="doc-hero" data-cat={d.cat}>
        <div className="dh-ic"><Icon name={d.icon} size={28}/></div>
        <div className="dh-fmt">{d.format || 'GENERATED'}</div>
        <div className="dh-stripes"/>
        {st === 'generating' && (
          <div style={{ position:'absolute', bottom:8, left:8, right:8, zIndex:3 }}>
            <div className="gp-bar"><span style={{ width: pg + '%' }}/></div>
            <div style={{textAlign:'center', fontFamily:'var(--font-mono)', fontSize:10, color:'var(--accent)', letterSpacing:'.1em', marginTop:4}}>BUILDING \u00b7 {pg}%</div>
          </div>
        )}
      </div>

      <h3 style={{ marginTop: 4 }}>{d.name}</h3>
      <div className="sub">{cat?.name?.toUpperCase()}</div>

      <p style={{ fontSize:11.5, color:'var(--text-2)', lineHeight:1.55, margin: 0 }}>{d.desc}</p>

      <div className="kv">
        <span className="k">Status</span>
        <span className="v">
          <span className={`status-pill st-${st}`}><span className="d"/>{fmtStatus(st)}</span>
        </span>
        {d.format && (<React.Fragment><span className="k">Format</span><span className="v mono">{d.format}</span></React.Fragment>)}
        {d.size  && isReady(st) && (<React.Fragment><span className="k">Size</span>  <span className="v mono">{d.size}</span></React.Fragment>)}
        {d.updated && isReady(st) && (<React.Fragment><span className="k">Updated</span><span className="v mono">{d.updated}</span></React.Fragment>)}
        <span className="k">Source</span><span className="v">Auto-generated from script + project bible</span>
      </div>

      <div style={{ display:'flex', flexDirection:'column', gap: 6 }}>
        {st === 'pending' && (
          <button className="btn primary" onClick={()=>onGenerate(d.id)}><Icon name="sparkle" size={11}/> Generate {d.name}</button>
        )}
        {st === 'generating' && (
          <button className="btn primary" disabled><Icon name="clock" size={11}/> Generating \u2026 {pg}%</button>
        )}
        {isReady(st) && (
          <React.Fragment>
            <button className="btn primary"><Icon name="folder" size={11}/> {d.primary || 'Open'}</button>
            {(d.actions || []).map((a, i) => (
              <button key={i} className="btn">{a.label}</button>
            ))}
            <button className="btn" onClick={()=>onGenerate(d.id)}><Icon name="sparkle" size={11}/> Regenerate</button>
          </React.Fragment>
        )}
        {st === 'configure' && (
          <React.Fragment>
            <button className="btn primary"><Icon name="settings" size={11}/> Open Deal Generator</button>
            <button className="btn">Configure Terms</button>
          </React.Fragment>
        )}
      </div>

      {isReady(st) && (
        <div style={{ borderTop:'1px solid var(--line-1)', paddingTop: 10 }}>
          <div style={{ fontSize:9.5, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'.08em', marginBottom: 6, fontFamily:'var(--font-mono)' }}>Version History</div>
          {[
            { v:'v3', t:'today 2:14p',   who:'You',       note:'Tightened comp slide titles' },
            { v:'v2', t:'today 11:08a',  who:'Hitchcock', note:'Refreshed audience map' },
            { v:'v1', t:'yesterday',     who:'System',    note:'Initial generation' },
          ].map((v,i) => (
            <div key={i} className="version-row">
              <span className="vr-v">{v.v}</span>
              <span className="vr-t">{v.t}</span>
              <span className="vr-who">{v.who}</span>
              <span className="vr-note">{v.note}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/* ---------- Bottom: Build queue ---------- */
const BuildQueue = ({ items }) => {
  const list = items && items.length ? items : [];
  return (
    <div className="act">
      <div className="row head">
        <span>TIME</span>
        <span>WHO</span>
        <span>SUITE</span>
        <span>EVENT</span>
        <span>STATE</span>
      </div>
      {list.length === 0 ? (
        <div style={{ padding:'18px 12px', textAlign:'center', color:'var(--text-3)', fontFamily:'var(--font-mono)', fontSize:11, letterSpacing:'.06em' }}>
          Queue is empty. Click <strong style={{color:'var(--accent)'}}>Generate All</strong> to build the package.
        </div>
      ) : list.map((a,i) => (
        <div key={i} className="row">
          <span>{a.t}</span>
          <span className="who">{a.who}</span>
          <span className="tag" style={{ color: STAGES[a.tag]?.color || 'var(--text-3)', background:'rgba(255,255,255,0.04)' }}>{STAGES[a.tag]?.label || a.tag}</span>
          <span className="what">
            {a.what}
            {a.state === 'in-progress' && (
              <span style={{display:'inline-flex',alignItems:'center',gap:6,marginLeft:8}}>
                <span style={{width:80,height:4,background:'var(--bg-3)',borderRadius:2,overflow:'hidden',display:'inline-block'}}>
                  <span style={{display:'block',width:(a.pct||0)+'%',height:'100%',background:'var(--accent)', transition:'width 200ms linear'}}/>
                </span>
                <span style={{fontFamily:'var(--font-mono)',fontSize:10,color:'var(--accent)'}}>{a.pct||0}%</span>
              </span>
            )}
          </span>
          <span style={{textTransform:'uppercase',letterSpacing:'.08em',fontSize:9.5, fontWeight:700, color: a.state==='in-progress' ? 'var(--accent)' : 'var(--ok)'}}>
            {a.state==='in-progress' ? 'BUILDING' : 'COMPLETE'}
          </span>
        </div>
      ))}
    </div>
  );
};

Object.assign(window, { CategoriesPanel, DocsTable, DocInspector, BuildQueue, DOCS, D_CATS });
