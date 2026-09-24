/*
 * 侧栏目录：课（h2）永远显示，课内小标题（h3）默认折叠，点课名才展开，同时只留一个课开着。
 *
 * 为什么要自己写：主题的 expand_all=false 那套折叠靠 .active > .nav-child，
 * 也就是「滚到哪个课就自动撑开哪个」，滚动时侧栏自己跳动；
 * 而且它按 nav-item 算高度，标题一换行就不准。
 * 现在 _config.next.yml 里把 toc.expand_all 设成 true 关掉主题那套 CSS，
 * 折叠样式在 source/_data/styles.styl（认 .toc-open 这个类），本文件只负责加类 + 写实测高度。
 *
 * 没开 pjax，所以一次页面加载跑一次就够。脚本用 defer 挂在 </body> 前（tools/toc-fold.njk），
 * 等 DOMContentLoaded 再动手，那时主题的滚动高亮也已经装好了。
 */

(() => {
  // .toc-parent 只加在「有子目录的课」那一层，所以它可以当「这是课吗」用
  const childListOf = item => item?.querySelector(':scope > .nav-child') || null;

  const setOpen = (item, child, open) => {
    // 折叠时 height:0 + overflow:hidden，scrollHeight 仍是内容的真实高度，量得到
    if (open) child.style.setProperty('--height', `${child.scrollHeight}px`);
    item.classList.toggle('toc-open', open);
    item.querySelector(':scope > a')?.setAttribute('aria-expanded', open ? 'true' : 'false');
  };

  const init = () => {
    const nav = document.querySelector('.post-toc:not(.placeholder-toc) .nav');
    if (!nav) return;

    nav.querySelectorAll(':scope > .nav-item').forEach(item => {
      const child = childListOf(item);
      if (!child?.querySelector('.nav-item')) return;
      item.classList.add('toc-parent');
      setOpen(item, child, false);
    });

    nav.addEventListener('click', event => {
      // 只认课那一层的链接：小标题点下去就是普通跳转，别把整课关掉
      const item = event.target.closest('a')?.closest('.nav-item');
      if (!item?.classList.contains('toc-parent')) return;
      const child = childListOf(item);
      // 点课名照常跳到那一课，顺手展开它的小标题；再点一次收起。别的课同时关上。
      const willOpen = !item.classList.contains('toc-open');
      nav.querySelectorAll(':scope > .nav-item.toc-open').forEach(other => {
        if (other !== item) setOpen(other, childListOf(other), false);
      });
      setOpen(item, child, willOpen);
    });

    // 带 #锚点 进来时（例如从别的课点到某一课里的小节），把那一课展开，
    // 不然侧栏看着像「没这一节」。正文的跳转不受折叠影响，这里只是让侧栏对得上。
    if (window.location.hash.length > 1) {
      const link = nav.querySelector(`a[href="${window.location.hash}"]`);
      const item = link?.closest('.nav-item.toc-parent');
      const child = childListOf(item);
      if (child) setOpen(item, child, true);
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
