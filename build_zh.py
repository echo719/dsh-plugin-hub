#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中文版渲染器 → public/zh/(与英文版共用 audit 数据,文案独立)"""
import json, os, html, copy, datetime
from pathlib import Path

ROOT = Path(__file__).parent
PUB  = ROOT / "public"
DATA = ROOT / "data"

cfg      = json.load(open(DATA/"site.json", encoding="utf-8"))
zh_local = json.load(open(DATA/"zh"/"local.json", encoding="utf-8"))
site     = {**cfg, "roles": zh_local["roles"]}
scenarios= json.load(open(DATA/"zh"/"scenarios.json", encoding="utf-8"))
releases = json.load(open(DATA/"zh"/"releases.json", encoding="utf-8"))
audit    = json.load(open(ROOT/"audit"/"audit.json", encoding="utf-8"))

DOMAIN  = site["domain"].rstrip("/")
REPO    = site.get("github_repo","")
PLUG    = {p["name"]: copy.deepcopy(p) for p in audit["plugins"] if not p.get("error")}
GEN_AT  = audit["meta"]["generated_at"][:10]

# 人工权限档中文原文(audit.json 已英文化,中文页还原)
ZH_NOTES = {"dsh-chat-import": "读指定 JSONL 文件 · 不联网"}
for _n,_t in ZH_NOTES.items():
    if _n in PLUG and PLUG[_n]["checks"]["permissions"].get("status")=="g":
        PLUG[_n]["checks"]["permissions"]["note"]=_t

def esc(s): return html.escape(str(s), quote=True)

GA4 = ""
if site.get("ga4_id"):
    GA4 = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={site['ga4_id']}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
gtag('js',new Date());gtag('config','{site['ga4_id']}');</script>"""

def shell(title, desc, path, active, content, extra_head=""):
    nav = ""
    for href, key, label in [
        ("/zh/","home","首页"),
        ("/zh/scenarios.html","scenarios","场景库"),
        ("/zh/opc.html","opc","OPC"),
        ("/zh/plugins/","plugins","插件体检"),
        ("/zh/breaking-changes.html","breaking","破坏性变更"),
        ("/zh/scenarios/01-migration.html","guide","上手教程")]:
        cls = ' class="on"' if key==active else ""
        nav += f'<a href="{href}"{cls}>{label}</a>'
    submit = f"https://github.com/{REPO}/issues/new?labels=plugin-submit&title=%5BSubmit%5D+owner%2Frepo" if REPO else "https://github.com/topics/dsh-plugin"
    en_url=f"{DOMAIN}{path}"; zh_url=f"{DOMAIN}/zh{path}"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{zh_url}">
<link rel="alternate" hreflang="en" href="{en_url}">
<link rel="alternate" hreflang="zh-CN" href="{zh_url}">
<link rel="alternate" hreflang="x-default" href="{en_url}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{zh_url}">
<meta property="og:type" content="website">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<title>{esc(title)}</title>
<link rel="stylesheet" href="/assets/style.css">
{GA4}{extra_head}
</head>
<body>
<nav><div class="wrap nav-in">
  <a class="logo" href="/zh/">dsh-plugin-hub<span class="tld">.com</span></a>
  <div class="nav-links">{nav}</div>
  <a class="lang-switch" href="{path}" title="English">EN</a>
  <a class="nav-cta" href="{submit}" rel="nofollow">提交插件</a>
</div></nav>
{content}
<footer><div class="wrap">
  <span class="mark">dsh-plugin-hub<span style="color:var(--seal)">.com</span> · 与 DeepSeek 无关联的社区站</span>
  <a href="/zh/scenarios.html">场景库</a>
  <a href="/zh/opc.html">OPC 工具箱</a>
  <a href="/zh/breaking-changes.html">破坏性变更</a>
  <a href="/zh/about-audit.html">体检方法</a>
  <a href="{submit}" rel="nofollow">提交插件</a>
</div></footer>
</body>
</html>"""

pages=[]
def write(path, htmlstr):
    p=PUB/"zh"/path.lstrip("/")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(htmlstr,encoding="utf-8")
    pages.append("/zh/"+path.lstrip("/"))

os.makedirs(PUB/"zh"/"plugins", exist_ok=True)
os.makedirs(PUB/"zh"/"scenarios", exist_ok=True)

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
    if link: out+=f'<a class="card-link" href="/zh/plugins/{p["name"]}.html">完整体检卡 →</a>'
    return out

def rx_card(name, tag, tag_top, desc_html, triage=""):
    p=PLUG[name]; sc,st=stamp_cls(p)
    tagcls=' top' if tag_top else ''
    return f"""<div class="rx-card" data-t="{triage}">
  <div class="rx-head">
    <span class="name">{esc(name)}</span><span class="tag{tagcls}">{esc(tag)}</span>
    <a class="stamp {sc}" href="/zh/plugins/{name}.html">{'合格' if not sc else st}</a>
  </div>
  <div class="rx-body">
    <div class="desc">{desc_html}</div>
    <div class="checks">{checks_block(p)}</div>
  </div>
  <div class="install"><span>{esc(install_cmd(p))}</span><button class="cp">复制</button></div>
  <div class="install-hint">安装后需 <b>重启 dsh</b> 方可生效(官方文档:the plugin becomes active after restarting dsh)</div>
</div>"""


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
  <span class="badge">热门入口</span><h3>{esc(s['title'])}</h3>
  <p>{esc(s['blurb'])}</p>
  <div class="rx"><span>℞ {len([x for x in s['plugins'] if x in PLUG])} 个已核验插件</span><span>{esc(s['star'])}</span></div></a>"""
    elif s["status"]=="gap":
        sc_cards+=f"""<a class="sc gap-card" href="/zh/scenarios.html">
  <div class="top-line"><span class="sym">GAP {s['num']}</span><span class="cat">{esc(s['cat_s'])}</span></div>
  <h3>{esc(s['title'])}</h3><p>{esc(s['blurb'])}</p>
  <div class="rx"><span>空位 · 征集中</span><span>欢迎提交 →</span></div></a>"""
    else:
        n=len([x for x in s['plugins'] if x in PLUG])
        tail=f"℞ {n} 已核验" if n else "整理中"
        sc_cards+=f"""<a class="sc" href="{href}">
  <div class="top-line"><span class="sym">SYMPTOM {s['num']}</span><span class="cat">{esc(s['cat_s'])}</span></div>
  <h3>{esc(s['title'])}</h3><p>{esc(s['blurb'])}</p>
  <div class="rx"><span>{tail}</span><span>{esc(s.get('star',''))}</span></div></a>"""

roles_html="".join(
    f"""<a class="role" href="/zh/opc.html"><span class="who">{r['who']}</span><span class="n{' gap' if r['gap'] else ''}">{esc(r['n'])}</span></a>"""
    for r in site["roles"])

rel_lines=""
for r in releases["timeline"][:3]:
    rel_lines+=f'<div class="line"><span class="ver">v{esc(r["version"])}</span>'
    rel_lines+=f'<span class="desc">{esc(r["date"])} 发布 · <a href="/zh/breaking-changes.html">{esc(r["note"])}</a></span></div>'

home=f"""<div class="wrap">
<section class="hero">
  <span class="reg tl">┌ EST. 2026-08</span><span class="reg tr">DAILY AUDIT {GEN_AT} ┐</span>
  <div class="hero-tag">DeepSeek Harness (dsh) · 非官方社区站 · 中文为主 / EN summaries</div>
  <h1>不必翻遍分类目录,<br>按<span class="u">问题场景</span>检索插件。</h1>
  <p class="lede">每个场景精选 2–4 个经过体检的插件:权限、维护状态、能否正常激活,安装前一次核对。</p>
  <div class="hero-seal"><span class="b">体检合格</span><span class="s">DSH·PLUGIN·HUB</span></div>
  <div class="search"><span class="prompt">&gt;_</span>
    <input id="q" placeholder="检索问题场景,如:context 超限 / 安装后未生效">
    <button onclick="location.href='/zh/scenarios.html'">找处方</button></div>
  <div class="hot-q"><span>常见问题:</span>
    <a href="/zh/scenarios/01-migration.html">Claude Code / Codex 迁移</a>
    <a href="/zh/scenarios.html">context 超限</a>
    <a href="/zh/scenarios.html">安装后未生效</a>
    <a href="/zh/breaking-changes.html">升级后插件失效</a></div>
  <div class="hero-stats">
    <span><b>{len(scenarios)}</b>场景收录 · 首批陆续上线</span>
    <span><b>{n_aud}</b>已核验并体检的插件</span>
    <span><b>每日</b>09:20 数据更新</span></div>
</section>
<div class="hooks">
  <div class="hook"><span class="k">01 · CHECKUP</span><h3>安装前先看体检结果</h3>
    <p>权限 / 维护状态 / dsh.bundle / 测试CI 四项检查,不合格项直接标注,不以 star 数代替质量判断。</p></div>
  <div class="hook"><span class="k">02 · BREAKING</span><h3>破坏性变更持续追踪</h3>
    <p>官方声明 THERE WILL BE COMPATIBILITY-BREAKING CHANGES。每次发版逐项核读,给出升级建议。</p></div>
  <div class="hook"><span class="k">03 · 症状 → 处方</span><h3>按使用场景组织,而非仓库列表</h3>
    <p>区别于平铺式目录,每个场景页提供可直接使用的安装方案与常见问题提示。</p></div>
</div>
<div class="sec-head"><span class="no">SECTION 01</span><h2>按场景检索</h2>
  <span class="sub">症状 → 处方 · 数量仅统计已核验存在的插件</span>
  <a class="more" href="/zh/scenarios.html">全部 {len(scenarios)} 个场景 →</a></div>
<div class="grid">{sc_cards}</div>
<div class="band">
  <div class="band-h"><span class="no">SECTION 02</span><h2>一人公司工具箱</h2>
    <span class="sub">按业务方向组织插件方案</span>
    <a class="more" href="/zh/opc.html">全部 10 个方向 →</a></div>
  <div class="roles">{roles_html}</div>
</div>
<div class="sec-head"><span class="no">SECTION 03</span><h2>插件体检</h2>
  <span class="sub">不止列出插件,还给出可安装性结论</span>
  <a class="more" href="/zh/plugins/{site['home_report_plugin']}.html">查看完整体检卡 →</a></div>
<div class="checkup">
  <div class="checkup-copy">
    <p>dsh 处于 developer preview 阶段,插件质量参差。每个收录插件均通过四项检查,不合格项直接标注:</p>
    <ul><li>权限范围 — 文件读写、网络访问、系统资源</li>
      <li>维护状态 — 最近一次有效更新距今时长</li>
      <li>能否正常激活 — 是否声明 dsh.bundle</li>
      <li>测试与 CI 覆盖情况</li></ul>
    <div class="verdicts"><span class="p">体检合格 {n_pass}</span><span class="w">注意 / 待复核 {n_aud-n_pass}</span></div>
    <p class="pipe-note">维护状态、dsh.bundle、测试CI 三项每日自动采集;权限一项由人工复核,复核超 60 天且仓库有更新时自动降回"待复核"——未经复核不给出权限结论。<a href="/zh/about-audit.html">体检方法说明 →</a></p>
  </div>
  <div class="report">
    <div class="report-head"><span class="name">{esc(rep['name'])}</span><span class="serial">AUDIT {GEN_AT}</span></div>
    {report_rows}
    <div class="mini-seal">合格</div>
    <div class="report-foot"><span>数据每日自动采集</span><span class="barcode"></span>
      <a href="/zh/plugins/{rep['name']}.html">完整体检卡 →</a></div>
  </div>
</div>
</div>
<div class="navy-band"><div class="wrap">
  <div class="sec-head"><span class="no" style="color:#ff9d8d">SECTION 04</span><h2>破坏性变更追踪</h2>
    <span class="sub">官方原话:THERE WILL BE COMPATIBILITY-BREAKING CHANGES</span>
    <a class="more" href="/zh/breaking-changes.html" style="color:#8fb3ff">完整时间线 →</a></div>
  <div class="strip">{rel_lines}
    <div class="strip-foot"><span>升级 dsh 前,建议先核对本表</span>
      <a href="https://github.com/deepseek-ai/deepseek-harness/releases" rel="nofollow">官方 Releases</a>
      <a href="/zh/breaking-changes.html">本站核读</a></div>
  </div>
</div></div>
<script>document.getElementById('q').addEventListener('keydown',e=>{{if(e.key==='Enter')location.href='/zh/scenarios.html'}});</script>"""
write("index.html", shell("DSH Plugin Hub — 按问题场景检索插件,安装前先看体检",
  "按问题场景检索 DeepSeek Harness 插件。每个插件经过四项体检(权限/维护/dsh.bundle/测试CI),破坏性变更持续追踪。",
  "/", "home", home))

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
  <h1 style="font-size:36px;margin-top:8px">{len(scenarios)} 个使用场景,按类检索</h1>
  <p class="lede" style="margin-top:8px;max-width:660px">七大类按使用场景组织。<b style="color:var(--ink)">已开方</b> = 方案页已上线;<b style="color:var(--ink)">开方中 / 整理中</b> = 插件已核验、页面撰写中;<b style="color:var(--amber)">空位</b> = 生态暂无成熟插件,先行收录需求。</p>
  <div class="search" style="margin-top:20px;max-width:560px"><span class="prompt">&gt;_</span>
    <input id="q" placeholder="检索场景:context / 通知 / 表格 / 记忆 …"></div>
  <div class="filters">
    <button class="fchip on" data-f="all">全部</button>
    <button class="fchip" data-f="live">已开方</button>
    <button class="fchip" data-f="wip">开方/整理中</button>
    <button class="fchip" data-f="gap">空位征集</button></div>
  <div class="count-line" id="count"></div>
</header>
{cat_html}
<div class="note"><span class="k">HOW THIS LIST GROWS · 收录节奏</span>
方案页按插件核验进度陆续开放;<b>处方数仅统计已核验存在的插件</b>。空位场景仅建立占位页,对应插件出现后第一时间体检收录。每周例行扫描 dsh-plugin topic 增量,归入现有场景或新建场景,并更新兼容状态。</div>
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
  "30 个 DSH 真实使用场景,七大类分类,按场景检索插件方案。","/scenarios.html","scenarios",scen_page))

# ---- SYM 01 场景页 ----
s01=next(s for s in scenarios if s["id"]=="01-migration")
cards_a="".join(rx_card(*args) for args in s01["rx_a"])
cards_b="".join(rx_card(*args) for args in s01["rx_b"])
habit_rows="".join(f"<div>{esc(a)}</div><div class='p'>{esc(b)}</div>" for a,b in s01["habit"])
rel_links="".join(f"""<a href="/zh/scenarios.html"><span class="s">SYMPTOM {n}</span>{esc(t)}</a>""" for n,t in s01["related"])
s01_page=f"""<div class="wrap">
<div class="crumb"><a href="/zh/scenarios.html">场景库</a> / A·迁移与上手</div>
<header class="hero" style="padding:22px 0 8px">
  <div class="sym">SYMPTOM · 场景 01 · 已开方</div>
  <h1 style="font-size:36px;margin-top:8px;line-height:1.3">{esc(s01['title'])}</h1>
  <p class="lede" style="margin-top:12px;max-width:660px">{s01['lede']}</p>
  <p class="en-line"><b>EN</b> {esc(s01['en'])}</p>
  <div class="triage">
    <button class="chip on" data-t="all">全部处方</button>
    <button class="chip" data-t="cc">Claude Code 用户</button>
    <button class="chip" data-t="codex">Codex 用户</button>
    <button class="chip" data-t="move">迁移会话历史</button></div>
  <div class="chip-hint" id="chipHint">选择迁移来源,筛选相关处方</div>
</header>
<section class="sec"><div class="sec-h"><span class="no">壹</span><h2>功能对照:原工具功能与 dsh 对应插件</h2></div>
<div class="habit"><div class="h">Claude Code / Codex 功能</div><div class="h">dsh 对应插件</div>{habit_rows}</div></section>
<section class="sec"><div class="sec-h"><span class="no">贰</span><h2>操作习惯还原</h2><span class="sub">按需安装</span></div>{cards_a}</section>
<section class="sec"><div class="sec-h"><span class="no">叁</span><h2>会话历史迁移</h2><span class="sub">历史会话可完整保留</span></div>{cards_b}</section>
<section class="sec"><div class="sec-h"><span class="no">肆</span><h2>迁移常见问题</h2><span class="sub">依据官方文档与真实体检</span></div>
<div class="pit"><h3>安装后未生效:检查 dsh.bundle 声明</h3>
<p>官方文档:没有 <code>dsh.bundle</code> 声明的包"仍然可以安装,但只作为普通依赖……不激活任何层"。本站体检卡包含该检查项——本页处方中即有一个插件当前未声明,体检卡已标红。</p></div>
<div class="pit"><h3>安装命令以官方文档为准</h3>
<p>当前官方流程仅有包规格写法:<code>dsh plugin --profile web add &lt;npm包名 | github:owner/repo&gt;</code>(本地开发用 <code>link:</code>)。早期文章流传的其他安装形式在官方文档中已不存在,按旧写法安装会失败。<a href="/zh/breaking-changes.html">版本变更追踪 →</a></p></div>
<div class="pit"><h3>安装后需重启</h3>
<p>插件作者与官方文档一致确认:安装后<b>重启 dsh 方可生效</b>("the plugin becomes active after restarting dsh")。未重启时插件不生效,并非安装失败。</p></div></section>
<section class="sec"><div class="sec-h"><span class="no">伍</span><h2>相关场景</h2></div>
<div class="rel">{rel_links}</div></section>
<div class="data-note"><span>本页体检数据 {GEN_AT} 采集 · 权限项人工复核中,完成后逐项更新</span>
<a href="/zh/about-audit.html">体检方法说明</a></div>
<div class="pager"><a href="/zh/scenarios.html"><span class="lbl">← 返回</span><b>场景库 · 分诊台</b></a>
<a class="next" href="/zh/scenarios.html"><span class="lbl">下一个场景</span><b>SYM 02 SillyTavern 迁移到 DSH(开方中)</b></a></div>
</div>
<script>
const chips=document.querySelectorAll('.chip'),cards=document.querySelectorAll('.rx-card'),hint=document.getElementById('chipHint');
chips.forEach(c=>c.addEventListener('click',()=>{{chips.forEach(x=>x.classList.remove('on'));c.classList.add('on');
const t=c.dataset.t;cards.forEach(k=>k.classList.toggle('dim',t!=='all'&&!(k.dataset.t||'').split(' ').includes(t)));
hint.textContent=(t==='all')?'选择迁移来源,筛选相关处方':'高亮为相关处方,其余可跳过'}}));
document.querySelectorAll('.cp').forEach(b=>b.addEventListener('click',()=>{{
const cmd=b.parentElement.querySelector('span').textContent;
if(navigator.clipboard)navigator.clipboard.writeText(cmd);
b.textContent='已复制';setTimeout(()=>b.textContent='复制',1500)}}));
</script>"""
write("scenarios/01-migration.html", shell(
  "Claude Code / Codex 迁移到 DSH:插件方案与常见问题 — DSH Plugin Hub",
  "保留 @file、批注、TUI 操作习惯,并迁移会话历史。全部处方经真实仓库核验体检,含三类迁移常见问题(依据官方文档)。",
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
<div class="crumb"><a href="/zh/">首页</a> / <a href="/zh/plugins/">插件体检</a> / {esc(name)}</div>
<div class="head-card">
  <div class="head-top">
    <div class="name">{esc(name)}<small><a href="https://github.com/{esc(p['repo'])}" rel="nofollow">github.com/{esc(p['repo'])}</a>{ver}</small></div>
    <div class="big-seal {sc}"><span class="b">{st}</span><span class="s">DSH·PLUGIN·HUB</span></div>
  </div>
  <p class="head-desc">{desc}</p>
  <div class="head-tags">{scen_tags}</div>
  <div class="install"><span>{esc(install_cmd(p))}</span><button class="cp" onclick="const s=this.parentElement.querySelector('span').textContent;if(navigator.clipboard)navigator.clipboard.writeText(s);this.textContent='已复制';setTimeout(()=>this.textContent='复制',1500)">复制</button></div>
  <p class="install-hint">安装后需 <b>重启 dsh</b> 方可生效 · 未重启时插件不生效,并非安装失败</p>
  <div class="serial-strip"><span>AUDIT {GEN_AT}</span><span class="barcode"></span></div>
</div>
<section class="sec"><div class="sec-h"><h2>四项检查</h2><span class="sub">采集于 {GEN_AT} · 每日自动更新</span></div>
<div class="check"><div class="check-h"><span class="light {pm[0].replace('p','p')}"></span><span class="t">① 权限范围</span>
  <span class="v"><b>{esc(pm[1])}</b></span></div>
  <div class="check-b"><div class="cell"><span class="k">自动线索</span>{esc(hint_txt)}。</div>{perm_cell2}
  <div class="policy"><b>权限为何采用人工档:</b>权限范围缺乏可靠的自动判定方法,因此仅由人工复核给出结论。人工结论超过 60 天且仓库有更新时,自动降回"待人工复核"。</div></div></div>
<div class="check"><div class="check-h"><span class="light {m['status']}"></span><span class="t">② 维护状态</span>
  <span class="v"><b>{esc(maint_txt(p))}</b><br>最近提交 {m['last_commit']}</span></div>
  <div class="check-b single"><div class="cell"><span class="k">判定规则</span>最后提交 ≤ <code>14 天</code> 绿 · ≤ <code>45 天</code> 黄 · 更久或已 archived 红。</div></div></div>
<div class="check"><div class="check-h"><span class="light {bd[0]}"></span><span class="t">③ dsh.bundle</span>
  <span class="v"><b>{esc(bd[1])}</b></span></div>
  <div class="check-b single"><div class="cell"><span class="k">检查依据</span>官方文档:没有 <code>dsh.bundle</code> 声明的包只作为普通依赖安装,<b>不激活任何层</b>——安装后未生效的常见原因。</div></div></div>
<div class="check"><div class="check-h"><span class="light {ts[0]}"></span><span class="t">④ 测试 / CI</span>
  <span class="v"><b>{esc(ts[1])}</b></span></div>
  <div class="check-b"><div class="cell"><span class="k">测试</span>{'发现 test 脚本或测试目录。' if p['checks']['tests_ci']['tests'] else '未发现 test 脚本或测试目录。'}</div>
  <div class="cell"><span class="k">CI</span>{'发现 .github/workflows 工作流。' if p['checks']['tests_ci']['ci'] else '未发现 CI 工作流。'}</div></div></div>
</section>
<section class="sec"><div class="sec-h"><h2>体检历史</h2></div>
<div class="hist"><div class="h-item"><span class="d">{GEN_AT}</span> · <b>首次收录体检</b>(判定:{st});兼容追踪随每日体检持续更新</div></div></section>
<div class="cta-row">
  <a class="pri" href="{'/zh/scenarios/01-migration.html' if any(name in s.get('plugins',[]) and s['status']=='live' for s in scenarios) else '/zh/scenarios.html'}">看它所在的场景处方 →</a>
  <a href="https://github.com/{esc(p['repo'])}/issues" rel="nofollow">结论有误?提交反馈</a>
  <a href="/zh/about-audit.html">体检方法说明</a></div>
</div>"""
    write(f"plugins/{name}.html", shell(f"{name} · 完整体检卡 — DSH Plugin Hub",
        f"{name} 插件体检:权限、维护状态、dsh.bundle、测试CI 四项检查,数据每日自动采集。",
        f"/plugins/{name}.html","plugins",body))
    plug_index_rows+=f"""<a class="srow" href="/zh/plugins/{name}.html">
  <span class="no" style="width:auto"><span class="dot {'g' if p['verdict']=='pass' else 'y' if p['verdict']=='watch' else 'p'}"></span></span>
  <span class="t"><b style="font-family:var(--mono);font-size:14px">{esc(name)}</b><small>{esc((p.get('desc') or '')[:90])}</small></span>
  <span class="rx">{esc(maint_txt(p))}</span>
  <span class="badge {'t1' if p['verdict']=='pass' else 't2'}">{st}</span><span class="arrow">→</span></a>"""

plist=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 12px">
  <div class="kicker">CHECKUP · 体检大厅</div>
  <h1 style="font-size:36px;margin-top:8px">{n_aud} 个插件,四项检查</h1>
  <p class="lede" style="margin-top:8px;max-width:660px">全部收录插件的体检结果。<b style="color:var(--ink)">合格</b> = 四项全绿且完成人工权限复核;<b style="color:var(--ink)">待复核</b> = 自动三项通过、权限待人工复核;<b style="color:var(--amber)">注意</b> = 存在红项,安装前请确认。</p>
  <div class="search" style="margin-top:20px;max-width:560px"><span class="prompt">&gt;_</span>
    <input id="pq" placeholder="搜插件名或功能 …"></div>
</header>
<div class="slist" style="margin-top:26px">{plug_index_rows}</div>
<div class="note"><span class="k">METHOD</span>体检方法与判定规则公开:<a href="/zh/about-audit.html" style="color:var(--blue)">看这页</a>。数据每日北京时间 09:20 自动采集。</div>
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
  <h1 style="font-size:36px;margin-top:8px">dsh 版本变更核读</h1>
  <p class="lede" style="margin-top:12px;max-width:660px">dsh 处于 developer preview 阶段,官方已明确提示兼容性风险。本页跟踪每次发版并核读变更内容:改动范围、受影响插件、升级建议。</p>
  <div class="quote">"DeepSeek Harness is currently in developer preview and is iterating rapidly. <b>THERE WILL BE COMPATIBILITY-BREAKING CHANGES.</b>"<small>— deepseek-ai/deepseek-harness 官方 README(2026-08 实录)</small></div>
  <div class="sub-row">
    <a class="pri" href="https://github.com/deepseek-ai/deepseek-harness/releases" rel="nofollow">Watch 官方 Releases</a>
    <a href="https://github.com/deepseek-ai/deepseek-harness/discussions" rel="nofollow">官方 Discussions</a></div>
</header>
<div class="selfcheck"><span class="k">30-SECOND CHECK</span><h2>升级前 30 秒自查</h2>
<div class="steps">
  <div class="step"><span class="n">第一步</span><br>执行 <code>dsh --version</code>,记录当前版本。</div>
  <div class="step"><span class="n">第二步</span><br>在下方时间线中找到目标版本,确认是否带 <b style="color:var(--seal)">BREAKING</b> 标注。</div>
  <div class="step"><span class="n">第三步</span><br>存在 BREAKING 时,先核对已装插件的<a href="/zh/plugins/" style="color:var(--blue)">体检卡</a>再升级。</div></div></div>
<section class="sec"><div class="sec-h"><h2>版本时间线</h2><span class="sub">数据来自 npm registry · 每日更新 · "核读中" = 变更内容尚未逐项核对,暂不标注结论</span></div>
{tl}</section>
<section class="sec"><div class="sec-h"><h2>已核实的安装迁移问题</h2><span class="sub">依据:官方文档与真实插件仓库</span></div>
<div class="pit"><h3>未声明 dsh.bundle 的包,安装后不激活</h3><p>官方文档原文:此类包"仍然可以安装,但只作为普通依赖……不激活任何层"。<a href="/zh/plugins/">体检大厅</a>中未声明的插件已全部标红。</p></div>
<div class="pit"><h3>安装命令以官方文档为准</h3><p>当前唯一官方流程:<code>dsh plugin --profile &lt;name&gt; add &lt;npm包 | github:owner/repo | link:本地路径&gt;</code>。早期文章中的其他安装形式在官方文档中已不存在。</p></div>
<div class="pit"><h3>安装后需重启 dsh</h3><p>插件激活发生在重启之后。安装后未生效时,先重启再排查。</p></div></section>
<div class="how"><b>跟踪机制:</b>每日自动抓取 npm 发版与官方仓库变动;新版本先标"核读中",人工核对变更后再标注 BREAKING / 非破坏,同日对全部收录插件重跑体检。<b>核读完成前不给出结论。</b></div>
</div>"""
write("breaking-changes.html", shell("破坏性变更追踪 — DSH Plugin Hub",
  "DSH 官方声明 THERE WILL BE COMPATIBILITY-BREAKING CHANGES。每个版本的变更内容核读与升级建议。",
  "/breaking-changes.html","breaking",brk))

# ---- OPC ----
opc=json.load(open(DATA/"zh"/"opc.json",encoding="utf-8"))
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
  <div class="name">{esc(c['plugin'])} <a class="stamp-s {sc[:1] if sc else ''}" href="/zh/plugins/{c['plugin']}.html">{('合格' if not sc else ('注意' if sc=='warn' else '待复核'))}</a></div>
  <p>{c['desc']}</p>
  <div class="foot"><a href="/zh/plugins/{c['plugin']}.html">完整体检卡 →</a></div></div>"""
issue_base=f"https://github.com/{REPO}/issues" if REPO else "https://github.com/topics/dsh-plugin"
votes=""
for v in opc["gaps"]:
    votes+=f"""<div class="vote"><span class="t">{esc(v['t'])}<small>{esc(v['s'])}</small></span>
  <a class="btn" href="{issue_base}" rel="nofollow">+1 · GitHub issue</a></div>"""
guides="".join(f"""<div class="bridge"><span class="k">GUIDE {i+1:02d}</span><p>{g}</p><span style="font-family:var(--mono);font-size:12px;color:#8a8f98">撰写中 · 即将上线</span></div>""" for i,g in enumerate(opc["guides"]))
opc_page=f"""<div class="wrap">
<header class="hero" style="padding:52px 0 8px">
  <div class="kicker">ONE-PERSON COMPANY · 工具箱</div>
  <h1 style="font-size:36px;margin-top:8px">按业务方向选择插件方案</h1>
  <p class="lede" style="margin-top:10px;max-width:680px">十个一人公司方向,每个方向 = <b style="color:var(--ink)">精选处方 + 相关场景组合 + 空位征集</b>。工具箱并非独立目录,而是场景库组合按业务方向的重新编排。</p>
  <div class="role-grid">{role_cards}</div>
  <p class="idx-note">带"空位"标注的方向暂无对口插件,先以站长实操教程补位(基于现有插件搭建流水线),同时公开征集需求;对应插件出现后第一时间体检收录。其余方向落地页按核验进度陆续开放,首个为跨境电商。</p>
</header>
<hr style="border:0;border-top:2px dashed var(--hair);margin:42px 0 0">
<div id="landing" class="crumb">一人公司工具箱 / 跨境电商</div>
<header class="hero" style="padding:18px 0 6px">
  <div class="role-tag" style="font-family:var(--mono);font-size:12px;color:var(--seal);letter-spacing:2.5px">TOOLBOX · 跨境电商</div>
  <h1 style="font-size:32px;max-width:720px;line-height:1.32">跨境电商运营中的 DSH 插件方案</h1>
  <p class="lede" style="max-width:680px">竞品与订单数据、报表、产品图检查等重复性运营工作,已核验的 DSH 插件可承接一部分。<b style="color:var(--ink)">可用方案如下,缺失能力可通过征集反馈。</b></p>
  <p class="en-line"><b>EN</b> Running a cross-border e-commerce store solo? Audited DSH plugins to offload data pulls, spreadsheets and image QA.</p>
</header>
<section class="sec"><div class="sec-h"><span class="no">壹</span><h2>当前可用的处方</h2><span class="sub">仅列已核验存在并通过体检的插件</span></div>
<div class="rx-grid">{rx_cards}</div></section>
<section class="sec"><div class="sec-h"><span class="no">贰</span><h2>相关场景</h2><span class="sub">来自场景库的组合</span></div>
<div class="flow">
  <a href="/zh/scenarios.html"><span class="s">SYMPTOM 10</span>成本控制与用量监控</a>
  <a href="/zh/scenarios.html"><span class="s">SYMPTOM 23</span>任务完成通知</a>
  <a href="/zh/scenarios/01-migration.html"><span class="s">SYMPTOM 01</span>从其他工具迁移到 DSH</a></div></section>
<section class="sec"><div class="sec-h"><span class="no">叁</span><h2>能力缺口征集</h2><span class="sub">征集数据公开可查</span></div>
<div class="gap-box">
  <p class="intro">以下能力需求常见,但 <b>DSH 生态暂无成熟插件</b>(或本站尚未核验到)。可在 GitHub 对应 issue 点 👍 表达需求,数据公开;按需求热度优先追踪,对应插件出现后第一时间体检收录。</p>
  <div class="votes">{votes}</div>
  <p class="gap-cta">插件作者可提交对应方向的作品 → <a href="{issue_base}" rel="nofollow">优先安排体检</a></p></div></section>
<section class="sec"><div class="sec-h"><span class="no">肆</span><h2>过渡方案:站长实操教程</h2><span class="sub">基于现有插件的组合方案</span></div>
{guides}
<p class="bridge-sub">教程基于站长的跨境 / SEO 实操经验;同一方式亦用于 SEO 内容站、视频自媒体两个空位方向。</p></section>
</div>"""
write("opc.html", shell("一人公司工具箱 · 跨境电商 — DSH Plugin Hub",
  "按业务方向(跨境电商/SEO内容站/视频自媒体等)组合 DSH 插件方案,仅收录经核验的插件,缺口公开征集。",
  "/opc.html","opc",opc_page))

# ---- 404 ----
write("404.html", shell("页面不存在 — DSH Plugin Hub","页面不存在。","/404.html","",
"""<div class="wrap"><header class="hero"><div class="kicker">404 · NOT FOUND</div>
<h1 style="font-size:40px;margin-top:8px">页面不存在</h1>
<p class="lede" style="margin-top:12px">链接可能已失效,或对应场景页尚未上线。可前往<a href="/zh/scenarios.html" style="color:var(--blue)">场景库</a>检索,或返回<a href="/zh/" style="color:var(--blue)">首页</a>。</p></header></div>"""))


(ROOT/"_pages_zh.json").write_text(json.dumps(pages))
print(f"[zh] built {len(pages)} pages → public/zh/")
