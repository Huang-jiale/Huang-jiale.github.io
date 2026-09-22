/**
 * 行测题库（27 考季高阶难题精刷）→ Hexo 文章（一个「难题组」一篇）
 *
 * 母本：`data/xingce-raw/`（原件 `D:\AI跑数据\数据`，**只复制不修改**；复制时逐个核 md5）
 *   9 个 md：判断推理/数量关系/言语理解/资料分析 各「（上）（下）」+ `_答案键.md`
 *   结构很规整：`#` 一册（`# 判断推理高分必刷难题（上）`），`##` 一个难题组
 *   （`## 定义高分必刷难题（一）`），组内是 `**N.（年份 省份）** 题干` + 选项 + `**答案：X**`；
 *   资料分析每组再按 `### 材料一/二/三` 分块并嵌入原页图片。
 *
 * 切法：**一个难题组一篇**（31 篇）+ 答案键总表 1 篇。
 *   - 为什么不是一册一篇：一册里混着 2~3 个题型（判断上册就有定义和类比），按册分类等于没分类
 *   - 为什么不是一题一篇：题目本身要连着材料/图表看，且组的题号是从 1 编号的，答案键也按组给
 *   - 分类四级：行测 / 27考季 / 模块 / 题型（题型与模块同名时只到三级，不重复一层）
 *   - 标签：刷题 / 27考季 / 模块 / 上册或下册 / 第 N 组
 *   - 图片只把正文引用到的复制进 `source/images/xingce/<ascii>/`（84 张，仓库里不放没用的图），路径同步改写；
 *     母本副本 `data/xingce-raw/assets/` 是完整的 152 张（gitignore，不入库），脚本按题数报出「引用不到」和
 *     「说了有图却一张都没有」两种缺口，供人工决定是否补图
 *   - 每篇末尾附本组的答案速览（从 `_答案键.md` 按 模块+册+题型+组号 对上号）
 *
 * 自检（跑完必须全绿，两道）：
 *   1. 逐行：除标题行外，9 个母本的每一行都必须在某篇文章里原样出现（`**`→<strong>、图片路径改写
 *      这两处归一化两侧同用，所以别处丢了照样报）；
 *   2. 结构：每个 `##` 都成篇、每个 `###` 都留在正文里、每组「题数 == 答案数」、答案都是单个 A–D、
 *      slug 不撞、引用的图片在 source 里真实存在、正文没有残留 `**`、答案键的组数与母本对得上
 *      （对不上只报警并把差异写进答案键那篇，不算失败——那是母本本身缺内容）。
 *
 *   node tools/import-xingce.mjs [--clean]
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync, copyFileSync, readdirSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const RAW = join(ROOT, 'data', 'xingce-raw');
const OUT = join(ROOT, 'source', '_posts', '行测题库');
const IMG = join(ROOT, 'source', 'images', 'xingce');
const cleanArg = process.argv.includes('--clean');

const die = msg => { console.error(msg); process.exit(1); };

if (!existsSync(RAW)) die(`找不到母本副本 ${relative(ROOT, RAW)}\n先把 D:\\AI跑数据\\数据 里的 md 和 assets/ 原样复制过去（不要动原件）。`);

/* ---------- 元信息 ---------- */

const esc = s => String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
const p2 = n => String(n).padStart(2, '0');
const ymd = d => `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} ${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`;

function frontMatter({ title, slug, date, categories, tags, description }) {
  const fm = ['---', `title: "${esc(title)}"`, `slug: ${slug}`, `date: ${ymd(date)}`];
  if (categories?.length) { fm.push('categories:'); for (const c of categories) fm.push(`  - "${esc(c)}"`); }
  if (tags?.length) { fm.push('tags:'); for (const t of tags) fm.push(`  - "${esc(t)}"`); }
  if (description) fm.push(`description: "${esc(description)}"`);
  fm.push('---', '');
  return fm.join('\n');
}

/* ---------- 母本里出现的名字 → 稳定 ASCII，URL 里不留中文 ---------- */

const MODULES = {
  判断推理: { code: 'pd', key: '判断' },
  数量关系: { code: 'sl', key: '数量' },
  言语理解: { code: 'yy', key: '言语' },
  资料分析: { code: 'zl', key: '资料' },
};
const VOL = { 上: '1', 下: '2' };
const VOL_NAME = { 上: '上册', 下: '下册' };
const ASSET_DIR = { 判断上: 'pd-shang', 判断下: 'pd-xia', 数量上: 'sl-shang', 数量下: 'sl-xia', 资料上: 'zl-shang', 资料下: 'zl-xia' };
const TYPE_FULL = { 定义: '定义判断', 类比: '类比推理', 数量: '数量关系' };   // 母本 H2 与答案键里的简写
const CN = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10 };

const level = l => (l.match(/^#+/) || [''])[0].length;
const headingText = l => l.replace(/^#+\s*/, '').trim();

const H1 = new RegExp(`^(${Object.keys(MODULES).join('|')})高分必刷难题（([上下])）$`);
// 题型名后面偶尔多一个「题」字（言语下册写的是 `中心理解题高分必刷难题（一）`），答案键那边没有，
// 所以捕获组只收题型，`题?` 放在组外——标题归一化后两边才对得上。
const H2RE = /^(定义|类比|逻辑判断|图形推理|数量关系|逻辑填空|语句表达|中心理解|资料分析)题?高分必刷难题（([一二三四五六七八九十]+)）$/;

/** 紧贴汉字的 `**粗体**` 会被 CommonMark 判成非边界，星号原样印到页面上；统一转 <strong>。
 *  母本每行 `**` 都是成对出现的（已核：奇数行 0），所以替换无损。 */
const strong = s => s.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
/** 图片路径改写：assets/判断下/p20.png -> /images/xingce/pd-xia/p20.png */
const imgPath = s => s.replace(/!\[([^\]]*)\]\(assets\/([^/]+)\/([^)]+)\)/g, (_, alt, dir, file) => {
  const ascii = ASSET_DIR[dir] || die(`图片目录没配 ASCII 名：${JSON.stringify(dir)}`);
  return `![${alt}](/images/xingce/${ascii}/${file})`;
});
const norm = s => imgPath(strong(s));

/* ---------- 读母本 ---------- */

const books = readdirSync(RAW).filter(f => f.endsWith('.md') && f !== '_答案键.md')
  .sort((a, b) => {                      // 固定成 模块 → 上/下 的顺序，别受文件系统排序影响
    const ma = H1.exec(headingText(readFileSync(join(RAW, a), 'utf8').split(/\r?\n/).find(l => level(l) === 1) || ''));
    const mb = H1.exec(headingText(readFileSync(join(RAW, b), 'utf8').split(/\r?\n/).find(l => level(l) === 1) || ''));
    if (!ma || !mb) die(`${a} 或 ${b} 的一级标题对不上模块名`);
    const ia = Object.keys(MODULES).indexOf(ma[1]) * 2 + (ma[2] === '上' ? 0 : 1);
    const ib = Object.keys(MODULES).indexOf(mb[1]) * 2 + (mb[2] === '上' ? 0 : 1);
    return ia - ib;
  });

/* ---------- 答案键：模块+册+题型+组号 -> 那一行 ---------- */

const KEY_H2 = /^## (判断|数量|言语|资料)（([上下])）\s+p\d+$/;
const KEY_ITEM = /^- (.+?)\(([一二三四五六七八九十]+)\): /;
const keyLines = readFileSync(join(RAW, '_答案键.md'), 'utf8').split(/\r?\n/);
const keyByGroup = new Map();             // '判断推理|上|定义判断|1' -> 原文行
const keyAll = [];                        // 顺序保留，用于对账和整表成篇
for (const l of keyLines) {
  const m = KEY_H2.exec(l);
  if (m) { var keyMod = Object.keys(MODULES).find(k => MODULES[k].key === m[1]), keyVol = m[2]; continue; }
  const k = KEY_ITEM.exec(l);
  if (!k) continue;
  const t = TYPE_FULL[k[1]] || k[1];
  const g = CN[k[2]];
  if (!keyMod || !g) die(`答案键这行对不上模块或组号：${JSON.stringify(l)}`);
  const id = `${keyMod}|${keyVol}|${t}|${g}`;
  if (keyByGroup.has(id)) die(`答案键里同一个组出现了两次：${id}`);
  keyByGroup.set(id, l);
  keyAll.push({ id, mod: keyMod, vol: keyVol, type: t, group: g, line: l });
}

/* ---------- 切篇 ---------- */

const posts = [];
const dropped = [];
const srcH3 = [];
const usedKeys = new Set();
let seqAll = 0;

for (const f of books) {
  const lines = readFileSync(join(RAW, f), 'utf8').split(/\r?\n/);
  const h1 = lines.find(l => level(l) === 1);
  const m = H1.exec(headingText(h1 || '')) || die(`${f} 的一级标题不认识：${JSON.stringify(h1)}`);
  const [, mod, vol] = m;
  const preamble = [];                    // H1 与第一个 H2 之间的内容（资料分析那册的 `> 说明：…`）
  let cur = null;

  const flush = () => {
    if (!cur) return;
    const body = [];
    for (const l of cur.lines) {
      if (!l.trim()) { body.push(''); continue; }
      body.push(norm(l));
    }
    const q = cur.lines.filter(l => /^\*\*\d+\.[（(]/.test(l)).length;
    const a = cur.lines.filter(l => /^\*\*答案：/.test(l)).length;
    // 「如下图所示」这类措辞说明原题带图；整篇一张图都没有，就是母本转换时把图弄丢了
    const figWords = cur.lines.filter(l => /如[上下左右]?图|下图|示意图/.test(l)).length;
    const imgs = cur.lines.filter(l => /^!\[/.test(l)).length;
    const id = `${mod}|${vol}|${cur.type}|${cur.group}`;
    const key = keyByGroup.get(id);
    if (key) usedKeys.add(id);
    seqAll++;
    posts.push({
      slug: `xc-${MODULES[mod].code}${VOL[vol]}-${p2(cur.n)}`,
      title: cur.type === mod ? `${mod} · 高分必刷难题（${cur.cn}）` : `${mod} · ${cur.type} 高分必刷难题（${cur.cn}）`,
      date: new Date(2026, 8, 22, 9, seqAll, 0),
      categories: ['行测', '27考季', mod, ...(cur.type === mod ? [] : [cur.type])],
      tags: ['刷题', '27考季', mod, VOL_NAME[vol], `第 ${cur.n} 组`],
      description: `${mod}${cur.type === mod ? '' : ` · ${cur.type}`} 第 ${cur.n} 组，共 ${q} 题（题号 1–${q}），答案随题给出，末尾附答案速览。`,
      questions: q, answers: a, figWords, imgs,
      missingKey: !key,
      content: [
        `<strong>出处</strong>：27 考季【${mod}】${VOL_NAME[vol]} · ${cur.heading}`, '',
        ...preamble.map(norm), '',
        ...body.map(l => l.trim()).filter((l, i, arr) => !(l === '' && arr[i - 1] === '')), '',
        '## 答案速览', '',
        key ? norm(key) : '（母本 `_答案键.md` 里没有这一组，待补）', '',
      ].join('\n'),
    });
    cur = null;
  };

  for (const l of lines) {
    if (level(l) === 1) continue;
    if (level(l) === 2) {
      flush();
      const heading = headingText(l);
      const g = H2RE.exec(heading) || die(`${f} 里的二级标题不认识，拒绝猜：${JSON.stringify(heading)}`);
      const cn = g[2];
      cur = { heading, type: TYPE_FULL[g[1]] || g[1], cn, group: CN[cn], n: 0, lines: [] };
      cur.n = posts.filter(p => p.slug.startsWith(`xc-${MODULES[mod].code}${VOL[vol]}-`)).length + 1;
      continue;
    }
    if (level(l) === 3) srcH3.push(headingText(l));
    if (cur) cur.lines.push(l);
    else if (l.trim()) preamble.push(l);
  }
  flush();
}

/* ---------- 答案键整表也成一篇（考前对答案只用翻一页），并对账 ---------- */

{
  const unmatched = keyAll.filter(k => !usedKeys.has(k.id));
  const keyBody = keyLines.map(l => (l.trim() ? norm(l) : '')).join('\n').replace(/\n{3,}/g, '\n\n').trim();
  const note = unmatched.length
    ? ['', `> 对账：答案键里有 ${unmatched.length} 组在母本里找不到对应题目（题还没导进来）：`,
       ...unmatched.map(k => `> - ${k.mod} ${VOL_NAME[k.vol]} · ${k.type}（${'一二三四五六七八九十'[k.group - 1]}）`)].join('\n')
    : '';
  posts.push({
    slug: 'xc-answer',
    title: '行测难题精刷 · 全模块答案键（27 考季）',
    date: new Date(2026, 8, 22, 10, 0, 0),
    categories: ['行测', '27考季', '答案键'],
    tags: ['刷题', '27考季', '答案键'],
    description: `各册「答案速览」页的汇总，题号在每个难题组内从 1 重新编号。${note ? '末尾列出尚未导入母本的组。' : ''}`,
    questions: 0, answers: 0, missingKey: false,
    content: keyBody + note + '\n',
  });
  var keyGap = unmatched.length;
}

/* ---------- 图片入库：只搬正文引用到的，其余留在母本目录并如实报数 ---------- */

const wanted = new Set();
for (const p of posts) for (const m of p.content.matchAll(/\/images\/xingce\/([^/]+)\/([^")\s]+)/g)) wanted.add(`${m[1]}|${m[2]}`);
const onDisk = new Set();                      // 'pd-xia|p20.png'，母本目录里真实存在的
for (const [dir, ascii] of Object.entries(ASSET_DIR)) {
  const d = join(RAW, 'assets', dir);
  if (!existsSync(d)) continue;
  for (const f of readdirSync(d)) onDisk.add(`${ascii}|${f}`);
}
if (cleanArg && existsSync(IMG)) rmSync(IMG, { recursive: true });
mkdirSync(IMG, { recursive: true });
let copied = 0;
for (const w of wanted) {
  const [ascii, file] = w.split('|');
  const dir = Object.keys(ASSET_DIR).find(k => ASSET_DIR[k] === ascii) || die(`图片目录映射反查不到：${ascii}`);
  const src = join(RAW, 'assets', dir, file);
  if (!existsSync(src)) die(`母本里引用了不存在的图片：assets/${dir}/${file}`);
  mkdirSync(join(IMG, ascii), { recursive: true });
  copyFileSync(src, join(IMG, ascii, file));
  copied++;
}
const orphan = [...onDisk].filter(w => !wanted.has(w));

/* ---------- 产出 ---------- */

if (cleanArg && existsSync(OUT)) rmSync(OUT, { recursive: true });
for (const p of posts) {
  const dir = join(OUT, p.categories[2]);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, `${p.slug}.md`), frontMatter(p) + p.content, 'utf8');
}

/* ---------- 自检①：母本每一行都得在文章里 ---------- */

const emitted = new Set();
for (const p of posts) for (const l of p.content.split('\n')) if (l.trim()) emitted.add(l.trim());
const allow = new Set(dropped.map(l => l.trim()).filter(Boolean));

const files = [...books, '_答案键.md'];
const missing = [];
for (const f of files) {
  for (const raw of readFileSync(join(RAW, f), 'utf8').split(/\r?\n/)) {
    const l = norm(raw.trim());
    if (!l || level(l) >= 1) continue;
    if (allow.has(l) || emitted.has(l)) continue;
    missing.push(`${f}: ${raw.trim().slice(0, 80)}`);
  }
}

/* ---------- 自检②：结构 ---------- */

const problems = [];
const arts = posts.filter(p => p.slug !== 'xc-answer');
if (new Set(arts.map(p => p.slug)).size !== arts.length) problems.push('slug 有重复');
for (const p of arts) {
  if (p.questions !== p.answers) problems.push(`${p.slug} 题数 ${p.questions} != 答案数 ${p.answers}`);
  if (!p.questions) problems.push(`${p.slug} 一题都没有`);
}
for (const p of posts) if (/\*\*/.test(p.content)) problems.push(`${p.slug} 正文残留 **`);
for (const h of srcH3) if (![...emitted].some(l => l.includes(h))) problems.push(`材料小标题没进任何正文：${h}`);
for (const w of wanted) {
  const [ascii, file] = w.split('|');
  if (!existsSync(join(IMG, ascii, file))) problems.push(`图片没入库：${ascii}/${file}`);
}
const gapArts = arts.filter(p => p.missingKey).length;
const lostFigs = arts.filter(p => p.figWords > 0 && p.imgs === 0);

/* ---------- 汇报 ---------- */

console.log(`生成文章 ${posts.length} 篇 -> ${relative(ROOT, OUT)}；图片 ${copied} 张 -> ${relative(ROOT, IMG)}`);
const byCat = {};
for (const p of posts) { const k = p.categories.slice(2).join(' / '); byCat[k] = (byCat[k] || 0) + 1; }
for (const [k, v] of Object.entries(byCat)) console.log(`  ${k}: ${v} 篇`);
console.log(`题目合计 ${arts.reduce((s, p) => s + p.questions, 0)} 题；答案键 ${keyAll.length} 组，其中 ${usedKeys.size} 组对上了文章${keyGap ? `，${keyGap} 组没有题目可对` : ''}`);
if (keyGap) console.log(`⚠ 答案键里有 ${keyGap} 组在母本里没有对应题目（已写进「答案键」那篇的对账，需要补题）`);
if (gapArts) console.log(`⚠ 有 ${gapArts} 篇文章没配到答案键那行`);
console.log(`母本图片 ${onDisk.size} 张，正文引用到并已入库 ${wanted.size} 张，未被引用 ${orphan.length} 张（仍留在 ${relative(ROOT, join(RAW, 'assets'))} 里，没动原件）`);
if (orphan.length) {
  const per = {};
  for (const o of orphan) { const a = o.split('|')[0]; per[a] = (per[a] || 0) + 1; }
  console.log(`   未被引用的目录：${Object.entries(per).map(([k, v]) => `${k} ${v} 张`).join('、')}`);
}
if (lostFigs.length) {
  console.log(`⚠ 有 ${lostFigs.length} 篇正文里出现「如下图所示」这类措辞却一张图都没有，图在转换时丢了：${lostFigs.map(p => p.slug).join('、')}`);
  console.log(`   （上面「未被引用」的图片很可能就是它们缺的图，但按题号配图要对不上就不如不配，等你确认后我再补）`);
}

let bad = 0;
if (missing.length) {
  bad++;
  console.error(`自检①失败：${missing.length} 行源内容没有出现在任何文章里`);
  for (const l of missing.slice(0, 10)) console.error('   ', l);
}
if (problems.length) { bad++; console.error(`自检②失败：\n    ${problems.slice(0, 10).join('\n    ')}`); }
console.log(bad ? '自检未通过' : `自检通过：${arts.length} 个难题组全部成篇、题数与答案数逐组相等、母本逐行都在文章里`);
process.exit(bad);
