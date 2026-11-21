// Camera and pointer for the recording. Injected into the page; Python calls window.__cam.*
(() => {
  if (window.__cam) return;
  const W = innerWidth, H = innerHeight, body = document.body;
  const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const norm = s => (s || '').replace(/\s+/g, ' ').trim().toUpperCase();
  // A transformed body becomes the containing block for the app's absolute and fixed layers,
  // so it must span the viewport (Streamlit leaves it 0px tall).
  Object.assign(body.style, {transformOrigin: '0 0', width: W + 'px', height: H + 'px', overflow: 'hidden'});
  // k: zoom; t: translate; the view is body transformed by translate(t) scale(k).
  const st = {k: 1, tx: 0, ty: 0};
  const scroller = () => document.querySelector('[data-testid=stMain]') || document.scrollingElement;
  const apply = (k, vx, vy) => {  // vx, vy: layout point to put at the screen centre
    st.k = k;
    st.tx = clamp(W / 2 - k * vx, W - k * W, 0);
    st.ty = clamp(H / 2 - k * vy, H - k * H, 0);
    body.style.transform = k <= 1.0001 ? '' : `translate(${st.tx}px,${st.ty}px) scale(${k})`;
  };
  const view = () => ({x: (W / 2 - st.tx) / st.k, y: (H / 2 - st.ty) / st.k});
  const CANDIDATES = '.ln, pre, summary, [data-testid=stPopoverButton], [data-testid=stTextInput], ' +
    '[data-testid=stSelectbox], [data-testid=stExpander], [data-testid=stDataFrame], [data-testid=stButton], [data-testid=stCaptionContainer], ' +
    '#card [data-cam]';
  // Elements a spec names: {sel} | {a, n} (a and the n candidates after it) | {a, b}.
  const find = spec => {
    if (spec.sel) { const e = document.querySelector(spec.sel); return e ? [e] : null; }
    const all = [...document.querySelectorAll(CANDIDATES)].filter(e => e.getClientRects().length);
    const i = all.findIndex(e => norm(e.innerText).includes(norm(spec.a)));
    if (i < 0) return null;
    if (spec.b) { const j = all.findIndex((e, j) => j > i && norm(e.innerText).includes(norm(spec.b))); return j < 0 ? null : [all[i], all[j]]; }
    return all.slice(i, i + (spec.n || 0) + 1);
  };
  const layoutRect = els => {  // union of the elements' rects, undoing the current camera
    const rs = els.map(e => e.getBoundingClientRect());
    const L = Math.min(...rs.map(r => r.left)), R = Math.max(...rs.map(r => r.right));
    const T = Math.min(...rs.map(r => r.top)), B = Math.max(...rs.map(r => r.bottom));
    return {l: (L - st.tx) / st.k, r: (R - st.tx) / st.k, t: (T - st.ty) / st.k, b: (B - st.ty) / st.k};
  };
  let gen = 0, busy = false;
  const animate = (dur, step) => {
    const g = ++gen, t0 = performance.now(); busy = true;
    const f = now => { if (g !== gen) return; const p = Math.min(1, (now - t0) / dur); step(ease(p));
      if (p < 1) requestAnimationFrame(f); else busy = false; };
    requestAnimationFrame(f);
  };
  // Glide the camera onto a spec. {full: true} zooms out; {top: true} also scrolls to the top.
  // Returns where spec.focus (or the spec's first element) will sit on screen once the glide ends.
  const cam = spec => {
    const s = scroller(), s0 = s.scrollTop, k0 = st.k, v0 = view(), dur = spec.dur || 900;
    let s1 = s0, k1 = 1, cx = W / 2, cy = H / 2, els = null;
    if (!spec.full) {
      els = find(spec);
      if (!els) return false;
      const r = layoutRect(els), pad = spec.pad ?? 24;
      if (s.contains(els[0])) s1 = clamp(s0 + (r.t + r.b) / 2 - H / 2, 0, s.scrollHeight - s.clientHeight);
      cx = (r.l + r.r) / 2; cy = (r.t + r.b) / 2 - (s1 - s0);
      k1 = clamp(Math.min(W * .86 / (r.r - r.l + 2 * pad), H * .8 / (r.b - r.t + 2 * pad)), 1, spec.zoom || 1.8);
    } else if (spec.top) s1 = 0;
    // Interpolate the view centre in page space, so scroll and zoom move as one glide.
    const y0 = v0.y + s0, y1 = cy + s1;
    animate(dur, e => {
      const sc = s0 + (s1 - s0) * e; s.scrollTop = sc;
      apply(k0 * Math.pow(k1 / k0, e), v0.x + (cx - v0.x) * e, y0 + (y1 - y0) * e - sc);
    });
    const fe = spec.focus ? document.querySelector(spec.focus) : els && els[0];
    if (!fe) return {};
    const r = layoutRect([fe]), dy = s.contains(fe) ? s1 - s0 : 0;
    const tx1 = clamp(W / 2 - k1 * cx, W - k1 * W, 0), ty1 = clamp(H / 2 - k1 * cy, H - k1 * H, 0);
    return {x: k1 * (r.l + r.r) / 2 + tx1, y: k1 * ((r.t + r.b) / 2 - dy) + ty1};
  };
  // The visible pointer lives on <html>, outside the zoomed body, so it stays screen-sized.
  const ptr = document.createElement('div');
  ptr.innerHTML = '<svg width="34" height="34" viewBox="0 0 24 24"><path d="M4 2l15 11.5-6.6 1 3.9 7.6-3 1.5-3.9-7.7L4 21z" fill="#1d2f2a" stroke="#fdfcf7" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  Object.assign(ptr.style, {position: 'fixed', left: '0', top: '0', zIndex: 2147483647, pointerEvents: 'none',
    transform: `translate(${W + 40}px, ${H * .7}px)`, filter: 'drop-shadow(2px 3px 2px rgba(0,0,0,.25))'});
  document.documentElement.appendChild(ptr);
  const p = {x: W + 40, y: H * .7};
  const glide = (x, y, dur) => new Promise(res => {
    const x0 = p.x, y0 = p.y, t0 = performance.now();
    const f = now => { const e = ease(Math.min(1, (now - t0) / dur)); p.x = x0 + (x - x0) * e; p.y = y0 + (y - y0) * e;
      ptr.style.transform = `translate(${p.x - 4}px, ${p.y - 2}px)`; e < 1 ? requestAnimationFrame(f) : res(); };
    requestAnimationFrame(f);
  });
  const press = () => ptr.animate([{scale: 1}, {scale: .82}, {scale: 1}], {duration: 220});
  window.__cam = {cam, glide, press, busy: () => busy, state: () => ({...st, scroll: scroller().scrollTop})};
})();
