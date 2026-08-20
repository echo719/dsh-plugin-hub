#!/usr/bin/env python3
"""双语收尾:favicon / robots / sitemap(en+zh 全量)"""
import json, datetime
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
def loc(p):
    # /page.html 与 /page/index.html 都归一到 Cloudflare 实际提供服务的规范网址
    # (html_handling: auto-trailing-slash 会把 .html 重定向掉),sitemap 不再自相矛盾。
    if p.endswith("/index.html"): p=p[:-10]
    elif p.endswith(".html"): p=p[:-5]
    return p
urls="".join(f"<url><loc>{DOMAIN}{loc(p)}</loc><lastmod>{today}</lastmod></url>"
  for p in pages if not p.endswith("/404.html"))
(PUB/"sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',encoding="utf-8")
print(f"[finalize] sitemap {len(pages)} pages (en+zh)")
