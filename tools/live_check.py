#!/usr/bin/env python3
"""배포된 페이지 실제 점검 (404 없음 · 24편 전부 표시).

    python3 tools/live_check.py [URL]
기본 URL: https://vivaceop16.github.io/cheotbangnote-dashboard/
"""
import json
import sys
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else 'https://vivaceop16.github.io/cheotbangnote-dashboard/').rstrip('/') + '/'
UA = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)'}
bad = []


def get(path, binary=False):
    url = BASE + path.lstrip('/')
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            return r.status, (data if binary else data.decode('utf-8', 'replace'))
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def check(path, need_status=200, contains=None, binary=False):
    st, body = get(path, binary)
    ok = st == need_status and (contains is None or (contains in (body if isinstance(body, str) else '')))
    print(('  OK  ' if ok else '  FAIL') + f' {path} ({st})')
    if not ok:
        bad.append(path)
    return body if ok else None


print('BASE', BASE)
check('', contains='첫방노트')
check('style.css')
check('app.js', contains='bodyHTML')
check('robots.txt')

man = check('data/manifest.json')
posts = 0
imgs = []
if man:
    m = json.loads(man)
    days = [d['date'] for d in m['days']]
    print(f'  날짜 {len(days)}일: {days[0]} ~ {days[-1]}')
    if len(days) != 8:
        bad.append(f'날짜 수 {len(days)}')
    if days != sorted(days, reverse=True):
        bad.append('manifest 정렬')
    for dt in days:
        body = check(f'data/{dt}.json')
        if not body:
            continue
        d = json.loads(body)
        n = len(d.get('posts', []))
        posts += n
        print(f'    {dt}: {n}편 / ' + ' · '.join(p.get('title', '')[:16] for p in d.get('posts', [])))
        if n != 3:
            bad.append(f'{dt} 편수 {n}')
        for p in d.get('posts', []):
            for im in p.get('images', []):
                if im.get('src'):
                    imgs.append(im['src'])
            if p.get('thumb', {}).get('src'):
                imgs.append(p['thumb']['src'])
            for sec in p.get('sections', []):
                for b in sec.get('blocks', []):
                    if b.get('t') == 'img' and b.get('src'):
                        imgs.append(b['src'])
    imgs = sorted(set(imgs))
    print(f'  원고 {posts}편 · 이미지 {len(imgs)}장')
    if posts != 24:
        bad.append(f'원고 {posts}편')
    miss = 0
    for src in imgs:
        st, body = get(src, binary=True)
        if st != 200 or not body or len(body) < 1000:
            print('  FAIL 이미지', src, st)
            miss += 1
    print(f'  이미지 200 확인: {len(imgs) - miss}/{len(imgs)}')

print('RESULT:', 'PASS' if not bad else f'FAIL {len(bad)}건 {bad[:6]}')
sys.exit(0 if not bad else 1)
