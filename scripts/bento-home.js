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

// 52 周 × 7 天的 GitHub 式日历（2026-09-24 用户点名要回来）。中间那一版改成过按月柱状图，
// 撤了：日历是「什么时候入库的」，柱子是「入库了多少」，他要的是前者。
// 代价说清楚：137 篇集中在 9 天里，整张图绝大多数格子是空的——这不是算错，是这套数据的
// 真实形状（内容按批导入，不是日更）。格子只读，悬停出日期。
const WEEKS = 52;

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

// 一格 = 一天，7 行一列 = 一周（周一起）。列数固定 WEEKS 列，末列是本周，
// 所以今天之后的格子留空并标成 future，整张图始终是方的。
function pad2(n) {
  return String(n).padStart(2, '0');
}

function dayKey(dt) {
  return `${dt.getFullYear()}-${pad2(dt.getMonth() + 1)}-${pad2(dt.getDate())}`;
}

function buildHeat(posts) {
  const byDay = new Map();
  posts.forEach(p => {
    // moment 对象转本地日历日：入库日期给人看的，别按 UTC 差 8 小时挪到前一天
    const js = p.date.toDate();
    const key = dayKey(js);
    const rec = byDay.get(key) || { count: 0, mods: new Set() };
    rec.count++;
    // 悬停里报「模块」这一层（三层分类的第 2 层），比只说「学习」有用
    const cat = p.categories && p.categories.length > 1 ? p.categories.data[1].name : '';
    if (cat) rec.mods.add(cat);
    byDay.set(key, rec);
  });

  const now = new Date();
  // getDay(): 周日=0，减 1 再取模把周一摆到第 0 行
  const mondayOfThisWeek = now.getDate() - ((now.getDay() + 6) % 7);
  const start = new Date(now.getFullYear(), now.getMonth(), mondayOfThisWeek - (WEEKS - 1) * 7);
  const todayKey = dayKey(now);

  // 色阶按「单日最多那天」四等分，篇数整体涨上去也不用回来改阈值。
  // 先乘后除：和校验器里 Python 的 -(-n*4//peak) 同一个算法，别让浮点误差把边界天挪一档。
  const peak = Math.max(1, ...[...byDay.values()].map(r => r.count));
  const levelOf = n => (!n ? 0 : Math.min(4, Math.ceil(n * 4 / peak)));

  const weeks = [];
  const monthMarks = [];
  let lastMonth = -1;
  let shown = 0;
  for (let w = 0; w < WEEKS; w++) {
    const cells = [];
    for (let d = 0; d < 7; d++) {
      const dt = new Date(start.getFullYear(), start.getMonth(), start.getDate() + w * 7 + d);
      const key = dayKey(dt);
      const rec = byDay.get(key);
      const count = rec ? rec.count : 0;
      shown += count;
      // 本周之外（未来）的格子留空：它们不是「那天没写」，是「那天还没到」
      const future = key > todayKey;
      cells.push({
        date  : key,
        count,
        future,
        level : future ? -1 : levelOf(count),
        label : future ? '' : `${key} · ${count} 篇${rec && rec.mods.size ? ` · ${[...rec.mods].join('、')}` : ''}`
      });
    }
    // 月首标签：这一列的周一换了月份就标一次，够稀疏也够定位
    const month = cells[0].date.slice(5, 7);
    if (Number(month) !== lastMonth) {
      lastMonth = Number(month);
      monthMarks.push({ col: w, label: `${lastMonth}月` });
    }
    weeks.push({ cells });
  }

  // 月首标签挨太近会叠字，丢季后面的那个
  const marks = monthMarks.filter((m, i) => !i || m.col - monthMarks[i - 1].col >= 2);

  return {
    weeks,
    monthMarks : marks,
    shown,
    peak,
    active     : [...byDay].filter(([, r]) => r.count).length,
    from       : dayKey(start),
    to         : todayKey,
    // 整张图 WEEKS*7 格，有内容的那几天之外全是空格子——把比例摆在脚注里，别让人自己数
    idle       : WEEKS * 7 - [...byDay.values()].filter(r => r.count).length
  };
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
    heat  : buildHeat(posts),
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
    + `日历 ${bento.heat.from} → ${bento.heat.to}，${WEEKS} 周合计 ${bento.heat.shown} 篇，`
    + `有内容的 ${bento.heat.active} 天，单日最多 ${bento.heat.peak} 篇`);
}, 10);
