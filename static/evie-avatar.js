// evie-avatar.js — Evie's shape-shifting SVG avatar. No dependencies.
// Usage: EvieAvatar.render(container, { phase, mood, size, ink, accent, glow })
// phase: 'idea' | 'script' | 'pitch' | 'invest'
// mood:  'idle' | 'thinking' | 'excited' | 'listening'
// size:  px (number). Default 40.

(function() {

const CSS = `
@keyframes _evBreathe { 0%,100%{transform:scale(1)} 50%{transform:scale(1.04)} }
@keyframes _evSpin    { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
@keyframes _evWobble  { 0%,100%{transform:rotate(-3deg)} 50%{transform:rotate(3deg)} }
@keyframes _evBob     { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-2px)} }
@keyframes _evBlink   { 0%,90%,100%{transform:scaleY(1)} 95%{transform:scaleY(.08)} }
@keyframes _evDart    { 0%,100%{transform:translate(0,0)} 25%{transform:translate(2px,-1px)} 50%{transform:translate(-1px,1px)} 75%{transform:translate(1px,2px)} }
@keyframes _evRay     { 0%,100%{opacity:.35;transform:scale(1)} 50%{opacity:1;transform:scale(1.08)} }
@keyframes _evOrb1    { from{transform:rotate(0deg) translateX(var(--ev-orbit)) rotate(0deg)} to{transform:rotate(360deg) translateX(var(--ev-orbit)) rotate(-360deg)} }
@keyframes _evOrb2    { from{transform:rotate(120deg) translateX(var(--ev-orbit)) rotate(-120deg)} to{transform:rotate(480deg) translateX(var(--ev-orbit)) rotate(-480deg)} }
@keyframes _evOrb3    { from{transform:rotate(240deg) translateX(var(--ev-orbit)) rotate(-240deg)} to{transform:rotate(600deg) translateX(var(--ev-orbit)) rotate(-600deg)} }
@keyframes _evStack   { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-1px)} }
._evBreath{animation:_evBreathe 3.2s ease-in-out infinite;transform-origin:center}
._evWob   {animation:_evWobble 2.6s ease-in-out infinite;transform-origin:center}
._evBob   {animation:_evBob 2.4s ease-in-out infinite}
._evBlink {animation:_evBlink 4s steps(8) infinite;transform-origin:center;transform-box:fill-box}
._evDart  {animation:_evDart .8s ease-in-out infinite}
._evRay   {animation:_evRay 2.4s ease-in-out infinite;transform-origin:center;transform-box:fill-box}
._evSpin  {animation:_evSpin 18s linear infinite;transform-origin:center;transform-box:fill-box}
._evOrb1  {animation:_evOrb1 4s linear infinite;transform-origin:center;transform-box:fill-box}
._evOrb2  {animation:_evOrb2 4s linear infinite;transform-origin:center;transform-box:fill-box}
._evOrb3  {animation:_evOrb3 4s linear infinite;transform-origin:center;transform-box:fill-box}
._evStack {animation:_evStack 2.6s ease-in-out infinite}
`;

function _injectCSS() {
    if (document.getElementById('_ev-avatar-css')) return;
    const s = document.createElement('style');
    s.id = '_ev-avatar-css';
    s.textContent = CSS;
    document.head.appendChild(s);
}

function _svg(size, wrapClass, inner) {
    return `<svg width="${size}" height="${size}" viewBox="0 0 60 60" class="${wrapClass}" style="overflow:visible;display:block;">${inner}</svg>`;
}

function _phaseIdea(ink, accent, glow, mood) {
    const exc = mood === 'excited';
    const think = mood === 'thinking';
    const smile = exc
        ? `<path d="M26 33 Q30 36 34 33" fill="none" stroke="${ink}" stroke-width="1.4" stroke-linecap="round"/>`
        : `<path d="M27 33 L33 33" stroke="${ink}" stroke-width="1.4" stroke-linecap="round"/>`;
    return `<g style="--ev-orbit:17px">
  <circle cx="30" cy="30" r="22" fill="${glow}" opacity="${think ? .5 : .3}"/>
  <g class="_evBreath">
    <circle cx="30" cy="30" r="9" fill="${accent}"/>
    <circle cx="30" cy="30" r="9" fill="none" stroke="${ink}" stroke-width="1.5"/>
    <ellipse class="_evBlink" cx="27" cy="29" rx="1.4" ry="${exc ? 2 : 1.6}" fill="${ink}"/>
    <ellipse class="_evBlink" cx="33" cy="29" rx="1.4" ry="${exc ? 2 : 1.6}" fill="${ink}"/>
    ${smile}
  </g>
  <circle class="_evOrb1" cx="30" cy="30" r="2.2" fill="${ink}"/>
  <circle class="_evOrb2" cx="30" cy="30" r="2.2" fill="${accent}"/>
  <circle class="_evOrb3" cx="30" cy="30" r="2.2" fill="${ink}"/>
  <path d="M30 19 q-2 -3 -1 -6" fill="none" stroke="${ink}" stroke-width="1.4" stroke-linecap="round"/>
  <circle cx="29" cy="13" r="1.4" fill="${accent}"/>
</g>`;
}

function _phaseScript(ink, accent, glow, mood) {
    const exc = mood === 'excited';
    return `<g>
  <rect x="10" y="11" width="40" height="38" rx="3" fill="${glow}"/>
  <rect x="10" y="11" width="40" height="38" rx="3" fill="none" stroke="${ink}" stroke-width="1.4"/>
  <g stroke="${ink}" stroke-width="1.4" stroke-linecap="round">
    <line class="_evStack" x1="15" y1="20" x2="38" y2="20"/>
    <line x1="15" y1="26" x2="42" y2="26"/>
    <line class="_evStack" x1="15" y1="32" x2="34" y2="32" style="animation-delay:.3s"/>
    <line x1="15" y1="38" x2="40" y2="38"/>
    <line x1="15" y1="44" x2="28" y2="44" stroke="${accent}" stroke-width="2"/>
  </g>
  <g class="_evBob">
    <rect x="36" y="6" width="14" height="10" rx="2" fill="${accent}"/>
    <rect x="36" y="6" width="14" height="10" rx="2" fill="none" stroke="${ink}" stroke-width="1.3"/>
    <ellipse class="_evBlink" cx="40" cy="11" rx="1.2" ry="${exc ? 1.8 : 1.4}" fill="${ink}"/>
    <ellipse class="_evBlink" cx="46" cy="11" rx="1.2" ry="${exc ? 1.8 : 1.4}" fill="${ink}"/>
  </g>
</g>`;
}

function _phasePitch(ink, accent, glow, mood) {
    const exc = mood === 'excited';
    const rays = [0,45,90,135,180,225,270,315].map((a,i) =>
        `<g class="_evRay" style="animation-delay:${i*.1}s;transform-origin:30px 30px" transform="rotate(${a} 30 30)">
      <path d="M30 6 L31.6 14 L28.4 14 Z" fill="${accent}"/>
    </g>`
    ).join('');
    return `<g>
  <circle cx="30" cy="30" r="26" fill="${glow}" opacity=".55"/>
  <g class="_evSpin">${rays}</g>
  <g class="_evBreath">
    <circle cx="30" cy="30" r="11" fill="${ink}"/>
    <circle cx="30" cy="30" r="11" fill="none" stroke="${accent}" stroke-width="1.4"/>
    <ellipse class="_evBlink" cx="26.5" cy="29" rx="1.3" ry="${exc ? 2.2 : 1.6}" fill="${accent}"/>
    <ellipse class="_evBlink" cx="33.5" cy="29" rx="1.3" ry="${exc ? 2.2 : 1.6}" fill="${accent}"/>
    <path d="M26 33.5 Q30 36 34 33.5" fill="none" stroke="${accent}" stroke-width="1.4" stroke-linecap="round"/>
  </g>
</g>`;
}

function _phaseInvest(ink, accent, glow, mood) {
    const exc = mood === 'excited';
    return `<g>
  <ellipse cx="30" cy="44" rx="22" ry="6" fill="${glow}" opacity=".5"/>
  <ellipse cx="30" cy="46" rx="18" ry="5" fill="${ink}"/>
  <rect x="12" y="38" width="36" height="8" fill="${ink}"/>
  <ellipse cx="30" cy="38" rx="18" ry="5" fill="${accent}" stroke="${ink}" stroke-width="1.4"/>
  <ellipse cx="30" cy="36" rx="14" ry="4" fill="${ink}"/>
  <rect x="16" y="29" width="28" height="7" fill="${ink}"/>
  <ellipse cx="30" cy="29" rx="14" ry="4" fill="${accent}" stroke="${ink}" stroke-width="1.4"/>
  <g class="_evBob">
    <ellipse cx="30" cy="22" rx="11" ry="3.5" fill="${ink}"/>
    <rect x="19" y="14" width="22" height="8" fill="${ink}"/>
    <ellipse cx="30" cy="14" rx="11" ry="3.5" fill="${accent}" stroke="${ink}" stroke-width="1.4"/>
    <ellipse class="_evBlink" cx="26.5" cy="18" rx="1.3" ry="${exc ? 2 : 1.5}" fill="${ink}"/>
    <ellipse class="_evBlink" cx="33.5" cy="18" rx="1.3" ry="${exc ? 2 : 1.5}" fill="${ink}"/>
  </g>
  <text x="30" y="44" text-anchor="middle" font-size="6" font-family="monospace" fill="${ink}" font-weight="700">$</text>
</g>`;
}

const PHASES = { idea: _phaseIdea, script: _phaseScript, pitch: _phasePitch, invest: _phaseInvest };
const MOOD_CLASS = { excited: '_evWob', listening: '_evBob', thinking: '_evDart', idle: '' };

window.EvieAvatar = {
    render(container, opts) {
        _injectCSS();
        opts = opts || {};
        const phase  = opts.phase  || 'idea';
        const mood   = opts.mood   || 'idle';
        const size   = opts.size   || 40;
        const ink    = opts.ink    || '#1c1814';
        const accent = opts.accent || '#c5562a';
        const glow   = opts.glow   || 'rgba(197,86,42,.18)';

        const shapeFn = PHASES[phase] || _phaseIdea;
        const inner   = shapeFn(ink, accent, glow, mood);
        const wClass  = MOOD_CLASS[mood] || '';
        const el = typeof container === 'string'
            ? document.getElementById(container)
            : container;
        if (!el) return;
        el.innerHTML = _svg(size, wClass, inner);
    },

    // Convenience: drop an avatar inline next to a DOM node
    inline(size, phase, mood, ink, accent, glow) {
        _injectCSS();
        const shapeFn = PHASES[phase || 'idea'] || _phaseIdea;
        const wClass  = MOOD_CLASS[mood || 'idle'] || '';
        ink    = ink    || '#1c1814';
        accent = accent || '#c5562a';
        glow   = glow   || 'rgba(197,86,42,.18)';
        return _svg(size || 40, wClass, shapeFn(ink, accent, glow, mood || 'idle'));
    }
};

})();
