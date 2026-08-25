#!/usr/bin/env python3
"""双语收尾:favicon / robots / sitemap(en+zh 全量)"""
import json, datetime, hashlib
from pathlib import Path
ROOT=Path(__file__).parent; PUB=ROOT/"public"
site=json.load(open(ROOT/"data"/"site.json",encoding="utf-8"))
DOMAIN=site["domain"].rstrip("/")
pages=[]
for f in ("_pages_en.json","_pages_zh.json"):
    pages+=json.load(open(ROOT/f))
(PUB/"assets").mkdir(parents=True,exist_ok=True)
(PUB/"assets"/"favicon.svg").write_text(
"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="28" fill="none" stroke="#bf3a2e" stroke-width="4"/><circle cx="32" cy="32" r="22" fill="none" stroke="#bf3a2e" stroke-width="1.5"/><text x="32" y="42" font-family="serif" font-size="26" font-weight="900" fill="#bf3a2e" text-anchor="middle">℞</text></svg>""",encoding="utf-8")
(PUB/"robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n",encoding="utf-8")
today=datetime.date.today().isoformat()

# 体检数据的采集日期:插件页正文里印着它,每天都会变。算内容指纹时要和 today 一起抹掉,
# 否则"内容其实没动、只有日期戳变了"也会被当成改动。
try:
    GEN_AT=json.load(open(ROOT/"audit"/"audit.json",encoding="utf-8"))["meta"]["generated_at"][:10]
except Exception:
    GEN_AT=today

def loc(p):
    # /page.html 与 /page/index.html 都归一到 Cloudflare 实际提供服务的规范网址
    # (html_handling: auto-trailing-slash 会把 .html 重定向掉),sitemap 不再自相矛盾。
    if p.endswith("/index.html"): p=p[:-10]
    elif p.endswith(".html"): p=p[:-5]
    return p
# lastmod:内容真的变了才推进日期。做法是把每天都会变的日期戳抹掉之后算一次指纹,
# 指纹和上次一样就沿用上次的日期。避免全站 94 个页面天天集体"最后修改于今天",
# 那种信号 Google 学会忽略之后,真正改过的页也换不来优先抓取。
STATE=ROOT/"data"/"lastmod.json"
try:
    prev=json.load(open(STATE,encoding="utf-8"))
except Exception:
    prev={}

def fingerprint(path):
    try:
        src=(PUB/path.lstrip("/")).read_text(encoding="utf-8")
    except OSError:
        return ""
    src=src.replace(today,"@D@").replace(GEN_AT,"@D@")
    return hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]

state={}; parts=[]; kept=0
for p in pages:
    if p.endswith("/404.html"): continue
    h=fingerprint(p)
    old_rec=prev.get(p)
    if old_rec and old_rec.get("h")==h:
        lm=old_rec.get("d",today); kept+=1
    else:
        lm=today
    state[p]={"h":h,"d":lm}
    parts.append(f'<url><loc>{DOMAIN}{loc(p)}</loc><lastmod>{lm}</lastmod></url>')
json.dump(state,open(STATE,"w",encoding="utf-8"),indent=0,sort_keys=True)
urls="".join(parts)
(PUB/"sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',encoding="utf-8")
print(f"[finalize] sitemap {len(parts)} pages (en+zh) · lastmod 沿用旧日期 {kept} 页 / 推进到 {today} {len(parts)-kept} 页")
