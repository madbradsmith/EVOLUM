/* =====================================================================
   EVOLUM — Budget room
   ===================================================================== */
const BUDGET_SECTIONS = [
  { id:'topsheet',  name:'Top Sheet',         icon:'invest' },
  { id:'detail',    name:'Detailed Budget',   icon:'folder' },
  { id:'schedule',  name:'Cash Flow',         icon:'clock' },
  { id:'comps',     name:'Comp Budgets',      icon:'film' },
  { id:'funding',   name:'Funding Status',    icon:'invest' },
];

const BUDGET_LINES = [
  /* ABOVE THE LINE */
  { id:'b01', group:'ABOVE THE LINE',  name:'Director',                amount: 75000,  suggested:true },
  { id:'b02', group:'ABOVE THE LINE',  name:'Producer(s)',             amount: 55000,  suggested:true },
  { id:'b03', group:'ABOVE THE LINE',  name:'Writer',                  amount: 35000,  suggested:true },
  { id:'b04', group:'ABOVE THE LINE',  name:'Cast (Top 3 Roles)',      amount: 120000, suggested:true },
  /* BELOW THE LINE */
  { id:'b05', group:'BELOW THE LINE',  name:'Crew',                    amount: 180000, suggested:true },
  { id:'b06', group:'BELOW THE LINE',  name:'Production Office',       amount: 24000,  suggested:true },
  { id:'b07', group:'BELOW THE LINE',  name:'Equipment & Camera',      amount: 60000,  suggested:true },
  { id:'b08', group:'BELOW THE LINE',  name:'Locations & Permits',     amount: 35000,  suggested:true },
  { id:'b09', group:'BELOW THE LINE',  name:'Art, Wardrobe, Makeup',   amount: 42000,  suggested:true },
  /* POST-PRODUCTION */
  { id:'b10', group:'POST-PRODUCTION', name:'Editorial & Sound',       amount: 48000,  suggested:true },
  { id:'b11', group:'POST-PRODUCTION', name:'VFX & Color',             amount: 32000,  suggested:true },
  { id:'b12', group:'POST-PRODUCTION', name:'Music & Score',           amount: 26000,  suggested:true },
  /* OTHER */
  { id:'b13', group:'OTHER',           name:'Insurance & Legal',       amount: 18000,  suggested:true },
  { id:'b14', group:'OTHER',           name:'Festivals & Distribution',amount: 22000,  suggested:true },
  { id:'b15', group:'OTHER',           name:'Contingency (10%)',       amount: 54000,  suggested:true },
];

const BUDGET_COMPS = [
  { title:'Manchester by the Sea (2016)', budget:'$8.5M', boxOffice:'$78.7M', stage:'comp' },
  { title:'The Florida Project (2017)',    budget:'$2.0M', boxOffice:'$11.0M', stage:'comp' },
  { title:'Sound of Metal (2019)',         budget:'$5.4M', boxOffice:'$1.2M',  stage:'comp' },
  { title:'A Real Pain (2024)',            budget:'$3.0M', boxOffice:'$9.9M',  stage:'comp' },
  { title:'Aftersun (2022)',               budget:'$2.5M', boxOffice:'$8.2M',  stage:'comp' },
];

const usd = (n) => n.toLocaleString('en-US', { style:'currency', currency:'USD', maximumFractionDigits: 0 });

/* ---------- Left: Sections + summary ---------- */
const BudgetSectionsPanel = ({ active, setActive, total, target, raised }) => {
  const tier = total < 500000 ? 'MICRO' : total < 1500000 ? 'INDIE' : total < 5000000 ? 'BOUTIQUE' : 'STUDIO';
  return (
    <React.Fragment>
      <div style={{ padding:'12px 14px 10px', borderBottom:'1px solid var(--line-1)', flexShrink:0 }}>
        <div style={{fontSize:9.5, letterSpacing:'.14em', textTransform:'uppercase', color:'var(--text-3)', fontFamily:'var(--font-mono)', marginBottom:4}}>Total Budget</div>
        <div style={{ display:'flex', alignItems:'baseline', gap:6 }}>
          <span style={{ fontSize:24, fontFamily:'Georgia, serif', fontWeight:700, color:'var(--accent)' }}>{usd(total)}</span>
        </div>
        <div style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-3)', marginTop:4, letterSpacing:'.06em' }}>{tier} TIER \u00b7 USD</div>
        <div className="bar" style={{ height:5, background:'var(--bg-3)', borderRadius:2, overflow:'hidden', marginTop:10 }}>
          <span style={{ display:'block', width: Math.min(100, (raised/total)*100) + '%', height:'100%', background:'var(--ok)' }}/>
        </div>
        <div style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text-3)', marginTop:4 }}>
          <span style={{color:'var(--ok)'}}>{usd(raised)}</span> raised \u00b7 {Math.round((raised/total)*100)}% to budget
        </div>
      </div>
      <div style={{flex:1, overflowY:'auto', padding:'6px 0'}}>
        {BUDGET_SECTIONS.map(s => (
          <button key={s.id} className={`cat-row ${active===s.id?'active':''}`} onClick={()=>setActive(s.id)}>
            <span className="ic"><Icon name={s.icon} size={14}/></span>
            <span className="name">{s.name}</span>
          </button>
        ))}
      </div>
      <div style={{ padding:'10px 12px', borderTop:'1px solid var(--line-1)', flexShrink:0 }}>
        <button className="btn primary" style={{width:'100%'}}><Icon name="folder" size={11}/> Download .xlsx</button>
        <div style={{ fontSize:10, color:'var(--text-3)', textAlign:'center', marginTop:6, fontFamily:'var(--font-mono)', letterSpacing:'.08em' }}>Top Sheet + 60-line Detailed Budget</div>
      </div>
    </React.Fragment>
  );
};

/* ---------- Main: Top Sheet ---------- */
const BudgetTopSheet = ({ lines, populating, populatingIdx, onAutoPopulate, onEdit, onReset }) => {
  const total = lines.reduce((a,l) => a + (l.amount || 0), 0);
  const groups = ['ABOVE THE LINE', 'BELOW THE LINE', 'POST-PRODUCTION', 'OTHER'];
  return (
    <div className="invest-detail" style={{padding:0}}>
      <div className="budget-head">
        <div>
          <div className="budget-title">Mandatory Reporter \u2014 Top Sheet</div>
          <div className="budget-sub">USD \u00b7 Editable. Subtotals and totals update live. Soft \u201CWarren-suggested\u201D chips disappear when you edit a row.</div>
        </div>
        <div style={{display:'flex', gap:6}}>
          <button className="btn" onClick={onReset}><Icon name="undock" size={11}/> Reset</button>
          <button className="btn primary" onClick={onAutoPopulate} disabled={populating}>
            <Icon name="sparkle" size={11}/> {populating ? `Populating\u2026 ${populatingIdx + 1}/${BUDGET_LINES.length}` : 'Auto-Populate (Warren)'}
          </button>
        </div>
      </div>

      <div className="budget-explainer">
        <strong>How this works:</strong> Tap <em>Auto-Populate</em> and Warren reads your project \u2014 genre, scope, comps, your stated budget tier \u2014 then proposes a dollar amount for each of the twelve standard line items. Every estimate is yours to override. The downloaded .xlsx includes a full Detailed Budget sheet with sixty-plus sub-line items if you want to grow this into a real shooting budget.
      </div>

      <div className="budget-table">
        <div className="bt-head">
          <span>LINE ITEM</span>
          <span style={{ textAlign:'right' }}>AMOUNT (USD)</span>
          <span style={{ textAlign:'right' }}>% OF TOTAL</span>
          <span/>
        </div>
        {groups.map(g => {
          const groupLines = lines.filter(l => l.group === g);
          const subtotal = groupLines.reduce((a,l) => a + (l.amount || 0), 0);
          return (
            <React.Fragment key={g}>
              <div className="bt-group">{g}</div>
              {groupLines.map(l => {
                const idx = lines.findIndex(x => x.id === l.id);
                const active = populating && populatingIdx === idx;
                const filled = !populating || populatingIdx >= idx;
                return (
                  <div key={l.id} className={`bt-row ${active?'animating':''} ${l.suggested && filled ? 'suggested' : ''}`}>
                    <span className="bt-name">
                      {l.name}
                      {l.suggested && filled && <span className="warren-chip">WARREN-SUGGESTED</span>}
                    </span>
                    <span className="bt-amount">
                      {!filled ? <span style={{color:'var(--text-3)', fontFamily:'var(--font-mono)'}}>—</span> : (
                        <input className="bt-input" type="text" value={l.amount ? l.amount.toLocaleString() : ''} onChange={(e)=>onEdit(l.id, parseInt(e.target.value.replace(/[^0-9]/g,'') || '0', 10))} />
                      )}
                    </span>
                    <span className="bt-pct">{filled && total ? ((l.amount/total)*100).toFixed(1) + '%' : '—'}</span>
                    <span className="bt-tool">
                      <button title="Notes"><Icon name="script" size={11}/></button>
                      <button title="Comp range"><Icon name="film" size={11}/></button>
                    </span>
                  </div>
                );
              })}
              <div className="bt-subtotal">
                <span>Subtotal \u2014 {g}</span>
                <span style={{textAlign:'right'}}>{usd(subtotal)}</span>
                <span style={{textAlign:'right'}}>{total ? ((subtotal/total)*100).toFixed(1) + '%' : '—'}</span>
                <span/>
              </div>
            </React.Fragment>
          );
        })}
        <div className="bt-total">
          <span>TOTAL BUDGET</span>
          <span style={{textAlign:'right'}}>{usd(total)}</span>
          <span style={{textAlign:'right'}}>100%</span>
          <span/>
        </div>
      </div>
    </div>
  );
};

/* ---------- Right: Warren coach + comps ---------- */
const BudgetCoach = ({ tier, total, onAutoPopulate, populating }) => {
  return (
    <div className="insp" style={{ padding: '12px 14px 16px' }}>
      <div className="evie-head" style={{ marginBottom: 6 }}>
        <div className="evie-avt">W</div>
        <div>
          <div className="evie-name">Warren</div>
          <div className="evie-mode"><span className="d"/>{populating ? 'POPULATING\u2026' : 'READY \u00b7 BUDGET COACH'}</div>
        </div>
      </div>

      <div style={{ fontSize:11.5, color:'var(--text-2)', lineHeight:1.55 }}>
        I read your project as <strong style={{color:'var(--accent)'}}>{tier}</strong> tier \u2014 single-location drama, 4-week shoot, SAG modified low, 6-person above-the-line. Here\u2019s a defensible starting point.
      </div>

      <button className="btn primary" style={{ width:'100%' }} onClick={onAutoPopulate} disabled={populating}>
        <Icon name="sparkle" size={11}/> {populating ? 'Populating\u2026' : 'Auto-Populate Budget'}
      </button>

      <div style={{ borderTop:'1px solid var(--line-1)', paddingTop:10 }}>
        <div style={{fontSize:9.5, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'.08em', marginBottom:6, fontFamily:'var(--font-mono)'}}>Comparable Budgets</div>
        {BUDGET_COMPS.map((c, i) => (
          <div key={i} className="comp-row">
            <div>
              <div className="comp-title">{c.title}</div>
              <div className="comp-meta">Budget {c.budget} \u00b7 BO {c.boxOffice}</div>
            </div>
            <button className="btn" style={{padding:'4px 8px', fontSize:10}}><Icon name="folder" size={10}/></button>
          </div>
        ))}
      </div>

      <div style={{ borderTop:'1px solid var(--line-1)', paddingTop:10 }}>
        <div style={{fontSize:9.5, color:'var(--text-3)', textTransform:'uppercase', letterSpacing:'.08em', marginBottom:6, fontFamily:'var(--font-mono)'}}>Sanity Checks</div>
        <div style={{display:'flex', flexDirection:'column', gap:5, fontSize:11, color:'var(--text-2)'}}>
          <div style={{display:'flex', gap:8}}>
            <span style={{ color:'var(--ok)', flexShrink:0 }}><Icon name="check" size={11}/></span>
            <span>Above-the-line is 34.5% of total \u2014 within indie norm (30\u201340%).</span>
          </div>
          <div style={{display:'flex', gap:8}}>
            <span style={{ color:'var(--ok)', flexShrink:0 }}><Icon name="check" size={11}/></span>
            <span>Crew at 21.8% is reasonable for a 24-day shoot.</span>
          </div>
          <div style={{display:'flex', gap:8}}>
            <span style={{ color:'var(--accent)', flexShrink:0 }}><Icon name="star" size={11}/></span>
            <span>Consider raising contingency from 10% to 12% given location count.</span>
          </div>
        </div>
      </div>
    </div>
  );
};

Object.assign(window, { BudgetSectionsPanel, BudgetTopSheet, BudgetCoach, BUDGET_SECTIONS, BUDGET_LINES, BUDGET_COMPS, usd });
