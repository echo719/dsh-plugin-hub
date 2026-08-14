#!/usr/bin/env python3
"""public/ 上线前校验:标签配对、内链有效、必备 meta、体检数值来源抽查。exit 0 = 可推。"""
import re, os, sys, json
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).parent; PUB=ROOT/"public"
VOID={'meta','br','hr','img','input','link','wbr','source','col'}

class Chk(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.stack=[]; self.errs=[]
    def handle_starttag(self,t,a):
        if t not in VOID: self.stack.append((t,self.getpos()[0]))
    def handle_endtag(self,t):
        if t in VOID: return
        if self.stack and self.stack[-1][0]==t: self.stack.pop()
        else:
            for i in range(len(self.stack)-1,-1,-1):
                if self.stack[i][0]==t:
                    self.errs.append(f"L{self.getpos()[0]} </{t}> 越过未闭合 {[x for x,_ in self.stack[i+1:]]}")
                    del self.stack[i:]; break
            else: self.errs.append(f"L{self.getpos()[0]} 多余 </{t}>")

problems=[]
pages=sorted(PUB.rglob("*.html"))
if len(pages)<5: problems.append(f"页面数异常: {len(pages)}")
for f in pages:
    rel="/"+str(f.relative_to(PUB))
    src=f.read_text(encoding="utf-8")
    c=Chk(); c.feed(src)
    for e in c.errs: problems.append(f"{rel}: {e}")
    for t,l in c.stack: problems.append(f"{rel}: 未闭合 <{t}> L{l}")
    if rel!="/404.html":
        for need in ('name="description"','rel="canonical"','<title>'):
            if need not in src: problems.append(f"{rel}: 缺 {need}")
    for m in re.finditer(r'href="(/[^"#]*)"',src):
        p=m.group(1)
        tgt=PUB/p.lstrip("/")
        if p.endswith("/"): tgt=tgt/"index.html"
        if not tgt.exists(): problems.append(f"{rel}: 死内链 {p}")
    # 虚构 dsh 版本拦截:只查展示 dsh 版本时间线的页面(插件自身版本号可能合法地是 0.4.x)
    if rel in ("/index.html","/breaking-changes.html") and re.search(r'v0\.4\.[0-2]',src):
        problems.append(f"{rel}: 出现虚构 dsh 版本号 v0.4.x")

# 数值来源抽查:首页体检卡行数必须与 audit.json 对得上
audit=json.load(open(ROOT/"audit"/"audit.json",encoding="utf-8"))
idx=(PUB/"index.html").read_text(encoding="utf-8")
rep=next(p for p in audit["plugins"] if p["name"]=="dsh-chat-import")
if rep["checks"]["maintenance"]["last_commit"] not in idx:
    problems.append("首页体检卡维护日期与 audit.json 不符")
n=audit["meta"]["count"]
if f"<b>{n}</b>" not in idx: problems.append("首页插件数与 audit.json 不符")

for extra in ("sitemap.xml","robots.txt","assets/style.css","assets/favicon.svg"):
    if not (PUB/extra).exists(): problems.append(f"缺 {extra}")

if problems:
    print("VALIDATE FAIL:"); [print(" -",p) for p in problems]; sys.exit(1)
print(f"VALIDATE PASS · {len(pages)} pages")
