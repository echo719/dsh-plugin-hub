#!/usr/bin/env python3
"""每日体检:git 浅克隆采集(Actions 里跑)。读 plugins.json + overrides.json → 写 audit.json。
权限:自动只给线索;结论读人工档;人工结论>60天且仓库有更新 → 降回待复核。"""
import json, os, subprocess, shutil, tempfile, concurrent.futures as cf
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
PLUGINS = json.load(open(HERE/"plugins.json"))
OVR = json.load(open(HERE/"overrides.json")) if (HERE/"overrides.json").exists() else {}
NET  = {"axios","node-fetch","undici","got","ws","socket.io-client","openai"}
EXEC = {"execa","shelljs","cross-spawn","node-pty","zx"}
FRESH_G, FRESH_Y, MANUAL_TTL = 14, 45, 60

def audit(entry):
    name, repo = entry["name"], entry["repo"]
    d = tempfile.mkdtemp(); out = {"name":name,"repo":repo,"error":None,"checks":{}}
    try:
        r = subprocess.run(['git','clone','--depth','1','--quiet',
            f'https://github.com/{repo}.git', d], capture_output=True, timeout=120)
        if r.returncode: out["error"]="clone_fail"; return out
        iso = subprocess.run(['git','-C',d,'log','-1','--format=%cI'],
            capture_output=True,text=True,timeout=20).stdout.strip()
        days = (datetime.now(timezone.utc)-datetime.fromisoformat(iso)).days
        out["checks"]["maintenance"]={"status":"g" if days<=FRESH_G else "y" if days<=FRESH_Y else "r",
            "last_commit":iso[:10],"days":days}
        pj={}
        p=os.path.join(d,'package.json')
        if os.path.exists(p):
            try: pj=json.load(open(p))
            except: pass
        bundle=bool(pj.get('dsh',{}).get('bundle'))
        out["checks"]["bundle"]={"status":"g" if bundle else "r","declared":bundle}
        deps={**pj.get('dependencies',{}),**pj.get('devDependencies',{})}
        hints=sorted((set(deps)&NET)|(set(deps)&EXEC))
        has_test=bool(pj.get('scripts',{}).get('test')) or \
            any(os.path.isdir(os.path.join(d,t)) for t in('test','tests','__tests__'))
        wf=os.path.join(d,'.github','workflows')
        has_ci=os.path.isdir(wf) and any(f.endswith(('.yml','.yaml')) for f in os.listdir(wf))
        out["checks"]["tests_ci"]={"status":"g" if has_test and has_ci else "y" if (has_test or has_ci) else "r",
            "tests":has_test,"ci":has_ci}
        perm={"status":"pending","note":"Pending manual review","hints":hints}
        ov=OVR.get(repo,{}).get("permissions")
        if ov and ov.get("status")=="g":
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(ov["reviewed_at"]+"T00:00:00+00:00")).days
            if age>MANUAL_TTL and days<age:
                perm={"status":"pending","note":f"Manual review older than {MANUAL_TTL} days with new commits since — reverted to pending","hints":hints}
            else:
                perm={**ov,"hints":hints}
        out["checks"]["permissions"]=perm
        out["desc"]=(pj.get('description') or '')[:220]
        out["version"]=pj.get('version','')
    except Exception as e:
        out["error"]=str(e)[:120]
    finally:
        shutil.rmtree(d,ignore_errors=True)
    return out

def verdict(r):
    if r["error"]: return "error"
    c=r["checks"]
    if c["bundle"]["status"]=="r" or c["maintenance"]["status"]=="r": return "watch"
    if c["permissions"]["status"]=="pending": return "watch_pending"
    if all(c[k]["status"]=="g" for k in("maintenance","bundle","tests_ci")) and c["permissions"]["status"]=="g": return "pass"
    return "watch"

results=[]
with cf.ThreadPoolExecutor(6) as ex:
    results=list(ex.map(audit,PLUGINS))
for r in results: r["verdict"]=verdict(r)
ok=[r for r in results if not r["error"]]
if len(ok) < len(PLUGINS)*0.7:
    raise SystemExit(f"abort: only {len(ok)}/{len(PLUGINS)} audited, keeping previous audit.json")
meta={"generated_at":datetime.now(timezone.utc).isoformat()[:19]+"Z","count":len(ok),"source":"daily-git-clone"}
json.dump({"meta":meta,"plugins":results},open(HERE/"audit.json","w"),ensure_ascii=False,indent=1)
print("audited",len(ok),"/",len(PLUGINS))

# ---- dsh 版本时间线:每天从 npm registry 实录一次,人工写的说明按版本号保留 ----
# 不加这一步的话 data/releases.json 就是一张死快照,而页面上"每日更新"那句话是假的
# (2026-08-25 发现它停在 8/15、漏了 4 个版本,其中含一次 0.1.0 -> 0.1.1 的版本线跃迁)。
import urllib.request, urllib.parse

NPM_PKG = "@deepseek-ai/dsh"
SITE = HERE.parent
EN_DEFAULT = {"pending": True, "note": "Review in progress", "note_html": "Change review in progress."}
ZH_DEFAULT = {"pending": True, "note": "变更核读中", "note_html": "变更内容核读中。"}
EN_LATEST = {"pending": True, "auto_latest": True, "note": "Current latest · review in progress",
             "note_html": 'Current latest release on npm. Change review in progress — we do not label a release BREAKING or safe until the review is done. Before upgrading, see the <a href="https://github.com/deepseek-ai/deepseek-harness/releases" rel="nofollow">official release notes</a>.'}
ZH_LATEST = {"pending": True, "auto_latest": True, "note": "当前最新版 · 变更核读中",
             "note_html": 'npm 上的当前最新版。变更内容核读中——核读完成前不下 BREAKING / 非破坏结论。升级前建议先看 <a href="https://github.com/deepseek-ai/deepseek-harness/releases" rel="nofollow">官方 release note</a>。'}


def refresh_releases():
    url = "https://registry.npmjs.org/" + urllib.parse.quote(NPM_PKG, safe="")
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8"))
    tm = d.get("time", {})
    vs = sorted(((ts, v) for v, ts in tm.items() if v not in ("created", "modified")), reverse=True)
    if not vs:
        raise RuntimeError("npm time 字段为空")
    day = datetime.now(timezone.utc).date().isoformat()
    for rel, default, latest, src in (
        ("data/releases.json", EN_DEFAULT, EN_LATEST,
         "npm registry %s · time field · refreshed daily, last fetch %s" % (NPM_PKG, day)),
        ("data/zh/releases.json", ZH_DEFAULT, ZH_LATEST,
         "npm registry %s · time 字段 · 每日自动刷新,最近一次 %s" % (NPM_PKG, day)),
    ):
        f = SITE / rel
        doc = json.load(open(f, encoding="utf-8"))
        # auto_latest 那条属于"第一名"这个位置,不属于某个版本号,重建时先丢掉再重新贴
        keep = {x["version"]: x for x in doc.get("timeline", []) if not x.get("auto_latest")}
        doc["source"] = src
        doc["timeline"] = [dict(default, **dict(
            {k: val for k, val in keep.get(v, {}).items() if k != "date"}, version=v, date=ts[:10]))
            for ts, v in vs]
        doc["timeline"][0] = dict(doc["timeline"][0], **dict(
            latest, version=vs[0][1], date=vs[0][0][:10]))
        json.dump(doc, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return len(vs)


try:
    print("releases refreshed:", refresh_releases(), "versions")
except Exception as e:
    print("releases refresh FAILED, keeping previous file:", str(e)[:150])
