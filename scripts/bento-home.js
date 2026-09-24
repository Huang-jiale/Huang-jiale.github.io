/*
 * 首页：最近 52 周的发文热力图 + 三张一级模块卡（工作 / 学习 / 生活）。
 * 不 fork 主题，靠两个官方能力拼出来：
 *
 *   1. before_generate（优先级 10，排在主题自己的 injects 之后）里算好一份数据挂到
 *      hexo.theme.config.bento，模板只管渲染，不写死任何篇数/分类名。
 *   2. 同一处调 hexo.theme.setView('index.njk', 模板原文) 覆盖主题的首页模板。
 *      Hexo 的 index 生成器只登记 route + layout 名，模板在渲染那一刻才查，
 *      所以 before_generate 里换掉即可；主题自己也是用 setView 注入自定义视图的
 *      （node_modules/hexo-theme-next/scripts/events/lib/injects.js）。
 *      模板照抄主题 layout/index.njk 的骨架：extends _layout.njk + sidebar 宏，
 *      头部、侧栏、页脚、搜索、深色模式开关全部保留。
 *
 * 只有首页第 1 页走这套；第 2 页起（hexo 按 index_generator.per_page 分页）落回主题原来的
 * 文章列表 + 分页，老链接 /page/2/ 不坏。
 *
 * 模块的 name 必须和 _posts 里的一级分类逐字一致（现在是三层：学习 / 模块 / 子分类）。
 * 篇数、子分类、题数、热力图全部从站点数据库现算，导完新内容不用改这个文件；
 * blurb 这类文案是人写的，改这里。
 */

/* global hexo */

'use strict';

const fs = require('fs');
const path = require('path');

// 模板放在 tools/ 而不是 scripts/：Hexo 会把 scripts/ 下的每个文件当 JS 加载，
// 一个 .njk 丢进去就是「Script load failed」。
const TEMPLATE = path.join(__dirname, '..', 'tools', 'bento-home.njk');

// 首页那张卡从「一周一格」改成「一月一根柱」（2026-09-24）：52 周里只有 9 天有数据，
// 整张图 96% 是空白，看着像坏了。按月是这套数据唯一诚实的精度——时政本来就按月归档，
// 其余内容是按月导入的，所以柱子上标的是「这个月入库多少篇」，不是「哪天写的」。
const MONTHS = 12;

// 三个一级模块，文案写在这里；哪个模块没文章就渲染成虚线占位卡（现在只有「工作」还空着）。
const TOPS = [
  {
    name : '学习',
    blurb: '公考备考：行测难题刷题库、按月归档的时政考点。点分类名下钻，左侧栏自由选。'
  },
  { name: '工作', blurb: '竞品与选品、流程和复盘。写什么、怎么写，等第一篇定口径。' },
  { name: '生活', blurb: '爱好系统课：素描 30 课，加上猜灯谜、八段锦、数独、象棋、五子棋、书法各一套（每项 3 个阶段一篇，共 64 课）。' }
];

// 分类名 -> URL 片段：hexo 把分类目录名里的空格换成 -，中文原样保留再百分号编码
function catUrl(names) {
  return '/categories/' + names.map(n => encodeURIComponent(n.replace(/ /g, '-'))).join('/') + '/';
}

// 一格 = 一个月：柱高按「当月入库篇数 / 最高月份」，0 篇的月份留一条矮栈
function buildMonths(posts) {
  const byMonth = new Map();
  posts.forEach(p => {
    const key = p.date.format('YYYY-MM');
    const rec = byMonth.get(key) || { count: 0, mods: new Set() };
    rec.count++;
    // 悬停里报「模块」这一层（三层分类的第 2 层），比只说「学习」有用
    const cat = p.categories && p.categories.length > 1 ? p.categories.data[1].name : '';
    if (cat) rec.mods.add(cat);
    byMonth.set(key, rec);
  });

  // 从本月往前推 MONTHS - 1 个月：Date 的年/月会自动向借位，不用自己处理跨年
  const now = new Date();
  const cells = [];
  for (let i = MONTHS - 1; i >= 0; i--) {
    const dt = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}`;
    const rec = byMonth.get(key);
    cells.push({
      key  : key,
      name : `${dt.getMonth() + 1}月`,
      count: rec ? rec.count : 0,
      mods : rec ? [...rec.mods] : []
    });
  }

  const top = Math.max(1, ...cells.map(c => c.count));
  let shown = 0;
  cells.forEach(c => {
    shown += c.count;
    c.ratio  = c.count / top;
    // 最低给 6%，不然「1 篇」和「0 篇」在 104px 高的图里分不出来
    c.height = c.count ? Math.max(6, Math.round(c.ratio * 100)) : 2;
    c.label  = `${c.key} · ${c.count} 篇${c.mods.length ? ` · ${c.mods.join('、')}` : ''}`;
  });

  return { cells, shown, top, from: cells[0].key, to: cells[MONTHS - 1].key };
}

function build(hexo) {
  // Warehouse 的 Query 不是数组、也不可迭代（`.filter()` 返回的还是 Query），必须 toArray() 摊平；
  // 摊平后再排序，因为 Query.sort(…) 收的是 '-date' 这种字段名，传比较函数会被忽略。
  const posts = hexo.locals.get('posts').filter(p => p.published !== false).toArray();
  const nameAt = (p, i) => (p.categories && p.categories.length > i ? p.categories.data[i].name : '');

  const tops = TOPS.map(cfg => {
    const mine = posts.filter(p => nameAt(p, 0) === cfg.name);

    // 第 2 层（行测 / 时政要点 / 素描 …）：按文章里出现的顺序去重，篇数一并带上
    const kids = new Map();
    mine.forEach(p => {
      const name = nameAt(p, 1);
      if (name) kids.set(name, (kids.get(name) || 0) + 1);
    });

    // 题数：渲染后的正文里每道题一个 <details class="answer">，数它最不容易说谎
    const questions = mine.reduce((sum, p) => sum + ((String(p.content).match(/<details class="answer"/g) || []).length), 0);

    return {
      name   : cfg.name,
      url    : catUrl([cfg.name]),
      blurb  : cfg.blurb,
      count  : mine.length,
      questions,
      kicker : mine.length
        ? (questions ? `${questions} 题 · ${mine.length} 篇` : `${mine.length} 篇`)
        : '还没有内容',
      kids   : [...kids].map(([name, n]) => ({ name, url: catUrl([cfg.name, name]), count: n }))
    };
  });

  const recent = posts
    .sort((a, b) => b.date - a.date)
    .slice(0, 6)
    .map(p => ({
      title: p.title,
      url  : `/${p.path}`,
      day  : p.date.format('MM-DD'),
      cat  : p.categories.length ? p.categories.data[p.categories.length - 1].name : ''
    }));

  return {
    tops,
    months: buildMonths(posts),
    recent,
    total : posts.length
  };
}

// Hexo 把 scripts/ 下的文件包进 `function(exports, require, module, __filename, __dirname, hexo)`
// 直接执行，不会调用 module.exports，所以这里用注入进来的全局 hexo（主题自己的脚本也这么写）。
hexo.extend.filter.register('before_generate', () => {
  const bento = build(hexo);
  if (!bento.tops.some(t => t.count)) {
    hexo.log.warn('[bento-home] 三大模块一篇都没匹配上，首页保持主题原样');
    return;
  }
  hexo.theme.config.bento = bento;
  hexo.theme.setView('index.njk', fs.readFileSync(TEMPLATE, 'utf8'));
  hexo.log.info(`[bento-home] 首页 ${bento.tops.map(t => `${t.name} ${t.kicker}`).join(' / ')}；`
    + `按月热度 ${bento.months.from} → ${bento.months.to}，${MONTHS} 个月合计 ${bento.months.shown} 篇，最高 ${bento.months.top} 篇/月`);
}, 10);
