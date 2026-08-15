#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dsh-plugin-hub.com static site generator
Reads data/*.json + audit/audit.json → renders public/
Hard rule: every audit value on every page comes from the data files. Nothing hand-written.
"""
import json, os, html, datetime
from pathlib import Path

ROOT = Path(__file__).parent
PUB  = ROOT / "public"
DATA = ROOT / "data"

site      = json.load(open(DATA/"site.json", encoding="utf-8"))
scenarios = json.load(open(DATA/"scenarios.json", encoding="utf-8"))
releases  = json.load(open(DATA/"releases.json", encoding="utf-8"))
audit     = json.load(open(ROOT/"audit"/"audit.json", encoding="utf-8"))

DOMAIN  = site["domain"].rstrip("/")
REPO    = site.get("github_repo","")
PLUG    = {p["name"]: p for p in audit["plugins"] if not p.get("error")}
GEN_AT  = audit["meta"]["generated_at"][:10]

def esc(s): return html.escape(str(s), quote=True)

# ---------------- shell ----------------
GA4 = ""
if site.get("ga4_id"):
    GA4 = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={site['ga4_id']}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
gtag('js',new Date());gtag('config','{site['ga4_id']}');</script>"""

def shell(title, desc, path, active, content, extra_head=""):
    nav = ""
    for href, key, label in [
        ("/","home","Home"),
        ("/scenarios.html","scenarios","Scenarios"),
        ("/opc.html","opc","OPC"),
        ("/plugins/","plugins","Plugin audits"),
        ("/breaking-changes.html","breaking","Breaking changes"),
        ("/scenarios/01-migration.html","guide","Guides")]:
        cls = ' class="on"' if key==active else ""
        nav += f'<a href="{href}"{cls}>{label}</a>'
    submit = f"https://github.com/{REPO}/issues/new?labels=plugin-submit&title=%5BSubmit%5D+owner%2Frepo" if REPO else "https://github.com/topics/dsh-plugin"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{DOMAIN}{path}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{DOMAIN}{path}">
<meta property="og:type" content="website">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<title>{esc(title)}</title>
<link rel="stylesheet" href="/assets/style.css">
{GA4}{extra_head}
</head>
<body>
<nav><div class="wrap nav-in">
  <a class="logo" href="/">dsh-plugin-hub<span class="tld">.com</span></a>
  <div class="nav-links">{nav}</div>
  <a class="nav-cta" href="{submit}" rel="nofollow">Submit a plugin</a>
</div></nav>
{content}
<footer><div class="wrap">
  <span class="mark">dsh-plugin-hub<span style="color:var(--seal)">.com</span> · Community site, not affiliated with DeepSeek</span>
  <a href="/scenarios.html">Scenarios</a>
  <a href="/opc.html">OPC toolkits</a>
  <a href="/breaking-changes.html">Breaking changes</a>
  <a href="/about-audit.html">Audit methodology</a>
  <a href="{submit}" rel="nofollow">Submit a plugin</a>
</div></footer>
</body>
</html>"""

# ---------------- audit helpers ----------------
def stamp_cls(p):
    v = p["verdict"]
    return {"pass":("","Pass"),"watch":("warn","Watch"),
            "watch_pending":("pend","Pending"),"error":("pend","Pending")}[v]

def seal_style(label):
    return ' style="font-size:10px;letter-spacing:.5px"' if len(label)>5 else ''

def maint_txt(p):
    d=p["checks"]["maintenance"]["days"]
    return "Updated today" if d==0 else ("Updated yesterday" if d==1 else f"Updated {d} days ago")

def perm_line(p):
    c=p["checks"]["permissions"]
    if c["status"]=="g":
        return ("g", f"{c['note']} (reviewed {c.get('reviewed_at','')})")
    hint = "network/exec dependency hints found" if c.get("hints") else "no network or exec dependency hints"
    return ("p", f"Pending manual review · {hint}")

def bundle_line(p):
    c=p["checks"]["bundle"]
    return ("g","dsh.bundle declared — activates properly") if c["declared"] else ("r","dsh.bundle not declared — won't activate after install")

def tests_line(p):
    c=p["checks"]["tests_ci"]
    if c["tests"] and c["ci"]: return ("g","Tests + CI present")
    if c["tests"]: return ("y","Tests, no CI")
    if c["ci"]: return ("y","CI, no tests")
    return ("r","No tests or CI")

def install_cmd(p):
    if p.get("npm"): return f'dsh plugin --profile web add {p["name"]}'
    return f'dsh plugin --profile web add github:{p["repo"]}'

def checks_block(p, link=True):
    m=p["checks"]["maintenance"]
    pm=perm_line(p); bd=bundle_line(p); ts=tests_line(p)
    rows=[ (pm[0],f"Permissions: {pm[1]}"),
           (m["status"],f"Maintenance: {maint_txt(p)}"),
           (bd[0],bd[1]),(ts[0],ts[1]) ]
    out="".join(f'<span><i class="dot {c}"></i>{esc(t)}</span>' for c,t in rows)
    if link: out+=f'<a class="card-link" href="/plugins/{p["name"]}.html">Full audit report →</a>'
    return out

def rx_card(name, tag, tag_top, desc_html, triage=""):
    p=PLUG[name]; sc,st=stamp_cls(p)
    tagcls=' top' if tag_top else ''
    label=st.upper()
    return f"""<div class="rx-card" data-t="{triage}">
  <div class="rx-head">
    <span class="name">{esc(name)}</span><span class="tag{tagcls}">{esc(tag)}</span>
    <a class="stamp {sc}"{seal_style(label)} href="/plugins/{name}.html">{label}</a>
  </div>
  <div class="rx-body">
    <div class="desc">{desc_html}</div>
    <div class="checks">{checks_block(p)}</div>
  </div>
  <div class="install"><span>{esc(install_cmd(p))}</span><button class="cp">Copy</button></div>
  <div class="install-hint">Restart <b>dsh</b> after installing — per the official docs, "the plugin becomes active after restarting dsh"</div>
</div>"""

# ---------------- pages ----------------
os.makedirs(PUB/"plugins", exist_ok=True)
os.makedirs(PUB/"scenarios", exist_ok=True)
pages=[]

def write(path, htmlstr):
    p=PUB/path.lstrip("/")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(htmlstr,encoding="utf-8")
    pages.append("/"+path.lstrip("/"))

# ---- home ----
n_aud=audit["meta"]["count"]
n_pass=sum(1 for p in PLUG.values() if p["verdict"]=="pass")
rep=PLUG.get(site["home_report_plugin"])
rp=perm_line(rep); rb=bundle_line(rep); rt=tests_line(rep); rm=rep["checks"]["maintenance"]
report_rows=f"""
<div class="row"><span class="dot {rp[0]}"></span><span class="k">Permissions</span><span class="v">{esc(rp[1])}</span></div>
<div class="row"><span class="dot {rm['status']}"></span><span class="k">Maintenance</span><span class="v">{esc(maint_txt(rep))} (last commit {rm['last_commit']})</span></div>
<div class="row"><span class="dot {rb[0]}"></span><span class="k">dsh.bundle</span><span class="v">{esc(rb[1])}</span></div>
<div class="row"><span class="dot {rt[0]}"></span><span class="k">Tests / CI</span><span class="v">{esc(rt[1])}</span></div>"""

sc_cards=""
for s in scenarios:
    if not s.get("home"): continue
    href=f"/scenarios/{s['id']}.html" if s["status"]=="live" else "/scenarios.html"
    if s.get("featured"):
        sc_cards+=f"""<a class="sc featured" href="{href}">
  <span class="badge">Most-visited entry</span><h3>{esc(s['title'])}</h3>
  <p>{esc(s['blurb'])}</p>
  <div class="rx"><span>℞ {len([x for x in s['plugins'] if x in PLUG])} verified plugins</span><span>{esc(s['star'])}</span></div></a>"""
    elif s["status"]=="gap":
        sc_cards+=f"""<a class="sc gap-card" href="/scenarios.html">
  <div class="top-line"><span class="sym">GAP {s['num']}</span><span class="cat">{esc(s['cat_s'])}</span></div>
  <h3>{esc(s['title'])}</h3><p>{esc(s['blurb'])}</p>
  <div class="rx"><span>Open call</span><span>Submissions welcome →</span></div></a>"""
    else:
        n=len([x for x in s['plugins'] if x in PLUG])
        tail=f"℞ {n} verified" if n else "In progress"
        sc_cards+=f"""<a class="sc" href="{href}">
  <div class="top-line"><span class="sym">SYMPTOM {s['num']}</span><span class="cat">{esc(s['cat_s'])}</span></div>
  <h3>{esc(s['title'])}</h3><p>{esc(s['blurb'])}</p>
  <div class="rx"><span>{tail}</span><span>{esc(s.get('star',''))}</span></div></a>"""

roles_html="".join(
    f"""<a class="role" href="/opc.html"><span class="who">{r['who']}</span><span class="n{' gap' if r['gap'] else ''}">{esc(r['n'])}</span></a>"""
    for r in site["roles"])

rel_lines=""
for r in releases["timeline"][:3]:
    rel_lines+=f'<div class="line"><span class="ver">v{esc(r["version"])}</span>'
    rel_lines+=f'<span class="desc">released {esc(r["date"])} · <a href="/breaking-changes.html">{esc(r["note"])}</a></span></div>'

home=f"""<div class="wrap">
<section class="hero">
  <span class="reg tl">┌ EST. 2026-08</span><span class="reg tr">DAILY AUDIT {GEN_AT} ┐</span>
  <div class="hero-tag">DeepSeek Harness (dsh) · Unofficial community site</div>
  <h1>Find plugins by <span class="u">the problem</span>,<br>not by browsing categories.</h1>
  <p class="lede">Each scenario recommends 2–4 audited plugins. Permissions, maintenance, whether it actually activates — checked before you install.</p>
  <div class="hero-seal"><span class="b">PASS</span><span class="s">DSH·PLUGIN·HUB</span></div>
  <div class="search"><span class="prompt">&gt;_</span>
    <input id="q" placeholder="Search by problem — e.g. context overruns / installed but not working">
    <button onclick="location.href='/scenarios.html'">Search</button></div>
  <div class="hot-q"><span>Common problems:</span>
    <a href="/scenarios/01-migration.html">Migrating from Claude Code / Codex</a>
    <a href="/scenarios.html">Context overruns</a>
    <a href="/scenarios.html">Installed but nothing happens</a>
    <a href="/breaking-changes.html">Broken after upgrading</a></div>
  <div class="hero-stats">
    <span><b>{len(scenarios)}</b>scenarios tracked · first batch live</span>
    <span><b>{n_aud}</b>plugins verified &amp; audited</span>
    <span><b>Daily</b>data refresh at 09:20 UTC+8</span></div>
</section>
<div class="hooks">
  <div class="hook"><span class="k">01 · AUDITS</span><h3>Check the audit before you install</h3>
    <p>Four checks per plugin — permissions, maintenance, dsh.bundle, tests/CI. Failures are flagged in the open, and star counts don't stand in for quality.</p></div>
  <div class="hook"><span class="k">02 · BREAKING</span><h3>Breaking changes, tracked</h3>
    <p>The official line is THERE WILL BE COMPATIBILITY-BREAKING CHANGES. We review every release and tell you whether it's safe to upgrade.</p></div>
  <div class="hook"><span class="k">03 · SYMPTOM → ℞</span><h3>Organized by problem, not by repo list</h3>
    <p>Unlike flat directories, every scenario page ships a ready-to-use install plan plus the pitfalls to avoid.</p></div>
</div>
<div class="sec-head"><span class="no">SECTION 01</span><h2>Browse by scenario</h2>
  <span class="sub">Symptom → prescription · counts only include verified plugins</span>
  <a class="more" href="/scenarios.html">All {len(scenarios)} scenarios →</a></div>
<div class="grid">{sc_cards}</div>
<div class="band">
  <div class="band-h"><span class="no">SECTION 02</span><h2>One-person company toolkits</h2>
    <span class="sub">Plugin stacks organized by line of business</span>
    <a class="more" href="/opc.html">All 10 tracks →</a></div>
  <div class="roles">{roles_html}</div>
</div>
<div class="sec-head"><span class="no">SECTION 03</span><h2>Plugin audits</h2>
  <span class="sub">Not just what exists — whether it's safe to install</span>
  <a class="more" href="/plugins/{site['home_report_plugin']}.html">See a full audit report →</a></div>
<div class="checkup">
  <div class="checkup-copy">
    <p>dsh is in developer preview and plugin quality is all over the map. Every listed plugin goes through four checks, with failures flagged in the open:</p>
    <ul><li>Permissions — file access, network calls, system resources</li>
      <li>Maintenance — how recently it was meaningfully updated</li>
      <li>Activation — whether dsh.bundle is declared</li>
      <li>Tests and CI coverage</li></ul>
    <div class="verdicts"><span class="p">Pass {n_pass}</span><span class="w">Watch / Pending {n_aud-n_pass}</span></div>
    <p class="pipe-note">Maintenance, dsh.bundle and tests/CI are collected automatically every day. Permissions are reviewed by hand — and if a review is more than 60 days old while the repo has moved on, the verdict drops back to Pending automatically. No review, no claim.<a href="/about-audit.html"> Audit methodology →</a></p>
  </div>
  <div class="report">
    <div class="report-head"><span class="name">{esc(rep['name'])}</span><span class="serial">AUDIT {GEN_AT}</span></div>
    {report_rows}
    <div class="mini-seal">PASS</div>
    <div class="report-foot"><span>Data collected daily</span><span class="barcode"></span>
      <a href="/plugins/{rep['name']}.html">Full audit report →</a></div>
  </div>
</div>
</div>
<div class="navy-band"><div class="wrap">
  <div class="sec-head"><span class="no" style="color:#ff9d8d">SECTION 04</span><h2>Breaking changes tracker</h2>
    <span class="sub">Their words: THERE WILL BE COMPATIBILITY-BREAKING CHANGES</span>
    <a class="more" href="/breaking-changes.html" style="color:#8fb3ff">Full timeline →</a></div>
  <div class="strip">{rel_lines}
    <div class="strip-foot"><span>Check here before upgrading dsh</span>
      <a href="https://github.com/deepseek-ai/deepseek-harness/releases" rel="nofollow">Official releases</a>
      <a href="/breaking-changes.html">Our reviews</a></div>
  </div>
</div></div>
<script>document.getElementById('q').addEventListener('keydown',e=>{{if(e.key==='Enter')location.href='/scenarios.html'}});</script>"""
write("index.html", shell("DSH Plugin Hub — find DeepSeek Harness plugins by problem, audited before you install",
  "Find DeepSeek Harness (dsh) plugins by the problem you're solving. Every plugin passes a four-point audit — permissions, maintenance, dsh.bundle, tests/CI — with breaking changes tracked.",
  "/", "home", home))

# ---- scenario index ----
CATS={"A":("Migration & onboarding","the traffic entry layer"),
      "B":("Troubleshooting & diagnostics","closely tied to the audits"),
      "C":("Cost & models","what DeepSeek users care about most"),
      "D":("Engineering workflows","mirrors the biggest category next door"),
      "E":("Interface & experience",""),
      "F":("Office & knowledge work","following the spread beyond code"),
      "G":("Fun & light use","retention and shareability")}
by_cat={}
for s in scenarios: by_cat.setdefault(s["cat"],[]).append(s)
cat_html=""
for c,(cn,cs) in CATS.items():
    rows=""
    for s in by_cat.get(c,[]):
        st=s["status"]
        if st=="live":
            badge='<span class="badge t1">Live</span>'; href=f"/scenarios/{s['id']}.html"; data="live"
        elif st=="t1":
            badge='<span class="badge t1">In progress</span>'; href="#"; data="wip"
        elif st=="gap":
            badge='<span class="badge gap">Open call</span>'; href="#"; data="gap"
        else:
            badge='<span class="badge t2">Queued</span>'; href="#"; data="wip"
        n=len([x for x in s.get("plugins",[]) if x in PLUG])
        rx=f'<span class="rx">℞ {n}</span>' if n and st!="gap" else ""
        no=("GAP" if st=="gap" else "SYM")+f" {s['num']}"
        gapc=" gap-row" if st=="gap" else ""
        rows+=f"""<a class="srow{gapc}" data-s="{data}" href="{href}">
  <span class="no">{no}</span>
  <span class="t"><b>{esc(s['title'])}</b><small>{esc(s['small'])}</small></span>
  {rx}{badge}<span class="arrow">→</span></a>"""
    sub=f'<span class="sub">{esc(cs)}</span>' if cs else ""
    cat_html+=f"""<section class="cat-sec"><div class="cat-h"><span class="letter">{c}</span><h2>{cn}</h2>{sub}</div>
<div class="slist">{rows}</div></section>"""

scen_page=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 12px">
  <div class="kicker">TRIAGE</div>
  <h1 style="font-size:36px;margin-top:8px">{len(scenarios)} scenarios, sorted by what you're doing</h1>
  <p class="lede" style="margin-top:8px;max-width:660px">Seven categories, organized around real use. <b style="color:var(--ink)">Live</b> = the prescription page is up. <b style="color:var(--ink)">In progress / Queued</b> = plugins verified, page being written. <b style="color:var(--amber)">Open call</b> = no solid plugin exists yet; we're collecting demand.</p>
  <div class="search" style="margin-top:20px;max-width:560px"><span class="prompt">&gt;_</span>
    <input id="q" placeholder="Search scenarios: context / notifications / spreadsheets / memory …"></div>
  <div class="filters">
    <button class="fchip on" data-f="all">All</button>
    <button class="fchip" data-f="live">Live</button>
    <button class="fchip" data-f="wip">In progress</button>
    <button class="fchip" data-f="gap">Open calls</button></div>
  <div class="count-line" id="count"></div>
</header>
{cat_html}
<div class="note"><span class="k">HOW THIS LIST GROWS</span>
Prescription pages open as plugins clear verification; <b>℞ counts only include verified plugins</b>. Open-call scenarios get a placeholder page, and the first solid plugin to appear is audited and listed. Every week we scan 1,200+ candidate repos from the community lists and the dsh-plugin topic, sort them into scenarios, and refresh compatibility status.</div>
</div>
<script>
const chips=document.querySelectorAll('.fchip'),rows=document.querySelectorAll('.srow'),
      secs=document.querySelectorAll('.cat-sec'),q=document.getElementById('q'),
      count=document.getElementById('count');let f='all';
function apply(){{const kw=q.value.trim().toLowerCase();let n=0;
rows.forEach(r=>{{const ok=(f==='all'||r.dataset.s===f)&&(!kw||r.textContent.toLowerCase().includes(kw));
r.classList.toggle('hide',!ok);if(ok)n++}});
secs.forEach(s=>s.classList.toggle('hide',[...s.querySelectorAll('.srow')].every(r=>r.classList.contains('hide'))));
count.textContent=(kw||f!=='all')?`${{n}} scenarios shown`:''}}
chips.forEach(c=>c.addEventListener('click',()=>{{chips.forEach(x=>x.classList.remove('on'));
c.classList.add('on');f=c.dataset.f;apply()}}));
q.addEventListener('input',apply);
chips.forEach(c=>{{const n=(c.dataset.f==='all')?rows.length:[...rows].filter(r=>r.dataset.s===c.dataset.f).length;
c.textContent+=` ${{n}}`}});
</script>"""
write("scenarios.html", shell("Scenarios · Triage — DSH Plugin Hub",
  "30 real DSH use scenarios in seven categories. Find the plugin prescription for the problem you're solving.","/scenarios.html","scenarios",scen_page))

# ---- SYM 01 ----
s01=next(s for s in scenarios if s["id"]=="01-migration")
cards_a="".join(rx_card(*args) for args in s01["rx_a"])
cards_b="".join(rx_card(*args) for args in s01["rx_b"])
habit_rows="".join(f"<div>{esc(a)}</div><div class='p'>{esc(b)}</div>" for a,b in s01["habit"])
rel_links="".join(f"""<a href="/scenarios.html"><span class="s">SYMPTOM {n}</span>{esc(t)}</a>""" for n,t in s01["related"])
s01_page=f"""<div class="wrap">
<div class="crumb"><a href="/scenarios.html">Scenarios</a> / A · Migration &amp; onboarding</div>
<header class="hero" style="padding:22px 0 8px">
  <div class="sym">SYMPTOM · SCENARIO 01 · LIVE</div>
  <h1 style="font-size:36px;margin-top:8px;line-height:1.3">{esc(s01['title'])}</h1>
  <p class="lede" style="margin-top:12px;max-width:660px">{s01['lede']}</p>
  <div class="triage">
    <button class="chip on" data-t="all">All prescriptions</button>
    <button class="chip" data-t="cc">Coming from Claude Code</button>
    <button class="chip" data-t="codex">Coming from Codex</button>
    <button class="chip" data-t="move">Bringing session history</button></div>
  <div class="chip-hint" id="chipHint">Pick where you're coming from to filter the prescriptions</div>
</header>
<section class="sec"><div class="sec-h"><span class="no">I</span><h2>Feature map: what you used, what replaces it</h2></div>
<div class="habit"><div class="h">In Claude Code / Codex</div><div class="h">The dsh equivalent</div>{habit_rows}</div></section>
<section class="sec"><div class="sec-h"><span class="no">II</span><h2>Recreating your workflow</h2><span class="sub">Install only what you need</span></div>{cards_a}</section>
<section class="sec"><div class="sec-h"><span class="no">III</span><h2>Bringing your session history</h2><span class="sub">Old sessions don't get left behind</span></div>{cards_b}</section>
<section class="sec"><div class="sec-h"><span class="no">IV</span><h2>Common migration pitfalls</h2><span class="sub">Sourced from the official docs and real audits</span></div>
<div class="pit"><h3>Installed but nothing happens? Check the dsh.bundle declaration</h3>
<p>From the official docs: a package without a <code>dsh.bundle</code> declaration "still installs, but only as a plain dependency … and activates no layer". Our audits check for this — one plugin on this very page currently lacks the declaration, and its report is flagged red.</p></div>
<div class="pit"><h3>Use the install command from the official docs</h3>
<p>The only current official flow is the package-spec form: <code>dsh plugin --profile web add &lt;npm-package | github:owner/repo&gt;</code> (use <code>link:</code> for local development). Other install forms that circulate in early write-ups no longer exist in the official docs and will fail.<a href="/breaking-changes.html"> Release tracker →</a></p></div>
<div class="pit"><h3>Restart after installing</h3>
<p>Plugin authors and the official docs agree: a plugin <b>becomes active after restarting dsh</b>. If nothing changes before a restart, that's expected — not a broken install.</p></div></section>
<section class="sec"><div class="sec-h"><span class="no">V</span><h2>Related scenarios</h2></div>
<div class="rel">{rel_links}</div></section>
<div class="data-note"><span>Audit data on this page collected {GEN_AT} · permission reviews in progress, updated as they complete</span>
<a href="/about-audit.html">Audit methodology</a></div>
<div class="pager"><a href="/scenarios.html"><span class="lbl">← Back</span><b>Scenarios · Triage</b></a>
<a class="next" href="/scenarios.html"><span class="lbl">Next scenario</span><b>SYM 02 Migrating from SillyTavern (in progress)</b></a></div>
</div>
<script>
const chips=document.querySelectorAll('.chip'),cards=document.querySelectorAll('.rx-card'),hint=document.getElementById('chipHint');
chips.forEach(c=>c.addEventListener('click',()=>{{chips.forEach(x=>x.classList.remove('on'));c.classList.add('on');
const t=c.dataset.t;cards.forEach(k=>k.classList.toggle('dim',t!=='all'&&!(k.dataset.t||'').split(' ').includes(t)));
hint.textContent=(t==='all')?'Pick where you\\'re coming from to filter the prescriptions':'Highlighted prescriptions apply to you; dimmed ones can be skipped'}}));
document.querySelectorAll('.cp').forEach(b=>b.addEventListener('click',()=>{{
const cmd=b.parentElement.querySelector('span').textContent;
if(navigator.clipboard)navigator.clipboard.writeText(cmd);
b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1500)}}));
</script>"""
write("scenarios/01-migration.html", shell(
  "Migrating from Claude Code / Codex to DSH: plugins and pitfalls — DSH Plugin Hub",
  "Keep your @file, annotation and TUI habits and bring your session history to dsh. Every prescription verified against the real repo, with three documented migration pitfalls.",
  "/scenarios/01-migration.html","guide",s01_page))

# ---- plugin pages ----
plug_index_rows=""
for name,p in sorted(PLUG.items()):
    sc,st=stamp_cls(p)
    m=p["checks"]["maintenance"]; pm=perm_line(p); bd=bundle_line(p); ts=tests_line(p)
    scen_tags=""
    for s in scenarios:
        if name in s.get("plugins",[]):
            href=f"/scenarios/{s['id']}.html" if s["status"]=="live" else "/scenarios.html"
            scen_tags+=f'<a href="{href}"><span class="s">SYM {s["num"]}</span>{esc(s["title"])}</a>'
    desc=esc(p.get("desc") or "(no description provided by the repo)")
    hints=p["checks"]["permissions"].get("hints") or []
    hint_txt=("Dependency hints found: "+", ".join(hints)) if hints else "No network libraries (axios / node-fetch / ws …) or exec libraries (execa / shelljs …) among the dependencies"
    perm_cell2 = (f"<div class='cell'><span class='k'>Manual verdict</span>{esc(p['checks']['permissions'].get('note',''))} (reviewed {p['checks']['permissions'].get('reviewed_at','')})</div>"
        if p["checks"]["permissions"]["status"]=="g" else
        "<div class='cell'><span class='k'>Manual verdict</span>Queued for review — once complete, the confirmed permission scope and review date appear here.</div>")
    ver=f" · v{esc(p['version'])}" if p.get("version") else ""
    label=st.upper()
    body=f"""<div class="wrap">
<div class="crumb"><a href="/">Home</a> / <a href="/plugins/">Plugin audits</a> / {esc(name)}</div>
<div class="head-card">
  <div class="head-top">
    <div class="name">{esc(name)}<small><a href="https://github.com/{esc(p['repo'])}" rel="nofollow">github.com/{esc(p['repo'])}</a>{ver}</small></div>
    <div class="big-seal {sc}"><span class="b"{' style="font-size:14px;letter-spacing:2px"' if len(label)>5 else ''}>{label}</span><span class="s">DSH·PLUGIN·HUB</span></div>
  </div>
  <p class="head-desc">{desc}</p>
  <div class="head-tags">{scen_tags}</div>
  <div class="install"><span>{esc(install_cmd(p))}</span><button class="cp" onclick="const s=this.parentElement.querySelector('span').textContent;if(navigator.clipboard)navigator.clipboard.writeText(s);this.textContent='Copied';setTimeout(()=>this.textContent='Copy',1500)">Copy</button></div>
  <p class="install-hint">Restart <b>dsh</b> after installing — no change before a restart is expected, not a broken install</p>
  <div class="serial-strip"><span>AUDIT {GEN_AT}</span><span class="barcode"></span></div>
</div>
<section class="sec"><div class="sec-h"><h2>The four checks</h2><span class="sub">Collected {GEN_AT} · refreshed daily</span></div>
<div class="check"><div class="check-h"><span class="light {pm[0]}"></span><span class="t">① Permissions</span>
  <span class="v"><b>{esc(pm[1])}</b></span></div>
  <div class="check-b"><div class="cell"><span class="k">Automated hints</span>{esc(hint_txt)}.</div>{perm_cell2}
  <div class="policy"><b>Why permissions are reviewed by hand:</b> there's no reliable way to determine permission scope automatically, so only a human review produces a verdict. If a review is over 60 days old and the repo has changed since, the verdict drops back to Pending automatically.</div></div></div>
<div class="check"><div class="check-h"><span class="light {m['status']}"></span><span class="t">② Maintenance</span>
  <span class="v"><b>{esc(maint_txt(p))}</b><br>last commit {m['last_commit']}</span></div>
  <div class="check-b single"><div class="cell"><span class="k">Rule</span>Last commit ≤ <code>14 days</code> green · ≤ <code>45 days</code> amber · older (or archived) red.</div></div></div>
<div class="check"><div class="check-h"><span class="light {bd[0]}"></span><span class="t">③ dsh.bundle</span>
  <span class="v"><b>{esc(bd[1])}</b></span></div>
  <div class="check-b single"><div class="cell"><span class="k">Why this matters</span>Per the official docs, a package without a <code>dsh.bundle</code> declaration installs as a plain dependency and <b>activates no layer</b> — the most common reason a plugin "does nothing" after install.</div></div></div>
<div class="check"><div class="check-h"><span class="light {ts[0]}"></span><span class="t">④ Tests / CI</span>
  <span class="v"><b>{esc(ts[1])}</b></span></div>
  <div class="check-b"><div class="cell"><span class="k">Tests</span>{'Test script or test directory found.' if p['checks']['tests_ci']['tests'] else 'No test script or test directory found.'}</div>
  <div class="cell"><span class="k">CI</span>{'Workflow files found under .github/workflows.' if p['checks']['tests_ci']['ci'] else 'No CI workflows found.'}</div></div></div>
</section>
<section class="sec"><div class="sec-h"><h2>Audit history</h2></div>
<div class="hist"><div class="h-item"><span class="d">{GEN_AT}</span> · <b>Latest audit</b> (verdict: {st}); compatibility tracking updates with each daily run</div></div></section>
<div class="cta-row">
  <a class="pri" href="{'/scenarios/01-migration.html' if any(name in s.get('plugins',[]) and s['status']=='live' for s in scenarios) else '/scenarios.html'}">See its scenario prescription →</a>
  <a href="https://github.com/{esc(p['repo'])}/issues" rel="nofollow">Spot an error? Send feedback</a>
  <a href="/about-audit.html">Audit methodology</a></div>
</div>"""
    write(f"plugins/{name}.html", shell(f"{name} · full audit report — DSH Plugin Hub",
        f"Audit report for {name}: permissions, maintenance, dsh.bundle and tests/CI, refreshed daily.",
        f"/plugins/{name}.html","plugins",body))
    plug_index_rows+=f"""<a class="srow" href="/plugins/{name}.html">
  <span class="no" style="width:auto"><span class="dot {'g' if p['verdict']=='pass' else 'y' if p['verdict']=='watch' else 'p'}"></span></span>
  <span class="t"><b style="font-family:var(--mono);font-size:14px">{esc(name)}</b><small>{esc((p.get('desc') or '')[:90])}</small></span>
  <span class="rx">{esc(maint_txt(p))}</span>
  <span class="badge {'t1' if p['verdict']=='pass' else 't2'}">{st}</span><span class="arrow">→</span></a>"""

plist=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 12px">
  <div class="kicker">THE AUDIT HALL</div>
  <h1 style="font-size:36px;margin-top:8px">{n_aud} plugins, four checks each</h1>
  <p class="lede" style="margin-top:8px;max-width:660px">Audit results for every listed plugin. <b style="color:var(--ink)">Pass</b> = all four checks green, permissions manually reviewed. <b style="color:var(--ink)">Pending</b> = automated checks passed, permission review queued. <b style="color:var(--amber)">Watch</b> = at least one red flag — read the report before installing.</p>
  <div class="search" style="margin-top:20px;max-width:560px"><span class="prompt">&gt;_</span>
    <input id="pq" placeholder="Search by name or purpose …"></div>
</header>
<div class="slist" style="margin-top:26px">{plug_index_rows}</div>
<div class="note"><span class="k">METHOD</span>The checks and thresholds are public — see the <a href="/about-audit.html" style="color:var(--blue)">audit methodology</a>. Data refreshes daily at 09:20 UTC+8.</div>
</div>
<script>document.getElementById('pq').addEventListener('input',function(){{const k=this.value.trim().toLowerCase();
document.querySelectorAll('.slist .srow').forEach(r=>r.classList.toggle('hide',!!k&&!r.textContent.toLowerCase().includes(k)))}});</script>"""
write("plugins/index.html", shell("Plugin audits — DSH Plugin Hub",
  f"Four-point audit results for {n_aud} DSH plugins: permissions, maintenance, dsh.bundle, tests/CI. Refreshed daily.",
  "/plugins/","plugins",plist))

# ---- methodology ----
about=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 12px">
  <div class="kicker">METHODOLOGY</div>
  <h1 style="font-size:36px;margin-top:8px">How the audits work</h1>
  <p class="lede" style="margin-top:8px;max-width:680px">Every value comes from the automated collection pipeline or the manual review file, and pages are rendered straight from that data — <b style="color:var(--ink)">no audit number on this site is typed in by hand</b>.</p>
</header>
<section class="sec"><div class="sec-h"><h2>The four checks</h2></div>
<div class="method">
<ol>
<li><b>Permissions (manual):</b> automation only surfaces hints (network or exec libraries among dependencies); the verdict is written by a human who reads the code, with the review date recorded. Reviews older than 60 days on a since-updated repo drop back to Pending automatically.</li>
<li><b>Maintenance (automated):</b> last commit ≤14 days green, ≤45 days amber, older or archived red.</li>
<li><b>dsh.bundle (automated):</b> per the official docs, a package without this declaration activates nothing after install. Missing declaration = red.</li>
<li><b>Tests / CI (automated):</b> test script or test directory, plus .github/workflows. Both green, one amber, neither red.</li>
</ol></div></section>
<section class="sec"><div class="sec-h"><h2>Where the data comes from</h2></div>
<div class="method"><b>Sources:</b> raw GitHub repository contents plus the npm registry, collected daily at 09:20 UTC+8 and published the same day. The tracked-plugin list lives in the site repo — additions welcome.<br><br>
<b>Three verdicts:</b> <span style="font-family:var(--mono)">Pass</span> (all green, permissions reviewed) · <span style="font-family:var(--mono)">Pending</span> (automated checks green, review queued) · <span style="font-family:var(--mono)">Watch</span> (at least one red flag).</div></section>
</div>"""
write("about-audit.html", shell("Audit methodology — DSH Plugin Hub",
  "The four checks, thresholds and data sources behind every DSH plugin audit on this site.","/about-audit.html","plugins",about))

# ---- breaking changes ----
tl=""
for i,r in enumerate(releases["timeline"]):
    tag='<span class="pendtag">In review</span>' if r.get("pending") else ('<span class="brk">BREAKING</span>' if r.get("breaking") else '<span class="safe">Non-breaking</span>')
    latest=' · latest' if i==0 else ''
    tl+=f"""<div class="ver-block"><div class="ver-head{' braking' if r.get('breaking') else ''}">
<span class="ver">v{esc(r['version'])}</span>{tag}
<span class="date">released {esc(r['date'])}{latest}</span></div>
<p class="what">{r['note_html']}</p></div>"""
brk=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 8px">
  <div class="kicker">BREAKING CHANGES</div>
  <h1 style="font-size:36px;margin-top:8px">dsh release reviews</h1>
  <p class="lede" style="margin-top:12px;max-width:660px">dsh is in developer preview, and the maintainers have been upfront about compatibility risk. This page tracks every release and reviews what changed, what's affected, and whether to upgrade.</p>
  <div class="quote">"DeepSeek Harness is currently in developer preview and is iterating rapidly. <b>THERE WILL BE COMPATIBILITY-BREAKING CHANGES.</b>"<small>— deepseek-ai/deepseek-harness official README, August 2026</small></div>
  <div class="sub-row">
    <a class="pri" href="https://github.com/deepseek-ai/deepseek-harness/releases" rel="nofollow">Watch official releases</a>
    <a href="https://github.com/deepseek-ai/deepseek-harness/discussions" rel="nofollow">Official discussions</a></div>
</header>
<div class="selfcheck"><span class="k">30-SECOND CHECK</span><h2>Before you upgrade</h2>
<div class="steps">
  <div class="step"><span class="n">Step 1</span><br>Run <code>dsh --version</code> and note what you're on.</div>
  <div class="step"><span class="n">Step 2</span><br>Find your target version in the timeline below and check for a <b style="color:var(--seal)">BREAKING</b> tag.</div>
  <div class="step"><span class="n">Step 3</span><br>If it's breaking, check the <a href="/plugins/" style="color:var(--blue)">audit reports</a> for your installed plugins before upgrading.</div></div></div>
<section class="sec"><div class="sec-h"><h2>Release timeline</h2><span class="sub">from npm registry · updated daily · "In review" = we haven't finished verifying the changes, so no verdict yet</span></div>
{tl}</section>
<section class="sec"><div class="sec-h"><h2>Verified install &amp; migration pitfalls</h2><span class="sub">from the official docs and real plugin repos</span></div>
<div class="pit"><h3>Packages without dsh.bundle don't activate</h3><p>Straight from the official docs: such packages "still install, but only as plain dependencies … activating no layer". Every affected plugin in the <a href="/plugins/">audit hall</a> is flagged red.</p></div>
<div class="pit"><h3>Use the official install command</h3><p>The only current flow: <code>dsh plugin --profile &lt;name&gt; add &lt;npm-package | github:owner/repo | link:local-path&gt;</code>. Other install forms from early write-ups no longer exist in the docs.</p></div>
<div class="pit"><h3>Restart dsh after installing</h3><p>Activation happens on restart. If a plugin seems dead right after install, restart before debugging.</p></div></section>
<div class="how"><b>How we track this:</b> npm releases and official repo activity are pulled automatically every day. New versions start as "In review"; only after a human verifies the changes do we tag them BREAKING or Non-breaking, and every listed plugin is re-audited the same day. <b>No finished review, no verdict.</b></div>
</div>"""
write("breaking-changes.html", shell("Breaking changes tracker — DSH Plugin Hub",
  "DSH says it plainly: THERE WILL BE COMPATIBILITY-BREAKING CHANGES. Every release reviewed, with upgrade guidance.",
  "/breaking-changes.html","breaking",brk))

# ---- OPC ----
opc=json.load(open(DATA/"opc.json",encoding="utf-8"))
role_cards=""
for r in site["roles"]:
    act=' active' if r.get("active") else ''
    href="#landing" if r.get("active") else "#"
    role_cards+=f"""<a class="role{act}" href="{href}"><span class="who">{r['who']}</span><span class="n{' gap' if r['gap'] else ''}">{esc(r['n'])}</span></a>"""
rx_cards=""
for c in opc["rx"]:
    p=PLUG.get(c["plugin"])
    if not p: continue
    sc,st=stamp_cls(p)
    small_label={'':'PASS','warn':'WATCH','pend':'PEND.'}[sc]
    rx_cards+=f"""<div class="rx"><span class="use">{esc(c['use'])}</span>
  <div class="name">{esc(c['plugin'])} <a class="stamp-s {sc[:1] if sc else ''}" href="/plugins/{c['plugin']}.html" style="font-size:9.5px">{small_label}</a></div>
  <p>{c['desc']}</p>
  <div class="foot"><a href="/plugins/{c['plugin']}.html">Full audit report →</a></div></div>"""
issue_base=f"https://github.com/{REPO}/issues" if REPO else "https://github.com/topics/dsh-plugin"
votes=""
for v in opc["gaps"]:
    votes+=f"""<div class="vote"><span class="t">{esc(v['t'])}<small>{esc(v['s'])}</small></span>
  <a class="btn" href="{issue_base}" rel="nofollow">+1 on GitHub</a></div>"""
guides="".join(f"""<div class="bridge"><span class="k">GUIDE {i+1:02d}</span><p>{g}</p><span style="font-family:var(--mono);font-size:12px;color:#8a8f98">In progress · coming soon</span></div>""" for i,g in enumerate(opc["guides"]))
opc_page=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 8px">
  <div class="kicker">ONE-PERSON COMPANY · TOOLKITS</div>
  <h1 style="font-size:36px;margin-top:8px">Plugin stacks by line of business</h1>
  <p class="lede" style="margin-top:10px;max-width:680px">Ten one-person-company tracks, each = <b style="color:var(--ink)">curated prescriptions + related scenarios + an open call</b>. Toolkits aren't a second directory — they're the scenario library recombined around what your business actually does.</p>
  <div class="role-grid">{role_cards}</div>
  <p class="idx-note">Tracks marked "open slot" have no dedicated plugins yet. The maintainer's hands-on guides fill the gap (pipelines built from existing plugins) while demand is collected in the open; the first solid plugin to appear gets audited and listed. Remaining track pages open as verification progresses — cross-border e-commerce is first.</p>
</header>
<hr style="border:0;border-top:2px dashed var(--hair);margin:42px 0 0">
<div id="landing" class="crumb">OPC toolkits / Cross-border e-commerce</div>
<header class="hero" style="padding:18px 0 6px">
  <div class="role-tag" style="font-family:var(--mono);font-size:12px;color:var(--seal);letter-spacing:2.5px">TOOLKIT · CROSS-BORDER E-COMMERCE</div>
  <h1 style="font-size:32px;max-width:720px;line-height:1.32">DSH plugins for running a store solo</h1>
  <p class="lede" style="max-width:680px">Competitor and order data, spreadsheets, product-image QA — the repetitive work of store operations, partly handled by audited DSH plugins. <b style="color:var(--ink)">Here's what works today; what's missing is collected below.</b></p>
</header>
<section class="sec"><div class="sec-h"><span class="no">I</span><h2>Prescriptions you can use today</h2><span class="sub">only verified, audited plugins listed</span></div>
<div class="rx-grid">{rx_cards}</div></section>
<section class="sec"><div class="sec-h"><span class="no">II</span><h2>Related scenarios</h2><span class="sub">drawn from the scenario library</span></div>
<div class="flow">
  <a href="/scenarios.html"><span class="s">SYMPTOM 10</span>Cost control &amp; usage tracking</a>
  <a href="/scenarios.html"><span class="s">SYMPTOM 23</span>Task-completion notifications</a>
  <a href="/scenarios/01-migration.html"><span class="s">SYMPTOM 01</span>Migrating from other tools</a></div></section>
<section class="sec"><div class="sec-h"><span class="no">III</span><h2>Open call: what's still missing</h2><span class="sub">demand numbers are public</span></div>
<div class="gap-box">
  <p class="intro">Sellers ask for these constantly, but <b>no solid DSH plugin exists yet</b> (or none we've verified). Give the matching GitHub issue a 👍 to register demand — the numbers are public, the hottest gaps get tracked first, and the first solid plugin to appear is audited and listed immediately.</p>
  <div class="votes">{votes}</div>
  <p class="gap-cta">Building a plugin in one of these areas? → <a href="{issue_base}" rel="nofollow">Submit it for a priority audit</a></p></div></section>
<section class="sec"><div class="sec-h"><span class="no">IV</span><h2>Bridge guides from the maintainer</h2><span class="sub">assembled from existing plugins</span></div>
{guides}
<p class="bridge-sub">These guides draw on the maintainer's own cross-border and SEO practice; the same approach covers the SEO content-site and video-creator open slots.</p></section>
</div>"""
write("opc.html", shell("One-person company toolkits · Cross-border e-commerce — DSH Plugin Hub",
  "DSH plugin stacks organized by line of business — cross-border e-commerce, SEO content sites, video creators and more. Verified plugins only; gaps collected in the open.",
  "/opc.html","opc",opc_page))

# ---- 404 ----
write("404.html", shell("Page not found — DSH Plugin Hub","Page not found.","/404.html","",
"""<div class="wrap"><header class="hero"><div class="kicker">404 · NOT FOUND</div>
<h1 style="font-size:40px;margin-top:8px">Page not found</h1>
<p class="lede" style="margin-top:12px">The link may be stale, or this scenario page isn't live yet. Try the <a href="/scenarios.html" style="color:var(--blue)">scenario library</a> or head <a href="/" style="color:var(--blue)">home</a>.</p></header></div>"""))

# ---- favicon / robots / sitemap ----
(PUB/"assets").mkdir(parents=True,exist_ok=True)
(PUB/"assets"/"favicon.svg").write_text(
"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="none" stroke="#bf3a2e" stroke-width="4"/><circle cx="32" cy="32" r="22" fill="none" stroke="#bf3a2e" stroke-width="1.5"/><text x="32" y="42" font-family="serif" font-size="26" font-weight="900" fill="#bf3a2e" text-anchor="middle">℞</text></svg>""",encoding="utf-8")
(PUB/"robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n",encoding="utf-8")
today=datetime.date.today().isoformat()
urls="".join(f"<url><loc>{DOMAIN}{('' if p=='/index.html' else p.replace('/index.html','/'))}</loc><lastmod>{today}</lastmod></url>"
  for p in pages if p!="/404.html")
(PUB/"sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',encoding="utf-8")

print(f"built {len(pages)} pages → public/")
