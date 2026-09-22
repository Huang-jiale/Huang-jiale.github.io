/**
 * 时政要点知识库 → Hexo 文章（一条目一篇）
 *
 * 母本：`data/shizheng-raw/shizheng-summary.md`
 *   （原件在 `C:\Users\lenovo\Documents\Qoder\...\shizheng-2025-11_to_2026-02\`，**只复制、不修改**）
 * 结构是 h1 一个月（`# 2025年11月　关键词 · 关键词 …`），月内 h2 是分类（重要讲话/文件/事件/科技/纪念日），
 * h3 是一条考点（标题尾部带 ★ 重要度）；文件末尾另有「三大专题」和「跨月速查表」两块跨月内容。
 *
 * 切法（2026-09-22 返工：先前「一月一篇」把 70 多个考点压进 4 篇，分类页等于没有）：
 *   - 月内每个 h3 考点 → 一篇。slug `sz-YYMM-序号`，date 落在当月 1 号 09:序号 分，按母本顺序稳定排列
 *   - 月内 h2 分类 → 文章的第三个 category，「时政要点 / 2025年 / 2025年11月 / 重要讲话与指示」四级，
 *     分类页因此就是考点清单，这正是用户要的「好分类」
 *   - 三大专题 → 一个专题一篇（内部还有小标题，是给一整场会议串讲的，拆开就断了上下文）
 *   - 跨月速查表 → 一篇（高频数字 + 易混提法 + 来源清单，考前一晚是一起看的，拆成三页反而没法查）
 *   - 汇总首页的引言抄进跨月那几篇；`## 目录` 丢掉——拆分后的文章里锚点指不到东西
 *
 * 母本是人写的干净 markdown，不需要 OCR 那套清洗，但同样有「静默丢内容」的风险，所以两道自检：
 *   1. 逐行：除声明丢弃的行和标题行，母本每一行都必须在某篇文章正文里原样出现；
 *   2. 标题：月内的 h2 必须是认识的分类、h3 必须逐条成篇且 slug 不撞，对不上就非零退出。
 * 改完规则务必重跑。
 *
 *   node tools/import-shizheng.mjs [--clean]
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'data', 'shizheng-raw', 'shizheng-summary.md');
const OUT = join(ROOT, 'source', '_posts', '时政要点');
const cleanArg = process.argv.includes('--clean');

if (!existsSync(SRC)) {
  console.error(`找不到母本副本：${relative(ROOT, SRC)}\n先把原件原样复制过去（不要改原件）。`);
  process.exit(1);
}

const die = msg => { console.error(msg); process.exit(1); };

/* ---------- 元信息 ---------- */

const esc = s => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
const p2 = n => String(n).padStart(2, '0');
const ymd = d => `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`;

function frontMatter({ title, slug, date, categories, tags, description }) {
  const fm = ['---', `title: "${esc(title)}"`, `slug: ${slug}`, `date: ${ymd(date)}`];
  if (categories?.length) {
    fm.push('categories:');
    for (const c of categories) fm.push(`  - "${esc(c)}"`);
  }
  if (tags?.length) {
    fm.push('tags:');
    for (const t of tags) fm.push(`  - "${esc(t)}"`);
  }
  if (description) fm.push(`description: "${esc(description)}"`);
  fm.push('---', '');
  return fm.join('\n');
}

/* ---------- 标题工具 ---------- */

const level = l => (l.match(/^#+/) || [''])[0].length;
const headingText = l => l.replace(/^#+\s*/, '').trim();
const starsOf = s => (s.match(/★/g) || []).length;
/** 星级有的标在标题尾部，有的写在括号里（`……（★★★★★） ★★★★★`），做标题时都得去掉 */
const bareTitle = s => s.replace(/（[★\s]+）/g, '').replace(/\s*★+\s*$/, '').trim();
const STAR_TAG = { 5: '五星必背', 4: '四星高频', 3: '三星', 2: '二星', 1: '一星' };

/** `**粗体**` 夹在中文字符里会被 CommonMark 判成非边界（`纳入**「四个全面」战略布局**` 就把星号原样印出来），
 *  生成时直接换成 HTML 标签。母本 391 对 `**` 全部同行成对、无嵌套，替换是无损的。 */
const strong = s => s.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');

const MONTH_H1 = /^(\d{4})年(\d{1,2})月\s*(.+)$/;
const SEP = /^---\s*$/;                     // 分节线：切完就是噪声，还可能被当成 setext 标题下划线
const HOME = /^时政要点汇总/;                // 汇总首页只有引言和跨月目录，不单独成篇

/** 母本把分类写成 `一、重要讲话 / 指示`，斜杠进分类名会让 URL 变样，改写成不带序号的短名 */
const CAT_NAME = {
  '一、重要讲话 / 指示': '重要讲话与指示',
  '二、重要文件 / 文章': '重要文件与文章',
  '三、重要事件': '重要事件',
  '四、重要科技': '重要科技',
  '五、重要周年与纪念日': '周年与纪念日',
};

/** 按 h1 切；返回 [{ heading, lines }]，首页（带目录的那块）heading 为 null */
function splitByH1(text) {
  const blocks = [];
  let cur = { heading: null, lines: [] };
  for (const raw of text.split(/\r?\n/)) {
    if (level(raw) === 1) {
      blocks.push(cur);
      cur = { heading: headingText(raw), lines: [] };
      continue;
    }
    cur.lines.push(raw);
  }
  blocks.push(cur);
  return blocks;
}

/** 卡片式列表页要一句话摘要：取正文第一条实义行，去掉项目符号、引用号和加粗标记 */
function firstSentence(body) {
  for (const l of body) {
    const t = l.replace(/^[-*>]\s*/, '').replace(/<[^>]+>/g, '').replace(/\|/g, ' ').trim();
    if (!t) continue;
    return t.length > 90 ? `${t.slice(0, 90)}…` : t;
  }
  return '';
}

/* ---------- 解析 ---------- */

const src = readFileSync(SRC, 'utf8');
const blocks = splitByH1(src);

// 三处「详见本页【专题一】」在拆分后「本页」不成立，得先知道每篇专题落在哪个 URL，才能改写正文
const CN_NUM = { 一: 1, 二: 2, 三: 3 };
const ZT_DATE = new Date(2026, 1, 5, 9, 0, 0);         // 三篇专题同一天，靠分钟区分先后
const zhuantiBlock = blocks.find(b => b.heading === '三大专题') || die('找不到「三大专题」，专题引用无处可指');
const ZT = {};                                          // 专题一 -> { title, slug, url, seq }
for (const l of zhuantiBlock.lines) {
  if (level(l) !== 2) continue;
  const name = headingText(l).split(/\s*·\s*/)[0].trim();
  const i = CN_NUM[name.replace(/^专题/, '')];
  if (!i) die(`专题编号不认识：${JSON.stringify(name)}`);
  ZT[name] = { title: headingText(l), slug: `sz-zt-${p2(i)}`, url: `/2026/02/05/sz-zt-${p2(i)}/`, seq: i };
}
if (Object.keys(ZT).length !== 3) die(`只认出 ${Object.keys(ZT).length} 个专题，母本里应有 3 个`);

/** 母本里 h3 的星级有时写两遍（`……（★★★★★） ★★★★★`），正文里留一遍就够。
 *  这条改写两侧对称（自检时也套同一个函数），所以丢了行照样会被逐行自检抓到。 */
const dedupeStars = s => s.replace(/（★+）\s*(?=★)/g, '');

/** 唯一允许的文字改写；自检两侧套用同一函数，所以别处丢了照样报 */
const xref = s => s.replace(/详见本页【(专题[一二三])】/g, (_, k) => `详见[${ZT[k].title}](${ZT[k].url})`);

/** 正文清洗：粗体转 HTML、同页引用改链接、去掉重复星级、丢分节线、收拢连续空行、去行尾空格 */
function cleanBody(lines) {
  const kept = lines.map(l => dedupeStars(xref(strong(l)))).filter(l => !SEP.test(l));
  const out = [];
  for (const l of kept) {
    if (l.trim() === '' && (out.length === 0 || out[out.length - 1].trim() === '')) continue;
    out.push(l.replace(/[ \t]+$/, ''));
  }
  while (out.length && out[out.length - 1].trim() === '') out.pop();
  return out;
}

const posts = [];
const dropped = [];                 // 有意不发布的源行，自检①豁免
const monthH3 = [];                 // 自检②：月内 h3 原文，逐条必须成篇
const monthH2 = [];                 // 自检②：月内 h2 原文，必须是认识的分类

const homeBlock = blocks.find(b => HOME.test(b.heading || ''));
// 引言（`> 依据 QMind…`）解释星级和「易错」的来历，抄到跨月那几篇开头；目录整段丢弃并记入豁免
const INTRO = (homeBlock?.lines || []).filter(l => /^>\s/.test(l)).map(l => dedupeStars(xref(strong(l.trim()))));
for (const l of homeBlock?.lines || []) if (l.trim() && !/^>\s/.test(l)) dropped.push(dedupeStars(xref(strong(l.trim()))));

for (const b of blocks) {
  if (!b.heading || HOME.test(b.heading)) continue;
  const m = MONTH_H1.exec(b.heading);

  if (!m) {
    if (b.heading === '跨月速查表') {
      const body = cleanBody(b.lines);
      posts.push({
        slug: 'sz-suchuo',
        title: '时政跨月速查 · 高频数字 + 易混提法对照',
        date: new Date(2026, 1, 10, 9, 0, 0),
        categories: ['时政要点', '速查'],
        tags: ['时政', '速查', '高频数字', '易混提法'],
        description: '考前串记：跨月高频数字、易混提法对照表、讲义来源清单。',
        content: [...INTRO, '', ...body].join('\n') + '\n',
      });
    } else if (b.heading === '三大专题') {
      let cur = null;
      const flush = () => {
        if (!cur) return;
        const body = cleanBody(cur.lines);
        posts.push({
          slug: cur.slug,
          title: `时政专题 · ${cur.title}`,
          date: new Date(ZT_DATE.getTime() + cur.seq * 60000),
          categories: ['时政要点', '专题'],
          tags: ['时政', '三大专题', cur.name],
          description: firstSentence(body),
          content: [...INTRO, '', `**专题定位**：${dedupeStars(cur.heading)}`, '', ...body].join('\n') + '\n',
        });
        cur = null;
      };
      for (const l of b.lines) {
        if (level(l) === 2) {
          flush();
          const heading = headingText(l);
          const name = heading.split(/\s*·\s*/)[0].trim();
          const found = ZT[name] || die(`专题标题对不上母本目录：${JSON.stringify(heading)}`);
          cur = { heading, name, slug: found.slug, seq: found.seq, title: heading.replace(/^专题[一二三]\s*·\s*/, ''), lines: [] };
          continue;
        }
        if (!cur && l.trim()) die('专题块里第一个 h2 之前出现了正文，先确认母本结构');
        cur?.lines.push(l);
      }
      flush();
    } else {
      die(`不认识的一级标题，拒绝猜：${JSON.stringify(b.heading)}`);
    }
    continue;
  }

  /* 一个月内：h2 是分类，h3 是一条考点 */
  const [, y, mo, keywords] = m;
  const month = `${y}年${+mo}月`;
  let cat = null;
  let item = null;
  let seq = 0;
  const flush = () => {
    if (!item) return;
    const body = cleanBody(item.lines);
    const stars = starsOf(item.heading);
    if (seq > 59) die(`${month} 条目超过 59 条，date 的分钟位会溢出`);
    posts.push({
      slug: `sz-${y.slice(2)}${p2(+mo)}-${p2(seq)}`,
      title: `${month} · ${item.title}`,
      date: new Date(+y, +mo - 1, 1, 9, seq, 0),
      categories: ['时政要点', `${y}年`, month, CAT_NAME[cat]],
      tags: ['时政', month, STAR_TAG[stars] || `${stars}星`],
      description: firstSentence(body),
      // 月的关键词串留在每篇开头，否则一篇考点孤立看不出当月主线
      content: [`**出处**：${month}（${keywords}） · ${cat}`, '', ...body].join('\n') + '\n',
    });
    item = null;
  };
  for (const l of b.lines) {
    const lv = level(l);
    if (lv === 2) {
      flush();
      cat = headingText(l);
      monthH2.push(cat);
      if (!CAT_NAME[cat]) die(`月的分类标题不认识，拒绝猜：${JSON.stringify(cat)}`);
      continue;
    }
    if (lv === 3) {
      flush();
      const heading = headingText(l);
      monthH3.push(heading);
      item = { heading, title: bareTitle(heading), lines: [] };
      seq++;
      continue;
    }
    if (item) item.lines.push(l);
    else if (l.trim()) die(`${month} 的正文出现在第一个 h3 之前：${JSON.stringify(l.trim())}`);
  }
  flush();
}

/* ---------- 产出 ---------- */

if (cleanArg && existsSync(OUT)) rmSync(OUT, { recursive: true });
mkdirSync(OUT, { recursive: true });
for (const p of posts) writeFileSync(join(OUT, `${p.slug}.md`), frontMatter(p) + p.content, 'utf8');

/* ---------- 自检①：母本每一行都得在文章里（除声明丢弃的行与标题行） ---------- */

const emitted = new Set();
for (const p of posts) for (const l of p.content.split('\n')) if (l.trim()) emitted.add(l.trim());
const allow = new Set(dropped.map(l => l.trim()).filter(Boolean));

const missing = [];
for (const raw of src.split(/\r?\n/)) {
  const l = dedupeStars(xref(strong(raw.trim())));   // 两侧都用替换后的写法比对
  if (!l || SEP.test(l) || level(l) >= 1) continue;
  if (allow.has(l) || emitted.has(l)) continue;
  missing.push(raw.trim());
}

/* ---------- 自检②：h2/h3 要逐条对上，别把整节静默丢掉 ---------- */

const problems = [];
const itemPosts = posts.filter(p => /^sz-\d{4}-\d{2}$/.test(p.slug));
if (itemPosts.length !== monthH3.length) problems.push(`母本月考点 ${monthH3.length} 条，成篇 ${itemPosts.length} 篇`);
if (new Set(itemPosts.map(p => p.slug)).size !== itemPosts.length) problems.push('条目 slug 有重复');
if (new Set(posts.map(p => p.slug)).size !== posts.length) problems.push('slug 有重复');
if (new Set(monthH2).size !== Object.keys(CAT_NAME).length) {
  problems.push(`母本里出现 ${new Set(monthH2).size} 种分类，脚本认识 ${Object.keys(CAT_NAME).length} 种`);
}

/* ---------- 汇报 ---------- */

console.log(`生成文章 ${posts.length} 篇 -> ${relative(ROOT, OUT)}`);
const groups = {};
for (const p of posts) {
  const k = p.categories.slice(1).join(' / ');
  groups[k] = (groups[k] || 0) + 1;
}
for (const [k, v] of Object.entries(groups)) console.log(`  ${k}: ${v} 篇`);

let bad = 0;
if (missing.length) {
  bad++;
  console.error(`自检①失败：${missing.length} 行源内容没有出现在任何文章里`);
  for (const l of missing.slice(0, 10)) console.error('   ', l.slice(0, 100));
}
if (problems.length) {
  bad++;
  console.error(`自检②失败：${problems.join('；')}`);
}
console.log(bad
  ? '自检未通过'
  : `自检通过：${monthH3.length} 条考点成篇、${new Set(monthH2).size} 类分类全部认识、母本逐行都在文章里（丢弃 ${allow.size} 行首页目录）`);
process.exit(bad);
