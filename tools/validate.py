#!/usr/bin/env python3
"""대시보드 데이터 자체 점검 (배포 전 확인용).

    python3 tools/validate.py

- data/manifest.json 과 data/*.json 이 서로 맞는지
- 편마다 제목 3종·본문 섹션·이미지·썸네일이 채워졌는지
- 모든 이미지 경로가 실제 파일로 존재하는지
- 제목에 말줄임표(…, ...)가 들어갔는지 (승미 님 규칙: 금지)
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []
warns = []


def main():
    man_path = os.path.join(ROOT, 'data', 'manifest.json')
    if not os.path.isfile(man_path):
        print('data/manifest.json 없음', file=sys.stderr)
        return 1
    manifest = json.load(open(man_path, encoding='utf-8'))
    dates = [d['date'] for d in manifest['days']]
    files = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, 'data', '*.json')) if not p.endswith('manifest.json'))
    if dates != sorted(dates, reverse=True):
        errors.append('manifest 날짜가 최신순이 아님')
    if sorted(dates) != files:
        errors.append(f'manifest({len(dates)}) 와 data 파일({len(files)}) 목록 불일치')

    total_posts = 0
    total_imgs = 0
    total_bytes = 0
    for date in dates:
        p = os.path.join(ROOT, 'data', f'{date}.json')
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception as e:  # noqa: BLE001
            errors.append(f'{date}: JSON 읽기 실패 {e}')
            continue
        if d.get('date') != date:
            errors.append(f'{date}: 파일 안 date 값({d.get("date")}) 불일치')
        posts = d.get('posts', [])
        if len(posts) != 3:
            warns.append(f'{date}: 편수 {len(posts)}')
        for post in posts:
            pid = post.get('id', '?')
            total_posts += 1
            if not post.get('title'):
                errors.append(f'{pid}: 제목 없음')
            titles = post.get('titles', [])
            if len(titles) != 3:
                errors.append(f'{pid}: 제목 3종이 {len(titles)}개')
            for t in titles:
                if not t.get('text'):
                    errors.append(f'{pid}: 빈 제목({t.get("label")})')
                if re.search(r'…|\.\.\.', t.get('text', '')):
                    errors.append(f'{pid}: 제목에 말줄임표 {t["text"][:30]}')
            if not post.get('sections'):
                errors.append(f'{pid}: 본문 섹션 없음')
            for sec in post.get('sections', []):
                if not sec.get('blocks'):
                    errors.append(f'{pid}: 빈 섹션 {sec.get("heading")}')
            if not post.get('images'):
                errors.append(f'{pid}: 본문 사진 없음')
            if not (post.get('thumb') or {}).get('src'):
                errors.append(f'{pid}: 대표 썸네일 없음')
            if not post.get('hashtags', '').startswith('#'):
                errors.append(f'{pid}: 해시태그 없음')
            if len(post.get('cta', '')) < 10:
                warns.append(f'{pid}: CTA 짧음')
            srcs = [im.get('src') for im in post.get('images', [])]
            if post.get('thumb', {}).get('src'):
                srcs.append(post['thumb']['src'])
            for sec in post.get('sections', []):
                for b in sec.get('blocks', []):
                    if b.get('t') == 'img' and b.get('src'):
                        srcs.append(b['src'])
            uniq = sorted(set(s for s in srcs if s))
            total_imgs += len(uniq)
            for s in uniq:
                fp = os.path.join(ROOT, s)
                if not os.path.isfile(fp):
                    errors.append(f'{pid}: 이미지 파일 없음 {s}')
                else:
                    total_bytes += os.path.getsize(fp)

    print(f'날짜 {len(dates)}일 · 원고 {total_posts}편 · 이미지 {total_imgs}장 · {total_bytes/1048576:.1f}MB')
    for w in warns:
        print('  경고:', w)
    for e in errors:
        print('  오류:', e)
    print('OK' if not errors else f'실패 {len(errors)}건')
    return 0 if not errors else 1


if __name__ == '__main__':
    sys.exit(main())
