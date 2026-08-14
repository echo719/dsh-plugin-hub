#!/bin/bash
# 部署:校验 → 提交 → 推送。用法: bash deploy.sh "提交信息" | bash deploy.sh --push-only
# token 读自 ../.github-token(项目根,不入库);输出全程脱敏。
set -e
cd "$(dirname "$0")"
rm -f .git/index.lock .git/HEAD.lock 2>/dev/null || true

TOK=$(tr -d '[:space:]' < ../.github-token)
[ -z "$TOK" ] && { echo "no token"; exit 1; }
REPO_PATH=$(grep -o '"github_repo": *"[^"]*"' data/site.json | cut -d'"' -f4)
[ -z "$REPO_PATH" ] && { echo "data/site.json github_repo 未填"; exit 1; }

if [ "$1" != "--push-only" ]; then
  python3 build.py
  python3 validate_site.py
  git add -A
  git -c user.name="dsh-plugin-hub" -c user.email="daydayupecho@gmail.com" \
    commit -m "${1:-update}" || echo "nothing to commit"
fi
git push "https://x-access-token:${TOK}@github.com/${REPO_PATH}.git" HEAD:main 2>&1 | sed "s/${TOK}/***/g"
git update-ref refs/remotes/origin/main HEAD 2>/dev/null || true
echo "DEPLOY DONE → https://github.com/${REPO_PATH}"
