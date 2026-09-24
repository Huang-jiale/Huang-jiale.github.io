/*
 * 侧栏「站点概览」那一栏，在文章页里换成同一模块下的其他文章（模板：tools/sidebar-module.njk）。
 * 模块 = 分类的第二层（学习/行测/判断推理 里的「行测」，生活/象棋/… 里的「象棋」）。
 *
 * 排序按 date 升序：导入脚本给每篇写的是当天的不同分钟（sh-xiangqi-1 是 09:10、-2 是 09:11），
 * 所以升序就是教学顺序；时政按月份、行测按导入顺序也都在这里成立。
 * 超过 GROUP_MIN 篇才按第三层分类（题型 / 月份）分组，三篇的阶段课不需要。
 * 分组后「当前篇所在那一组」默认展开，其余组由 source/js/sidebar-module.js 点开才展开——
 * 时政 74 篇、行测 38 篇，一次全铺开侧栏就成了第二篇文章，只留当前组才翻得动。
 */

/* global hexo */

'use strict';

const GROUP_MIN = 6;

function catUrl(names) {
  return '/categories/' + names.map(n => encodeURIComponent(n.replace(/ /g, '-'))).join('/') + '/';
}

hexo.extend.helper.register('module_nav', function (page) {
  const cats = page && page.categories;
  if (!cats || cats.length < 2) return null;
  const mod = cats.data[1];
  const top = cats.data[0];

  const mine = hexo.locals.get('posts')
    .filter(p => p.published !== false
      && p.categories && p.categories.length > 1
      && p.categories.data[1]._id === mod._id)
    .toArray()
    .sort((a, b) => a.date - b.date);

  const items = mine.map(p => ({
    title  : p.title,
    url    : '/' + p.path,
    current: p.path === page.path,
    group  : p.categories.length > 2 ? p.categories.data[2].name : ''
  }));

  let groups = null;
  if (items.length > GROUP_MIN && items.some(i => i.group)) {
    const map = new Map();
    items.forEach(i => {
      if (!map.has(i.group)) map.set(i.group, []);
      map.get(i.group).push(i);
    });
    groups = [...map].map(([name, list]) => ({
      name,
      list,
      count  : list.length,
      // 当前篇在哪一组，那一组就默认展开
      current: list.some(i => i.current)
    }));
  }

  return { name: mod.name, url: catUrl([top.name, mod.name]), total: items.length, items, groups };
});
