#!/usr/bin/env python3
"""
0.8% After-Hours Trading Tracker
Tracks SOXL and TSLL fluctuations during earnings months.
Run: python app.py  →  open http://localhost:5000
"""

from flask import Flask, jsonify, render_template_string
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

app = Flask(__name__)

# ── Earnings months for each ticker ──────────────────────────────────────────
# SOXL (3× Semiconductor ETF) — underlying semis report Jan, Apr, Jul, Oct
# TSLL (2× Tesla ETF)          — Tesla reports Jan, Apr, Jul, Oct
EARNINGS_MONTHS = {
    "SOXL": [1, 4, 7, 10],
    "TSLL": [1, 4, 7, 10],
}

ET = pytz.timezone("America/New_York")


def market_state() -> str:
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return "after_hours"
    t = now.hour * 60 + now.minute
    if 570 <= t < 960:   # 9:30 – 16:00
        return "open"
    if 240 <= t < 570 or 960 <= t < 1200:  # 4:00–9:30 or 16:00–20:00
        return "extended"
    return "closed"


# ── HTML / CSS / JS template ──────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>0.8% Trading Tracker — SOXL &amp; TSLL</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-adapter-date-fns/3.0.0/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#060d1a;--card:#0d1b2a;--card2:#08111e;--border:#1a3050;
  --accent:#00c9a7;--accent2:#00e5ff;
  --red:#ff4757;--green:#2ed573;--yellow:#ffd32a;
  --text:#dde6f0;--dim:#7899aa;
}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}

/* ── header ── */
.header{display:flex;align-items:center;justify-content:space-between;padding:12px 24px;
  background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}
.logo{font-size:1.1rem;font-weight:800;color:var(--accent);letter-spacing:1px}
.logo span{color:var(--text);font-weight:400}
.tabs{display:flex;gap:6px}
.tab{padding:6px 20px;border-radius:20px;border:1px solid var(--border);background:transparent;
  color:var(--dim);cursor:pointer;font-size:.85rem;font-weight:600;transition:all .2s}
.tab.active{background:var(--accent);color:#060d1a;border-color:var(--accent)}
.mstatus{display:flex;align-items:center;gap:8px;font-size:.8rem}
.dot{width:8px;height:8px;border-radius:50%}
.dot-open{background:var(--green);animation:blink 2s infinite}
.dot-ext{background:var(--yellow)}
.dot-closed{background:var(--red)}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.35}}
.ah-tag{background:rgba(255,211,42,.15);border:1px solid rgba(255,211,42,.3);color:var(--yellow);
  padding:2px 8px;border-radius:4px;font-size:.72rem;font-weight:700}

/* ── layout ── */
.wrap{padding:18px 24px;max-width:1700px;margin:0 auto}
.statusbar{background:var(--card2);border:1px solid var(--border);border-radius:8px;
  padding:9px 16px;display:flex;align-items:center;gap:10px;margin-bottom:16px;font-size:.82rem}
.rBtn{background:none;border:1px solid var(--border);color:var(--dim);padding:3px 10px;
  border-radius:6px;cursor:pointer;font-size:.72rem;transition:all .2s;margin-left:auto}
.rBtn:hover{border-color:var(--accent);color:var(--accent)}

/* ── stats row ── */
.stats{display:grid;grid-template-columns:210px 1fr 230px 230px;gap:14px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px}
.clabel{font-size:.68rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--dim);margin-bottom:8px}
.bigprice{font-size:2.1rem;font-weight:700;letter-spacing:-1px}
.chg{font-size:.83rem;margin-top:4px}
.up{color:var(--green)}.down{color:var(--red)}.neutral{color:var(--dim)}

/* ── calculator ── */
.calc-inner{display:flex;gap:16px;align-items:flex-start}
.cinput-wrap{flex:0 0 160px}
.clabel2{font-size:.68rem;color:var(--dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}
.entry-inp{width:100%;background:var(--card2);border:1px solid var(--border);border-radius:8px;
  padding:9px 12px;color:var(--text);font-size:1.05rem;font-weight:600;outline:none;transition:border-color .2s}
.entry-inp:focus{border-color:var(--accent)}
.cresults{display:grid;grid-template-columns:1fr 1fr;gap:10px;flex:1}
.tbox{background:var(--card2);border-radius:8px;padding:11px 13px;border-left:3px solid}
.tbox-up{border-color:var(--green)}.tbox-dn{border-color:var(--red)}.tbox-rng{border-color:var(--accent2);grid-column:span 2}
.tlabel{font-size:.65rem;color:var(--dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:3px}
.tval{font-size:1.2rem;font-weight:700}
.tval-up{color:var(--green)}.tval-dn{color:var(--red)}.tval-rng{color:var(--accent2)}
.tdiff{font-size:.73rem;color:var(--dim);margin-top:2px}
.signal{margin-top:10px;padding:9px 12px;border-radius:8px;font-size:.8rem;font-weight:600;text-align:center;display:none}
.sig-buy{background:rgba(46,213,115,.1);color:var(--green);border:1px solid rgba(46,213,115,.2)}
.sig-sell{background:rgba(255,71,87,.1);color:var(--red);border:1px solid rgba(255,71,87,.2)}
.sig-hold{background:rgba(120,153,170,.1);color:var(--dim);border:1px solid var(--border)}
.sig-warn{background:rgba(255,211,42,.1);color:var(--yellow);border:1px solid rgba(255,211,42,.2)}

/* ── earnings card ── */
.ebadge{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:4px;
  font-size:.74rem;font-weight:700;margin-bottom:9px}
.eb-on{background:rgba(255,211,42,.12);color:var(--yellow);border:1px solid rgba(255,211,42,.25)}
.eb-off{background:rgba(120,153,170,.08);color:var(--dim);border:1px solid var(--border)}
.mpills{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}
.mpill{padding:3px 8px;border-radius:4px;font-size:.7rem;border:1px solid var(--border);color:var(--dim)}
.mpill-on{background:rgba(255,211,42,.12);border-color:var(--yellow);color:var(--yellow)}

/* ── session card ── */
.session-state{font-size:1.05rem;font-weight:700;margin-bottom:10px}
.srow{font-size:.78rem;color:var(--dim);margin-bottom:3px}
.srow span{color:var(--text)}
.snote{font-size:.75rem;color:var(--yellow);margin-top:9px}

/* ── chart ── */
.chart-card{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:18px;margin-bottom:16px}
.chart-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.chart-title{font-size:.92rem;font-weight:600}
.ctrls{display:flex;gap:6px}
.cbtn{padding:5px 14px;border-radius:6px;border:1px solid var(--border);background:transparent;
  color:var(--dim);cursor:pointer;font-size:.77rem;transition:all .2s}
.cbtn.active{background:rgba(0,201,167,.12);border-color:var(--accent);color:var(--accent)}
.chart-wrap{position:relative;height:390px}

/* ── trade log ── */
.trade-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px}
.shdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.stitle{font-size:.92rem;font-weight:600}
.hacts{display:flex;gap:8px}
.btn{padding:7px 15px;border-radius:8px;border:none;cursor:pointer;font-size:.8rem;font-weight:600;transition:all .2s}
.btn-p{background:var(--accent);color:#060d1a}.btn-p:hover{opacity:.85}
.btn-o{background:transparent;border:1px solid var(--border);color:var(--text)}
.btn-o:hover{border-color:var(--accent);color:var(--accent)}
.btn-d{background:transparent;border:1px solid var(--red);color:var(--red);padding:4px 10px;font-size:.74rem}
table{width:100%;border-collapse:collapse}
th{font-size:.67rem;text-transform:uppercase;letter-spacing:1px;color:var(--dim);
  padding:9px 11px;text-align:left;border-bottom:1px solid var(--border)}
td{padding:11px;font-size:.83rem;border-bottom:1px solid rgba(26,48,80,.45)}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.018)}
.empty{text-align:center;padding:36px;color:var(--dim);font-size:.86rem}
.pnlp{color:var(--green);font-weight:600}.pnln{color:var(--red);font-weight:600}
.summary{display:none;margin-top:14px;padding:14px;background:var(--card2);border-radius:8px;
  gap:22px;flex-wrap:wrap}
.sumitem .clabel{margin-bottom:4px}
.sumval{font-size:1.15rem;font-weight:700}

/* ── modal ── */
.overlay{display:none;position:fixed;inset:0;background:rgba(6,13,26,.88);
  backdrop-filter:blur(4px);z-index:200;align-items:center;justify-content:center}
.overlay.show{display:flex}
.modal{background:var(--card);border:1px solid var(--border);border-radius:14px;
  padding:26px;width:480px;max-width:92vw}
.modal-title{font-size:.95rem;font-weight:600;margin-bottom:18px;color:var(--accent)}
.fgroup{margin-bottom:13px}
.flabel{font-size:.68rem;color:var(--dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px;display:block}
.finp{width:100%;background:var(--card2);border:1px solid var(--border);border-radius:7px;
  padding:9px 11px;color:var(--text);font-size:.88rem;outline:none}
.finp:focus{border-color:var(--accent)}
.fgrid{display:grid;grid-template-columns:1fr 1fr;gap:11px}
.facts{display:flex;gap:9px;margin-top:18px;justify-content:flex-end}

@media(max-width:1200px){.stats{grid-template-columns:1fr 1fr}}
@media(max-width:768px){.stats{grid-template-columns:1fr}.calc-inner{flex-direction:column}.wrap{padding:10px}}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div class="logo">0.8%<span> Trading Tracker</span></div>
  <div class="tabs">
    <button class="tab active" onclick="switchTicker('SOXL',this)">SOXL</button>
    <button class="tab" onclick="switchTicker('TSLL',this)">TSLL</button>
  </div>
  <div class="mstatus">
    <div class="dot dot-closed" id="dot"></div>
    <span id="mstatTxt">Loading…</span>
    <span class="ah-tag" id="ahTag" style="display:none">AFTER HOURS</span>
    <span style="color:var(--dim);margin-left:10px" id="clock"></span>
  </div>
</div>

<!-- MAIN -->
<div class="wrap">
  <!-- status bar -->
  <div class="statusbar">
    <span>⚡</span>
    <span id="sbarTxt">Fetching real-time data…</span>
    <button class="rBtn" onclick="loadAll()">↻ Refresh</button>
  </div>

  <!-- stats row -->
  <div class="stats">
    <!-- price -->
    <div class="card">
      <div class="clabel">Current Price</div>
      <div class="bigprice" id="cprice">—</div>
      <div class="chg" id="cchg">—</div>
      <div style="margin-top:10px;font-size:.73rem;color:var(--dim)" id="cupdated">—</div>
    </div>

    <!-- calculator -->
    <div class="card">
      <div class="clabel">0.8% Calculator</div>
      <div class="calc-inner">
        <div class="cinput-wrap">
          <div class="clabel2">Entry Price ($)</div>
          <input type="number" class="entry-inp" id="entryPrice" placeholder="0.00" step="0.01" oninput="calcTargets()">
          <div class="signal sig-hold" id="sigBox">—</div>
        </div>
        <div class="cresults">
          <div class="tbox tbox-up">
            <div class="tlabel">▲ +0.8% Sell Target</div>
            <div class="tval tval-up" id="upTarget">—</div>
            <div class="tdiff" id="upDiff">—</div>
          </div>
          <div class="tbox tbox-dn">
            <div class="tlabel">▼ −0.8% Stop Loss</div>
            <div class="tval tval-dn" id="dnTarget">—</div>
            <div class="tdiff" id="dnDiff">—</div>
          </div>
          <div class="tbox tbox-rng">
            <div class="tlabel">Total Range Width</div>
            <div class="tval tval-rng" id="rngVal">—</div>
            <div class="tdiff">1.6% band around entry</div>
          </div>
        </div>
      </div>
    </div>

    <!-- earnings -->
    <div class="card">
      <div class="clabel">Earnings Season</div>
      <div id="ebadge">—</div>
      <div style="font-size:.76rem;color:var(--dim);margin-top:8px">Active months:</div>
      <div class="mpills" id="mpills">—</div>
      <div style="font-size:.73rem;color:var(--dim);margin-top:9px" id="enext">—</div>
    </div>

    <!-- session -->
    <div class="card">
      <div class="clabel">Session Status</div>
      <div class="session-state" id="sessState">—</div>
      <div class="srow">Pre-Market <span>4:00 AM ET</span></div>
      <div class="srow">Regular <span>9:30 AM – 4:00 PM ET</span></div>
      <div class="srow">After-Hours <span>4:00 – 8:00 PM ET</span></div>
      <div class="snote" id="snote">—</div>
    </div>
  </div>

  <!-- chart -->
  <div class="chart-card">
    <div class="chart-hdr">
      <div class="chart-title" id="chartTitle">Price History &amp; Forecast — SOXL</div>
      <div class="ctrls">
        <button class="cbtn active" id="btnHistory" onclick="setMode('history')">Historical</button>
        <button class="cbtn" id="btnForecast" onclick="setMode('forecast')">Forecast (90d)</button>
        <button class="cbtn" id="btnBoth" onclick="setMode('both')">Both</button>
      </div>
    </div>
    <div class="chart-wrap"><canvas id="chart"></canvas></div>
  </div>

  <!-- trade log -->
  <div class="trade-card">
    <div class="shdr">
      <div class="stitle">📋 Trade Log</div>
      <div class="hacts">
        <button class="btn btn-p" onclick="openModal()">+ Add Trade</button>
        <button class="btn btn-o" onclick="dlCSV()">⬇ CSV</button>
        <button class="btn btn-o" style="border-color:var(--red);color:var(--red)" onclick="clearAll()">🗑 Clear</button>
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Date</th><th>Ticker</th><th>Entry</th>
          <th>+0.8% Target</th><th>−0.8% Stop</th>
          <th>Exit</th><th>P&amp;L $</th><th>P&amp;L %</th><th>Notes</th><th></th>
        </tr>
      </thead>
      <tbody id="tbody"></tbody>
    </table>
    <div class="summary" id="summary">
      <div class="sumitem"><div class="clabel">Trades</div><div class="sumval" id="sumN">0</div></div>
      <div class="sumitem"><div class="clabel">Total P&amp;L</div><div class="sumval" id="sumPnl">$0</div></div>
      <div class="sumitem"><div class="clabel">Win Rate</div><div class="sumval" id="sumWR">—</div></div>
      <div class="sumitem"><div class="clabel">Best Trade</div><div class="sumval" id="sumBest">—</div></div>
    </div>
  </div>
</div>

<!-- MODAL -->
<div class="overlay" id="modal">
  <div class="modal">
    <div class="modal-title">📊 Log a Trade</div>
    <div class="fgrid">
      <div class="fgroup">
        <label class="flabel">Date</label>
        <input type="date" class="finp" id="mDate">
      </div>
      <div class="fgroup">
        <label class="flabel">Ticker</label>
        <select class="finp" id="mTicker">
          <option value="SOXL">SOXL</option>
          <option value="TSLL">TSLL</option>
        </select>
      </div>
      <div class="fgroup">
        <label class="flabel">Entry Price ($)</label>
        <input type="number" class="finp" id="mEntry" step="0.0001" oninput="mCalc()">
      </div>
      <div class="fgroup">
        <label class="flabel">Exit Price ($) — optional</label>
        <input type="number" class="finp" id="mExit" step="0.0001">
      </div>
      <div class="fgroup">
        <label class="flabel">+0.8% Target (auto)</label>
        <input type="number" class="finp" id="mUpper" readonly style="opacity:.55">
      </div>
      <div class="fgroup">
        <label class="flabel">−0.8% Stop (auto)</label>
        <input type="number" class="finp" id="mLower" readonly style="opacity:.55">
      </div>
    </div>
    <div class="fgroup">
      <label class="flabel">Notes</label>
      <input type="text" class="finp" id="mNotes" placeholder="Optional…">
    </div>
    <div class="facts">
      <button class="btn btn-o" onclick="closeModal()">Cancel</button>
      <button class="btn btn-p" onclick="saveTrade()">Save Trade</button>
    </div>
  </div>
</div>

<script>
// ── state ────────────────────────────────────────────────────────────────────
let ticker = 'SOXL';
let mode = 'both';
let chart = null;
let hist = {};   // { SOXL: {dates,closes}, TSLL: ... }
let fore = {};   // { SOXL: {dates,p10,p25,p50,p75,p90}, ... }
let quote = {};  // { SOXL: {...}, TSLL: {...} }
let trades = JSON.parse(localStorage.getItem('oh_trades_v3') || '[]');

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const EM = { SOXL:[1,4,7,10], TSLL:[1,4,7,10] };

// ── clock ────────────────────────────────────────────────────────────────────
function tick(){
  const et = new Date(new Date().toLocaleString('en-US',{timeZone:'America/New_York'}));
  const pad = n => String(n).padStart(2,'0');
  document.getElementById('clock').textContent =
    `${pad(et.getHours())}:${pad(et.getMinutes())}:${pad(et.getSeconds())} ET`;
}
setInterval(tick,1000); tick();

// ── switch ticker ─────────────────────────────────────────────────────────────
function switchTicker(t, el){
  ticker = t;
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('chartTitle').textContent = `Price History & Forecast — ${t}`;
  document.getElementById('mTicker').value = t;
  updateQuoteUI(); updateEarningsUI(); calcTargets(); buildChart();
  if(!hist[t] || !fore[t]) loadAll();
}

// ── load data ─────────────────────────────────────────────────────────────────
async function loadAll(){
  setStatus(`Fetching ${ticker} quote…`);
  try{
    const q = await fetch(`/api/quote/${ticker}`).then(r=>r.json());
    quote[ticker] = q;
    updateQuoteUI(); updateEarningsUI(); calcTargets();

    if(!hist[ticker]){
      setStatus(`Loading historical data 2010–2026…`);
      hist[ticker] = await fetch(`/api/historical/${ticker}`).then(r=>r.json());
    }
    if(!fore[ticker]){
      setStatus(`Running Monte Carlo forecast (90 trading days)…`);
      fore[ticker] = await fetch(`/api/forecast/${ticker}`).then(r=>r.json());
    }
    buildChart();
    setStatus(`✓ ${ticker} updated — ${new Date().toLocaleTimeString()}`);
  } catch(e){
    setStatus(`⚠ ${e.message}`);
  }
}

function setStatus(msg){ document.getElementById('sbarTxt').textContent = msg; }

// ── quote UI ──────────────────────────────────────────────────────────────────
function updateQuoteUI(){
  const q = quote[ticker];
  if(!q || q.error) return;

  document.getElementById('cprice').textContent = q.price ? `$${q.price.toFixed(4)}` : '—';

  if(q.change !== null){
    const up = q.change >= 0;
    document.getElementById('cchg').innerHTML =
      `<span class="${up?'up':'down'}">${up?'▲':'▼'} ${Math.abs(q.change).toFixed(4)} `+
      `(${Math.abs(q.change_pct).toFixed(2)}%)</span> vs prev close`;
  }
  document.getElementById('cupdated').textContent = `Updated: ${q.timestamp}`;

  // dot
  const dot = document.getElementById('dot');
  const mst = document.getElementById('mstatTxt');
  const ah  = document.getElementById('ahTag');
  dot.className = 'dot';
  if(q.state === 'open'){
    dot.classList.add('dot-open'); mst.textContent='Market Open'; ah.style.display='none';
  } else if(q.state === 'extended'){
    dot.classList.add('dot-ext'); mst.textContent='Extended Hours'; ah.style.display='inline-flex';
  } else {
    dot.classList.add('dot-closed'); mst.textContent='Market Closed'; ah.style.display='none';
  }

  // session card
  const labels = {open:'🟢 Regular Hours', extended:'🟡 After Hours', closed:'🔴 Closed'};
  const notes  = {
    open:'Regular session in progress',
    extended:'⚡ After-hours active — 0.8% strategy window',
    closed:'Market closed — next session upcoming'
  };
  document.getElementById('sessState').textContent = labels[q.state] || '—';
  document.getElementById('snote').textContent = notes[q.state] || '';

  calcTargets();
}

// ── earnings UI ───────────────────────────────────────────────────────────────
function updateEarningsUI(){
  const em = EM[ticker] || [];
  const cur = new Date().getMonth()+1;
  const active = em.includes(cur);

  document.getElementById('ebadge').innerHTML = active
    ? `<div class="ebadge eb-on">⚡ EARNINGS SEASON ACTIVE</div>`
    : `<div class="ebadge eb-off">⏸ Not Earnings Month</div>`;

  document.getElementById('mpills').innerHTML =
    em.map(m=>`<span class="mpill${m===cur?' mpill-on':''}">${MONTHS[m-1]}</span>`).join('');

  const nxt = em.find(m=>m>cur) || em[0];
  const yr  = nxt <= cur ? new Date().getFullYear()+1 : new Date().getFullYear();
  document.getElementById('enext').textContent =
    active ? `Active through end of ${MONTHS[cur-1]}` : `Next: ${MONTHS[nxt-1]} ${yr}`;
}

// ── calculator ────────────────────────────────────────────────────────────────
function calcTargets(){
  const e = parseFloat(document.getElementById('entryPrice').value);
  if(!e || e<=0){
    ['upTarget','dnTarget','upDiff','dnDiff','rngVal'].forEach(id=>
      document.getElementById(id).textContent='—');
    document.getElementById('sigBox').style.display='none';
    buildChart(); return;
  }
  const up = e*1.008, dn = e*0.992, rng = up-dn;
  document.getElementById('upTarget').textContent = `$${up.toFixed(4)}`;
  document.getElementById('dnTarget').textContent = `$${dn.toFixed(4)}`;
  document.getElementById('upDiff').textContent   = `+$${(up-e).toFixed(4)} from entry`;
  document.getElementById('dnDiff').textContent   = `-$${(e-dn).toFixed(4)} from entry`;
  document.getElementById('rngVal').textContent   = `$${rng.toFixed(4)}`;

  const sig = document.getElementById('sigBox');
  sig.style.display = 'block';
  sig.className = 'signal';
  const q = quote[ticker];
  if(q && q.price){
    const p = q.price;
    if(p>=up){
      sig.textContent=`🎯 Price hit +0.8% target — consider taking profit`;
      sig.classList.add('sig-sell');
    } else if(p<=dn){
      sig.textContent=`⛔ Price at/below stop loss — review position`;
      sig.classList.add('sig-sell');
    } else if(p>e){
      sig.textContent=`✅ Above entry +$${(p-e).toFixed(4)} — approaching target`;
      sig.classList.add('sig-buy');
    } else {
      sig.textContent=`📉 Below entry −$${(e-p).toFixed(4)} — watching stop loss`;
      sig.classList.add('sig-warn');
    }
  } else {
    sig.textContent=`📊 Range set · $${rng.toFixed(4)} total band`;
    sig.classList.add('sig-hold');
  }
  buildChart();
}

// ── chart ─────────────────────────────────────────────────────────────────────
function setMode(m){
  mode=m;
  ['History','Forecast','Both'].forEach(n=>{
    document.getElementById('btn'+n).classList.toggle('active',n.toLowerCase()===m);
  });
  buildChart();
}

function buildChart(){
  const h = hist[ticker], f = fore[ticker];
  if(!h && !f) return;
  const ctx = document.getElementById('chart').getContext('2d');
  if(chart) chart.destroy();

  const ds = [];

  // historical
  if(h && (mode==='history'||mode==='both')){
    const step = Math.max(1,Math.floor(h.dates.length/600));
    ds.push({
      label:`${ticker} Historical`,
      data: h.dates.filter((_,i)=>i%step===0).map((d,i)=>({x:d,y:h.closes.filter((_,j)=>j%step===0)[i]})),
      borderColor:'#00c9a7',borderWidth:1.5,pointRadius:0,tension:0.1,fill:false,order:2
    });
  }

  // forecast bands
  if(f && (mode==='forecast'||mode==='both')){
    ds.push({
      label:'Forecast P90',
      data:f.dates.map((d,i)=>({x:d,y:f.p90[i]})),
      borderColor:'rgba(255,211,42,0)',backgroundColor:'rgba(255,211,42,0.07)',
      borderWidth:0,pointRadius:0,fill:'+1',order:3
    });
    ds.push({
      label:'Forecast P10',
      data:f.dates.map((d,i)=>({x:d,y:f.p10[i]})),
      borderColor:'rgba(255,211,42,0)',backgroundColor:'rgba(255,211,42,0.07)',
      borderWidth:0,pointRadius:0,fill:false,order:3
    });
    ds.push({
      label:'Forecast Median',
      data:f.dates.map((d,i)=>({x:d,y:f.p50[i]})),
      borderColor:'#ffd32a',borderDash:[5,3],borderWidth:2,pointRadius:0,fill:false,order:1
    });
    ds.push({
      label:'Forecast P25–P75',
      data:f.dates.map((d,i)=>({x:d,y:f.p75[i]})),
      borderColor:'rgba(255,211,42,0.15)',backgroundColor:'rgba(255,211,42,0.05)',
      borderWidth:1,pointRadius:0,fill:'+1',order:3
    });
    ds.push({
      label:'__p25',
      data:f.dates.map((d,i)=>({x:d,y:f.p25[i]})),
      borderColor:'rgba(255,211,42,0.15)',borderWidth:1,pointRadius:0,fill:false,order:3
    });
  }

  // entry / target lines
  const entry = parseFloat(document.getElementById('entryPrice').value);
  if(!isNaN(entry) && entry>0){
    const x0 = h ? h.dates[0] : (f ? f.dates[0] : null);
    const x1 = f ? f.dates[f.dates.length-1] : (h ? h.dates[h.dates.length-1] : null);
    if(x0 && x1){
      const line = (y,color,dash,label)=>({
        label,data:[{x:x0,y},{x:x1,y}],
        borderColor:color,borderWidth:1.2,borderDash:dash,
        pointRadius:0,fill:false,order:0
      });
      ds.push(line(entry,      'rgba(220,220,220,0.45)',[8,4],'Entry'));
      ds.push(line(entry*1.008,'rgba(46,213,115,0.55)', [4,4],'+0.8% Target'));
      ds.push(line(entry*0.992,'rgba(255,71,87,0.55)',  [4,4],'−0.8% Stop'));
    }
  }

  chart = new Chart(ctx,{
    type:'line',data:{datasets:ds},
    options:{
      responsive:true,maintainAspectRatio:false,
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{
          labels:{color:'#7899aa',boxWidth:14,font:{size:11},
            filter:item=>!item.text.startsWith('__')&&item.text!=='Forecast P25–P75'&&item.text!=='Forecast P10'&&item.text!=='Forecast P90'}
        },
        tooltip:{
          backgroundColor:'#0d1b2a',borderColor:'#1a3050',borderWidth:1,
          titleColor:'#dde6f0',bodyColor:'#7899aa',
          callbacks:{label:c=>`${c.dataset.label}: $${(+c.parsed.y).toFixed(4)}`}
        }
      },
      scales:{
        x:{type:'time',
          time:{unit: mode==='forecast'?'week':'month',
                tooltipFormat:'MMM d, yyyy'},
          grid:{color:'rgba(26,48,80,0.5)'},
          ticks:{color:'#7899aa',maxTicksLimit:10}},
        y:{grid:{color:'rgba(26,48,80,0.5)'},
           ticks:{color:'#7899aa',callback:v=>`$${(+v).toFixed(2)}`}}
      }
    }
  });
}

// ── trade log ─────────────────────────────────────────────────────────────────
function openModal(){
  document.getElementById('mDate').value = new Date().toISOString().split('T')[0];
  document.getElementById('mTicker').value = ticker;
  ['mEntry','mExit','mUpper','mLower','mNotes'].forEach(id=>
    document.getElementById(id).value='');
  document.getElementById('modal').classList.add('show');
}
function closeModal(){ document.getElementById('modal').classList.remove('show'); }

function mCalc(){
  const e = parseFloat(document.getElementById('mEntry').value);
  if(!isNaN(e)&&e>0){
    document.getElementById('mUpper').value=(e*1.008).toFixed(4);
    document.getElementById('mLower').value=(e*0.992).toFixed(4);
  }
}

function saveTrade(){
  const e=parseFloat(document.getElementById('mEntry').value);
  if(!e||e<=0){alert('Enter a valid entry price');return;}
  const x=parseFloat(document.getElementById('mExit').value);
  trades.unshift({
    id:Date.now(),
    date:document.getElementById('mDate').value,
    ticker:document.getElementById('mTicker').value,
    entry:e, upper:+(e*1.008).toFixed(4), lower:+(e*0.992).toFixed(4),
    exit:isNaN(x)?null:x,
    notes:document.getElementById('mNotes').value
  });
  save(); renderTable(); closeModal();
}

function delTrade(id){ trades=trades.filter(t=>t.id!==id); save(); renderTable(); }
function save(){ localStorage.setItem('oh_trades_v3',JSON.stringify(trades)); }

function renderTable(){
  const tb = document.getElementById('tbody');
  if(!trades.length){
    tb.innerHTML='<tr><td colspan="10" class="empty">No trades yet — click "+ Add Trade" to log one.</td></tr>';
    document.getElementById('summary').style.display='none';
    return;
  }
  tb.innerHTML=trades.map(t=>{
    const pnl = t.exit!==null ? +(t.exit-t.entry).toFixed(4) : null;
    const pp  = t.exit!==null ? +((t.exit-t.entry)/t.entry*100).toFixed(3) : null;
    const cls = pnl>0?'pnlp':pnl<0?'pnln':'neutral';
    return `<tr>
      <td>${t.date}</td><td><strong>${t.ticker}</strong></td>
      <td>$${t.entry.toFixed(4)}</td>
      <td class="up">$${t.upper.toFixed(4)}</td>
      <td class="down">$${t.lower.toFixed(4)}</td>
      <td>${t.exit!==null?'$'+t.exit.toFixed(4):'<span class="neutral">Open</span>'}</td>
      <td class="${cls}">${pnl!==null?(pnl>=0?'+':'')+pnl:'—'}</td>
      <td class="${cls}">${pp!==null?(pp>=0?'+':'')+pp+'%':'—'}</td>
      <td class="neutral">${t.notes||'—'}</td>
      <td><button class="btn btn-d" onclick="delTrade(${t.id})">×</button></td>
    </tr>`;
  }).join('');

  const closed=trades.filter(t=>t.exit!==null);
  const tpnl=closed.reduce((s,t)=>s+(t.exit-t.entry),0);
  const wins=closed.filter(t=>t.exit>t.entry).length;
  const best=closed.length?Math.max(...closed.map(t=>t.exit-t.entry)):null;
  const sum=document.getElementById('summary');
  sum.style.display='flex';
  document.getElementById('sumN').textContent=trades.length;
  document.getElementById('sumPnl').innerHTML=
    `<span class="${tpnl>=0?'pnlp':'pnln'}">${tpnl>=0?'+':''}$${tpnl.toFixed(4)}</span>`;
  document.getElementById('sumWR').textContent=
    closed.length?`${Math.round(wins/closed.length*100)}%`:'N/A';
  document.getElementById('sumBest').innerHTML=
    best!==null?`<span class="pnlp">+$${best.toFixed(4)}</span>`:'—';
}

// ── CSV download ──────────────────────────────────────────────────────────────
function dlCSV(){
  if(!trades.length){alert('No trades to export');return;}
  const hdr=['Date','Ticker','Entry','Upper(+0.8%)','Lower(-0.8%)','Exit','PnL $','PnL %','Notes'];
  const rows=trades.map(t=>{
    const pnl=t.exit!==null?(t.exit-t.entry).toFixed(4):'';
    const pp =t.exit!==null?((t.exit-t.entry)/t.entry*100).toFixed(3)+'%':'';
    return[t.date,t.ticker,t.entry.toFixed(4),t.upper.toFixed(4),t.lower.toFixed(4),
           t.exit!==null?t.exit.toFixed(4):'',pnl,pp,t.notes||''];
  });
  const csv=[hdr,...rows].map(r=>r.map(c=>`"${c}"`).join(',')).join('\n');
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download=`trade_log_${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
}

function clearAll(){
  if(confirm('Clear all trade records? This cannot be undone.')){
    trades=[]; save(); renderTable();
  }
}

// ── auto-refresh every 5 min ──────────────────────────────────────────────────
setInterval(()=>{
  fetch(`/api/quote/${ticker}`).then(r=>r.json()).then(q=>{
    quote[ticker]=q; updateQuoteUI(); updateEarningsUI(); calcTargets();
  }).catch(()=>{});
}, 5*60*1000);

// ── init ──────────────────────────────────────────────────────────────────────
renderTable();
updateEarningsUI();
loadAll();
</script>
</body>
</html>
"""


# ── API routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/quote/<ticker>")
def api_quote(ticker):
    ticker = ticker.upper()
    try:
        fi = yf.Ticker(ticker).fast_info
        price = float(fi.last_price) if fi.last_price else None
        prev  = float(fi.previous_close) if fi.previous_close else None
        chg   = round(price - prev, 6) if (price and prev) else None
        chgp  = round((price - prev) / prev * 100, 4) if (price and prev) else None
        state = market_state()
        return jsonify({
            "ticker": ticker,
            "price":  round(price, 6) if price else None,
            "prev_close": round(prev, 6) if prev else None,
            "change": chg, "change_pct": chgp,
            "state": state,
            "timestamp": datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S ET"),
            "earnings_months": EARNINGS_MONTHS.get(ticker, []),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/historical/<ticker>")
def api_historical(ticker):
    ticker = ticker.upper()
    try:
        h = yf.Ticker(ticker).history(start="2010-01-01")
        h = h[~h.index.duplicated(keep="last")]
        return jsonify({
            "dates":  [d.strftime("%Y-%m-%d") for d in h.index],
            "closes": [round(float(v), 6) for v in h["Close"]],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/forecast/<ticker>")
def api_forecast(ticker):
    ticker = ticker.upper()
    try:
        h = yf.Ticker(ticker).history(period="2y")
        rets  = h["Close"].pct_change().dropna()
        last  = float(h["Close"].iloc[-1])
        mu    = float(rets.mean())
        sigma = float(rets.std())

        N = 90
        SIMS = 300
        np.random.seed(42)
        paths = np.zeros((SIMS, N + 1))
        paths[:, 0] = last
        for i in range(SIMS):
            r = np.random.normal(mu, sigma, N)
            paths[i, 1:] = last * np.cumprod(1 + r)

        bdays = pd.bdate_range(start=pd.Timestamp.today(), periods=N + 1)
        dates = [d.strftime("%Y-%m-%d") for d in bdays]

        def pct(p): return np.percentile(paths, p, axis=0).round(6).tolist()

        return jsonify({
            "dates": dates,
            "p10": pct(10), "p25": pct(25), "p50": pct(50),
            "p75": pct(75), "p90": pct(90),
            "last_price": round(last, 6),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── launch ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "="*52)
    print("  0.8% After-Hours Trading Tracker")
    print("  Stocks: SOXL · TSLL")
    print("="*52)
    print("  → Open  http://localhost:5000  in your browser")
    print("  → Press Ctrl+C to stop\n")
    app.run(port=5000, debug=False)
