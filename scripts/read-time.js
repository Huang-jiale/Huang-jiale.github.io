/*
 * 文章标题下面那行的「xxxx 字 · 约 n 分钟读完」，由 tools/post-readtime.njk 调用
 * （靠主题的官方钩子 custom_file_path.postMeta 渲染进 .post-meta）。
 *
 * 为什么自己算：装过 hexo-word-counter 又删了。它统计的是 markdown 原文，
 * 图片路径、表格竖线全算进字数，行测那种一篇几百题的页面能虚报一半。
 * 这里统计渲染后的正文（post.content 就是渲染完的 HTML），先剥标签再数：
 * 汉字/假名/谚文各按 1 字算，一串连续的英文或数字按 1 词算，标点不算。
 * 400 字/分钟是中文阅读速度的常用估值（用户 2026-09-24 拍板的口径），要改就改 WPZ。
 */

/* global hexo */

'use strict';

const WPZ = 400;

// 汉字（基本 + 扩展 A）+ 假名 + 谚文各算 1 个字。写成 \u 转义，肉眼才看得出没写错边界。
const CJK = /[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u30ff\uac00-\ud7af]/g;
const LATIN = /[A-Za-z0-9]+/g;
const TAG = /<[^>]*>/g;
// 一律当噪声吃掉、不翻译：&mdash; 这类如果留着，剩下的 "mdash" 会被英文词正则数成一个字
const ENTITY = /&[#A-Za-z0-9]{1,8};/g;

function countChars(html) {
  const text = String(html || '')
    .replace(TAG, ' ')
    .replace(ENTITY, ' ');
  return (text.match(CJK) || []).length + (text.match(LATIN) || []).length;
}

function formatMinutes(minutes) {
  if (minutes < 60) return `约 ${minutes} 分钟读完`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `约 ${h} 小时 ${m} 分钟读完` : `约 ${h} 小时读完`;
}

hexo.extend.helper.register('post_readtime', function(post) {
  const chars = countChars(post && post.content);
  if (!chars) return '';
  const minutes = Math.max(1, Math.round(chars / WPZ));
  return `${chars.toLocaleString('en-US')} 字 · ${formatMinutes(minutes)}`;
});
