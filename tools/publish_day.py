#!/usr/bin/env python3
"""하루치 원고를 대시보드에 추가한다.

사용 예 (매일 아침 원고 준비 액션이 끝난 뒤):
    python3 tools/publish_day.py \
        --date 2026-11-27 \
        --md /workspace/downloads/첫방노트_2026-11-27_원고3편.md \
        --images /workspace/downloads/up_1127/final \
        --images /workspace/downloads/up_1127/web \
        --push

하는 일
  1) 원고 마크다운(3편)을 파싱한다 (parse_md.py).
  2) 참조된 이미지 전부를 웹용으로 줄여 assets/<날짜>/ 에 저장한다.
  3) data/<날짜>.json 을 쓰고 data/manifest.json 을 갱신한다.
  4) --push 이면 git add/commit/push 까지 한다.

이미지 파일명은 원고에 적힌 이름 그대로 쓴다. --images 는 여러 번 줄 수 있고
앞에 준 폴더를 먼저 찾는다. 하나라도 없으면 아무것도 쓰지 않고 exit 2 로 끝난다.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_md import parse_md, collect_images  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']
IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.gif')


def find_image(name, dirs):
    for d in dirs:
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    p = os.path.join(dirs[0], 'raw', name) if dirs else None
    if p and os.path.isfile(p):
        return p
    return None


def save_web_image(src, dest, is_thumb):
    """웹용으로 줄여서 저장. 실패하면 원본 복사."""
    if Image is None:
        shutil.copyfile(src, dest)
        return
    try:
        im = Image.open(src)
        im = im.convert('RGB')
        limit = 800 if is_thumb else 1000
        w, h = im.size
        if max(w, h) > limit:
            if w >= h:
                im = im.resize((limit, round(h * limit / w)), Image.LANCZOS)
            else:
                im = im.resize((round(w * limit / h), limit), Image.LANCZOS)
        out = os.path.splitext(dest)[0] + '.jpg'
        im.save(out, 'JPEG', quality=82, optimize=True, progressive=True)
        return out
    except Exception as e:  # noqa: BLE001
        print(f'  ! 이미지 변환 실패 {src}: {e} -> 원본 복사', file=sys.stderr)
        shutil.copyfile(src, dest)
        return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True, help='YYYY-MM-DD')
    ap.add_argument('--md', required=True, help='원고 마크다운 경로')
    ap.add_argument('--images', action='append', default=[], help='이미지 폴더 (여러 번 가능, 앞이 우선)')
    ap.add_argument('--push', action='store_true', help='git add/commit/push 까지')
    ap.add_argument('--force', action='store_true', help='같은 날짜 데이터를 덮어쓰기')
    args = ap.parse_args()

    date = dt.date.fromisoformat(args.date)
    ds = date.isoformat()
    weekday = WEEKDAYS[date.weekday()]

    data_path = os.path.join(ROOT, 'data', f'{ds}.json')
    if os.path.exists(data_path) and not args.force:
        print(f'이미 있음: {data_path} (덮어쓰려면 --force)', file=sys.stderr)
        return 3

    with open(args.md, encoding='utf-8') as f:
        posts = parse_md(f.read(), ds)
    if len(posts) != 3:
        print(f'! 원고 편수가 {len(posts)}편입니다(보통 3편). 그대로 진행합니다.', file=sys.stderr)

    names = collect_images(posts)
    if not names:
        print('! 원고에서 이미지를 하나도 찾지 못했습니다.', file=sys.stderr)
        return 2

    missing = [n for n in names if not find_image(n, args.images)]
    if missing:
        print('! 이미지 파일을 찾지 못했습니다: ' + ', '.join(missing), file=sys.stderr)
        print('  --images 폴더를 확인하세요. 아무것도 쓰지 않았습니다.', file=sys.stderr)
        return 2

    # 2) 이미지
    dest_dir = os.path.join(ROOT, 'assets', ds)
    os.makedirs(dest_dir, exist_ok=True)
    written = {}
    for n in names:
        src = find_image(n, args.images)
        is_thumb = 'thumb' in n.lower()
        out = save_web_image(src, os.path.join(dest_dir, n), is_thumb)
        written[n] = f'assets/{ds}/' + os.path.basename(out)
        print(f'  · {n} -> {os.path.basename(out)}')

    # 3) 데이터
    for p in posts:
        for b in p.get('images', []):
            b['src'] = written[b['file']]
        for sec in p['sections']:
            for b in sec['blocks']:
                if b['t'] == 'img':
                    b['src'] = written.get(b['file'], '')
        if p.get('thumb'):
            p['thumb']['src'] = written.get(p['thumb']['file'], '')
        for b in p['sections']:
            pass
        # 대표 썸네일이 본문 이미지 목록에 있으면 함께 표시되도록 유지
        p.pop('image_plan', None)

    payload = {
        'date': ds,
        'weekday': weekday,
        'label': f'{date.month}월 {date.day}일',
        'generated': dt.datetime.now().astimezone().isoformat(timespec='seconds'),
        'posts': posts,
    }
    os.makedirs(os.path.dirname(data_path), exist_ok=True)
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))

    rebuild_manifest()
    print(f'저장 완료: data/{ds}.json ({len(posts)}편, 이미지 {len(names)}장)')

    if args.push:
        commit_and_push(ds, len(posts))
    return 0


def rebuild_manifest():
    ddir = os.path.join(ROOT, 'data')
    items = []
    for fn in sorted(os.listdir(ddir)):
        m = re.match(r'^(\d{4}-\d{2}-\d{2})\.json$', fn)
        if not m:
            continue
        p = os.path.join(ddir, fn)
        try:
            with open(p, encoding='utf-8') as f:
                d = json.load(f)
        except Exception:  # noqa: BLE001
            continue
        items.append({'date': d['date'], 'weekday': d.get('weekday', ''), 'label': d.get('label', ''), 'count': len(d.get('posts', []))})
    items.sort(key=lambda x: x['date'], reverse=True)
    with open(os.path.join(ddir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump({'days': items, 'updated': dt.datetime.now().astimezone().isoformat(timespec='seconds')}, f, ensure_ascii=False, indent=1)
    print(f'manifest: {len(items)}일')


def commit_and_push(ds, n):
    def run(*cmd, check=True):
        print('  $', ' '.join(cmd))
        return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=check)

    run('git', 'pull', '--rebase', '--autostash', check=False)
    run('git', 'add', '-A')
    msg = f'{ds} 원고 {n}편 추가'
    r = run('git', 'commit', '-m', msg, check=False)
    if r.returncode != 0 and 'nothing to commit' not in (r.stdout + r.stderr):
        print(r.stdout, r.stderr, file=sys.stderr)
    r = run('git', 'push', 'origin', 'HEAD', check=False)
    if r.returncode != 0:
        print('! push 실패:', r.stdout, r.stderr, file=sys.stderr)
        return 1
    print('push 완료')
    return 0


if __name__ == '__main__':
    sys.exit(main())
