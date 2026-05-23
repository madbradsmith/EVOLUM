// editor-play.jsx — full-fidelity Play tab.
// Mounts EDITOR_PREVIEW in mode='play' on its own canvas, adds HUD chrome.

const { useEffect, useRef, useState } = React;

function PlayTab() {
  const ref = useRef(null);
  const [mounted, setMounted] = useState(false);
  const [camMode, setCamMode] = useState('top');
  const [audioOn, setAudioOn] = useState(false);
  const [recording, setRecording] = useState(false);
  const [showMobileJoy, setShowMobileJoy] = useState(window.EDITOR_PREVIEW && window.EDITOR_PREVIEW.IS_MOBILE);

  useEffect(() => {
    if (!ref.current) return;
    window.EDITOR_PREVIEW.mount(ref.current, { mode: 'play' });
    setMounted(true);
    return () => {
      try { window.EDITOR_PREVIEW.unmount(); } catch (e) {}
    };
  }, []);

  const enterAudio = () => {
    window.EDITOR_PREVIEW.unlockAudioOnGesture();
    setAudioOn(true);
  };
  const switchCam = (m) => {
    window.EDITOR_PREVIEW.setCameraMode(m);
    setCamMode(m);
  };
  const toggleRec = () => {
    if (recording) {
      window.EDITOR_PREVIEW.exportRecording();
      window.EDITOR_PREVIEW.stopRecording();
      setRecording(false);
    } else {
      window.EDITOR_PREVIEW.startRecording();
      setRecording(true);
    }
  };

  return (
    <div className="play-host">
      <canvas ref={ref} id="playCanvas"></canvas>

      <div className="play-overlay">
        <span className="live">● LIVE</span> &nbsp;·&nbsp; play mode
      </div>

      <div style={{ position: 'absolute', top: 12, right: 12, display: 'flex', gap: 6, zIndex: 6 }}>
        <button className={'btn ' + (camMode === 'top' ? 'primary' : '')}
          onClick={() => switchCam('top')}>TOP DOWN</button>
        <button className={'btn ' + (camMode === 'fly' ? 'primary' : '')}
          onClick={() => switchCam('fly')}>FREE FLY</button>
        <button className={'btn ' + (recording ? 'warn' : '')} onClick={toggleRec}>
          {recording ? '■ STOP REC' : '● REC'}
        </button>
        {!audioOn && (
          <button className="btn primary" onClick={enterAudio}>♪ AUDIO ON</button>
        )}
      </div>

      <div style={{ position: 'absolute', bottom: 12, left: 12, zIndex: 5,
        fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 9.5,
        color: 'rgba(184,196,224,0.5)', letterSpacing: '0.06em',
        textTransform: 'uppercase', lineHeight: 1.6 }} className="play-controls-hint">
        FREE FLY: WASD walk · mouse drag look · push to a wall to reveal the egg
      </div>

      {/* Boundary-egg HUD popup */}
      <div id="rippleHud" className="ripple-hud">
        <div className="top">·· STARGATE BOUNDARY ··</div>
        <div className="face">·</div>
        <div className="body">A green terminal flickers on at the wall.<br/>The tribe finder is listening.</div>
        <div className="small">click the panel in-world to follow the signal</div>
      </div>

      {showMobileJoy && camMode === 'fly' && <MobileJoystick />}
    </div>
  );
}

// ─── Mobile virtual joystick ───
function MobileJoystick() {
  // left zone = move (WASD via keyboard events), right zone = look (mouse move)
  const leftRef = useRef(null);
  const rightRef = useRef(null);
  const [leftPos, setLeftPos] = useState({ x: 0, y: 0 });
  const [rightActive, setRightActive] = useState(false);
  const keysRef = useRef({ w: false, a: false, s: false, d: false });

  useEffect(() => {
    const setKey = (k, v) => {
      if (keysRef.current[k] === v) return;
      keysRef.current[k] = v;
      const code = { w: 'KeyW', a: 'KeyA', s: 'KeyS', d: 'KeyD' }[k];
      const which = { w: 87, a: 65, s: 83, d: 68 }[k];
      const ev = new KeyboardEvent(v ? 'keydown' : 'keyup', { code, key: k, keyCode: which, which });
      window.dispatchEvent(ev);
    };

    let activeLeft = null;
    const onDown = (zone) => (ev) => {
      const t = ev.touches ? ev.touches[0] : ev;
      const r = (zone === 'left' ? leftRef : rightRef).current.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      if (zone === 'left') activeLeft = { cx, cy, id: ev.pointerId || 0 };
      else setRightActive(true);
      handleMove(zone, t);
    };
    const handleMove = (zone, t) => {
      const r = (zone === 'left' ? leftRef : rightRef).current.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const dx = (t.clientX - cx), dy = (t.clientY - cy);
      const max = r.width / 2;
      const len = Math.min(max, Math.hypot(dx, dy));
      const a = Math.atan2(dy, dx);
      const nx = Math.cos(a) * len, ny = Math.sin(a) * len;
      if (zone === 'left') {
        setLeftPos({ x: nx, y: ny });
        const u = len / max;
        setKey('w', ny < -max * 0.3 * Math.sign(1));
        setKey('s', ny > max * 0.3);
        setKey('a', nx < -max * 0.3);
        setKey('d', nx > max * 0.3);
      } else {
        // synthesize mousemove for look
        const ev = new MouseEvent('pointermove', { clientX: t.clientX, clientY: t.clientY, bubbles: true });
        document.elementFromPoint(t.clientX, t.clientY) && document.elementFromPoint(t.clientX, t.clientY).dispatchEvent(ev);
      }
    };
    const onMove = (ev) => {
      if (activeLeft) {
        const t = ev.touches ? ev.touches[0] : ev;
        handleMove('left', t);
      }
    };
    const onUp = () => {
      activeLeft = null;
      setLeftPos({ x: 0, y: 0 });
      ['w','a','s','d'].forEach(k => setKey(k, false));
      setRightActive(false);
    };

    const lEl = leftRef.current, rEl = rightRef.current;
    if (!lEl || !rEl) return;
    lEl.addEventListener('pointerdown', onDown('left'));
    rEl.addEventListener('pointerdown', onDown('right'));
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      lEl.removeEventListener('pointerdown', onDown('left'));
      rEl.removeEventListener('pointerdown', onDown('right'));
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, []);

  return (
    <>
      <div ref={leftRef} style={joyZone('left')}>
        <div style={joyDot(leftPos.x, leftPos.y)} />
      </div>
      <div ref={rightRef} style={joyZone('right')}>
        <div style={{ ...joyDot(0, 0), opacity: rightActive ? 0.8 : 0.4 }} />
      </div>
    </>
  );
}
const joyZone = (side) => ({
  position: 'absolute',
  bottom: 24,
  [side]: 24,
  width: 110, height: 110,
  borderRadius: '50%',
  background: 'rgba(14,16,24,0.6)',
  border: '1px solid rgba(184,196,224,0.18)',
  touchAction: 'none',
  zIndex: 30,
});
const joyDot = (x, y) => ({
  position: 'absolute',
  left: 'calc(50% - 14px)',
  top: 'calc(50% - 14px)',
  width: 28, height: 28,
  borderRadius: '50%',
  background: 'rgba(70,217,197,0.5)',
  transform: `translate(${x}px, ${y}px)`,
  pointerEvents: 'none',
});

window.PlayTab = PlayTab;
