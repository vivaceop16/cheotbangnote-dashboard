#!/bin/sh
# 저장소가 만들어진 뒤 한 번 실행: push → GitHub Pages 활성화 → 빌드 대기
#   tools/deploy.sh
set -e
OWNER=vivaceop16
REPO=cheotbangnote-dashboard
cd "$(dirname "$0")/.."

git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$OWNER/$REPO.git"
git remote set-url origin "https://github.com/$OWNER/$REPO.git"

echo "== 원격 확인"
gh api "/repos/$OWNER/$REPO" --jq '.full_name + " private=" + (.private|tostring)' || {
  echo "저장소가 없거나 접근 권한이 없습니다: https://github.com/$OWNER/$REPO" >&2; exit 2; }

echo "== push"
git push -u origin main

echo "== GitHub Pages 활성화"
# GitHub Pages API는 본문을 {"source":{"branch":..,"path":..}} 형태의 JSON으로 받는다.
# gh api -f 는 중첩 키를 그대로 보내 실패하므로 --input 으로 넘긴다.
PAGES_JSON=/tmp/pages_$REPO.json
printf '%s' '{"build_type":"legacy","source":{"branch":"main","path":"/"}}' > "$PAGES_JSON"
gh api -X POST "/repos/$OWNER/$REPO/pages" --input "$PAGES_JSON" >/dev/null 2>&1 \
  || gh api -X PUT "/repos/$OWNER/$REPO/pages" --input "$PAGES_JSON" >/dev/null 2>&1 \
  || echo "  (Pages 활성화 요청 실패 — 이미 켜져 있거나 GitHub App에 pages 권한이 없을 수 있음)"

if ! gh api "/repos/$OWNER/$REPO/pages" --jq '{status, html_url, source}' 2>/dev/null; then
  echo "Pages가 꺼져 있습니다. 저장소 Settings → Pages → Deploy from a branch (main / root)로 한 번 켜 주세요." >&2
  echo "  https://github.com/$OWNER/$REPO/settings/pages" >&2
  exit 3
fi

echo "== 빌드 대기"
i=0
while [ $i -lt 30 ]; do
  st=$(gh api "/repos/$OWNER/$REPO/pages/builds/latest" --jq '.status' 2>/dev/null || echo unknown)
  echo "  $i: $st"
  [ "$st" = "built" ] && break
  i=$((i+1)); sleep 10
done
if [ "$i" -ge 30 ]; then echo "빌드가 30회 확인 안에 끝나지 않았습니다(계속 진행 중일 수 있음)." >&2; fi
echo "완료: https://$OWNER.github.io/$REPO/"
