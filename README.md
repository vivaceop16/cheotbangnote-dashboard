# 첫방노트 원고 보관함 (누적 대시보드)

승미 님 네이버 블로그 '첫방노트'(canmore_663)용 검토 원고 3편을 매일 쌓아 두고,
휴대폰에서 바로 복사·저장해 발행할 수 있게 만든 정적 페이지입니다.

- 주소: **https://vivaceop16.github.io/cheotbangnote-dashboard/**
- 저장소: `vivaceop16/cheotbangnote-dashboard` (public, GitHub Pages `main` 브랜치 `/` 루트)
- 로컬 클론: `/workspace/cheotbangnote-dashboard` ← 매일 아침 액션이 이 폴더에서 push 합니다.

## 폴더 구조

```
index.html          화면 (CSS/JS 분리, 빌드 과정 없음)
style.css           모바일 우선 스타일
app.js              데이터 로딩·렌더·복사·발행 체크
data/manifest.json  날짜 목록 (최신순)
data/<날짜>.json    하루치 원고 3편 (이 파일만 추가하면 화면에 자동 반영)
assets/<날짜>/      그날 원고에 쓰인 사진 (본문 최대 1000px, 썸네일 1:1 최대 800px, JPEG q82)
tools/parse_md.py   원고 마크다운 → JSON 파서 (세 가지 원고 서식 모두 지원)
tools/publish_day.py 하루치 추가 + 이미지 경량화 + manifest 갱신 + (옵션) commit/push
tools/publish_today.sh 날짜만 주면 위 과정을 기본 경로에서 찾아 실행
tools/validate.py   배포 전 자체 점검 (편수·이미지·제목 규칙)
robots.txt          검색 로봇 차단
```

## 매일 아침 자동 누적 (원고 준비 액션에서)

원고 준비 액션이 08:00에 끝난 뒤 아래 한 줄을 실행하면 그날 원고가 대시보드에 추가되고 push됩니다.

```sh
/workspace/cheotbangnote-dashboard/tools/publish_today.sh 2026-11-27
```

- 원고: `/workspace/downloads/첫방노트_2026-11-27_원고3편.md`
- 이미지: `/workspace/downloads/up_1127/{web,final,raw}` 중 있는 폴더를 자동으로 사용
- 이미지 파일명은 원고 본문에 적힌 이름 그대로 찾습니다. 하나라도 없으면 **아무것도 쓰지 않고 종료(exit 2)** 하므로, 그때는 원고·이미지 이름을 맞춘 뒤 다시 실행하면 됩니다.
- push 권한이 없거나 네트워크가 막히면 `! push 실패`를 남기고 exit 1. 데이터·이미지는 이미 커밋 전 상태로 저장되어 있으니 권한이 풀린 뒤 `git push`만 하면 됩니다.
- 이미 그 날짜 데이터가 있으면 덮어쓰지 않습니다(다시 만들려면 `--force`).

## 화면 기능

- 최신 날짜가 기본 선택, 상단 탭에서 `전체` 또는 날짜별(11/26 ~ 11/19) 이동
- 카드마다
  - 제목 3종(추천형·후킹형·검색형) 각각 원클릭 복사
  - **서식 그대로 복사**: 메타박스(인용구)·소제목·문단 구조를 유지한 HTML을 클립보드에 넣음 → 네이버 스마트에디터 ONE에 붙여넣기
  - 일반 텍스트 복사 / 해시태그 복사
  - 대표 썸네일(1:1)과 본문 사진 목록, 사진마다 `저장` 버튼(모바일에서 파일로 저장)
  - `발행 완료` 체크 → 이 기기 localStorage에 저장, 상단 진행 표시에 반영
- `<meta name="robots" content="noindex, nofollow">` + `robots.txt`로 검색 노출 차단

## 새 날짜를 손으로 추가할 때

```sh
cd /workspace/cheotbangnote-dashboard
python3 tools/publish_day.py --date 2026-11-27 \
  --md "/workspace/downloads/첫방노트_2026-11-27_원고3편.md" \
  --images /workspace/downloads/up_1127/final --push
python3 tools/validate.py   # 점검
```

## 검증 기록

- 데이터: 8일 · 24편 · 이미지 132장 · 10.4MB (`tools/validate.py` OK)
- 로컬 크로미움(iPhone 390×844 뷰포트)에서 카드 24장 렌더, 이미지 132장 전부 200·로드 확인,
  클립보드(`text/html` 포함) 복사·발행 체크·새로고침 유지·가로 넘침 없음 확인.
