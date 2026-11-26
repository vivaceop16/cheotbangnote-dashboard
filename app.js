/* 첫방노트 원고 보관함 — data/<날짜>.json 을 읽어 카드로 그린다.
   새 날짜는 data/<날짜>.json 과 assets/<날짜>/ 만 추가하면 자동으로 나타난다. */
(function () {
  'use strict';

  var DONE_KEY = 'cheotbangnote.done.v1';
  var FALLBACK_START = '2026-11-19';
  var state = { days: [], active: '', done: {}, collapsed: {} };

  /* ── 유틸 ─────────────────────────── */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function loadJSON(key, def) {
    try { var v = JSON.parse(localStorage.getItem(key) || 'null'); return v || def; } catch (e) { return def; }
  }
  function saveJSON(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {} }
  function toast(msg) {
    var t = $('#toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.remove('show'); }, 1600);
  }
  function fail(msg) {
    var b = $('#banner');
    b.hidden = false;
    b.textContent = msg;
  }
  window.addEventListener('error', function (e) { fail('스크립트 오류: ' + (e.message || e.type)); });

  /* ── 데이터 ───────────────────────── */
  function isoToday() {
    var d = new Date(Date.now() + 9 * 3600 * 1000); // KST
    return d.toISOString().slice(0, 10);
  }
  function enumerateDates(start, end) {
    var out = [], d = new Date(start + 'T00:00:00Z'), last = new Date(end + 'T00:00:00Z'), guard = 0;
    while (d <= last && guard++ < 400) {
      out.push(d.toISOString().slice(0, 10));
      d.setUTCDate(d.getUTCDate() + 1);
    }
    return out.reverse();
  }
  function getJSON(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(r.status + ' ' + url);
      return r.json();
    });
  }

  function loadDays() {
    return getJSON('data/manifest.json')
      .then(function (m) { return (m.days || []).map(function (d) { return d.date; }); })
      .catch(function () { return enumerateDates(FALLBACK_START, isoToday()); })
      .then(function (dates) {
        return Promise.all(dates.map(function (dt) {
          return getJSON('data/' + dt + '.json').catch(function () { return null; });
        }));
      })
      .then(function (list) {
        state.days = list.filter(Boolean).sort(function (a, b) { return a.date < b.date ? 1 : -1; });
      });
  }

  /* ── 복사 ─────────────────────────── */
  function legacyCopyText(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;';
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, text.length);
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }
  function copyText(text, okMsg) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        toast(okMsg || '복사했어요');
      }).catch(function () {
        toast(legacyCopyText(text) ? (okMsg || '복사했어요') : '복사 실패 — 길게 눌러 복사해 주세요');
      });
    } else {
      toast(legacyCopyText(text) ? (okMsg || '복사했어요') : '복사 실패 — 길게 눌러 복사해 주세요');
    }
  }
  function copyRich(html, text, okMsg) {
    var done = false;
    if (window.ClipboardItem && navigator.clipboard && navigator.clipboard.write) {
      try {
        var item = new ClipboardItem({
          'text/html': new Blob([html], { type: 'text/html' }),
          'text/plain': new Blob([text], { type: 'text/plain' })
        });
        navigator.clipboard.write([item]).then(function () {
          toast(okMsg || '서식 그대로 복사했어요');
        }).catch(function () { fallbackRich(); });
        done = true;
      } catch (e) { done = false; }
    }
    if (!done) fallbackRich();

    function fallbackRich() {
      var box = document.createElement('div');
      box.contentEditable = 'true';
      box.innerHTML = html;
      box.style.cssText = 'position:fixed;top:-3000px;left:0;width:10px;opacity:0;';
      document.body.appendChild(box);
      var sel = window.getSelection();
      var range = document.createRange();
      range.selectNodeContents(box);
      sel.removeAllRanges();
      sel.addRange(range);
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      sel.removeAllRanges();
      document.body.removeChild(box);
      toast(ok ? (okMsg || '서식 그대로 복사했어요') : '복사 실패 — 본문 미리보기를 길게 눌러 복사해 주세요');
    }
  }

  /* ── 본문 HTML / 텍스트 만들기 ────── */
  function photosOf(post) {
    return (post.images || []).map(function (im, i) {
      return { file: im.file, src: im.src, cap: im.cap || '', label: im.label || ('사진 ' + (i + 1)) };
    });
  }
  function bodyHTML(post) {
    var h = [];
    if (post.meta && post.meta.length) {
      h.push('<blockquote>');
      post.meta.forEach(function (m) {
        h.push(m.k ? '<p><b>' + esc(m.k) + '</b> ' + esc(m.v) + '</p>' : '<p>' + esc(m.v) + '</p>');
      });
      h.push('</blockquote>');
    }
    (post.hook || []).forEach(function (line) { h.push('<p>' + esc(line) + '</p>'); });
    (post.sections || []).forEach(function (sec) {
      if (sec.heading) h.push('<h3><b>' + esc(sec.heading) + '</b></h3>');
      (sec.blocks || []).forEach(function (b) {
        if (b.t === 'img') {
          var label = b.label || '';
          if (!label) {
            var idx = (post.images || []).findIndex(function (im) { return im.file === b.file; });
            label = '사진 ' + (idx >= 0 ? idx + 1 : '');
          }
          h.push('<p style="color:#999999;font-size:12px">[' + esc(label) + '] ' + esc(b.cap || '') + '</p>');
        } else {
          h.push('<p>' + esc(b.text) + '</p>');
        }
      });
    });
    if (post.cta) h.push('<p>' + esc(post.cta) + '</p>');
    return h.join('');
  }
  function bodyText(post) {
    var out = [];
    (post.meta || []).forEach(function (m) { out.push(m.k ? m.k + ': ' + m.v : m.v); });
    if (out.length) out.push('');
    (post.hook || []).forEach(function (l) { out.push(l); out.push(''); });
    (post.sections || []).forEach(function (sec) {
      if (sec.heading) { out.push(sec.heading); out.push(''); }
      (sec.blocks || []).forEach(function (b) {
        if (b.t === 'img') {
          var label = b.label || '';
          if (!label) {
            var idx = (post.images || []).findIndex(function (im) { return im.file === b.file; });
            label = '사진 ' + (idx >= 0 ? idx + 1 : '');
          }
          out.push('[' + label + '] ' + (b.cap || ''));
        } else {
          out.push(b.text);
        }
        out.push('');
      });
    });
    if (post.cta) { out.push(post.cta); out.push(''); }
    return out.join('\n').replace(/\n{3,}/g, '\n\n').trim();
  }

  /* ── 렌더 ─────────────────────────── */
  function dayLabel(day) {
    var d = new Date(day.date + 'T00:00:00');
    return (d.getMonth() + 1) + '월 ' + d.getDate() + '일' + (day.weekday ? ' (' + day.weekday + ')' : '');
  }
  function dateShort(date) {
    return date.slice(5, 7).replace(/^0/, '') + '/' + date.slice(8, 10);
  }

  function renderTabs() {
    var tabs = $('#tabs');
    var total = state.days.reduce(function (n, d) { return n + d.posts.length; }, 0);
    var html = '<button class="tab' + (state.active === '' ? ' on' : '') + '" data-date="">전체<i>' + total + '</i></button>';
    state.days.forEach(function (d) {
      var doneN = d.posts.filter(function (p) { return state.done[p.id]; }).length;
      html += '<button class="tab' + (state.active === d.date ? ' on' : '') + '" data-date="' + d.date + '">' +
        dateShort(d.date) + '<i>' + (doneN ? doneN + '/' : '') + d.posts.length + '</i></button>';
    });
    tabs.innerHTML = html;
    var on = tabs.querySelector('.tab.on');
    if (on && on.scrollIntoView) {
      try { on.scrollIntoView({ block: 'nearest', inline: 'center' }); } catch (e) {}
    }
  }

  function cardHTML(post, dateIso) {
    var done = !!state.done[post.id];
    var collapsed = state.collapsed[post.id] === true;
    var photos = photosOf(post);
    var metaKV = (post.meta || []).map(function (m) {
      return m.k ? '<dt>' + esc(m.k) + '</dt><dd>' + esc(m.v) + '</dd>' : '<dt></dt><dd>' + esc(m.v) + '</dd>';
    }).join('');
    var titles = (post.titles || []).map(function (t, i) {
      return '<div class="title-row"><span class="t-label">' + esc(t.label) + '</span>' +
        '<span class="t-text">' + esc(t.text) + '</span>' +
        '<button class="btn tiny" data-act="copy-title" data-id="' + esc(post.id) + '" data-i="' + i + '">복사</button></div>';
    }).join('');
    var photoGrid = photos.map(function (p, i) {
      return '<div class="photo"><a href="' + esc(p.src) + '" target="_blank" rel="noopener">' +
        '<img src="' + esc(p.src) + '" alt="' + esc(p.label) + '" loading="lazy"></a>' +
        '<div class="cap">' + esc(p.label) + '. ' + esc(p.cap) + '</div>' +
        '<a class="btn tiny save" href="' + esc(p.src) + '" download="' + esc(post.date + '_' + post.no + '_' + p.file) + '">저장</a></div>';
    }).join('');
    var preview = (post.sections || []).map(function (sec) {
      var inner = '';
      (sec.blocks || []).forEach(function (b) {
        if (b.t === 'img') {
          inner += '<figure><img src="' + esc(b.src || '') + '" alt="" loading="lazy">' +
            '<figcaption><span>' + esc(b.cap || '') + '</span>' +
            '<a class="btn tiny save" href="' + esc(b.src || '') + '" download="' + esc(post.date + '_' + post.no + '_' + b.file) + '">저장</a></figcaption></figure>';
        } else {
          inner += '<p>' + esc(b.text) + '</p>';
        }
      });
      return (sec.heading ? '<h3>' + esc(sec.heading) + '</h3>' : '') + inner;
    }).join('');
    var sources = (post.sources || []).filter(function (s) { return s.url; }).map(function (s) {
      return '<li><a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.label) + '</a></li>';
    }).join('');
    var thumb = post.thumb && post.thumb.src
      ? '<div class="thumb-wrap"><img src="' + esc(post.thumb.src) + '" alt="대표 썸네일" loading="lazy">' +
        '<div class="thumb-info"><p><b>대표 썸네일</b> (1:1)<br>' + esc(post.thumb.cap || '') + '</p>' +
        '<a class="btn tiny save" href="' + esc(post.thumb.src) + '" download="' + esc(post.date + '_' + post.no + '_thumb.jpg') + '">썸네일 저장</a></div></div>'
      : '';

    return '<article class="card' + (done ? ' done' : '') + (collapsed ? ' collapsed' : '') + '" data-post="' + esc(post.id) + '" data-date="' + esc(dateIso) + '">' +
      '<div class="card-head" data-act="toggle">' +
        '<span class="badge">' + post.no + '편</span>' +
        '<div class="head-main"><h2>' + esc(post.title) + '</h2>' +
          (post.headline && post.headline !== post.title ? '<p class="head-sub">' + esc(post.headline) + '</p>' : '') + '</div>' +
        '<button class="check' + (done ? ' on' : '') + '" data-act="done" data-id="' + esc(post.id) + '" aria-pressed="' + done + '">✓<span>발행 완료</span></button>' +
        '<span class="chev">▼</span>' +
      '</div>' +
      '<div class="card-body">' +
        '<div class="actions">' +
          '<button class="btn primary" data-act="copy-html" data-id="' + esc(post.id) + '">서식 그대로 복사</button>' +
          '<button class="btn" data-act="copy-text" data-id="' + esc(post.id) + '">일반 텍스트 복사</button>' +
          '<button class="btn wide" data-act="copy-tags" data-id="' + esc(post.id) + '">해시태그 복사</button>' +
        '</div>' +
        '<div class="label">제목 3종</div>' + titles +
        (metaKV ? '<div class="label">메타 정보</div><dl class="meta">' + metaKV + '</dl>' : '') +
        (post.hook && post.hook.length ? '<div class="label">3초 핵심 요약</div><div class="hook">' +
          post.hook.map(function (l) { return '<p>' + esc(l) + '</p>'; }).join('') + '</div>' : '') +
        (thumb ? '<div class="label">대표 썸네일</div>' + thumb : '') +
        (photoGrid ? '<div class="label">본문 사진 ' + photos.length + '장</div><div class="photos">' + photoGrid + '</div>' : '') +
        (preview ? '<div class="label">본문 미리보기</div><details class="preview"><summary>본문 펼쳐 보기</summary><div class="preview-body">' + preview + '</div></details>' : '') +
        (post.cta ? '<div class="label">마무리 질문</div><p class="cta">' + esc(post.cta) + '</p>' : '') +
        (post.hashtags ? '<div class="label">해시태그</div><div class="tags">' + esc(post.hashtags) + '</div>' : '') +
        (sources ? '<div class="label">공식 출처</div><ul class="sources">' + sources + '</ul>' : '') +
      '</div></article>';
  }

  function render() {
    var list = $('#list');
    var days = state.days.filter(function (d) { return state.active === '' || d.date === state.active; });
    if (!days.length) {
      list.innerHTML = '<p class="empty">표시할 원고가 없습니다.<br>data/ 폴더를 확인해 주세요.</p>';
    } else {
      list.innerHTML = days.map(function (d) {
        return '<div class="day-head"><b>' + dayLabel(d) + '</b><span>' + d.posts.length + '편</span></div>' +
          d.posts.map(function (p) { return cardHTML(p, d.date); }).join('');
      }).join('');
    }
    var total = state.days.reduce(function (n, d) { return n + d.posts.length; }, 0);
    var doneN = 0;
    state.days.forEach(function (d) { d.posts.forEach(function (p) { if (state.done[p.id]) doneN++; }); });
    $('#progressText').textContent = '발행 ' + doneN + '/' + total;
    $('#progressBar').style.width = total ? (doneN / total * 100) + '%' : '0%';
    $('#stats').textContent = state.days.length + '일 · ' + total + '편 보관 중';
    renderTabs();
  }

  function findPost(id) {
    for (var i = 0; i < state.days.length; i++) {
      var ps = state.days[i].posts;
      for (var j = 0; j < ps.length; j++) if (ps[j].id === id) return ps[j];
    }
    return null;
  }

  /* ── 이벤트 ───────────────────────── */
  document.addEventListener('click', function (ev) {
    var tab = ev.target.closest ? ev.target.closest('.tab') : null;
    if (tab) {
      state.active = tab.getAttribute('data-date');
      render();
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    var el = ev.target.closest ? ev.target.closest('[data-act]') : null;
    if (!el) return;
    var act = el.getAttribute('data-act');

    if (act === 'toggle') {
      var card = el.closest('.card');
      if (!card) return;
      if (ev.target.closest('[data-act="done"]')) return;
      card.classList.toggle('collapsed');
      state.collapsed[card.getAttribute('data-post')] = card.classList.contains('collapsed');
      return;
    }
    if (act === 'done') {
      ev.stopPropagation();
      var id = el.getAttribute('data-id');
      if (state.done[id]) delete state.done[id]; else state.done[id] = true;
      saveJSON(DONE_KEY, state.done);
      var c = el.closest('.card');
      if (c) c.classList.toggle('done', !!state.done[id]);
      el.classList.toggle('on', !!state.done[id]);
      el.setAttribute('aria-pressed', String(!!state.done[id]));
      updateCounts();
      toast(state.done[id] ? '발행 완료로 표시했어요' : '표시를 해제했어요');
      return;
    }
    var post = findPost(el.getAttribute('data-id'));
    if (!post) return;
    if (act === 'copy-title') {
      var t = post.titles[parseInt(el.getAttribute('data-i'), 10)];
      if (t) copyText(t.text, '제목을 복사했어요');
      return;
    }
    if (act === 'copy-tags') {
      copyText(post.hashtags || '', '해시태그를 복사했어요');
      return;
    }
    if (act === 'copy-text') {
      copyText(bodyText(post), '본문을 텍스트로 복사했어요');
      return;
    }
    if (act === 'copy-html') {
      copyRich(bodyHTML(post), bodyText(post), '서식 그대로 복사했어요');
      return;
    }
  });

  function updateCounts() {
    var total = state.days.reduce(function (n, d) { return n + d.posts.length; }, 0);
    var doneN = 0;
    state.days.forEach(function (d) { d.posts.forEach(function (p) { if (state.done[p.id]) doneN++; }); });
    $('#progressText').textContent = '발행 ' + doneN + '/' + total;
    $('#progressBar').style.width = total ? (doneN / total * 100) + '%' : '0%';
    renderTabs();
  }

  /* ── 시작 ─────────────────────────── */
  state.done = loadJSON(DONE_KEY, {});
  loadDays().then(function () {
    if (!state.days.length) {
      $('#list').innerHTML = '<p class="empty">원고 데이터를 불러오지 못했습니다.<br>잠시 뒤 새로고침해 주세요.</p>';
      $('#stats').textContent = '데이터 없음';
      return;
    }
    state.active = state.days[0].date;   // 최신 날짜가 기본
    render();
  }).catch(function (e) {
    fail('데이터를 불러오지 못했습니다: ' + e.message);
    $('#list').innerHTML = '<p class="empty">불러오기 실패. 새로고침해 주세요.</p>';
  });
})();
