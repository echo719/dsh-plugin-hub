# dsh-plugin-hub.com

按问题找 DeepSeek Harness 插件;每个插件过四道体检。静态站,Cloudflare Pages 托管(输出目录 `public/`)。

- `build.py` — 生成器:`data/*.json` + `audit/audit.json` → `public/`。体检数值一律来自数据文件,禁止手写。
- `audit/` — 体检管线:`plugins.json` 收录清单 → `audit_daily.py`(每日 09:20 Actions 跑)→ `audit.json`
- `validate_site.py` — 上线前校验(标签/内链/meta/数值来源/虚构版本号拦截)
- `deploy.sh` — 本地校验+提交+推送(token 读 `../.github-token`,不入库)

上线三步:填 `data/site.json` 的 `github_repo` 与 `ga4_id` → `bash deploy.sh "msg"` → Cloudflare Pages 连仓库(build 留空,输出 `public/`)。
