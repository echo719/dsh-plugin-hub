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
