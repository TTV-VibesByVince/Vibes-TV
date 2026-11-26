/* The Vibesmas Express: alerts as a holiday train (see vibesmas.py, which decides
   the cars). Used by the TV and the OBS overlay:

     Vibesmas.run(host, train, { dir: "ltr" | "rtl", sound: true, muted: false })

   host is a positioned element the train runs along the bottom of. The scene is
   drawn at 1920 wide and scaled to the host. The train takes train.seconds: a
   short one rolls in, stops for the bell and rolls out; a long one (10 gift subs)
   crawls past so every name gets its moment. Cars are SVG; their lettering stays
   readable when the train runs the other way. */
const Vibesmas = (() => {
  const W = 1920, TOP = 740, GOLDS = "#e9cf86";
  let FLIP = false, uid = 0, current = null;

  /* ── shared gradients: round boilers, metallic gold and brass, warm windows ── */
  function ensureDefs() {
    if (document.getElementById("vx-defs")) return;
    const d = document.createElement("div");
    d.innerHTML = `<svg id="vx-defs" width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
      <linearGradient id="gBoiler" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a403a"/><stop offset=".18" stop-color="#2a231f"/><stop offset=".55" stop-color="#120e0c"/><stop offset="1" stop-color="#050403"/></linearGradient>
      <radialGradient id="gSmokebox" cx=".4" cy=".35" r=".8"><stop offset="0" stop-color="#3a322d"/><stop offset="1" stop-color="#050404"/></radialGradient>
      <linearGradient id="gStack" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#0a0807"/><stop offset=".35" stop-color="#3f3631"/><stop offset="1" stop-color="#100c0a"/></linearGradient>
      <linearGradient id="gBrass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbe7a8"/><stop offset=".4" stop-color="#d4ac52"/><stop offset=".72" stop-color="#8f6a22"/><stop offset="1" stop-color="#c9a24b"/></linearGradient>
      <linearGradient id="gBrassV" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8f6a22"/><stop offset=".45" stop-color="#fbe7a8"/><stop offset="1" stop-color="#8f6a22"/></linearGradient>
      <linearGradient id="gGold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff0b8"/><stop offset=".45" stop-color="#e2bd62"/><stop offset=".75" stop-color="#9c7426"/><stop offset="1" stop-color="#e9cf86"/></linearGradient>
      <linearGradient id="gGoldText" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff4c8"/><stop offset=".5" stop-color="#f0cf74"/><stop offset="1" stop-color="#c0922f"/></linearGradient>
      <linearGradient id="gBurg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b42a40"/><stop offset=".15" stop-color="#9b1f33"/><stop offset=".6" stop-color="#74142a"/><stop offset="1" stop-color="#3f0812"/></linearGradient>
      <linearGradient id="gRed" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d23a3a"/><stop offset=".6" stop-color="#a51f2a"/><stop offset="1" stop-color="#5e0d14"/></linearGradient>
      <linearGradient id="gBlackCar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a302a"/><stop offset=".5" stop-color="#1a1411"/><stop offset="1" stop-color="#080605"/></linearGradient>
      <linearGradient id="gPlate" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6e1424"/><stop offset="1" stop-color="#3c0811"/></linearGradient>
      <linearGradient id="gRoof" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a403a"/><stop offset=".3" stop-color="#221c18"/><stop offset="1" stop-color="#080605"/></linearGradient>
      <linearGradient id="gInk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2e2723"/><stop offset="1" stop-color="#070605"/></linearGradient>
      <radialGradient id="gWin" cx=".5" cy=".55" r=".75"><stop offset="0" stop-color="#fff4cf"/><stop offset=".45" stop-color="#ffd27a"/><stop offset="1" stop-color="#c9742a"/></radialGradient>
      <radialGradient id="gLamp"><stop offset="0" stop-color="#ffffff"/><stop offset=".5" stop-color="#fff2b0"/><stop offset="1" stop-color="#f0b648"/></radialGradient>
      <linearGradient id="gBeam" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#fff3c4" stop-opacity=".5"/><stop offset="1" stop-color="#fff3c4" stop-opacity="0"/></linearGradient>
      <radialGradient id="gWheel"><stop offset="0" stop-color="#b8303f"/><stop offset=".7" stop-color="#8b1a24"/><stop offset="1" stop-color="#4e0b14"/></radialGradient>
      <linearGradient id="gSteel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f2f0ec"/><stop offset=".5" stop-color="#a9a39a"/><stop offset="1" stop-color="#6c665e"/></linearGradient>
      <radialGradient id="gCoal" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#5a5450"/><stop offset="1" stop-color="#141210"/></radialGradient>
      <linearGradient id="gBank" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#eef3fb"/><stop offset="1" stop-color="#b9c6da"/></linearGradient>
      <filter id="fBlur" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="4"/></filter>
      <filter id="fGlow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="6"/></filter>
    </defs></svg>`;
    document.body.appendChild(d.firstChild);
    const st = document.createElement("style");
    st.textContent = `.vx-layer { position: absolute; inset: 0; overflow: hidden; pointer-events: none; z-index: 30; }
      .vx-stage { position: absolute; left: 0; bottom: 0; width: ${W}px; height: 1080px; transform-origin: 0 100%; }
      .vx-rails { position: absolute; left: 0; top: 990px; width: ${W}px; height: 90px; opacity: 0; transition: opacity .8s; }
      .vx-rails.on { opacity: 1; }
      .vx-train { position: absolute; left: 0; top: ${TOP}px; height: 260px; display: flex; align-items: flex-end; will-change: transform; }
      .vx-train svg { display: block; overflow: visible; flex: none; }
      .vx-fx { position: absolute; left: 0; top: 0; width: ${W}px; height: 1080px; }
      .vx-cin { font-family: "Cinzel", Georgia, serif; font-weight: 800; }
      .vx-out { font-family: "Outfit", system-ui, sans-serif; }
      @keyframes vxTwinkle { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
      .vx-gem { animation: vxTwinkle 1.6s ease-in-out infinite; }
      @keyframes vxGlow { 0%, 100% { opacity: .88; } 50% { opacity: 1; } }
      .vx-lit { animation: vxGlow 2.4s ease-in-out infinite; }`;
    document.head.appendChild(st);
  }

  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  /* ── the parts ── */
  function wheel(cx, cy, r, spokes = 8, driver = false) {
    const big = r > 30;
    let s = `<g class="vx-wheel" data-r="${r}" style="transform-origin:${cx}px ${cy}px"><circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#gWheel)"/>`;
    if (driver) s += `<path d="M${cx - r * .62} ${cy + r * .25} A${r * .68} ${r * .68} 0 0 0 ${cx + r * .62} ${cy + r * .25} L${cx + r * .3} ${cy + r * .12} A${r * .33} ${r * .33} 0 0 1 ${cx - r * .3} ${cy + r * .12} Z" fill="#1a0b0e" opacity=".85"/>`;
    for (let i = 0; i < spokes; i++) { const a = i / spokes * Math.PI * 2;
      s += `<line x1="${cx + Math.cos(a) * r * .22}" y1="${cy + Math.sin(a) * r * .22}" x2="${cx + Math.cos(a) * (r - 5)}" y2="${cy + Math.sin(a) * (r - 5)}" stroke="${GOLDS}" stroke-width="${big ? 3.2 : 2}" stroke-linecap="round" opacity=".9"/>`; }
    return s + `<circle cx="${cx}" cy="${cy}" r="${r - 2}" fill="none" stroke="url(#gGold)" stroke-width="${big ? 5 : 3.5}"/>
      <circle cx="${cx}" cy="${cy}" r="${r - (big ? 7 : 5)}" fill="none" stroke="#4a0c16" stroke-width="1.5" opacity=".8"/>
      <circle cx="${cx}" cy="${cy}" r="${r * .24}" fill="url(#gBrass)" stroke="#6b4c16" stroke-width="1"/><circle cx="${cx}" cy="${cy}" r="${r * .08}" fill="#3a2a0c"/></g>`;
  }
  function plate(x, y, w, h, text, size, sub) {
    return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="5" fill="url(#gPlate)" stroke="url(#gGold)" stroke-width="3"/>
      <rect x="${x + 5}" y="${y + 5}" width="${w - 10}" height="${h - 10}" rx="3" fill="none" stroke="${GOLDS}" stroke-width=".8" opacity=".6"/>
      ${[[x + 9, y + 9], [x + w - 9, y + 9], [x + 9, y + h - 9], [x + w - 9, y + h - 9]].map(([a, b]) => `<circle cx="${a}" cy="${b}" r="1.8" fill="${GOLDS}"/>`).join("")}
      <text x="${x + w / 2}" y="${y + (sub ? h * .4 : h / 2) + 1}" text-anchor="middle" dominant-baseline="middle" class="vx-cin" font-size="${size}" fill="url(#gGoldText)" stroke="#2a070d" stroke-width="2.4" paint-order="stroke" letter-spacing=".05em">${esc(text)}</text>
      ${sub ? `<text x="${x + w / 2}" y="${y + h * .75}" text-anchor="middle" dominant-baseline="middle" class="vx-out" font-size="12" font-weight="600" fill="${GOLDS}" letter-spacing=".07em">${esc(sub)}</text>` : ""}`;
  }
  const fit = (text, w, max, min = 11) => Math.max(min, Math.min(max, Math.floor(w / (Math.max(1, text.length) * .68))));
  const flourish = (x, y, w) => `<path d="M${x} ${y} c${w * .1} -9 ${w * .2} 9 ${w * .3} 0 s${w * .12} -6 ${w * .2} 0 M${x + w} ${y} c${-w * .1} -9 ${-w * .2} 9 ${-w * .3} 0 s${-w * .12} -6 ${-w * .2} 0" fill="none" stroke="url(#gGold)" stroke-width="1.6"/>`;
  const rivets = (x1, x2, y, step = 12) => { let s = ""; for (let x = x1; x <= x2; x += step) s += `<circle cx="${x}" cy="${y}" r="1.5" fill="${GOLDS}" opacity=".75"/>`; return s; };
  const shine = (x, y, w) => `<rect x="${x}" y="${y}" width="${w}" height="2.5" rx="1" fill="#fff" opacity=".16"/>`;
  const shadow = w => `<ellipse cx="${w / 2}" cy="251" rx="${w / 2 - 6}" ry="7" fill="#000" opacity=".55" filter="url(#fBlur)"/>`;
  const coupler = (x, w = 12) => `<rect x="${x}" y="210" width="${w}" height="8" rx="2" fill="url(#gInk)"/>`;
  function truck(x1, x2) {
    const m = (x1 + x2) / 2;
    return `${wheel(x1, 233, 17, 6)}${wheel(x2, 233, 17, 6)}
      <rect x="${x1 - 14}" y="222" width="${x2 - x1 + 28}" height="9" rx="4" fill="url(#gInk)" stroke="#5a4520" stroke-width="1"/>
      <rect x="${m - 8}" y="214" width="16" height="12" rx="2" fill="#2a2320"/>${[0, 4, 8].map(d => `<line x1="${m - 6}" y1="${216 + d}" x2="${m + 6}" y2="${216 + d}" stroke="#7d6a4a" stroke-width="1.5"/>`).join("")}`;
  }
  function pane(x, y, w, h) {
    return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="url(#gWin)" class="vx-lit"/>
      <rect x="${x}" y="${y}" width="${w}" height="${h * .22}" rx="2" fill="#8c2a2a" opacity=".85"/>
      <path d="M${x} ${y + h * .22} q${w * .25} ${h * .18} ${w * .5} 0 q${w * .25} ${h * .18} ${w * .5} 0" fill="#8c2a2a" opacity=".6"/>
      <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="none" stroke="url(#gGold)" stroke-width="2"/>`;
  }
  function face(who, cx, cy, r) {       // their picture in the window (kept the right way round)
    const id = "vxc" + (++uid);
    const src = typeof avatarSrc === "function" ? avatarSrc({ avatar: who.avatar, display_name: who.name }) : who.avatar;
    return `<g data-keep="${cx}"><circle cx="${cx}" cy="${cy}" r="${r + 4}" fill="url(#gGold)"/>
      <clipPath id="${id}"><circle cx="${cx}" cy="${cy}" r="${r}"/></clipPath>
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="#3a1d14"/>
      <image href="${esc(src)}" x="${cx - r}" y="${cy - r}" width="${r * 2}" height="${r * 2}" clip-path="url(#${id})" preserveAspectRatio="xMidYMid slice"/></g>`;
  }
  function svg(w, body) {
    if (FLIP) body = `<g transform="translate(${w} 0) scale(-1 1)">${body
      .replace(/<text x="([\d.]+)"/g, (m, x) => `<text transform="translate(${2 * x} 0) scale(-1 1)" x="${x}"`)
      .replace(/<g data-keep="([\d.]+)">/g, (m, x) => `<g transform="translate(${2 * x} 0) scale(-1 1)">`)}</g>`;
    return { w, html: `<svg width="${w}" height="260" viewBox="0 0 ${w} 260">${body}</svg>` };
  }

  /* ── the cars ── */
  function loco(label) {
    return svg(440, `${shadow(440)}
      <polygon points="62,92 -300,30 -300,175" fill="url(#gBeam)" class="vx-lit"/>
      <polygon points="12,250 64,250 64,198 42,198" fill="url(#gBurg)" stroke="url(#gGold)" stroke-width="2"/>
      ${[20, 30, 40, 50].map(x => `<line x1="${x}" y1="249" x2="${x + 9}" y2="201" stroke="${GOLDS}" stroke-width="1.6" opacity=".8"/>`).join("")}
      <rect x="40" y="188" width="32" height="16" rx="2" fill="url(#gBurg)" stroke="url(#gGold)" stroke-width="1.5"/>
      <rect x="70" y="190" width="62" height="36" rx="8" fill="url(#gBoiler)" stroke="#6b5326" stroke-width="1.5"/>
      <rect x="74" y="196" width="54" height="4" fill="url(#gBrass)"/><rect x="74" y="216" width="54" height="4" fill="url(#gBrass)"/>
      <rect x="66" y="104" width="240" height="90" rx="42" fill="url(#gBoiler)"/>${shine(96, 114, 190)}
      ${[110, 186, 262].map(x => `<rect x="${x}" y="104" width="8" height="90" fill="url(#gBrassV)"/>`).join("")}
      <line x1="82" y1="122" x2="300" y2="122" stroke="url(#gBrass)" stroke-width="2.2"/>
      ${[100, 160, 220, 280].map(x => `<line x1="${x}" y1="122" x2="${x}" y2="128" stroke="#c9a24b" stroke-width="2"/>`).join("")}
      <ellipse cx="68" cy="149" rx="16" ry="44" fill="url(#gSmokebox)" stroke="url(#gGold)" stroke-width="2.5"/>
      <circle cx="66" cy="149" r="10" fill="url(#gBrass)" stroke="#6b4c16" stroke-width="1"/>
      <text x="66" y="150" text-anchor="middle" dominant-baseline="middle" class="vx-cin" font-size="9" fill="#3a2a0c">25</text>
      <rect x="56" y="70" width="44" height="36" rx="5" fill="url(#gBrass)" stroke="#6b4c16" stroke-width="2"/>
      <rect x="62" y="64" width="32" height="8" rx="2" fill="url(#gBrass)" stroke="#6b4c16" stroke-width="1.5"/>
      <circle cx="58" cy="88" r="16" fill="#fff2c2" opacity=".35" filter="url(#fGlow)" class="vx-lit"/>
      <circle cx="58" cy="88" r="12" fill="url(#gLamp)" class="vx-lit"/><circle cx="58" cy="88" r="12" fill="none" stroke="#6b4c16" stroke-width="3"/>
      <polygon points="96,30 146,30 133,66 133,108 109,108 109,66" fill="url(#gStack)" stroke="#6b5326" stroke-width="1.5"/>
      <rect x="92" y="23" width="58" height="10" rx="3" fill="url(#gBrass)" stroke="#6b4c16" stroke-width="1"/>
      <rect x="106" y="92" width="30" height="6" rx="2" fill="url(#gBrass)"/>
      <path d="M178 106 q0 -30 22 -30 q22 0 22 30 Z" fill="url(#gBrass)" stroke="#6b4c16" stroke-width="1.5"/>
      <rect x="174" y="102" width="52" height="6" rx="2" fill="url(#gBrass)"/>
      <path d="M238 106 q0 -22 15 -22 q15 0 15 22 Z" fill="url(#gBrass)" stroke="#6b4c16" stroke-width="1.5"/>
      <path d="M150 104 l4 -22 l8 0 l4 22 Z" fill="url(#gBrass)" stroke="#6b4c16" stroke-width="1"/><circle cx="158" cy="80" r="4" fill="url(#gBrass)"/>
      <rect x="286" y="78" width="7" height="28" rx="3" fill="url(#gBrass)"/><rect x="284" y="74" width="11" height="7" rx="2" fill="url(#gBrass)"/>
      ${plate(122, 130, 172, 50, label, fit(label, 150, 22, 14))}
      <rect x="304" y="54" width="118" height="144" rx="4" fill="url(#gBurg)" stroke="url(#gGold)" stroke-width="3"/>
      <rect x="311" y="61" width="104" height="130" rx="3" fill="none" stroke="${GOLDS}" stroke-width=".8" opacity=".6"/>${shine(306, 57, 114)}
      <path d="M292 56 Q298 38 316 38 L414 38 Q432 38 436 56 Z" fill="url(#gRoof)" stroke="url(#gGold)" stroke-width="1.5"/>
      ${pane(326, 74, 72, 54)}<line x1="362" y1="74" x2="362" y2="128" stroke="url(#gGold)" stroke-width="2.5"/>
      ${flourish(318, 162, 90)}${rivets(312, 414, 186, 10)}
      <rect x="58" y="190" width="372" height="10" fill="url(#gInk)"/><rect x="58" y="190" width="372" height="2.5" fill="url(#gGold)"/>
      ${wheel(92, 232, 18, 6)}${wheel(188, 211, 39, 14, true)}${wheel(276, 211, 39, 14, true)}${wheel(372, 230, 20, 8)}
      <line class="vx-rod" x1="208" y1="211" x2="296" y2="211" stroke="url(#gSteel)" stroke-width="8" stroke-linecap="round"/>
      <line class="vx-rod2" x1="122" y1="210" x2="208" y2="211" stroke="url(#gSteel)" stroke-width="6" stroke-linecap="round"/>
      ${coupler(426, 16)}`);
  }
  function tender() {
    let coal = "";
    for (let i = 0; i < 30; i++) { const x = 28 + i * 6.4 + (i % 3) * 2, y = 118 - (i % 4) * 4 - Math.sin(i) * 3, r = 7 + (i % 3) * 2;
      coal += `<circle cx="${x}" cy="${y}" r="${r}" fill="url(#gCoal)"/><circle cx="${x - r * .3}" cy="${y - r * .35}" r="${r * .25}" fill="#8a8580" opacity=".35"/>`; }
    return svg(240, `${shadow(240)}${coal}
      <rect x="14" y="116" width="212" height="98" rx="7" fill="url(#gBoiler)" stroke="url(#gGold)" stroke-width="3"/>${shine(18, 120, 204)}
      <rect x="14" y="116" width="212" height="9" rx="4" fill="url(#gBrass)" opacity=".9"/>
      ${plate(30, 140, 180, 46, "VIBESMAS EXPRESS", 15)}${flourish(46, 201, 148)}${rivets(22, 220, 210, 11)}
      <rect x="10" y="212" width="220" height="9" fill="url(#gInk)"/>${truck(56, 98)}${truck(144, 186)}${coupler(0, 16)}${coupler(226, 16)}`);
  }
  function shell(w, body, first) {
    return `${shadow(w)}
      <path d="M14 82 Q14 54 42 50 L${w - 42} 50 Q${w - 14} 54 ${w - 14} 82 Z" fill="url(#gRoof)" stroke="url(#gGold)" stroke-width="1.5"/>
      <rect x="${w * .24}" y="40" width="${w * .52}" height="14" rx="4" fill="url(#gRoof)" stroke="url(#gGold)" stroke-width="1"/>
      ${[.28, .37, .46, .55, .64].map(f => `<rect x="${w * f}" y="43" width="${w * .06}" height="8" rx="2" fill="url(#gWin)" opacity=".9"/>`).join("")}
      <rect x="12" y="80" width="${w - 24}" height="132" rx="8" fill="${body}" stroke="url(#gGold)" stroke-width="3"/>
      <rect x="19" y="87" width="${w - 38}" height="118" rx="5" fill="none" stroke="${GOLDS}" stroke-width=".8" opacity=".55"/>${shine(16, 84, w - 32)}
      <rect x="12" y="150" width="${w - 24}" height="4" fill="url(#gGold)" opacity=".9"/>
      ${first ? `<text x="${w / 2}" y="73" text-anchor="middle" class="vx-cin" font-size="11" fill="url(#gGoldText)" letter-spacing=".28em">FIRST CLASS</text>` : ""}
      ${rivets(20, w - 20, 207, 12)}
      <rect x="8" y="210" width="${w - 16}" height="9" fill="url(#gInk)"/>
      <path d="M40 219 L${w / 2 - 20} 226 L${w / 2 + 20} 226 L${w - 40} 219" fill="none" stroke="#3a312b" stroke-width="2"/>
      ${truck(46, 86)}${truck(w - 86, w - 46)}${coupler(0)}${coupler(w - 12)}`;
  }
  function coach(c) {
    const name = c.who.name;
    return svg(270, `${shell(270, c.first ? "url(#gBlackCar)" : "url(#gBurg)", c.first)}
      ${pane(26, 96, 26, 40)}${pane(60, 96, 26, 40)}${pane(184, 96, 26, 40)}${pane(218, 96, 26, 40)}
      <rect x="96" y="88" width="78" height="62" rx="6" fill="url(#gWin)" stroke="url(#gGold)" stroke-width="2.5" class="vx-lit"/>
      ${face(c.who, 135, 119, 23)}
      ${plate(36, 160, 198, 44, name, fit(name, 180, 19, 11), c.sub)}`);
  }
  function crowd() {
    let s = "";
    [26, 60, 94, 128, 162, 196].forEach((x, i) => { s += `${pane(x, 94, 28, 46)}<circle cx="${x + 14}" cy="${118 - (i % 2) * 3}" r="7" fill="#3a1d14"/><path d="M${x + 3} 140 q11 -16 22 0" fill="#3a1d14"/>`; });
    return svg(250, `${shell(250, "url(#gBurg)")}${s}${plate(54, 160, 142, 40, "RAIDERS", 15)}`);
  }
  function coal(c) {
    const a = c.amount, cols = a >= 10000 ? ["#ff3b3b", "#ff7a7a"] : a >= 5000 ? ["#0099fe", "#5cc3ff"] : a >= 1000 ? ["#1db2a5", "#6fe3d8"] : a >= 100 ? ["#a970ff", "#cfb0ff"] : ["#b9b9c8", "#e6e6f0"];
    let g = "";
    for (let i = 0; i < 34; i++) { const x = 30 + (i * 37) % 190, y = 92 + ((i * 13) % 34) - (i % 5) * 3, col = i % 5 === 4 ? "#f3d98f" : cols[i % 2], s = 7 + (i % 3) * 2;
      g += `<g class="vx-gem" style="animation-delay:${(i % 7) * .23}s"><polygon points="${x},${y - s} ${x + s * .8},${y} ${x},${y + s} ${x - s * .8},${y}" fill="${col}"/>
        <polygon points="${x},${y - s} ${x + s * .8},${y} ${x},${y}" fill="#fff" opacity=".35"/></g>`; }
    const label = a.toLocaleString("en-US") + " BITS";
    return svg(240, `${shadow(240)}${g}
      <polygon points="14,112 226,112 214,212 26,212" fill="url(#gBoiler)" stroke="url(#gGold)" stroke-width="3"/>${shine(18, 116, 204)}
      ${plate(40, 140, 160, 46, label, fit(label, 140, 18, 12))}${rivets(30, 212, 204, 12)}
      <rect x="10" y="210" width="220" height="9" fill="url(#gInk)"/>${truck(50, 90)}${truck(150, 190)}${coupler(0, 14)}${coupler(226, 14)}`);
  }
  function caboose(c) {
    return svg(250, `${shadow(250)}
      <rect x="80" y="28" width="90" height="36" rx="4" fill="url(#gRed)" stroke="url(#gGold)" stroke-width="2"/>
      <path d="M68 30 Q72 16 88 16 L162 16 Q178 16 182 30 Z" fill="url(#gRoof)" stroke="url(#gGold)" stroke-width="1"/>
      ${pane(94, 36, 24, 22)}${pane(132, 36, 24, 22)}
      <path d="M18 72 Q20 58 36 58 L214 58 Q230 58 232 72 Z" fill="url(#gRoof)" stroke="url(#gGold)" stroke-width="1.5"/>
      <rect x="30" y="70" width="190" height="142" rx="6" fill="url(#gRed)" stroke="url(#gGold)" stroke-width="3"/>${shine(34, 74, 182)}
      ${pane(44, 86, 30, 38)}${pane(176, 86, 30, 38)}
      ${plate(46, 134, 158, c.sub ? 52 : 44, c.text, fit(c.text, 140, 16, 11), c.sub)}
      <circle cx="229" cy="121" r="14" fill="#ff3b3b" opacity=".45" filter="url(#fGlow)" class="vx-lit"/>
      <rect x="222" y="110" width="14" height="22" rx="3" fill="#ff4444" class="vx-lit"/><rect x="220" y="106" width="18" height="6" rx="2" fill="url(#gBrass)"/>
      ${rivets(38, 214, 206, 11)}<rect x="22" y="210" width="210" height="9" fill="url(#gInk)"/>${truck(66, 106)}${truck(148, 188)}${coupler(12, 16)}`);
  }
  function banner(c) {
    const w = Math.min(640, 80 + c.text.length * 12);
    return svg(w + 70, `<path d="M0 150 C 30 140, 50 140, 70 120" fill="none" stroke="url(#gGold)" stroke-width="2"/>
      <path d="M70 92 L${w + 50} 92 L${w + 70} 118 L${w + 50} 144 L70 144 Z" fill="url(#gBurg)" stroke="url(#gGold)" stroke-width="3"/>
      <text x="${70 + w / 2}" y="119" text-anchor="middle" dominant-baseline="middle" class="vx-out" font-size="${c.text.length > 44 ? 16 : 20}" font-weight="600" font-style="italic" fill="url(#gGoldText)">“${esc(c.text)}”</text>`);
  }
  const BUILD = { loco: c => loco(c.label), tender, coach, crowd, coal, caboose, banner };

  /* ── the track and snow bank ── */
  function rails() {
    let s = `<path d="M0 32 Q 240 18 480 30 T 960 28 T 1440 30 T 1920 26 L1920 90 L0 90 Z" fill="url(#gBank)" opacity=".9"/>`;
    for (let x = 6; x < W; x += 34) s += `<rect x="${x}" y="12" width="20" height="10" rx="2" fill="#3b2a22"/>`;
    return s + `<rect x="0" y="8" width="${W}" height="5" fill="#8f8a85"/><rect x="0" y="8" width="${W}" height="2" fill="#d6d1c9"/>`;
  }

  /* ── sound: a whistle, a bell and chuffs, made in the browser ── */
  let ac = null;
  function audio(on) {
    if (!on) return null;
    try { ac = ac || new (window.AudioContext || window.webkitAudioContext)(); if (ac.state === "suspended") ac.resume(); } catch (e) { return null; }
    return ac;
  }
  function whistle(a) { if (!a) return; const t = a.currentTime, g = a.createGain(); g.connect(a.destination);
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(.12, t + .08); g.gain.setValueAtTime(.12, t + .5); g.gain.linearRampToValueAtTime(0, t + .9);
    [523, 659, 784].forEach(f => { const o = a.createOscillator(); o.type = "triangle"; o.frequency.setValueAtTime(f * .97, t); o.frequency.linearRampToValueAtTime(f, t + .15); o.connect(g); o.start(t); o.stop(t + 1); }); }
  function bell(a) { if (!a) return; [0, .45, .9].forEach(d => { const t = a.currentTime + d, g = a.createGain(), o = a.createOscillator(); o.frequency.value = 1320; o.type = "sine";
    g.gain.setValueAtTime(.12, t); g.gain.exponentialRampToValueAtTime(.001, t + .4); o.connect(g); g.connect(a.destination); o.start(t); o.stop(t + .45); }); }
  function chuff(a, vol) { if (!a) return; const t = a.currentTime, n = a.createBufferSource(), b = a.createBuffer(1, a.sampleRate * .12, a.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
    const f = a.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = 900; const g = a.createGain(); g.gain.value = .05 * vol;
    n.buffer = b; n.connect(f); f.connect(g); g.connect(a.destination); n.start(t); }

  /* ── running one train ── */
  const easeOut = u => 1 - Math.pow(1 - u, 3), easeIn = u => u * u * u;
  function stop() { if (current) { current.stop(); current = null; } }

  function run(host, train, opts = {}) {
    stop();
    ensureDefs();
    FLIP = (opts.dir || "ltr") === "ltr";
    const cars = train.cars.map(c => (BUILD[c.car] || caboose)(c));
    if (FLIP) cars.reverse();
    const L = cars.reduce((a, c) => a + c.w, 0), D = Math.max(4, train.seconds || 8.2);
    const fits = L <= W - 320, stopAt = (W - L) / 2;
    const layer = document.createElement("div");
    layer.className = "vx-layer";
    layer.innerHTML = `<div class="vx-stage"><svg class="vx-rails" viewBox="0 0 ${W} 90" preserveAspectRatio="none">${rails()}</svg>
      <div class="vx-train">${cars.map(c => c.html).join("")}</div><canvas class="vx-fx" width="${W}" height="1080"></canvas></div>`;
    host.appendChild(layer);
    const stage = layer.querySelector(".vx-stage"), trainEl = layer.querySelector(".vx-train"), fx = layer.querySelector(".vx-fx").getContext("2d");
    const wheels = [...trainEl.querySelectorAll(".vx-wheel")], rods = trainEl.querySelectorAll(".vx-rod, .vx-rod2");
    const scale = () => { stage.style.transform = `scale(${host.clientWidth / W})`; };
    scale(); addEventListener("resize", scale);
    requestAnimationFrame(() => layer.querySelector(".vx-rails").classList.add("on"));
    const a = audio(opts.sound && !opts.muted);
    whistle(a);
    const dist = W + 40 + L + 80, T_IN = 2, T_OUT = 2.4, HOLD = Math.max(1, D - T_IN - T_OUT - .4), RAMP = .12;
    // where the front of the train is (as if running right to left) at time t
    function pos(t) {
      if (fits) {
        if (t < T_IN) return stopAt + (W + 40 - stopAt) * (1 - easeOut(t / T_IN));
        if (t < T_IN + HOLD) return stopAt;
        return stopAt - (stopAt + L + 80) * easeIn(Math.min(1, (t - T_IN - HOLD) / T_OUT));
      }
      const u = Math.min(1, t / (D - .3)), k = 1 / (2 * RAMP * (1 - RAMP));
      const s = u < RAMP ? u * u * k : u > 1 - RAMP ? 1 - (1 - u) * (1 - u) * k : (u - RAMP / 2) / (1 - RAMP);
      return W + 40 - dist * s;
    }
    const steam = [], snow = [...Array(120)].map(() => ({ x: Math.random() * W, y: Math.random() * 1080, r: 1 + Math.random() * 3, s: 20 + Math.random() * 50, w: Math.random() * 6 }));
    let t0 = performance.now(), last = t0, x = pos(0), dist0 = 0, puff = 0, chuffAt = 0, rang = false, left = false, raf = 0, done = false;
    function frame(now) {
      const t = (now - t0) / 1000, dt = Math.min(.1, (now - last) / 1000); last = now;
      const nx = pos(t), v = (x - nx) / Math.max(dt, .001); dist0 += x - nx; x = nx;
      trainEl.style.transform = `translateX(${FLIP ? W - x - L : x}px)`;
      for (const w of wheels) w.style.transform = `rotate(${-dist0 / +w.dataset.r * 57.3}deg)`;
      const ang = -dist0 / 39, dy = Math.sin(ang) * 20, dx = Math.cos(ang) * 20;
      rods.forEach((rod, i) => { if (i % 2 === 0) { rod.setAttribute("x1", 188 + dx); rod.setAttribute("y1", 211 + dy); rod.setAttribute("x2", 276 + dx); rod.setAttribute("y2", 211 + dy); }
        else { rod.setAttribute("x2", 188 + dx); rod.setAttribute("y2", 211 + dy); } });
      if (fits && !rang && t >= T_IN) { rang = true; bell(a); }
      if (fits && !left && t >= T_IN + HOLD) { left = true; whistle(a); }
      puff -= dt;
      if (puff <= 0) { puff = v > 20 ? .09 : .3; const sx = x + 121 + Math.random() * 6, svx = 20 + v * .22 + Math.random() * 30;
        steam.push({ x: FLIP ? W - sx : sx, y: TOP + 20, vx: FLIP ? -svx : svx, vy: -110 - Math.random() * 50, r: 16 + Math.random() * 10, life: 1 }); }
      if (v > 20 && dist0 - chuffAt > 61) { chuffAt = dist0; chuff(a, Math.min(1, v / 1100) + .3); }
      fx.clearRect(0, 0, W, 1080);
      for (const f of snow) { f.y += f.s * dt; f.x += Math.sin(f.y / 60 + f.w) * 12 * dt; if (f.y > 1080) { f.y = -5; f.x = Math.random() * W; }
        fx.globalAlpha = .8; fx.fillStyle = "#fff"; fx.beginPath(); fx.arc(f.x, f.y, f.r, 0, 7); fx.fill(); }
      for (let i = steam.length - 1; i >= 0; i--) { const p = steam[i]; p.life -= dt * .55; p.x += p.vx * dt; p.y += p.vy * dt; p.vy *= .975; p.r += 46 * dt;
        if (p.life <= 0) { steam.splice(i, 1); continue; }
        const g = fx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r); g.addColorStop(0, `rgba(240,240,245,${.42 * p.life})`); g.addColorStop(1, "rgba(240,240,245,0)");
        fx.globalAlpha = 1; fx.fillStyle = g; fx.beginPath(); fx.arc(p.x, p.y, p.r, 0, 7); fx.fill(); }
      fx.globalAlpha = 1;
      if (t >= D) { finish(); return; }
      raf = requestAnimationFrame(frame);
    }
    function finish() {
      if (done) return;
      done = true; cancelAnimationFrame(raf); removeEventListener("resize", scale);
      layer.querySelector(".vx-rails").classList.remove("on");
      setTimeout(() => layer.remove(), 900);
      if (current && current.layer === layer) current = null;
      if (opts.onDone) opts.onDone();
    }
    raf = requestAnimationFrame(frame);
    current = { layer, stop: finish };
    return current;
  }

  return { run, stop };
})();
