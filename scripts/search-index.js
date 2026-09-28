/*
 * 站内搜索的索引瘦身：search.json 只留「标题 + 正文前 300 字」，不再打包全文。
 *
 * 为什么：hexo-generator-searchdb 默认把每篇文章的**全文**塞进一个 JSON —— 现在 172 条
 * 平均 20.6KB，整份 3.45MB（gzip 后 1.43MB）。NexT 的搜索脚本是点开搜索框才去拉它，
 * 在这台机器到 GitHub 的实测带宽下那一下要等 5 秒以上，看着就像「搜索坏了」。
 * 索引里留 300 字足够命中篇名和开头，整份缩到 200KB 上下。
 *
 * 为什么是再注册一个同名 generator、而不是配 `search.content: false`：那个开关只能
 * 全文/没有全文二选一，没有「留一截」；本文件在 scripts/ 里，加载顺序在插件之后，
 * 同一个 route path 后写的赢。tools/check-build.py 第 14 节钉着「每条 content ≤ 301 字」，
 * 哪天这个覆盖被插件抢回去（或文章数对不上）就会红，不会悄悄退回全文索引。
 *
 * NexT 的 search.js 读的是 title/url/content/categories/tags 这五个键，格式照抄插件，
 * 不改主题配置。
 */

/* global hexo */

'use strict';

const LIMIT = 300;
const ENTITIES = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#39;': "'", '&#x2F;': '/' };

function plainText(html) {
  // 块级标签收起始补一个空格，否则 </p><p> 之间的字会黏成一坨；不引 hexo-util（它只是 hexo 的传递依赖）
  const stripped = String(html)
    .replace(/<\/(p|div|li|h[1-6]|tr|blockquote|details|summary)>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/<!\[CDATA\[[\s\S]*?\]\]>/g, ' ');
  const decoded = stripped.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, m => ENTITIES[m] || ' ');
  return decoded.replace(/\s+/g, ' ').trim();
}

function indexText(post) {
  const text = plainText(post.content);
  return text.length > LIMIT ? `${text.slice(0, LIMIT)}…` : text;
}

hexo.extend.generator.register('search_index_trimmed', function (locals) {
  const root = this.config.root;
  const data = locals.posts.toArray().map(post => ({
    title: post.title,
    url: encodeURI(root + post.path),
    content: indexText(post),
    categories: post.categories.toArray().map(item => item.name),
    tags: post.tags.toArray().map(item => item.name)
  }));

  return {
    path: this.config.search.path,
    data: JSON.stringify(data)
  };
});
