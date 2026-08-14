#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dsh-plugin-hub.com 静态站生成器
读 data/*.json + audit/audit.json → 渲染 public/
硬规则:页面上所有体检数值必须来自 audit.json,禁止手写。
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
        ("/scenarios.html","scenarios","场景库"),
        ("/opc.html","opc","一人公司工具箱"),
        ("/plugins/","plugins","插件体检"),
        ("/breaking-changes.html","breaking","破坏性变更"),
        ("/scenarios/01-migration.html","guide","上手教程")]:
        cls = ' class="on"' if key==active else ""
        nav += f'<a href="{href}"{cls}>{label}</a>'
    submit = f"https://github.com/{REPO}/issues/new?labels=plugin-submit&title=%5B%E6%8F%90%E4%BA%A4%E6%8F%92%E4%BB%B6%5D+owner%2Frepo" if REPO else "https://github.com/topics/dsh-plugin"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
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
  <a class="nav-cta" href="{submit}" rel="nofollow">提交插件</a>
</div></nav>
{content}
<footer><div class="wrap">
  <span class="mark">dsh-plugin-hub<span style="color:var(--seal)">.com</span> · 与 DeepSeek 无关联的社区站</span>
  <a href="/scenarios.html">场景库</a>
  <a href="/opc.html">一人公司工具箱</a>
  <a href="/breaking-changes.html">破坏性变更</a>
  <a href="/about-audit.html">体检方法</a>
  <a href="{submit}" rel="nofollow">提交插件</a>
</div></footer>
</body>
</html>"""

# ---------------- audit helpers ----------------
def stamp_cls(p):
    v = p["verdict"]
    return {"pass":("","体检合格"),"watch":("warn","注意"),
            "watch_pending":("pend","待复核"),"error":("pend","待复核")}[v]

def maint_txt(p):
    c=p["checks"]["maintenance"]; d=c["days"]
    return ("今天更新" if d==0 else f"{d} 天前更新")

def perm_line(p):
    c=p["checks"]["permissions"]
    if c["status"]=="g":
        return ("g", f"{c['note']}(人工复核 {c.get('reviewed_at','')[5:]})")
    hint = "含网络/执行类依赖线索" if c.get("hints") else "未见网络/执行类依赖线索"
    return ("p", f"待人工复核 · {hint}")

def bundle_line(p):
    c=p["checks"]["bundle"]
    return ("g","dsh.bundle 已声明,可激活") if c["declared"] else ("r","未声明 dsh.bundle — 安装后不会激活")

def tests_line(p):
    c=p["checks"]["tests_ci"]
    if c["tests"] and c["ci"]: return ("g","测试 + CI 齐全")
    if c["tests"]: return ("y","有测试,无 CI")
    if c["ci"]: return ("y","有 CI,未见测试")
    return ("r","未见测试与 CI")

def install_cmd(p):
    if p.get("npm"): return f'dsh plugin --profile web add {p["name"]}'
    return f'dsh plugin --profile web add github:{p["repo"]}'

def checks_block(p, link=True):
    m=p["checks"]["maintenance"]
    pm=perm_line(p); bd=bundle_line(p); ts=tests_line(p)
    rows=[ (pm[0],f"权限:{pm[1]}"),
           (m["status"],f"维护:{maint_txt(p)}"),
           (bd[0],bd[1]),(ts[0],ts[1]) ]
    out="".join(f'<span><i class="dot {c}"></i>{esc(t)}</span>' for c,t in rows)
    if link: out+=f'<a class="card-link" href="/plugins/{p["name"]}.html">完整体检卡 →</a>'
    return out

def rx_card(name, tag, tag_top, desc_html, triage=""):
    p=PLUG[name]; sc,st=stamp_cls(p)
    tagcls=' top' if tag_top else ''
    return f"""<div class="rx-card" data-t="{triage}">
  <div class="rx-head">
    <span class="name">{esc(name)}</span><span class="tag{tagcls}">{esc(tag)}</span>
    <a class="stamp {sc}" href="/plugins/{name}.html">{'合格' if not sc else st}</a>
  </div>
  <div class="rx-body">
    <div class="desc">{desc_html}</div>
    <div class="checks">{checks_block(p)}</div>
  </div>
  <div class="install"><span>{esc(install_cmd(p))}</span><button class="cp">复制</button></div>
  <div class="install-hint">装完记得 <b>重启 dsh</b> 才生效(官方文档原话:the plugin becomes active after restarting dsh)</div>
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

# ---- 首页 ----
n_aud=audit["meta"]["count"]
n_pass=sum(1 for p in PLUG.values() if p["verdict"]=="pass")
live=[s for s in scenarios if s["status"]=="live"]
rep=PLUG.get(site["home_report_plugin"])
rp=perm_line(rep); rb=bundle_line(rep); rt=tests_line(rep); rm=rep["checks"]["maintenance"]
report_rows=f"""
<div class="row"><span class="dot {rp[0]}"></span><span class="k">权限范围</span><span class="v">{esc(rp[1])}</span></div>
<div class="row"><span class="dot {rm['status']}"></span><span class="k">维护状态</span><span class="v">{esc(maint_txt(rep))}(最近提交 {rm['last_commit']})</span></div>
<div class="row"><span class="dot {rb[0]}"></span><span class="k">dsh.bundle</span><span class="v">{esc(rb[1])}</span></div>
<div class="row"><span class="dot {rt[0]}"></span><span class="k">测试 / CI</span><span class="v">{esc(rt[1])}</span></div>"""

sc_cards=""
for s in scenarios:
    if not s.get("home"): continue
    href=f"/scenarios/{s['id']}.html" if s["status"]=="live" else "/scenarios.html"
    if s.get("featured"):
        sc_cards+=f"""<a class="sc featured" href="{href}">
  <span class="badge">最多人来的入口</span><h3>{esc(s['title'])}</h3>
  <p>{esc(s['blurb'])}</p>
  <div class="rx"><span>℞ {len([x for x in s['plugins'] if x in PLUG])} 个已核验插件</span><span>{esc(s['star'])}</span></div></a>"""
    elif s["status"]=="gap":
        sc_cards+=f"""<a class="sc gap-card" href="/scenarios.html">
  <div class="top-line"><span class="sym">GAP {s['num']}</span><span class="cat">{esc(s['cat_s'])}</span></div>
  <h3>{esc(s['title'])}</h3><p>{esc(s['blurb'])}</p>
  <div class="rx"><span>空位 · 征集中</span><span>等你来做 →</span></div></a>"""
    else:
        n=len([x for x in s['plugins'] if x in PLUG])
        tail=f"℞ {n} 已核验" if n else "整理中"
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
    rel_lines+=f'<span class="desc">{esc(r["date"])} 发布 · <a href="/breaking-changes.html">{esc(r["note"])}</a></span></div>'

home=f"""<div class="wrap">
<section class="hero">
  <span class="reg tl">┌ EST. 2026-08</span><span class="reg tr">DAILY AUDIT {GEN_AT} ┐</span>
  <div class="hero-tag">DeepSeek Harness (dsh) · 非官方社区站 · 中文为主 / EN summaries</div>
  <h1>别按分类翻插件,<br>按<span class="u">你卡住的问题</span>找。</h1>
  <p class="lede">每个场景只推荐 2–4 个体检过的插件:权限、维护状态、能否真正激活,一次看清,再决定装不装。</p>
  <div class="hero-seal"><span class="b">体检合格</span><span class="s">DSH·PLUGIN·HUB</span></div>
  <div class="search"><span class="prompt">&gt;_</span>
    <input id="q" placeholder="你现在卡在哪? 比如: context 爆了 / 装了没反应">
    <button onclick="location.href='/scenarios.html'">找处方</button></div>
  <div class="hot-q"><span>常见症状:</span>
    <a href="/scenarios/01-migration.html">从 Claude Code 迁移</a>
    <a href="/scenarios.html">context 爆了</a>
    <a href="/scenarios.html">装了没反应</a>
    <a href="/breaking-changes.html">升级后插件全挂了</a></div>
  <div class="hero-stats">
    <span><b>{len(scenarios)}</b>场景收录 · 首批开方中</span>
    <span><b>{n_aud}</b>插件已核验体检</span>
    <span><b>每日</b>09:20 数据更新</span></div>
</section>
<div class="hooks">
  <div class="hook"><span class="k">01 · CHECKUP</span><h3>装前先看体检,不是先看 star</h3>
    <p>权限 / 维护状态 / dsh.bundle / 测试CI 四道检查,不合格直接标出来。全场只有这里做。</p></div>
  <div class="hook"><span class="k">02 · BREAKING</span><h3>破坏性变更有人替你盯</h3>
    <p>官方明说 THERE WILL BE COMPATIBILITY-BREAKING CHANGES。每次发版我们核读一次,给出该不该升。</p></div>
  <div class="hook"><span class="k">03 · 症状 → 处方</span><h3>按你在干的事组织,不是仓库列表</h3>
    <p>竞品是平铺目录;这里从"你卡住的问题"出发,每页给可直接照抄的处方和避坑。</p></div>
</div>
<div class="sec-head"><span class="no">SECTION 01</span><h2>按场景找</h2>
  <span class="sub">症状 → 处方 · 处方数只统计已核验存在的插件</span>
  <a class="more" href="/scenarios.html">全部 {len(scenarios)} 个场景 →</a></div>
<div class="grid">{sc_cards}</div>
<div class="band">
  <div class="band-h"><span class="no">SECTION 02</span><h2>一人公司工具箱</h2>
    <span class="sub">按你在做的事找,不是按插件分类</span>
    <a class="more" href="/opc.html">全部 10 个方向 →</a></div>
  <div class="roles">{roles_html}</div>
</div>
<div class="sec-head"><span class="no">SECTION 03</span><h2>插件体检</h2>
  <span class="sub">别的目录告诉你有什么,我们告诉你敢不敢装</span>
  <a class="more" href="/plugins/{site['home_report_plugin']}.html">看一份完整体检卡 →</a></div>
<div class="checkup">
  <div class="checkup-copy">
    <p>dsh 还在 developer preview,插件生态鱼龙混杂。每个收录插件都过四道检查,不合格的直接标出来:</p>
    <ul><li>声明的权限范围 — 读文件?联网?系统资源?</li>
      <li>维护状态 — 最后一次有效更新距今多久</li>
      <li>能否真正激活 — 是否声明 dsh.bundle</li>
      <li>有没有测试 / CI</li></ul>
    <div class="verdicts"><span class="p">体检合格 {n_pass}</span><span class="w">注意 / 待复核 {n_aud-n_pass}</span></div>
    <p class="pipe-note">维护状态、dsh.bundle、测试CI 三项每日自动采集;权限一项人工复核,复核超 60 天且仓库有更新会自动降回"待复核"——宁可显示待复核,也不乱猜。<a href="/about-audit.html">体检方法说明 →</a></p>
  </div>
  <div class="report">
    <div class="report-head"><span class="name">{esc(rep['name'])}</span><span class="serial">AUDIT {GEN_AT}</span></div>
    {report_rows}
    <div class="mini-seal">合格</div>
    <div class="report-foot"><span>数据每日自动采集</span><span class="barcode"></span>
      <a href="/plugins/{rep['name']}.html">完整体检卡 →</a></div>
  </div>
</div>
</div>
<div class="navy-band"><div class="wrap">
  <div class="sec-head"><span class="no" style="color:#ff9d8d">SECTION 04</span><h2>破坏性变更追踪</h2>
    <span class="sub">官方原话:THERE WILL BE COMPATIBILITY-BREAKING CHANGES</span>
    <a class="more" href="/breaking-changes.html" style="color:#8fb3ff">完整时间线 →</a></div>
  <div class="strip">{rel_lines}
    <div class="strip-foot"><span>升级 dsh 前 30 秒,先来对一眼</span>
      <a href="https://github.com/deepseek-ai/deepseek-harness/releases" rel="nofollow">官方 Releases</a>
      <a href="/breaking-changes.html">本站核读</a></div>
  </div>
</div></div>
<script>document.getElementById('q').addEventListener('keydown',e=>{{if(e.key==='Enter')location.href='/scenarios.html'}});</script>"""
write("index.html", shell("DSH Plugin Hub — 按问题找插件,装前先看体检",
  "按你卡住的问题找 DeepSeek Harness 插件。每个插件过四道体检(权限/维护/dsh.bundle/测试CI),破坏性变更有人盯。",
  "/", "", home))

# ---- 场景索引 ----
CATS={"A":("迁移与上手","流量入口层"),"B":("排障与诊断","体检定位强关联层"),
      "C":("成本与模型","DeepSeek 用户核心关切"),"D":("工程工作流","对照 Claude Code 生态最大类"),
      "E":("界面与体验",""),"F":("办公与知识工作","对照 Claude Code 的非代码扩散趋势"),
      "G":("轻场景","留存与传播")}
by_cat={}
for s in scenarios: by_cat.setdefault(s["cat"],[]).append(s)
cat_html=""
for c,(cn,cs) in CATS.items():
    rows=""
    for s in by_cat.get(c,[]):
        st=s["status"]
        if st=="live":
            badge='<span class="badge t1">已开方</span>'; href=f"/scenarios/{s['id']}.html"; data="live"
        elif st=="t1":
            badge='<span class="badge t1">开方中</span>'; href="#"; data="wip"
        elif st=="gap":
            badge='<span class="badge gap">空位征集</span>'; href="#"; data="gap"
        else:
            badge='<span class="badge t2">整理中</span>'; href="#"; data="wip"
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
  <div class="kicker">TRIAGE · 分诊台</div>
  <h1 style="font-size:36px;margin-top:8px">{len(scenarios)} 个场景,你的问题挂哪一科?</h1>
  <p class="lede" style="margin-top:8px;max-width:660px">七大类按"你在干什么"组织。<b style="color:var(--ink)">已开方</b> = 处方页已上线可直接抄;<b style="color:var(--ink)">开方中 / 整理中</b> = 插件已核验、页面在写;<b style="color:var(--amber)">空位</b> = 生态还没有像样插件,先占位征集。</p>
  <div class="search" style="margin-top:20px;max-width:560px"><span class="prompt">&gt;_</span>
    <input id="q" placeholder="搜症状: context / 通知 / 表格 / 记忆 …"></div>
  <div class="filters">
    <button class="fchip on" data-f="all">全部</button>
    <button class="fchip" data-f="live">已开方</button>
    <button class="fchip" data-f="wip">开方/整理中</button>
    <button class="fchip" data-f="gap">空位征集</button></div>
  <div class="count-line" id="count"></div>
</header>
{cat_html}
<div class="note"><span class="k">HOW THIS LIST GROWS · 收录节奏</span>
处方页陆续开放,顺序按真实插件核验进度;<b>处方数只统计已核验存在的插件</b>。空位场景只建轻页占词,插件一出现,第一时间体检收录。每周例行:扫 dsh-plugin topic 增量 → 归入场景或开新场景 → 更新兼容状态。</div>
</div>
<script>
const chips=document.querySelectorAll('.fchip'),rows=document.querySelectorAll('.srow'),
      secs=document.querySelectorAll('.cat-sec'),q=document.getElementById('q'),
      count=document.getElementById('count');let f='all';
function apply(){{const kw=q.value.trim().toLowerCase();let n=0;
rows.forEach(r=>{{const ok=(f==='all'||r.dataset.s===f)&&(!kw||r.textContent.toLowerCase().includes(kw));
r.classList.toggle('hide',!ok);if(ok)n++}});
secs.forEach(s=>s.classList.toggle('hide',[...s.querySelectorAll('.srow')].every(r=>r.classList.contains('hide'))));
count.textContent=(kw||f!=='all')?`筛出 ${{n}} 个场景`:''}}
chips.forEach(c=>c.addEventListener('click',()=>{{chips.forEach(x=>x.classList.remove('on'));
c.classList.add('on');f=c.dataset.f;apply()}}));
q.addEventListener('input',apply);
chips.forEach(c=>{{const n=(c.dataset.f==='all')?rows.length:[...rows].filter(r=>r.dataset.s===c.dataset.f).length;
c.textContent+=` ${{n}}`}});
</script>"""
write("scenarios.html", shell("场景库 · 分诊台 — DSH Plugin Hub",
  "29+ 个 DSH 真实使用场景,七大类,按症状分诊找插件处方。","/scenarios.html","scenarios",scen_page))

# ---- SYM 01 场景页 ----
s01=next(s for s in scenarios if s["id"]=="01-migration")
cards_a="".join(rx_card(*args) for args in s01["rx_a"])
cards_b="".join(rx_card(*args) for args in s01["rx_b"])
habit_rows="".join(f"<div>{esc(a)}</div><div class='p'>{esc(b)}</div>" for a,b in s01["habit"])
rel_links="".join(f"""<a href="/scenarios.html"><span class="s">SYMPTOM {n}</span>{esc(t)}</a>""" for n,t in s01["related"])
s01_page=f"""<div class="wrap">
<div class="crumb"><a href="/scenarios.html">场景库</a> / A·迁移与上手</div>
<header class="hero" style="padding:22px 0 8px">
  <div class="sym">SYMPTOM · 场景 01 · 已开方</div>
  <h1 style="font-size:36px;margin-top:8px;line-height:1.3">{esc(s01['title'])}</h1>
  <p class="lede" style="margin-top:12px;max-width:660px">{s01['lede']}</p>
  <p class="en-line"><b>EN</b> {esc(s01['en'])}</p>
  <div class="triage">
    <button class="chip on" data-t="all">全部处方</button>
    <button class="chip" data-t="cc">我从 Claude Code 来</button>
    <button class="chip" data-t="codex">我从 Codex 来</button>
    <button class="chip" data-t="move">我要带历史记录搬家</button></div>
  <div class="chip-hint" id="chipHint">点选你的情况,只看相关处方</div>
</header>
<section class="sec"><div class="sec-h"><span class="no">壹</span><h2>先看对照:你的老习惯,dsh 里叫什么</h2></div>
<div class="habit"><div class="h">你在 Claude Code / Codex 的习惯</div><div class="h">dsh 里的处方</div>{habit_rows}</div></section>
<section class="sec"><div class="sec-h"><span class="no">贰</span><h2>找回操作手感</h2><span class="sub">按需装,不必全上</span></div>{cards_a}</section>
<section class="sec"><div class="sec-h"><span class="no">叁</span><h2>带着历史记录搬家</h2><span class="sub">老会话不必扔</span></div>{cards_b}</section>
<section class="sec"><div class="sec-h"><span class="no">肆</span><h2>迁移常见坑</h2><span class="sub">全部来自官方文档与真实体检</span></div>
<div class="pit"><h3>装了没反应?看 dsh.bundle</h3>
<p>官方文档:没有 <code>dsh.bundle</code> 声明的包"仍然可以安装,但只作为普通依赖……不激活任何层"。本站体检卡有这一项——本页处方里就有一个插件当前未声明,卡上直接标红。</p></div>
<div class="pit"><h3>别照抄旧教程的安装写法</h3>
<p>当前官方流程只有包规格写法:<code>dsh plugin --profile web add &lt;npm包名 | github:owner/repo&gt;</code>(本地开发用 <code>link:</code>)。早期文章流传的其他安装形式在官方文档中已不存在,照抄会失败。<a href="/breaking-changes.html">版本变更追踪 →</a></p></div>
<div class="pit"><h3>装完必须重启</h3>
<p>插件作者与官方文档一致确认:安装后<b>重启 dsh 才生效</b>("the plugin becomes active after restarting dsh")。不重启看不到变化,不是插件坏了。</p></div></section>
<section class="sec"><div class="sec-h"><span class="no">伍</span><h2>迁过来之后,你大概率会遇到</h2></div>
<div class="rel">{rel_links}</div></section>
<div class="data-note"><span>本页体检数据 {GEN_AT} 采集 · 权限项人工复核中,完成一个亮一个</span>
<a href="/about-audit.html">体检方法说明</a></div>
<div class="pager"><a href="/scenarios.html"><span class="lbl">← 返回</span><b>场景库 · 分诊台</b></a>
<a class="next" href="/scenarios.html"><span class="lbl">下一个场景</span><b>SYM 02 从 SillyTavern 迁移(开方中)</b></a></div>
</div>
<script>
const chips=document.querySelectorAll('.chip'),cards=document.querySelectorAll('.rx-card'),hint=document.getElementById('chipHint');
chips.forEach(c=>c.addEventListener('click',()=>{{chips.forEach(x=>x.classList.remove('on'));c.classList.add('on');
const t=c.dataset.t;cards.forEach(k=>k.classList.toggle('dim',t!=='all'&&!(k.dataset.t||'').split(' ').includes(t)));
hint.textContent=(t==='all')?'点选你的情况,只看相关处方':'高亮 = 与你相关的处方,变淡的可跳过'}}));
document.querySelectorAll('.cp').forEach(b=>b.addEventListener('click',()=>{{
const cmd=b.parentElement.querySelector('span').textContent;
if(navigator.clipboard)navigator.clipboard.writeText(cmd);
b.textContent='已复制';setTimeout(()=>b.textContent='复制',1500)}}));
</script>"""
write("scenarios/01-migration.html", shell(
  "从 Claude Code / Codex 迁移到 DSH:插件处方与避坑 — DSH Plugin Hub",
  "保留 @file、批注、TUI 手感,带会话历史搬家。全部处方经真实仓库核验体检,含三大迁移坑(官方文档依据)。",
  "/scenarios/01-migration.html","guide",s01_page))

# ---- 插件页 ----
plug_index_rows=""
for name,p in sorted(PLUG.items()):
    sc,st=stamp_cls(p)
    m=p["checks"]["maintenance"]; pm=perm_line(p); bd=bundle_line(p); ts=tests_line(p)
    scen_tags=""
    for s in scenarios:
        if name in s.get("plugins",[]):
            href=f"/scenarios/{s['id']}.html" if s["status"]=="live" else "/scenarios.html"
            scen_tags+=f'<a href="{href}"><span class="s">SYM {s["num"]}</span>{esc(s["title"])}</a>'
    desc=esc(p.get("desc") or "(仓库未提供描述)")
    hints=p["checks"]["permissions"].get("hints") or []
    hint_txt=("依赖线索:发现 "+", ".join(hints)) if hints else "依赖中未发现网络库(axios / node-fetch / ws …)或命令执行库(execa / shelljs …)"
    perm_cell2 = (f"<div class='cell'><span class='k'>人工结论</span>{esc(p['checks']['permissions'].get('note',''))}(复核 {p['checks']['permissions'].get('reviewed_at','')})</div>"
        if p["checks"]["permissions"]["status"]=="g" else
        "<div class='cell'><span class='k'>人工结论</span>排队复核中——完成后此处给出明确权限范围与复核日期。</div>")
    ver=f" · v{esc(p['version'])}" if p.get("version") else ""
    body=f"""<div class="wrap">
<div class="crumb"><a href="/">首页</a> / <a href="/plugins/">插件体检</a> / {esc(name)}</div>
<div class="head-card">
  <div class="head-top">
    <div class="name">{esc(name)}<small><a href="https://github.com/{esc(p['repo'])}" rel="nofollow">github.com/{esc(p['repo'])}</a>{ver}</small></div>
    <div class="big-seal {sc}"><span class="b">{st}</span><span class="s">DSH·PLUGIN·HUB</span></div>
  </div>
  <p class="head-desc">{desc}</p>
  <div class="head-tags">{scen_tags}</div>
  <div class="install"><span>{esc(install_cmd(p))}</span><button class="cp" onclick="const s=this.parentElement.querySelector('span').textContent;if(navigator.clipboard)navigator.clipboard.writeText(s);this.textContent='已复制';setTimeout(()=>this.textContent='复制',1500)">复制</button></div>
  <p class="install-hint">装完 <b>重启 dsh</b> 才生效 · 不重启看不到变化不是插件坏了</p>
  <div class="serial-strip"><span>AUDIT {GEN_AT}</span><span class="barcode"></span></div>
</div>
<section class="sec"><div class="sec-h"><h2>四项检查</h2><span class="sub">采集于 {GEN_AT} · 每日自动更新</span></div>
<div class="check"><div class="check-h"><span class="light {pm[0].replace('p','p')}"></span><span class="t">① 权限范围</span>
  <span class="v"><b>{esc(pm[1])}</b></span></div>
  <div class="check-b"><div class="cell"><span class="k">自动线索</span>{esc(hint_txt)}。</div>{perm_cell2}
  <div class="policy"><b>为什么权限是人工档:</b>权限没有可靠的自动判定方法,乱猜会砸掉体检的信任感。人工结论超过 60 天且仓库有更新,会自动降回"待人工复核"。</div></div></div>
<div class="check"><div class="check-h"><span class="light {m['status']}"></span><span class="t">② 维护状态</span>
  <span class="v"><b>{esc(maint_txt(p))}</b><br>最近提交 {m['last_commit']}</span></div>
  <div class="check-b single"><div class="cell"><span class="k">判定规则</span>最后提交 ≤ <code>14 天</code> 绿 · ≤ <code>45 天</code> 黄 · 更久或已 archived 红。</div></div></div>
<div class="check"><div class="check-h"><span class="light {bd[0]}"></span><span class="t">③ dsh.bundle</span>
  <span class="v"><b>{esc(bd[1])}</b></span></div>
  <div class="check-b single"><div class="cell"><span class="k">为什么查这项</span>官方文档:没有 <code>dsh.bundle</code> 声明的包只作为普通依赖安装,<b>不激活任何层</b>——"装了没反应"一半栽在这。</div></div></div>
<div class="check"><div class="check-h"><span class="light {ts[0]}"></span><span class="t">④ 测试 / CI</span>
  <span class="v"><b>{esc(ts[1])}</b></span></div>
  <div class="check-b"><div class="cell"><span class="k">测试</span>{'发现 test 脚本或测试目录。' if p['checks']['tests_ci']['tests'] else '未发现 test 脚本或测试目录。'}</div>
  <div class="cell"><span class="k">CI</span>{'发现 .github/workflows 工作流。' if p['checks']['tests_ci']['ci'] else '未发现 CI 工作流。'}</div></div></div>
</section>
<section class="sec"><div class="sec-h"><h2>体检历史</h2></div>
<div class="hist"><div class="h-item"><span class="d">{GEN_AT}</span> · <b>首次收录体检</b>(判定:{st});兼容追踪随每日体检持续更新</div></div></section>
<div class="cta-row">
  <a class="pri" href="{'/scenarios/01-migration.html' if any(name in s.get('plugins',[]) and s['status']=='live' for s in scenarios) else '/scenarios.html'}">看它所在的场景处方 →</a>
  <a href="https://github.com/{esc(p['repo'])}/issues" rel="nofollow">结论有误?向作者/本站反馈</a>
  <a href="/about-audit.html">体检方法说明</a></div>
</div>"""
    write(f"plugins/{name}.html", shell(f"{name} · 完整体检卡 — DSH Plugin Hub",
        f"{name} 插件体检:权限、维护状态、dsh.bundle、测试CI 四项检查,数据每日自动采集。",
        f"/plugins/{name}.html","plugins",body))
    plug_index_rows+=f"""<a class="srow" href="/plugins/{name}.html">
  <span class="no" style="width:auto"><span class="dot {'g' if p['verdict']=='pass' else 'y' if p['verdict']=='watch' else 'p'}"></span></span>
  <span class="t"><b style="font-family:var(--mono);font-size:14px">{esc(name)}</b><small>{esc((p.get('desc') or '')[:90])}</small></span>
  <span class="rx">{esc(maint_txt(p))}</span>
  <span class="badge {'t1' if p['verdict']=='pass' else 't2'}">{st}</span><span class="arrow">→</span></a>"""

plist=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 12px">
  <div class="kicker">CHECKUP · 体检大厅</div>
  <h1 style="font-size:36px;margin-top:8px">{n_aud} 个插件,四道检查</h1>
  <p class="lede" style="margin-top:8px;max-width:660px">全部收录插件的体检结果。<b style="color:var(--ink)">合格</b> = 四项全绿含人工权限复核;<b style="color:var(--ink)">待复核</b> = 自动三项已过、权限排队人工复核;<b style="color:var(--amber)">注意</b> = 有红项,装前看清。</p>
  <div class="search" style="margin-top:20px;max-width:560px"><span class="prompt">&gt;_</span>
    <input id="pq" placeholder="搜插件名或功能 …"></div>
</header>
<div class="slist" style="margin-top:26px">{plug_index_rows}</div>
<div class="note"><span class="k">METHOD</span>体检方法与判定规则公开:<a href="/about-audit.html" style="color:var(--blue)">看这页</a>。数据每日北京时间 09:20 自动采集。</div>
</div>
<script>document.getElementById('pq').addEventListener('input',function(){{const k=this.value.trim().toLowerCase();
document.querySelectorAll('.slist .srow').forEach(r=>r.classList.toggle('hide',!!k&&!r.textContent.toLowerCase().includes(k)))}});</script>"""
write("plugins/index.html", shell("插件体检大厅 — DSH Plugin Hub",
  f"{n_aud} 个 DSH 插件的四项体检结果:权限、维护状态、dsh.bundle、测试CI。每日自动更新。",
  "/plugins/","plugins",plist))

# ---- 体检方法页 ----
about=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 12px">
  <div class="kicker">METHOD · 体检方法</div>
  <h1 style="font-size:36px;margin-top:8px">体检怎么做,一次说清</h1>
  <p class="lede" style="margin-top:8px;max-width:680px">所有数值来自自动采集管线与人工复核档,页面构建时直接读数据文件渲染——<b style="color:var(--ink)">没有任何一个体检数值是手写的</b>。</p>
</header>
<section class="sec"><div class="sec-h"><h2>四项检查</h2></div>
<div class="method">
<ol>
<li><b>权限范围(人工):</b>自动只给线索(依赖里有没有网络/命令执行类库),结论由人工读代码后写入并标注复核日期。人工结论超 60 天且仓库有更新 → 自动降回"待人工复核"。</li>
<li><b>维护状态(自动):</b>最后提交 ≤14 天绿,≤45 天黄,更久或 archived 红。</li>
<li><b>dsh.bundle(自动):</b>官方文档规定,无此声明的包安装后不激活任何层。未声明直接标红。</li>
<li><b>测试 / CI(自动):</b>test 脚本/测试目录 + .github/workflows,全有绿、有一黄、全无红。</li>
</ol></div></section>
<section class="sec"><div class="sec-h"><h2>数据从哪来</h2></div>
<div class="method"><b>来源:</b>GitHub 仓库原始内容 + npm registry,每日北京时间 09:20 自动跑一轮,当天结果当天上线。收录清单公开在仓库里,欢迎提交补充。<br><br>
<b>判定三档:</b><span style="font-family:var(--mono)">体检合格</span>(四项全绿含人工权限档)· <span style="font-family:var(--mono)">待复核</span>(自动三项过、权限排队)· <span style="font-family:var(--mono)">注意</span>(有红项)。</div></section>
</div>"""
write("about-audit.html", shell("体检方法说明 — DSH Plugin Hub",
  "DSH 插件体检的四项检查、判定阈值与数据来源,全部公开。","/about-audit.html","plugins",about))

# ---- 破坏性变更 ----
tl=""
for i,r in enumerate(releases["timeline"]):
    tag='<span class="pendtag">核读中</span>' if r.get("pending") else ('<span class="brk">BREAKING</span>' if r.get("breaking") else '<span class="safe">非破坏</span>')
    latest=' · 当前最新' if i==0 else ''
    tl+=f"""<div class="ver-block"><div class="ver-head{' braking' if r.get('breaking') else ''}">
<span class="ver">v{esc(r['version'])}</span>{tag}
<span class="date">{esc(r['date'])} 发布{latest}</span></div>
<p class="what">{r['note_html']}</p></div>"""
brk=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 8px">
  <div class="kicker">BREAKING CHANGES · 追踪</div>
  <h1 style="font-size:36px;margin-top:8px">升级 dsh 前,先来对一眼</h1>
  <p class="lede" style="margin-top:12px;max-width:660px">dsh 还在 developer preview,官方把丑话说在了前头。我们盯每次发版,把变更翻译成人话:变了什么、影响谁、该不该升。</p>
  <div class="quote">"DeepSeek Harness is currently in developer preview and is iterating rapidly. <b>THERE WILL BE COMPATIBILITY-BREAKING CHANGES.</b>"<small>— deepseek-ai/deepseek-harness 官方 README(2026-08 实录)</small></div>
  <div class="sub-row">
    <a class="pri" href="https://github.com/deepseek-ai/deepseek-harness/releases" rel="nofollow">Watch 官方 Releases</a>
    <a href="https://github.com/deepseek-ai/deepseek-harness/discussions" rel="nofollow">官方 Discussions</a></div>
</header>
<div class="selfcheck"><span class="k">30-SECOND CHECK</span><h2>升级前 30 秒自查</h2>
<div class="steps">
  <div class="step"><span class="n">第一步</span><br>跑 <code>dsh --version</code>,记下当前版本。</div>
  <div class="step"><span class="n">第二步</span><br>在下面时间线里找你要升到的版本,看有没有 <b style="color:var(--seal)">BREAKING</b> 标。</div>
  <div class="step"><span class="n">第三步</span><br>有 BREAKING?先查你装的插件的<a href="/plugins/" style="color:var(--blue)">体检卡</a>再动手。</div></div></div>
<section class="sec"><div class="sec-h"><h2>版本时间线</h2><span class="sub">数据来自 npm registry · 每日更新 · "核读中"=尚未逐项核对变更内容,不乱标</span></div>
{tl}</section>
<section class="sec"><div class="sec-h"><h2>已核实的安装迁移坑</h2><span class="sub">依据:官方文档 + 真实插件仓库</span></div>
<div class="pit"><h3>没声明 dsh.bundle 的包,装了不激活</h3><p>官方文档原文:此类包"仍然可以安装,但只作为普通依赖……不激活任何层"。<a href="/plugins/">体检大厅</a>里未声明的插件已全部标红。</p></div>
<div class="pit"><h3>安装写法以官方文档为准</h3><p>当前唯一官方流程:<code>dsh plugin --profile &lt;name&gt; add &lt;npm包 | github:owner/repo | link:本地路径&gt;</code>。旧文章里的其他安装形式在官方文档中已不存在。</p></div>
<div class="pit"><h3>装完必须重启 dsh</h3><p>插件激活发生在重启后。装完没反应,先重启再排查。</p></div></section>
<div class="how"><b>我们怎么盯:</b>每日自动抓 npm 发版与官方仓库变动;出现新版本先挂"核读中",人工核对变更后才标 BREAKING / 非破坏,同一天对全部收录插件重跑体检。<b>不核读完,不下结论。</b></div>
</div>"""
write("breaking-changes.html", shell("破坏性变更追踪 — DSH Plugin Hub",
  "DSH 官方明说 THERE WILL BE COMPATIBILITY-BREAKING CHANGES。每个版本变了什么、该不该升,核读后才下结论。",
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
    rx_cards+=f"""<div class="rx"><span class="use">{esc(c['use'])}</span>
  <div class="name">{esc(c['plugin'])} <a class="stamp-s {sc[:1] if sc else ''}" href="/plugins/{c['plugin']}.html">{('合格' if not sc else ('注意' if sc=='warn' else '待复核'))}</a></div>
  <p>{c['desc']}</p>
  <div class="foot"><a href="/plugins/{c['plugin']}.html">完整体检卡 →</a></div></div>"""
issue_base=f"https://github.com/{REPO}/issues" if REPO else "https://github.com/topics/dsh-plugin"
votes=""
for v in opc["gaps"]:
    votes+=f"""<div class="vote"><span class="t">{esc(v['t'])}<small>{esc(v['s'])}</small></span>
  <a class="btn" href="{issue_base}" rel="nofollow">想要 · 去 GitHub 点 👍</a></div>"""
guides="".join(f"""<div class="bridge"><span class="k">GUIDE {i+1:02d}</span><p>{g}</p><span style="font-family:var(--mono);font-size:12px;color:#8a8f98">撰写中 · 即将上线</span></div>""" for i,g in enumerate(opc["guides"]))
opc_page=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 8px">
  <div class="kicker">ONE-PERSON COMPANY · 工具箱</div>
  <h1 style="font-size:36px;margin-top:8px">你在做什么,决定你装什么</h1>
  <p class="lede" style="margin-top:10px;max-width:680px">十个一人公司方向,每个 = <b style="color:var(--ink)">精选处方 + 相关场景组合 + 空位征集</b>。这不是第二套目录——每个工具箱都映射到场景库的组合,只是按"你的生意"重新打包。</p>
  <div class="role-grid">{role_cards}</div>
  <p class="idx-note">带"空位"标的方向,DSH 生态还没长出对口插件——这些页将由站长实操教程顶上(用现有插件拼流水线),同时开着征集收需求,插件一出现就体检收录。其余方向的落地页按处方核验进度陆续开放,先开跨境电商。</p>
</header>
<hr style="border:0;border-top:2px dashed var(--hair);margin:42px 0 0">
<div id="landing" class="crumb">一人公司工具箱 / 跨境电商</div>
<header class="hero" style="padding:18px 0 6px">
  <div class="role-tag" style="font-family:var(--mono);font-size:12px;color:var(--seal);letter-spacing:2.5px">TOOLBOX · 跨境电商</div>
  <h1 style="font-size:32px;max-width:720px;line-height:1.32">一个人打理店铺,把重复的活儿交给 DSH</h1>
  <p class="lede" style="max-width:680px">竞品与订单数据、报表、产品图检查——这些每天吃掉你几小时的事,已核验的 DSH 插件能接走一部分。<b style="color:var(--ink)">能用的先用起来,缺的告诉我们。</b></p>
  <p class="en-line"><b>EN</b> Running a cross-border e-commerce store solo? Audited DSH plugins to offload data pulls, spreadsheets and image QA.</p>
</header>
<section class="sec"><div class="sec-h"><span class="no">壹</span><h2>现在就能用的处方</h2><span class="sub">只列已核验存在并过体检的</span></div>
<div class="rx-grid">{rx_cards}</div></section>
<section class="sec"><div class="sec-h"><span class="no">贰</span><h2>你大概率会用到的场景</h2><span class="sub">来自场景库的组合</span></div>
<div class="flow">
  <a href="/scenarios.html"><span class="s">SYMPTOM 10</span>控制花费,看每轮成本</a>
  <a href="/scenarios.html"><span class="s">SYMPTOM 23</span>任务完成时提醒我</a>
  <a href="/scenarios/01-migration.html"><span class="s">SYMPTOM 01</span>从别的工具迁移过来</a></div></section>
<section class="sec"><div class="sec-h"><span class="no">叁</span><h2>还缺什么 — 告诉我们先盯哪个</h2><span class="sub">征集 = 需求收集器,不造票数</span></div>
<div class="gap-box">
  <p class="intro">这些是跨境卖家常要、但 <b>DSH 生态还没有像样插件</b>(或本站尚未核验到)的能力。想要哪个,去 GitHub 给对应 issue 点 👍——票数公开可查,我们按热度追踪:插件一出现,第一时间体检收录。</p>
  <div class="votes">{votes}</div>
  <p class="gap-cta">你在做插件?正好做到了这些方向 → <a href="{issue_base}" rel="nofollow">提交给我们优先体检</a></p></div></section>
<section class="sec"><div class="sec-h"><span class="no">肆</span><h2>等插件的日子,先这么干</h2><span class="sub">站长实操系列</span></div>
{guides}
<p class="bridge-sub">教程来自站长自己的跨境/SEO 实操;同样的套路也会顶在 SEO 内容站、视频自媒体两个空位方向上。</p></section>
</div>"""
write("opc.html", shell("一人公司工具箱 · 跨境电商 — DSH Plugin Hub",
  "按你在做的事(跨境电商/SEO内容站/视频自媒体…)组合 DSH 插件处方,只列核验过的,缺的公开征集。",
  "/opc.html","opc",opc_page))

# ---- 404 ----
write("404.html", shell("页面不存在 — DSH Plugin Hub","页面不存在。","/404.html","",
"""<div class="wrap"><header class="hero"><div class="kicker">404 · 查无此症</div>
<h1 style="font-size:40px;margin-top:8px">这个症状还没建档</h1>
<p class="lede" style="margin-top:12px">要么链接旧了,要么这个场景还在开方。去<a href="/scenarios.html" style="color:var(--blue)">分诊台</a>看看,或回<a href="/" style="color:var(--blue)">首页</a>。</p></header></div>"""))

# ---- favicon / robots / sitemap ----
(PUB/"assets").mkdir(parents=True,exist_ok=True)
(PUB/"assets"/"favicon.svg").write_text(
"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="none" stroke="#bf3a2e" stroke-width="4"/><circle cx="32" cy="32" r="22" fill="none" stroke="#bf3a2e" stroke-width="1.5"/><text x="32" y="40" font-family="serif" font-size="22" font-weight="900" fill="#bf3a2e" text-anchor="middle">合</text></svg>""",encoding="utf-8")
(PUB/"robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n",encoding="utf-8")
today=datetime.date.today().isoformat()
urls="".join(f"<url><loc>{DOMAIN}{('' if p=='/index.html' else p.replace('/index.html','/'))}</loc><lastmod>{today}</lastmod></url>"
  for p in pages if p!="/404.html")
(PUB/"sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',encoding="utf-8")

print(f"built {len(pages)} pages → public/")
