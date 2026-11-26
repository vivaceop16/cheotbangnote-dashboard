#!/usr/bin/env python3
"""첫방노트 원고 마크다운(3편) → 대시보드 데이터(dict) 파서.

지원 형식
  A) 11-19 ~ 11-24:  "## 1편 — 제목" / ### 제목 3종 / ### 이미지 배치 /
                     ### [인용구 메타 박스] / ### 3초 핵심 요약 훅 / ### ① ...
                     (본문 안 [IMG 1b.jpg → 캡션]) / ### CTA / ### 해시태그 / ### 출처
  B) 11-25 ~ 이후:   "## 1편. 제목" / ### [메타 정보 요약 박스] / ### [3초 핵심 요약] /
                     ### 본문 (#### ① + [사진 1] 캡션 (파일명)) / ### 마무리 질문 /
                     ### 해시태그 / ### 제목 3종 / ### 공식 출처 / ### 대표 썸네일
"""
import re

POST_HEAD = re.compile(r'^##\s*(\d)편\s*[—\.\-]?\s*(.*)$')
IMG_A = re.compile(r'^\[IMG\s+([^\]\s→]+)\s*(?:→\s*([^\]]*))?\]\s*$')
IMG_B = re.compile(r'^\[사진\s*(\d+)\]\s*(.*?)\s*\(([^()]+\.(?:jpe?g|png|webp|gif))\)\s*$', re.I)
PLAN_LINE = re.compile(r'^[\d]+[\.\)]\s*`?([^`]+?\.(?:jpe?g|png|webp))`?\s*(?:—|-|–|·)\s*(.*)$', re.I)
BULLET = re.compile(r'^\s*[-*]\s+(.*)$')
TITLE_LINE = re.compile(r'^\s*[-*]\s+(?:\*\*)?\s*([^:*]+?)\s*(?:\*\*)?\s*[:：]\s*(.+)$')
URL_LINE = re.compile(r'^\s*[-*]\s+(.*?)\s*[:：]\s*(https?://\S+)\s*$')
THUMB_LINE = re.compile(r'([\w.\-가-힣]+\.(?:jpe?g|png|webp))', re.I)

META_KEYS = ('메타', '인용구')
HOOK_KEYS = ('3초', '핵심 요약')
BODY_KEYS = ('본문',)
CTA_KEYS = ('cta', '마무리 질문', '마무리', '질문')
TAG_KEYS = ('해시태그', '태그')
SRC_KEYS = ('출처',)
TITLE_KEYS = ('제목',)
PLAN_KEYS = ('이미지 배치',)
THUMB_KEYS = ('대표 썸네일', '썸네일')


def _clean(s):
    s = s.replace('**', '').replace('`', '').replace('\\', '')
    s = s.strip()
    s = re.sub(r'^["\'“”]|["\'“”]$', '', s)
    return s.strip()


def _norm_label(s):
    s = _clean(s)
    s = s.replace('(홈판용)', '· 홈판용').replace('（홈판용）', '· 홈판용')
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*·\s*', ' · ', s)
    return s.strip(' ·')


def _section_kind(name):
    low = name.lower()
    if re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]', name):
        return 'body-heading'
    for k in PLAN_KEYS:
        if k in low:
            return 'plan'
    for k in META_KEYS:
        if k in low:
            return 'meta'
    for k in HOOK_KEYS:
        if k in low:
            return 'hook'
    if low.strip() in ('본문', '본문 ') or low.startswith('본문'):
        return 'body'
    for k in THUMB_KEYS:
        if k in low:
            return 'thumb'
    for k in TAG_KEYS:
        if k in low:
            return 'tags'
    for k in SRC_KEYS:
        if k in low:
            return 'sources'
    for k in CTA_KEYS:
        if k in low:
            return 'cta'
    if re.match(r'^제목\s*(3종|세트|3개)', low) or low in ('제목', '제목3종'):
        return 'titles'
    if '제목' in low and ':' not in low and len(low) < 12:
        return 'titles'
    return 'body-heading'


def parse_post(seg, date, no):
    heading_rest = POST_HEAD.match(seg[0]).group(2)
    post = {
        'id': f'{date}-{no}',
        'date': date,
        'no': no,
        'headline': _clean(heading_rest),
        'titles': [],
        'meta': [],
        'hook': [],
        'sections': [],
        'cta': '',
        'hashtags': '',
        'sources': [],
        'thumb': None,
        'images': [],
        'image_plan': [],
    }
    kind = None
    cur = None          # 현재 body 섹션
    section_name = ''
    for raw in seg[1:]:
        line = raw.rstrip()
        if line.startswith('#'):
            m = re.match(r'^#{3,6}\s*(.*)$', line)
            if m:
                name = _clean(m.group(1))
                k = _section_kind(name)
                if k in ('body-heading', 'body'):
                    if k == 'body' and name.lower().startswith('본문') and len(name) <= 3:
                        kind = 'body'
                        section_name = ''
                        cur = None
                        continue
                    # 소제목(① ② ③ ...)
                    kind = 'body'
                    cur = {'heading': name, 'blocks': []}
                    post['sections'].append(cur)
                    continue
                kind = k
                cur = None
                if k == 'titles':
                    post['titles'] = []
                elif k == 'sources':
                    post['sources'] = []
                continue
        if kind is None:
            continue
        s = line.strip()
        if not s:
            continue
        if kind == 'titles':
            m = TITLE_LINE.match(s)
            if m:
                post['titles'].append({'label': _norm_label(m.group(1)), 'text': _clean(m.group(2))})
            continue
        if kind == 'plan':
            m = PLAN_LINE.match(s)
            if m:
                post['image_plan'].append({'file': m.group(1).strip(), 'cap': _clean(m.group(2))})
            continue
        if kind == 'meta':
            t = BULLET.sub(r'\1', s)
            t = _clean(t)
            if not t or t.startswith('|') or set(t) <= set('-| '):
                continue
            if ': ' in t or t.count(':') == 1:
                k, v = t.split(':', 1)
                post['meta'].append({'k': _clean(k), 'v': _clean(v)})
            else:
                post['meta'].append({'k': '', 'v': t})
            continue
        if kind == 'hook':
            post['hook'].append(_clean(BULLET.sub(r'\1', s)))
            continue
        if kind == 'thumb':
            t = BULLET.sub(r'\1', s)
            m = THUMB_LINE.search(t)
            if m:
                post['thumb'] = {'file': m.group(1), 'cap': _clean(re.sub(r'\([0-9x ]+\)', '', t).replace(m.group(1), '').strip(' ·-—'))}
            continue
        if kind == 'tags':
            t = _clean(s)
            if t.startswith('#'):
                post['hashtags'] = (post['hashtags'] + ' ' + t).strip() if post['hashtags'] else t
            continue
        if kind == 'sources':
            m = URL_LINE.match(s)
            if m:
                post['sources'].append({'label': _clean(m.group(1)), 'url': m.group(2)})
            else:
                t = _clean(BULLET.sub(r'\1', s))
                if t:
                    post['sources'].append({'label': t, 'url': ''})
            continue
        if kind == 'cta':
            post['cta'] = (post['cta'] + ' ' + _clean(s)).strip() if post['cta'] else _clean(s)
            continue
        if kind == 'body':
            if cur is None:
                cur = {'heading': '', 'blocks': []}
                post['sections'].append(cur)
            ma = IMG_A.match(s)
            if ma:
                cur['blocks'].append({'t': 'img', 'file': ma.group(1).strip(), 'cap': _clean(ma.group(2) or '')})
                post['images'].append({'file': ma.group(1).strip(), 'cap': _clean(ma.group(2) or '')})
                continue
            mb = IMG_B.match(s)
            if mb:
                cur['blocks'].append({'t': 'img', 'file': mb.group(3).strip(), 'cap': _clean(mb.group(2)),
                                      'label': '사진 ' + mb.group(1)})
                post['images'].append({'file': mb.group(3).strip(), 'cap': _clean(mb.group(2)),
                                       'label': '사진 ' + mb.group(1)})
                continue
            cur['blocks'].append({'t': 'p', 'text': _clean(s)})
            continue

    # 캡션 보강(이미지 배치 목록에 더 자세한 설명이 있으면 그쪽을 쓴다)
    plan = {p['file']: p['cap'] for p in post['image_plan']}
    for im in post['images']:
        pc = plan.get(im['file'])
        if pc and (not im.get('cap') or len(pc) > len(im['cap']) + 6):
            im['cap'] = pc
    if post['thumb']:
        pc = plan.get(post['thumb']['file'])
        if pc and (not post['thumb'].get('cap') or len(pc) > len(post['thumb'].get('cap', '')) + 6):
            post['thumb']['cap'] = pc
    if not post['thumb']:
        for im in post['images']:
            if 'thumb' in im['file']:
                post['thumb'] = {'file': im['file'], 'cap': im['cap']}
                break
    if not post['thumb']:
        for pl in post['image_plan']:
            if 'thumb' in pl['file']:
                post['thumb'] = {'file': pl['file'], 'cap': pl['cap']}
                break
    if not post['thumb']:
        # 형식 A 기본 규칙: {편번호}a_thumb.jpg
        cand = f"{post['no']}a_thumb.jpg"
        for pl in post['image_plan']:
            if pl['file'] == cand:
                post['thumb'] = {'file': cand, 'cap': pl['cap']}
                break

    # 3초 훅이 비어 있으면 첫 body 단락으로 대체하지 않고 비워 둔다
    post['title'] = _short_title(post['headline'])
    return post


def _short_title(headline):
    t = headline
    t = re.sub(r'\(.*?\)\s*$', '', t).strip()
    return t.strip(' -—"')


def parse_md(text, date):
    lines = text.splitlines()
    heads = [i for i, l in enumerate(lines) if re.match(r'^##\s', l)]
    idxs = [i for i in heads if POST_HEAD.match(lines[i])]
    posts = []
    for n, i in enumerate(idxs):
        later = [h for h in heads if h > i]
        end = later[0] if later else len(lines)
        posts.append(parse_post(lines[i:end], date, n + 1))
    return posts


def collect_images(posts):
    out = []
    for p in posts:
        for im in p['images']:
            if im['file'] not in out:
                out.append(im['file'])
        if p['thumb'] and p['thumb']['file'] not in out:
            out.append(p['thumb']['file'])
    return out


if __name__ == '__main__':
    import sys, json
    path = sys.argv[1]
    date = sys.argv[2] if len(sys.argv) > 2 else '2026-01-01'
    with open(path, encoding='utf-8') as f:
        posts = parse_md(f.read(), date)
    print(json.dumps(posts, ensure_ascii=False, indent=1)[:6000])
    print('POSTS', len(posts), 'IMAGES', len(collect_images(posts)))
