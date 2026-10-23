/* Vibe TV: helpers shared by the TV page (index.html) and the stream overlay
   (overlay.html). A plain script, loaded before each page's own script: the
   names below are globals on purpose. */

const $ = id => document.getElementById(id);

const Q = new URLSearchParams(location.search);
const PREVIEW = Q.get("preview") === "1";
if (PREVIEW) document.body.classList.add("preview");
let timers = [];

let LITE = false, serverMode = null;

function later(fn, ms) { timers.push(setTimeout(fn, ms)); }
function clearTimers() { timers.forEach(clearTimeout); timers = []; }
function esc(s) { return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]); }

/* ── performance mode ─────────────────────────────────────────────
   auto = lite on TV sticks, smart TVs and Android boxes (Fully Kiosk),
   full on a PC. ?mode=lite / ?mode=full on the URL overrides it. */
function decideLite(mode) {
  const forced = Q.get("mode");
  if (forced === "lite" || forced === "full") mode = forced;
  if (mode === "lite") return true;
  if (mode === "full") return false;
  if (PREVIEW) return false;
  const ua = navigator.userAgent || "";
  const tvish = /Android|AFT|BRAVIA|SMART-TV|SmartTV|Tizen|Web0S|webOS|CrKey|HbbTV|NetCast|Roku/i.test(ua);
  const weak = (navigator.hardwareConcurrency || 8) <= 4 || (navigator.deviceMemory || 8) <= 2;
  return tvish || weak;
}
function applyMode(mode) {
  if (serverMode !== null && mode !== serverMode) { location.reload(); return; }
  serverMode = mode;
  LITE = decideLite(mode);
  document.body.classList.toggle("lite", LITE);
}

// The active theme (sent by the server; follows the date schedule)
let THEME = { id: "default", accent: "#9146ff", float: "heart", float_colors: ["#ff2a6d", "#ff6fa8", "#ffffff"],
  confetti: ["#ff3b3b", "#ff9f1c", "#ffe14d", "#3ddc84", "#3ba7ff", "#9146ff"], warp: ["#ffffff", "#ff2a6d", "#05d9e8"] };

function setAccent(hex) {
  document.documentElement.style.setProperty("--accent", hex ? "#" + hex : THEME.accent);
}
const T = ev => ev.text || {};   // the event's words, already filled in by the server
function accent() { return getComputedStyle(document.documentElement).getPropertyValue("--accent").trim(); }

// Picture for a person: the avatar, or a big initial when there is none
function avatarSrc(u) {
  if (u.avatar) return u.avatar;
  const ch = (u.display_name || "?").replace(/[^A-Za-z0-9]/g, "").charAt(0).toUpperCase() || "?";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${accent()}"/><stop offset="1" stop-color="#1a1028"/></linearGradient></defs><rect width="100" height="100" fill="url(#g)"/><text x="50" y="68" font-family="Bungee, Arial Black, sans-serif" font-size="52" text-anchor="middle" fill="#fff">${ch}</text></svg>`;
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

function restartAnim(el) { el.classList.remove("go", "out"); void el.offsetWidth; el.classList.add("go"); }

function fitText(el, maxWidthPx, startVh) {
  let size = startVh;
  el.style.fontSize = size + "vh";
  while (el.scrollWidth > maxWidthPx && size > 4) { size -= 0.5; el.style.fontSize = size + "vh"; }
}

// Bits gems take Twitch's cheer colours by amount
function gemColor(n) { return n >= 10000 ? "#ff3b3b" : n >= 5000 ? "#0099fe" : n >= 1000 ? "#1db2a5" : n >= 100 ? "#a970ff" : "#b9b9c8"; }

// Big title words that pop up one by one: words with a number in them
// (12 MONTHS, 500 BITS) take the accent colour, otherwise the last word does.
function renderWords(el, text, start = .35) {
  const words = text.split(/\s+/).filter(Boolean);
  const numbered = words.map(w => /\d/.test(w));
  const any = numbered.some(Boolean);
  el.innerHTML = words.map((w, i) =>
    `<span class="${(any ? numbered[i] : i === words.length - 1) ? "hl" : ""}" style="animation-delay:${(start + i * .13).toFixed(2)}s">${esc(w)}</span>`).join("");
}
// Count the leading number of a word up from 1 (12-STREAM: 1, 2, ... 12)
function tickNumber(span, delayMs, durMs) {
  const m = span && span.textContent.match(/^(\d[\d,]*)(.*)$/);
  if (!m) return;
  const target = parseInt(m[1].replace(/,/g, ""), 10), rest = m[2];
  if (!(target > 1)) return;
  const t0 = performance.now() + delayMs;
  const step = () => {
    const p = Math.min(Math.max((performance.now() - t0) / durMs, 0), 1);
    span.textContent = Math.max(1, Math.round(target * (1 - Math.pow(1 - p, 3)))).toLocaleString() + rest;
    if (p < 1) timers.push(setTimeout(step, 40));
  };
  span.textContent = "1" + rest;
  timers.push(setTimeout(step, delayMs));
}

// Soft glowing dots are pre-drawn once and stamped with drawImage: far
// cheaper than drawing gradients or blurred arcs every frame.
const spriteCache = {};
function glowSprite(color) {
  if (spriteCache[color]) return spriteCache[color];
  const c = document.createElement("canvas"), s = 64; c.width = c.height = s;
  const x = c.getContext("2d"), gr = x.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
  gr.addColorStop(0, "#ffffff"); gr.addColorStop(.18, color); gr.addColorStop(.45, color + "55"); gr.addColorStop(1, color + "00");
  x.fillStyle = gr; x.fillRect(0, 0, s, s);
  return (spriteCache[color] = c);
}
// Theme floats (follow screen): heart, bat, snowflake or clover, drawn once
// into a 64x64 sprite.
function floatSprite(shape, color) {
  const key = shape + color;
  if (spriteCache[key]) return spriteCache[key];
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const x = c.getContext("2d");
  x.fillStyle = x.strokeStyle = color;
  if (shape === "bat") {
    x.translate(0, 12); x.scale(2, 2);
    x.fill(new Path2D("M16 6c-1-2-2.6-2.6-2.6-2.6L14 6c-2.4-.4-4.6.4-6 2C6.6 6 3.6 5 0 6c2.4 1.6 3.4 3.6 3.6 6 1.4-1 3.4-1.2 4.8 0 .6-1.6 2.4-2.4 4-2 1 1.2 2.4 2.4 3.6 4 1.2-1.6 2.6-2.8 3.6-4 1.6-.4 3.4.4 4 2 1.4-1.2 3.4-1 4.8 0 .2-2.4 1.2-4.4 3.6-6-3.6-1-6.6 0-8 2-1.4-1.6-3.6-2.4-6-2l.6-2.6S17 4 16 6z"));
  } else if (shape === "snow") {
    x.translate(32, 32); x.lineWidth = 4; x.lineCap = "round";
    for (let i = 0; i < 6; i++) {
      x.rotate(Math.PI / 3);
      x.beginPath(); x.moveTo(0, 0); x.lineTo(0, -27);
      x.moveTo(0, -16); x.lineTo(-8, -23); x.moveTo(0, -16); x.lineTo(8, -23); x.stroke();
    }
  } else if (shape === "clover") {
    x.translate(32, 30);
    for (let i = 0; i < 3; i++) {
      x.save(); x.rotate(i * 2.094 - 0.2);
      x.beginPath(); x.arc(-6, -12, 10, 0, 6.283); x.arc(6, -12, 10, 0, 6.283); x.fill(); x.restore();
    }
    x.lineWidth = 4; x.lineCap = "round"; x.beginPath(); x.moveTo(0, 2); x.quadraticCurveTo(4, 18, 12, 28); x.stroke();
  } else {
    x.translate(0, 3); x.scale(2, 2);
    x.fill(new Path2D("M16 27.5S2 19.2 2 9.6A6.9 6.9 0 0 1 9 2.5c2.8 0 5.2 1.6 7 4 1.8-2.4 4.2-4 7-4a6.9 6.9 0 0 1 7 7.1c0 9.6-14 17.9-14 17.9z"));
  }
  return (spriteCache[key] = c);
}
// Bits: a faceted gem in the cheer colour
function gemSprite(color) {
  const key = "gem" + color;
  if (spriteCache[key]) return spriteCache[key];
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const x = c.getContext("2d"); x.scale(2, 2);
  x.fillStyle = color; x.fill(new Path2D("M9 4h14l7 8-14 17L2 12z"));
  x.fillStyle = "rgba(255,255,255,.45)"; x.fill(new Path2D("M9 4l3 8h8l3-8zM2 12h28l-14 17z"));
  x.fillStyle = "rgba(0,0,0,.18)"; x.fill(new Path2D("M16 29l4-17h10z"));
  x.strokeStyle = "rgba(255,255,255,.9)"; x.lineWidth = 1.2; x.lineJoin = "round"; x.stroke(new Path2D("M9 4h14l7 8-14 17L2 12z"));
  return (spriteCache[key] = c);
}
function hex6(c) {   // sprites need #rrggbb to append alpha
  c = c.trim();
  if (/^#[0-9a-f]{6}$/i.test(c)) return c;
  if (/^#[0-9a-f]{3}$/i.test(c)) return "#" + c.slice(1).split("").map(ch => ch + ch).join("");
  return "#9146ff";
}

// A gold coin (Tier 3 rain)
function coinSprite() {
  if (spriteCache.coin) return spriteCache.coin;
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const x = c.getContext("2d"), gr = x.createRadialGradient(24, 22, 4, 32, 32, 30);
  gr.addColorStop(0, "#fff6c4"); gr.addColorStop(.45, "#ffc93c"); gr.addColorStop(1, "#b86e00");
  x.fillStyle = gr; x.beginPath(); x.arc(32, 32, 29, 0, 6.283); x.fill();
  x.strokeStyle = "rgba(255,255,255,.85)"; x.lineWidth = 2.5; x.stroke();
  x.strokeStyle = "rgba(150,85,0,.7)"; x.lineWidth = 3; x.beginPath(); x.arc(32, 32, 20, 0, 6.283); x.stroke();
  x.fillStyle = "rgba(255,255,255,.9)";
  x.fill(new Path2D("M32 18l3.6 7.6 8.2 1-6 5.7 1.6 8.1-7.4-4-7.4 4 1.6-8.1-6-5.7 8.2-1z"));
  return (spriteCache.coin = c);
}

// The full-screen alert types (welcome pop-ups and the hype bar are separate)
const CARD_TYPES = ["shoutout", "raid", "follow", "gift", "sub", "resub", "bits", "streak", "modiversary", "gigantify"];

/* ── the websocket to the server, reconnecting by itself ─────────────
   screen: "tv" or "overlay". onEvent(message) handles each broadcast;
   dot (optional) turns red while disconnected. */
function openSocket(screen, onEvent, dot) {
  const qs = "?screen=" + screen + (PREVIEW ? "&preview=1" : "");
  const ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws" + qs);
  ws.onopen = () => dot && dot.classList.add("ok");
  ws.onclose = () => { dot && dot.classList.remove("ok"); setTimeout(() => openSocket(screen, onEvent, dot), 2000); };
  ws.onerror = () => ws.close();
  ws.onmessage = e => onEvent(JSON.parse(e.data));
}
