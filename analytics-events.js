/* 序引官网 · 事件追踪层 ———————————————————————
   核心转化：官网 → 海图 导流（跨域，pageview 抓不到，必须埋）；
   辅助：看报告 / 看案例·信号 的「从哪点进去」归因。
   「谁在就报给谁」：Umami 在报 Umami，Clarity 在报 Clarity，都没有则静默。
   用事件委托抓全部 <a href>，含 JS 动态生成的 atlas 链接（?market= / ?brand=）。
   首页 feed 的 icard 走 onclick=location.href 的站内跳转，由落地页 pageview 记录，
   不在此重复埋点。 */
(function () {
  function track(name, data) {
    try {
      if (window.umami && typeof window.umami.track === 'function') {
        window.umami.track(name, data);
      }
    } catch (e) { /* 静默 */ }
    try {
      if (typeof window.clarity === 'function') {
        window.clarity('event', name);
        if (data && data.dest)  window.clarity('set', name + '_dest', String(data.dest).slice(0, 200));
        if (data && data.label) window.clarity('set', name + '_label', String(data.label).slice(0, 80));
      }
    } catch (e) { /* 静默 */ }
  }

  function destOf(href) {
    try { var u = new URL(href, location.href); return u.pathname + (u.search || ''); }
    catch (_) { return href; }
  }
  function labelOf(a) {
    return ((a.textContent || '').trim().replace(/\s+/g, ' ')).slice(0, 80);
  }

  function onClick(e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var a = t.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (!href) return;

    // ① 跳海图：官网→海图 导流漏斗（跨域，pageview 抓不到）
    if (/atlas\.sequentry\.com/i.test(href)) {
      track('to_atlas', { dest: destOf(href), label: labelOf(a) });
      return;
    }
    // ② 看报告（站内，补来源归因）
    if (/^\/report(\/|$)/.test(href)) {
      track('view_report', { dest: destOf(href), label: labelOf(a) });
      return;
    }
    // ③ 看案例 / 信号（/briefs/ 下，站内，补来源归因）
    if (/^\/briefs(\/|$)/.test(href)) {
      track('view_briefs', { dest: destOf(href), label: labelOf(a) });
      return;
    }
  }

  document.addEventListener('click', onClick, true);
  document.addEventListener('auxclick', onClick, true);
})();
