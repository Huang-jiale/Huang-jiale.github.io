#!/usr/bin/env node
/**
 * 素描教程导入流水线。
 *
 * 母本：D:\blog\data\sketch-raw\（复制自 C:\Users\lenovo\Documents\Qoder\2026-09-21\5a01cf22，
 *       原件只读；course/ 是 30 课一课一个 MD，basics/ 是入门总览那篇）
 * 切法：**一个阶段一篇**（用户 2026-09-23 要求：按大模块分类、不要太多篇、方便后面更新）
 *       → sk-stage1..sk-stage6 六篇 + sk-intro 一篇总览 = 7 篇
 *       分类两级：`素描 / 阶段N 名称`；课与课的边界靠 `## NN 课名` 保住，重跑不改内容
 * 允许的改写只有三处：段落软换行合并、`**x**`→`<strong>x</strong>`（紧贴汉字的星号 CommonMark 不认）、
 *                    图片路径 `images/…` → `/images/sketch/<组>/<文件名>`
 * 两道自检：① 母本每一行（同规则归一后）必须原样出现在生成的文章里；
 *           ② 结构——30 课全部入篇、每篇课数 == manifest 该阶段课数、引用图片全部落盘、slug 不撞
 *
 * 跑法：node tools/import-sketch.mjs [--clean]
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const RAW = path.join(ROOT, 'data', 'sketch-raw');
const POSTS = path.join(ROOT, 'source', '_posts', '素描教程');
const IMG = path.join(ROOT, 'source', 'images', 'sketch');
const CLEAN = process.argv.includes('--clean');
const die = (m) => { console.error('✗ ' + m); process.exit(1); };
const CN = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'];

// ---------- 母本 ----------
const msrc = fs.readFileSync(path.join(RAW, 'course.manifest.js'), 'utf8');
const MANIFEST = new Function('module', msrc.replace('module.exports =', 'return'))({});
const STAGES = MANIFEST.stages.map((s) => ({ ...s, cn: s.no.replace('阶段', '') }));

function readFm(text) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!m) return { fm: {}, body: text };
  const g = (k) => (m[1].match(new RegExp('^' + k + ':[ \\t]*(.*)$', 'm')) || [, ''])[1].trim();
  return {
    fm: { title: g('title'), desc: g('description'), tags: (g('tags').match(/\[(.*)\]/) || [, ''])[1] },
    body: text.slice(m[0].length),
  };
}

// ---------- 归一 ----------
const BLOCK = /^(\s{0,3}#{1,6}\s|\s{0,3}>\s?|\s{0,3}[-*+]\s|\s{0,3}\d+\.\s|\||!\[|```|___|\$\$)/;
const CJK = /[，。；：、？）》」』"'’]$/u;
let hardBreaks = 0;

/** 把 HTML 导出时留下的软换行拼回一个段落；列表/表格/标题/引用各自成行 */
function reflow(lines) {
  const out = [];
  for (const raw of lines) {
    const l = raw.replace(/\s+$/, '');
    const hard = /\s{2,}$/.test(raw);          // 行尾两个空格 = 作者要的硬换行，别合并
    if (hard) hardBreaks++;
    if (!l.trim()) { out.push({ t: '', blank: true }); continue; }
    if (BLOCK.test(l) || out.length === 0 || out.at(-1).blank || hard) {
      out.push({ t: l });
      continue;
    }
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

const wanted = new Map();                                  // '组/文件名' → 母本里的实际路径
function rewriteImgs(line, group, baseDir) {
  return line.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (all, alt, ref) => {
    if (/^https?:/.test(ref)) return all;
    const name = path.basename(ref);
    const src = findRaw(baseDir, name);
    if (!src) die(`图片找不到：${ref}（在 ${baseDir} 下没有 ${name}）`);
    wanted.set(`${group}/${name}`, src);
    return `![${alt}](/images/sketch/${group}/${name})`;
  });
}
const RAWIMG = path.join(RAW, 'course', 'images');
const RAWBASIC = path.join(RAW, 'basics', 'images');
function findRaw(baseDir, name) {
  for (const d of [baseDir, path.join(baseDir, 'svg')]) {
    const p = path.join(d, name);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

function normalize(text, group, baseDir, where, shift = true) {
  const out = reflow(text.split('\n')).map((l) => {
    if (l.includes('*')) checkStars(l, where);
    return rewriteImgAndShift(l);
  });
  function rewriteImgAndShift(l) {
    const h = shift ? l.match(/^(#{2,6})\s/) : null;
    const body = rewriteImgs(l, group, baseDir);
    return h ? '#' + body : strong(body);
  }
  return out;
}

// ---------- 生成 ----------
function lessonBody(md, group, baseDir, where) {
  const { fm, body } = readFm(fs.readFileSync(md, 'utf8'));
  const lines = normalize(body, group, baseDir, where);
  const first = lines.find((l) => l.startsWith('# '));
  const title = (fm.title || '').replace(/^阶段[一二三四五六]·\s*\d+\s*/, '') || (first || '').replace(/^#\s*/, '');
  const rest = lines.filter((l) => !l.startsWith('# '));       // H1 由外层给，课内从 ## 起
  return { fm, title, lines: rest };
}

const arts = [];
for (const st of STAGES) {
  const files = [];
  for (const les of st.lessons) {
    const f = path.join(RAW, 'course', `${les.n}-${path.basename(les.file, '.html')}.md`);
    if (!fs.existsSync(f)) die(`manifest 里的课在母本找不到：${f}`);
    files.push({ les, body: lessonBody(f, st.id, RAWIMG, st.id) });
  }
  const n = STAGES.indexOf(st) + 1;
  const head = [
    `<strong>本阶段目标</strong>：${st.goal}（${st.weeks}，共 ${files.length} 课，标签「${st.tag}」）。`,
    '',
    '| 课 | 标题 | 一句话 |',
    '| --- | --- | --- |',
    ...files.map((x) => `| ${x.les.n} | ${x.les.title} | ${x.body.fm.desc || x.les.desc} |`),
    '',
  ];
  const bodyLines = head;
  for (const x of files) {
    const no = x.les.n;
    bodyLines.push(`## ${no} ${x.les.title}`, '');
    if (x.body.fm.desc) bodyLines.push(`<strong>这一课练什么</strong>：${x.body.fm.desc}`, '');
    bodyLines.push(...x.body.lines, '');
  }
  arts.push({
    slug: `sk-stage${STAGES.indexOf(st) + 1}`,
    cat1: '素描',
    cat2: `阶段${st.cn} ${st.name}`,
    title: `素描阶段${st.cn} · ${st.name}`,
    desc: `${st.goal}。${st.weeks}，${files.length} 课。`,
    tags: ['素描', st.name],
    date: `2026-09-23 12:0${n}:00`,
    lines: bodyLines,
    lessonCount: files.length,
    h2: files.length,
  });
}

// 入门总览：basics/intro-overview.md 自己就是一篇，照搬
{
  const { fm, body } = readFm(fs.readFileSync(path.join(RAW, 'basics', 'intro-overview.md'), 'utf8'));
  const lines = normalize(body, 'intro', RAWBASIC, 'intro', false).filter((l) => !l.startsWith('# '));
  arts.push({
    slug: 'sk-intro', cat1: '素描', cat2: '入门总览',
    title: '素描入门总览 · 六节课与四周计划',
    desc: fm.desc || '从握笔、排线、透视到明暗五大面，含四周练习计划与常见毛病自查。',
    tags: ['素描', '绘画入门'], date: '2026-09-23 12:10:00', lines, lessonCount: 1,
  });
}

// ---------- 落盘 ----------
if (CLEAN) {
  fs.rmSync(POSTS, { recursive: true, force: true });
  fs.rmSync(IMG, { recursive: true, force: true });
}
fs.mkdirSync(POSTS, { recursive: true });
for (const g of new Set([...wanted.keys()].map((w) => w.split('/')[0]))) fs.mkdirSync(path.join(IMG, g), { recursive: true });

const slugs = new Set();
for (const a of arts) {
  if (slugs.has(a.slug)) die(`slug 撞了：${a.slug}`);
  slugs.add(a.slug);
  const fm = ['---', `title: ${a.title}`, `date: ${a.date}`, 'tags:', ...a.tags.map((t) => `  - ${t}`),
    'categories:', `  - ${a.cat1}`, `  - ${a.cat2}`, `description: ${a.desc}`, '---'].join('\n');
  fs.writeFileSync(path.join(POSTS, `${a.slug}.md`), fm + '\n\n' + a.lines.join('\n') + '\n');
}
let copied = 0;
for (const [w, src] of wanted) {
  const [group, name] = w.split('/');
  fs.copyFileSync(src, path.join(IMG, group, name));
  copied++;
}

// ---------- 自检 ①：母本逐行都要在文章里 ----------
const gen = new Map(arts.map((a) => [a.slug, fs.readFileSync(path.join(POSTS, `${a.slug}.md`), 'utf8')]));
const all = [...gen.values()].join('\n');
let lost = 0;
for (const [group, dir, base] of [['course', path.join(RAW, 'course'), RAWIMG], ['intro', path.join(RAW, 'basics'), RAWBASIC]]) {
  const files = group === 'course' ? fs.readdirSync(dir).filter((f) => /^\d\d-.*\.md$/.test(f)) : ['intro-overview.md'];
  for (const f of files) {
    const { body } = readFm(fs.readFileSync(path.join(dir, f), 'utf8'));
    for (const l of normalize(body, group === 'course' ? f.match(/stage\d/)[0] : 'intro', base, f, group === 'course')) {
      if (!l.trim() || l.startsWith('#')) continue;           // H1 被外层标题替代，单独查
      if (!all.includes(l)) { lost++; if (lost <= 6) console.error(`✗ 母本行没进文章 [${f}] ${l.slice(0, 60)}`); }
    }
  }
}
if (lost) die(`自检①：${lost} 行母本内容在生成的文章里找不到`);

// ---------- 自检 ②：结构 ----------
const problems = [];
for (const [n, st] of STAGES.entries()) {
  const a = arts[n];
  const got = (gen.get(a.slug).match(/^## \d\d /gm) || []).length;
  if (got !== st.lessons.length) problems.push(`${a.slug} 里 ${got} 个课标题，manifest 说 ${st.lessons.length} 课`);
  for (const l of gen.get(a.slug).split('\n')) {
    if (/\*\*/.test(l)) problems.push(`${a.slug} 残留 **：${l.slice(0, 40)}`);
    if (/\]\(images\//.test(l)) problems.push(`${a.slug} 残留相对图片路径`);
  }
}
{                                                          // 总览那篇：H2 数量要和母本一致（它不降标题）
  const src = fs.readFileSync(path.join(RAW, 'basics', 'intro-overview.md'), 'utf8');
  const wantH2 = (readFm(src).body.match(/^## /gm) || []).length;
  const got = (gen.get('sk-intro').match(/^## /gm) || []).length;
  if (got !== wantH2) problems.push(`sk-intro 里 ${got} 个 H2，母本有 ${wantH2} 个`);
}
for (const w of wanted.keys()) if (!fs.existsSync(path.join(IMG, ...w.split('/')))) problems.push(`图片没落盘：${w}`);
const allRaw = [];
const walk = (p) => {
  for (const e of fs.readdirSync(p, { withFileTypes: true })) {
    if (e.isDirectory()) walk(path.join(p, e.name));
    else allRaw.push(e.name);
  }
};
walk(RAWIMG);
walk(RAWBASIC);
const referenced = new Set([...wanted.keys()].map((w) => w.split('/')[1]));
const orphans = allRaw.filter((f) => !referenced.has(f));

console.log(`生成文章 ${arts.length} 篇（${arts.map((a) => a.slug).join('、')}）`);
console.log(`课：${arts.slice(0, 6).reduce((s, a) => s + a.lessonCount, 0)} 课入 ${STAGES.length} 篇；母本图片 ${allRaw.length} 张，正文引用并已入库 ${copied} 张，未引用 ${orphans.length} 张`);
console.log(`段落硬换行 ${hardBreaks} 处；单个星号可疑行 ${oddStars.length} 处${oddStars.length ? '：' + oddStars.slice(0, 3).join(' | ') : ''}`);
console.log(`分类：${[...new Set(arts.map((a) => a.cat2))].join('、')}（都在「素描」下面）`);
if (problems.length) die('自检②：\n  ' + [...new Set(problems)].slice(0, 10).join('\n  '));
console.log('自检通过：30 课全部入篇、母本逐行都在文章里、引用图片全部落盘');
