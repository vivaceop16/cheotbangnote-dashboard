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
  echo "저장소가 아직 없습니다: https://github.com/new 에서 $REPO (public) 생성 필요" >&2; exit 2; }

echo "== push"
git push -u origin main

echo "== GitHub Pages 활성화"
gh api -X POST "/repos/$OWNER/$REPO/pages" \
  -f "build_type=legacy" -f "source[branch]=main" -f "source[path]=/" 2>/dev/null \
  || gh api -X PUT "/repos/$OWNER/$REPO/pages" \
       -f "build_type=legacy" -f "source[branch]=main" -f "source[path]=/" 2>/dev/null \
  || echo "(이미 활성화되어 있을 수 있음)"
gh api "/repos/$OWNER/$REPO/pages" --jq '{status, url, html_url, source}' 2>/dev/null || true

echo "== 빌드 대기"
i=0
while [ $i -lt 40 ]; do
  st=$(gh api "/repos/$OWNER/$REPO/pages/builds/latest" --jq '.status' 2>/dev/null || echo unknown)
  echo "  $i: $st"
  [ "$st" = "built" ] && break
  i=$((i+1)); sleep 10
done
echo "완료: https://$OWNER.github.io/$REPO/"
