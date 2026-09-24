/*
 * 分类页重做成树状图（2026-09-24 用户拍板：「思维导图，树状图」，总览页和点进去的列表页都要改）。
 *
 * 这里只出数据和挂模板，画线全在 source/_data/styles.styl：
 *   - /categories/           → 自己的 tools/cat-tree.njk（整棵树，三层铺开），
 *                             由 source/categories/index.md 的 `layout: cat-tree` 指过去
 *   - /categories/学习/行测/  → 顶掉主题的 layout/category.njk（hexo-generator-category
 *                             按 layout 名 'category' 取视图，只能这么换）。
 *                             node_modules 里的文件不能直接改：Actions 上 pnpm install 会拿回原版。
 *
 * 树的形状从文章的分类链现算（主题的 site.categories 是一张平表，父子关系得自己拼），
 * 顺序按 date 升序：导入脚本给每篇写的是当天的不同分钟，所以升序就是教学顺序，
 * 时政也才会 2025年11月 → 2026年2月 顺着排；主题默认按分类名排会把汉字数字排乱。
 */

/* global hexo */

'use strict';

const fs = require('fs');
const path = require('path');

// 模板放 tools/ 不放 scripts/：scripts/ 下的每个文件都会被当成 JS 加载，一个 .njk 丢进去就是报错
const TOOLS = p => path.join(__dirname, '..', 'tools', p);

// 分类名 -> URL 片段：hexo 把分类目录名里的空格换成 -，中文原样保留再百分号编码
function catUrl(names) {
  return '/categories/' + names.map(n => encodeURIComponent(n.replace(/ /g, '-'))).join('/') + '/';
}

// 当前是哪一个分类：主题的 category 页把整条路径放在 page.path 里
// （categories/学习/行测/index.html，也可能是百分号编码后的那一份），逐段 decode 还原。
function chainOf(page) {
  const raw = String((page && page.path) || '');
  if (!raw.startsWith('categories/')) return null;
  const segs = raw.replace(/^categories\//, '').replace(/index\.html$/, '').split('/').filter(Boolean);
  if (!segs.length) return null;
  try {
    return segs.map(s => decodeURIComponent(s));
  } catch (e) {
    return segs;
  }
}

// 文章 -> 分类链，拼成森林。每个节点挂 count（含全部子孙的篇数）和 children。
// 不缓存：hexo server 改完文章要立刻反映，森林才 40 个节点，重算一次不值钱。
function forest(hexo) {
  const posts = hexo.locals.get('posts')
    .filter(p => p.published !== false && p.categories && p.categories.length)
    .toArray()
    .sort((a, b) => a.date - b.date);

  const roots = [];
  const index = new Map();
  posts.forEach(p => {
    const names = p.categories.data.map(c => c.name);
    let siblings = roots;
    names.forEach((n, i) => {
      const sub = names.slice(0, i + 1);
      let node = index.get(sub.join('/'));
      if (!node) {
        node = { name: n, path: sub, url: catUrl(sub), count: 0, children: [] };
        index.set(sub.join('/'), node);
        siblings.push(node);
      }
      node.count++;
      siblings = node.children;
    });
  });

  // 每组最后一个节点：折线到此为止（模板里要读 node.last，nunjucks 的 loop.parent 不靠谱）
  const mark = list => list.forEach((n, i) => {
    n.last = i === list.length - 1;
    mark(n.children);
  });
  mark(roots);

  return { roots, total: hexo.locals.get('posts').filter(p => p.published !== false).length, kinds: index.size };
}

// 总览页：整片森林
hexo.extend.helper.register('cat_forest', function () {
  return forest(hexo);
});

// 单个分类页：当前节点 + 从一级到它上一层的路径
hexo.extend.helper.register('cat_here', function (page) {
  const names = chainOf(page);
  if (!names) return null;
  const f = forest(hexo);
  let siblings = f.roots;
  let node = null;
  for (let i = 0; i < names.length; i++) {
    node = siblings.find(c => c.name === names[i]);
    if (!node) return null;
    siblings = node.children;
  }
  return {
    total  : f.total,
    node,
    crumbs : node.path.slice(0, -1).map((n, i) => ({ name: n, url: catUrl(node.path.slice(0, i + 1)) }))
  };
});

hexo.extend.filter.register('before_generate', () => {
  const f = forest(hexo);
  if (!f.roots.length) {
    hexo.log.warn('[cat-tree] 一篇带分类的文章都没找到，分类页保持主题原样');
    return;
  }
  hexo.theme.setView('cat-tree.njk', fs.readFileSync(TOOLS('cat-tree.njk'), 'utf8'));
  hexo.theme.setView('category.njk', fs.readFileSync(TOOLS('cat-branch.njk'), 'utf8'));
  hexo.log.info(`[cat-tree] ${f.kinds} 个分类：`
    + f.roots.map(r => `${r.name} ${r.count} 篇 / ${r.children.length} 个子分类`).join('、'));
}, 12);
