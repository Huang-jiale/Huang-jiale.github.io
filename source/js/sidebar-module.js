/*
 * 侧栏「本模块文章」那一栏的两件事（模板：tools/sidebar-module.njk，样式：source/_data/styles.styl）：
 *
 * 1. 把格子标签从「站点概览」改成「本模块文章」。标签是主题模板里写死的
 *    （layout/_macro/sidebar.njk 用 __('sidebar.overview')），不改 node_modules 就只能改 DOM。
 *    判断依据用 DOM 里有没有 .module-nav —— 和样式隐藏概览那三块用的是同一个条件，
 *    所以首页/分类页（没有 .module-nav）标签照旧是「站点概览」。
 * 2. 分组的展开/收起：默认只开当前篇所在那一组（服务端已经写好 .is-open），
 *    点别的组名换 .is-open，一次只开一组，跟文章目录那套折叠一个手感。
 *
 * 主题的 tab 点击事件是绑在 <li> 元素上的（next-boot.js），换掉里面的文字不影响它。
 * 没开 pjax，一次加载跑一次就够；defer 挂在 </body> 前（tools/toc-fold.njk）。
 */

(() => {
  const secOf = button => button?.closest('.module-nav-sec') || null;

  const setOpen = (sec, open) => {
    const list = sec.querySelector(':scope > .module-nav-list');
    // 收起时 height:0 + overflow:hidden，scrollHeight 仍是内容的真实高度，量得到
    if (open && list) list.style.setProperty('--height', `${list.scrollHeight}px`);
    sec.classList.toggle('is-open', open);
    sec.querySelector(':scope > .module-nav-group')?.setAttribute('aria-expanded', open ? 'true' : 'false');
  };

  const init = () => {
    const nav = document.querySelector('.module-nav');
    if (!nav) return;

    const tab = document.querySelector('.sidebar-nav-overview');
    if (tab) tab.textContent = '本模块文章';

    nav.addEventListener('click', event => {
      const button = event.target.closest('.module-nav-group');
      const sec = secOf(button);
      if (!sec) return;
      const willOpen = !sec.classList.contains('is-open');
      nav.querySelectorAll(':scope > .module-nav-sec.is-open').forEach(other => {
        if (other !== sec) setOpen(other, false);
      });
      setOpen(sec, willOpen);
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
