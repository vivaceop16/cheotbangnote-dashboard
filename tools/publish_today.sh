#!/bin/sh
# 하루치 원고를 대시보드에 올리고 push까지 한다.
#   tools/publish_today.sh 2026-11-27
# 원고/이미지는 매일 아침 원고 준비 액션이 남기는 기본 경로에서 찾는다.
#   원고: /workspace/downloads/첫방노트_<날짜>_원고3편.md
#   이미지: /workspace/downloads/up_<MMDD>/{web,final} 또는 그 폴더
set -e
D="$1"
if [ -z "$D" ]; then echo "사용: tools/publish_today.sh YYYY-MM-DD" >&2; exit 2; fi
MMDD=$(echo "$D" | cut -c6-7,9-10)
BASE="/workspace/downloads"
MD="$BASE/첫방노트_${D}_원고3편.md"
if [ ! -f "$MD" ]; then
  # 예전 이름 규칙(_원고3편.md)도 시도
  ALT=$(ls "$BASE"/첫방노트_${D}*원고*.md 2>/dev/null | head -1 || true)
  if [ -n "$ALT" ]; then MD="$ALT"; else echo "원고 파일이 없습니다: $MD" >&2; exit 2; fi
fi
DIR="$BASE/up_$MMDD"
ARGS=""
for sub in web final raw ""; do
  if [ -d "$DIR/$sub" ]; then ARGS="$ARGS --images $DIR/$sub"; fi
done
if [ -z "$ARGS" ]; then echo "이미지 폴더가 없습니다: $DIR" >&2; exit 2; fi
cd "$(dirname "$0")/.."
python3 tools/publish_day.py --date "$D" --md "$MD" $ARGS --push
