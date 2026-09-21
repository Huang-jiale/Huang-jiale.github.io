/**
 * 时政要点知识库 → Hexo 文章（一月一篇）
 *
 * 母本：`data/shizheng-raw/shizheng-summary.md`
 *   （原件在 `C:\Users\lenovo\Documents\Qoder\...\shizheng-2025-11_to_2026-02\`，**只复制、不修改**）
 * 结构是一个 h1 一个月（`# 2025年11月　关键词 · 关键词 …`），月内 h2 是分类（重要讲话/文件/事件/科技/纪念日），
 * h3 是一条条目，标题尾部带 ★ 重要度；文件末尾另有「三大专题」和「跨月速查表」两块跨月内容。
 *
 * 切法：
 *   - 每个月 → 一篇（slug `shizheng-YYYY-MM`，date 落在当月 1 号，归档按月排序）
 *   - 三大专题 / 跨月速查表 → 各一篇，它们不属于单个月，硬塞进某个月会误导
 *   - 开头的汇总首页和 `## 目录` 丢掉：目录锚点在拆分后的文章里指不到东西
 *
 * 这份母本是人写的干净 markdown，不需要 OCR 那套清洗；但它同样有「静默丢内容」的风险，
 * 所以脚本自带逐行自检：除明确声明丢弃的行外，源文件每一行都必须在某篇文章里原样出现，
 * 否则非零退出。改完规则务必重跑。
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

/* ---------- 切块 ---------- */

const MONTH_H1 = /^(\d{4})年(\d{1,2})月\s*(.+)$/;   // 比对的是已去掉 `# ` 的标题文字
const SEP = /^---\s*$/;                          // 母本里的分节线，切完就是噪声，还可能被当成 setext 标题下划线

/** 按 h1 切；返回 [{ heading, lines }]，首页（带目录的那块）heading 为 null */
function splitByH1(text) {
  const blocks = [];
  let cur = { heading: null, lines: [] };
  for (const raw of text.split(/\r?\n/)) {
    if (/^# /.test(raw) && !/^##/.test(raw)) {
      blocks.push(cur);
      cur = { heading: raw.slice(2).trim(), lines: [] };
      continue;
    }
    cur.lines.push(raw);
  }
  blocks.push(cur);
  return blocks;
}

/** `**粗体**` 夹在中文字符里会被 CommonMark 判成非边界（`纳入**「四个全面」战略布局**` 就把星号原样印出来），
 *  生成时直接换成 HTML 标签。母本 391 对 `**` 全部同行成对、无嵌套，替换是无损的。 */
const strong = s => s.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');

/** 正文清洗：去分节线、粗体转 HTML、收拢连续空行、去掉首尾空白 */
function cleanBody(lines) {
  const kept = lines.map(strong).filter(l => !SEP.test(l));
  const out = [];
  for (const l of kept) {
    if (l.trim() === '' && (out.length === 0 || out[out.length - 1].trim() === '')) continue;
    out.push(l.replace(/[ \t]+$/, ''));
  }
  while (out.length && out[out.length - 1].trim() === '') out.pop();
  return out;
}

const posts = [];
const dropped = [];                              // 有意不发布的源行，自检时豁免

const blocks = splitByH1(readFileSync(SRC, 'utf8'));
const HOME = /^时政要点汇总/;                     // 汇总首页只有引言和跨月目录，不单独成篇

// 首页的引言（`> 依据 QMind…`）解释星级与「易错」的来历，抄到每篇开头；目录整段丢弃并记入豁免
const introBlock = blocks.find(b => HOME.test(b.heading || ''));
const INTRO = introBlock ? introBlock.lines.filter(l => /^>\s/.test(l)).map(l => strong(l.trim())) : [];
for (const l of introBlock?.lines || []) if (l.trim() && !/^>\s/.test(l)) dropped.push(strong(l.trim()));

for (const b of blocks) {
  if (!b.heading || HOME.test(b.heading)) continue;
  const m = b.heading ? MONTH_H1.exec(b.heading) : null;
  let meta;
  if (m) {
    const [, y, mo, keywords] = m;
    const keys = keywords.split(/\s*·\s*/).filter(Boolean);
    meta = {
      slug: `shizheng-${y}-${String(+mo).padStart(2, '0')}`,
      title: `${y}年${+mo}月时政要点`,
      date: new Date(+y, +mo - 1, 1, 9, 0, 0),
      categories: ['时政要点', `${y}年`],
      tags: ['时政', `${y}年${+mo}月`, ...keys],
      description: keywords,
      lead: `> **本月主线**：${keywords}`,
    };
  } else if (b.heading === '三大专题') {
    meta = {
      slug: 'shizheng-zhuanti',
      title: '时政三大专题 · 中央经济工作会议 / 中央一号文件 / 新年贺词',
      date: new Date(2026, 1, 5, 9, 0, 0),
      categories: ['时政要点', '专题'],
      tags: ['时政', '专题', '中央经济工作会议', '中央一号文件', '新年贺词'],
      description: '三场必考会议的专题串讲：2025 中央经济工作会议、2026 中央一号文件、2026 新年贺词。',
      lead: '',
    };
  } else if (b.heading === '跨月速查表') {
    meta = {
      slug: 'shizheng-suchuo',
      title: '时政跨月速查 · 高频数字 + 易混提法对照',
      date: new Date(2026, 1, 10, 9, 0, 0),
      categories: ['时政要点', '速查'],
      tags: ['时政', '速查', '高频数字', '易混提法'],
      description: '考前串记：跨月高频数字、易混提法对照表、讲义来源清单。',
      lead: '',
    };
  } else {
    console.error(`不认识的一级标题，拒绝猜：${JSON.stringify(b.heading)}`);
    process.exit(1);
  }

  const body = cleanBody(b.lines);
  const lead = [meta.lead, ...INTRO.filter(Boolean)].filter(Boolean);
  posts.push({
    ...meta,
    content: (lead.length ? `${lead.join('\n')}\n\n` : '') + body.join('\n') + '\n',
  });
}

/* ---------- 产出 ---------- */

if (cleanArg && existsSync(OUT)) rmSync(OUT, { recursive: true });
mkdirSync(OUT, { recursive: true });
for (const p of posts) writeFileSync(join(OUT, `${p.slug}.md`), frontMatter(p) + p.content, 'utf8');

/* ---------- 自检：源文件每一行都得在文章里（除声明丢弃的行） ---------- */

const emitted = new Set();
for (const p of posts) for (const l of p.content.split('\n')) if (l.trim()) emitted.add(l.trim());
const allow = new Set(dropped.map(l => l.trim()).filter(Boolean));

const missing = [];
for (const raw of readFileSync(SRC, 'utf8').split(/\r?\n/)) {
  const l = strong(raw.trim());                      // 比对两侧都用替换后的写法
  if (!l || SEP.test(l) || /^# /.test(l) && !/^##/.test(l)) continue;   // 分节线和 h1 是刻意不要的
  if (allow.has(l) || emitted.has(l)) continue;
  missing.push(raw.trim());
}

console.log(`生成文章 ${posts.length} 篇 -> ${relative(ROOT, OUT)}`);
for (const p of posts) {
  const n = p.content.split('\n').length;
  console.log(`  ${p.slug}.md  ${p.title}  (${n} 行)`);
}
if (missing.length) {
  console.error(`自检失败：${missing.length} 行源内容没有出现在任何文章里`);
  for (const l of missing.slice(0, 10)) console.error('   ', l.slice(0, 100));
  process.exit(1);
}
console.log(`自检通过：母本逐行都在文章里（丢弃 ${allow.size} 行目录/首页内容）`);
