/*
 * 文章正文的图片延迟加载：正文里第 3 张起打 loading="lazy"，前两张照常立即下载。
 *
 * 为什么：行测一页有 7~21 张扫描页（转 WebP 后仍约 100~200KB/张），素描和生活六项一页
 * 有 30~50 张图，但它们都在文档流下面，打开页面时根本不在视口里。首屏只要前两张，
 * 剩下的滚到跟前再要 —— 这是省下载量最大的一刀，且不用引入任何插件。
 * 前两张不延迟：首屏一定会看到，晚一拍反而更慢。
 *
 * 只在 after_post_render 改 post.content，不动源文件、不动主题模板（node_modules 里的东西
 * Actions 上 pnpm install 会拿回原版，改不得）。
 * 用的是浏览器原生懒加载，不依赖 JS，也不依赖 IntersectionObserver。
 */

/* global hexo */

'use strict';

const EAGER = 2;   // 每篇前两张照常加载

hexo.extend.filter.register('after_post_render', post => {
  let n = 0;
  post.content = post.content.replace(/<img\s(?![^>]*\bloading=)([^>]*?)>/g, (all, attrs) => {
    n += 1;
    return n <= EAGER ? all : `<img loading="lazy" ${attrs}>`;
  });
  return post;
});
