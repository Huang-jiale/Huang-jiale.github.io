#!/usr/bin/env node
/**
 * 知识库导入流水线：狼人杀 / 麻将 / 黑八 / 斯诺克 / 折纸 / 跳棋。
 *
 * 母本：data/kb-raw/<id>/（复制自 C:\Users\lenovo\Documents\Qoder\2026-09-21\5a01cf22\courses\kb\dist\，
 *       那边是六套词条的 Markdown 导出，**原件只读**；复制后逐文件核过 md5）
 *       每套一个 index.md（H1 是标题、紧跟一行 `> ` 是导语），示意图在 images/svg/ 下按 <id>-figN.svg 命名。
 * 切法：**一套一篇**（用户 2026-09-27：词条式，一套一页，不再拆阶段），六套 = 六篇。
 *       分类两层：`生活 / 麻将`（用户 2026-09-27 定的口径，不要三级，也不要总览页，靠分类页进）。
 * 允许的改写只有三处（和 import-shenghuo.mjs 同一套）：段落软换行合并、`**x**`→`<strong>x</strong>`
 *                                                    （紧贴汉字的星号 CommonMark 不认）、
 *                                                    图片路径 `../svg/…` → `/images/kb/<id>/…`
 * 不加任何母本里没有的句子：H1 和导语原样搬进 front-matter 的 title / description，正文一字不补。
 * 两道自检：① 母本每一行（同规则归一后）必须原样出现在生成的文章里，H1/导语必须逐字等于 title/description；
 *           ② 结构——六套全部入篇、每篇 H2 数与图数 == 母本、汉字数 == 母本、引用图片全部落盘、slug 不撞
 *
 * 跑法：node tools/import-kb.mjs [--clean]
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const RAW = path.join(ROOT, 'data', 'kb-raw');
const POSTS = path.join(ROOT, 'source', '_posts', '知识库');
const IMG = path.join(ROOT, 'source', 'images', 'kb');
const CLEAN = process.argv.includes('--clean');
const die = (m) => { console.error('✗ ' + m); process.exit(1); };

const DATE = '2026-09-27';
const POST_TOTAL = 6;

// id = 母本目录名（也是图片目录名，ASCII）；cn = 二级分类名（用户给的措辞，「黑八」不是「八球」）
const TOPICS = [
  { id: 'werewolf',        cn: '狼人杀' },
  { id: 'mahjong',         cn: '麻将' },
  { id: 'pool8',           cn: '黑八' },
  { id: 'snooker',         cn: '斯诺克' },
  { id: 'origami',         cn: '折纸' },
  { id: 'chinesecheckers', cn: '跳棋' },
];

// ---------- 归一（与 import-shenghuo.mjs 同一套判据）----------
const BLOCK = /^(\s{0,3}#{1,6}\s|\s{0,3}>\s?|\s{0,3}[-*+]\s|\s{0,3}\d+\.\s|\||!\[|```|___|\$\$)/;
let hardBreaks = 0;

function reflow(lines) {
  const out = [];
  for (const raw of lines) {
    const l = raw.replace(/\s+$/, '');
    const hard = /\s{2,}$/.test(raw);
    if (hard) hardBreaks++;
    if (!l.trim()) { out.push({ t: '', blank: true }); continue; }
    if (BLOCK.test(l) || out.length === 0 || out.at(-1).blank || hard) { out.push({ t: l }); continue; }
    const prev = out.at(-1);
    const a = prev.t.replace(/\s+$/, '');
    const b = l.replace(/^\s+/, '');
    const space = /[A-Za-z0-9)$]$/.test(a) && /^[A-Za-z0-9(]/.test(b);
    prev.t = a + (space ? ' ' : '') + b;
  }
  return out.map((x) => x.t);
}

const strong = (s) => s.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>');
const oddStars = [];
function checkStars(line, where) {
  if ((line.match(/(?<!\*)\*(?!\*)/g) || []).length % 2) oddStars.push(`${where}: ${line.slice(0, 40)}`);
}

const wanted = new Map();                                    // 'id/文件名' → 母本里的实际路径
function rewriteImgs(line, id) {
  return line.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (all, alt, ref) => {
    if (/^https?:/.test(ref)) return all;
    const name = path.basename(ref);
    const rel = path.dirname(ref).replace(/^(\.\.[\\/])+/, '');   // 母本里写 ../svg/x.svg，落盘在 images/svg/x.svg
    const dir = path.join(RAW, id, 'images', rel);
    const src = path.join(dir, name);
    if (!fs.existsSync(src)) die(`${id}：图片找不到 ${ref}（应在 ${dir}）`);
    wanted.set(`${id}/${name}`, src);
    return `![${alt}](/images/kb/${id}/${name})`;
  });
}

/** 母本一行行归一；返回 { title, lead, lines, h2, han, imgs } */
function normalizeOne(id, text) {
  const lines = reflow(text.split('\n')).map((l) => {
    if (l.includes('*')) checkStars(l, id);
    return strong(rewriteImgs(l, id));
  });
  const title = (lines.find((l) => l.startsWith('# ')) || '').slice(2).trim() || die(`${id}：母本没有 H1 标题`);
  const lead = (lines.find((l) => l.startsWith('> ')) || '').slice(2).trim() || die(`${id}：母本没有导语`);
  const body = lines.filter((l) => l !== `# ${title}` && l !== `> ${lead}`);
  const plain = body.join('\n').replace(/!\[[^\]]*\]\([^)]*\)/g, '');
  return {
    title, lead, body,
    h2: (body.filter((l) => /^## /.test(l))).length,
    han: (plain.match(/[㐀-鿿]/g) || []).length,
    imgs: new Set([...body.join('\n').matchAll(/!\[[^\]]*\]\((\/images\/kb\/[^)]+)\)/g)].map((m) => m[1])),
  };
}

// ---------- 生成 ----------
const arts = [];
for (const [i, tp] of TOPICS.entries()) {
  const dir = path.join(RAW, tp.id);
  if (!fs.existsSync(dir)) die(`母本目录不存在：${dir}`);
  const md = path.join(dir, 'index.md');
  if (!fs.existsSync(md)) die(`母本缺 index.md：${md}`);
  const n = normalizeOne(tp.id, fs.readFileSync(md, 'utf8'));

  const rawImgs = fs.readdirSync(path.join(dir, 'images', 'svg')).filter((f) => f.endsWith('.svg'));
  if (rawImgs.length !== n.imgs.size) die(`${tp.id}：母本有 ${rawImgs.length} 张图，正文只引用了 ${n.imgs.size} 张`);
  for (const f of rawImgs) if (!n.imgs.has(`/images/kb/${tp.id}/${f}`)) die(`${tp.id}/${f}：没被正文引用`);

  arts.push({ ...tp, ...n, slug: `kb-${tp.id}`, rawImgs,
    date: `${DATE} 09:${String(i + 1).padStart(2, '0')}:00` });
}

// ---------- 落盘 ----------
if (CLEAN) {
  fs.rmSync(POSTS, { recursive: true, force: true });
  fs.rmSync(IMG, { recursive: true, force: true });
}
fs.mkdirSync(POSTS, { recursive: true });
for (const id of new Set(arts.map((a) => a.id))) fs.mkdirSync(path.join(IMG, id), { recursive: true });

const esc = (s) => s.replace(/"/g, '”');
const slugs = new Set();
for (const a of arts) {
  if (slugs.has(a.slug)) die(`slug 撞了：${a.slug}`);
  slugs.add(a.slug);
  const fm = ['---', `title: "${esc(a.title)}"`, `slug: ${a.slug}`, `date: ${a.date}`,
    'categories:', '  - "生活"', `  - "${a.cn}"`, 'tags:', '  - "生活"', `  - "${a.cn}"`,
    `description: "${esc(a.lead)}"`, '---'].join('\n');
  fs.writeFileSync(path.join(POSTS, `${a.slug}.md`), fm + '\n\n' + a.body.join('\n') + '\n');
}
let copied = 0;
for (const [w, src] of wanted) {
  const [id, name] = w.split('/');
  fs.copyFileSync(src, path.join(IMG, id, name));
  copied++;
}

// ---------- 自检 ①：母本逐行都要在文章里，H1/导语逐字进 front-matter ----------
let lost = 0;
for (const a of arts) {
  const gen = fs.readFileSync(path.join(POSTS, `${a.slug}.md`), 'utf8');
  const { body } = normalizeOne(a.id, fs.readFileSync(path.join(RAW, a.id, 'index.md'), 'utf8'));
  for (const line of body) {
    if (!line.trim() || line.startsWith('# ')) continue;
    if (!gen.includes(line)) {
      lost++;
      if (lost <= 6) console.error(`✗ 母本行没进文章 [${a.id}] ${line.slice(0, 60)}`);
    }
  }
  if (!gen.includes(`title: "${esc(a.title)}"`)) die(`${a.id}：H1 没有逐字进 title`);
  if (!gen.includes(`description: "${esc(a.lead)}"`)) die(`${a.id}：导语没有逐字进 description`);
}
if (lost) die(`自检①：${lost} 行母本内容在生成的文章里找不到`);

// ---------- 自检 ②：结构 ----------
const problems = [];
for (const a of arts) {
  const gen = fs.readFileSync(path.join(POSTS, `${a.slug}.md`), 'utf8');
  const gotH2 = (gen.match(/^## /gm) || []).length;
  if (gotH2 !== a.h2) problems.push(`${a.slug} 里 ${gotH2} 个 H2，母本有 ${a.h2} 个`);
  const gotHan = ((gen.split('---\n').slice(2).join('')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '').match(/[㐀-鿿]/g) || []).length);
  if (gotHan !== a.han) problems.push(`${a.slug} 汉字 ${gotHan}，母本 ${a.han}（导入不该增删正文）`);
  if (!gen.includes('  - "生活"') || !gen.includes(`  - "${a.cn}"`)) problems.push(`${a.slug} 分类不是 生活 / ${a.cn}`);
  const cats = gen.split('\n').slice(gen.split('\n').findIndex(l => l === 'categories:') + 1);
  const catList = cats.slice(0, cats.findIndex(l => l === 'tags:'));
  if (catList.filter(l => l.startsWith('  - ')).length !== 2) problems.push(`${a.slug} 分类层数 ${catList.filter(l => l.startsWith('  - ')).length}，应该是两层`);
  for (const l of gen.split('\n')) {
    if (/\*\*/.test(l)) problems.push(`${a.slug} 残留 **：${l.slice(0, 40)}`);
    if (/\]\(\.\.\//.test(l)) problems.push(`${a.slug} 残留相对路径`);
  }
  if (a.imgs.size !== 3) problems.push(`${a.slug} 引用了 ${a.imgs.size} 张图，词条应该是 3 张`);
  for (const [id, name] of wanted) {
    if (id !== a.id) continue;
    if (!fs.existsSync(path.join(IMG, id, name))) problems.push(`图片没落盘：${id}/${name}`);
  }
}
if (arts.length !== POST_TOTAL) problems.push(`应该 ${POST_TOTAL} 篇，现在 ${arts.length} 篇`);
if (wanted.size !== arts.reduce((s, a) => s + a.rawImgs.length, 0)) {
  problems.push(`落盘图 ${wanted.size} 张 != 母本图 ${arts.reduce((s, a) => s + a.rawImgs.length, 0)} 张`);
}
if (problems.length) die('自检②：\n  ' + [...new Set(problems)].slice(0, 10).join('\n  '));

console.log(`生成文章 ${arts.length} 篇 -> ${path.relative(ROOT, POSTS)}；图片 ${copied} 张 -> ${path.relative(ROOT, IMG)}`);
for (const a of arts) {
  console.log(`  ${a.slug.padEnd(20)} 生活 / ${a.cn}　${String(a.h2).padStart(2)} 节、${a.imgs.size} 图、${a.han} 汉字`);
}
console.log(`段落硬换行 ${hardBreaks} 处；单个星号可疑行 ${oddStars.length} 处${oddStars.length ? '：' + oddStars.slice(0, 3).join(' | ') : ''}`);
console.log(`自检通过：${POST_TOTAL} 套全部入篇、母本逐行都在文章里、引用图片全部落盘`);
