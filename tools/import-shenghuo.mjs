#!/usr/bin/env node
/**
 * 生活六项导入流水线：猜灯谜 / 八段锦 / 数独 / 中国象棋 / 五子棋 / 书法。
 *
 * 母本：D:\blog\data\shenghuo-raw\<id>\（复制自 C:\Users\lenovo\Documents\Qoder\2026-09-21\5a01cf22\courses\
 *       <id>\dist\markdown\，那边是六套课的 Markdown 导出，**原件只读**；复制后逐文件核过 md5）
 *       每套课一课一个 md（带 front-matter：title / date / tags / description），示意图在 images/svg/ 下按课命名。
 * 切法：**一项一个阶段一篇**（用户 2026-09-24：「按素描的结构去分类」→ 三层 + 拆篇，完全照素描），
 *       六套课 × 各 3 个阶段 = 18 篇，64 课一课不落。
 *       分类三层：`生活 / 数独 / 候选数与结构`，第三层就用母本的阶段名（用户 2026-09-24 选的口径），
 *       课号与课名进 H2 标题，靠 `## NN 课名` 保住课与课的边界，重跑不改内容。
 * 允许的改写只有三处（和 import-sketch.mjs 同一套）：段落软换行合并、`**x**`→`<strong>x</strong>`
 *                                                    （紧贴汉字的星号 CommonMark 不认）、
 *                                                    图片路径 `images/svg/…` → `/images/shenghuo/<id>/…`
 * 唯一新增的文字是每篇开头的两行说明 + 课程表（课号/课名/description 全部取自母本 front-matter，不是我编的）。
 * 两道自检：① 母本每一行（同规则归一后）必须原样出现在生成的文章里；
 *           ② 结构——64 课全部入篇、每篇 H2 数 == 该阶段课数、每篇 H3 数 == 母本这些课的 H2 总数、
 *                引用图片全部落盘、slug 不撞
 *
 * 跑法：node tools/import-shenghuo.mjs [--clean]
 */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(import.meta.dirname, '..');
const RAW = path.join(ROOT, 'data', 'shenghuo-raw');
const POSTS = path.join(ROOT, 'source', '_posts', '生活六项');
const IMG = path.join(ROOT, 'source', 'images', 'shenghuo');
const CLEAN = process.argv.includes('--clean');
const die = (m) => { console.error('✗ ' + m); process.exit(1); };

const DATE = '2026-09-24';   // 十八篇同一天导入，靠时刻错开保证顺序稳定（同一项的三篇连号）
const LESSON_TOTAL = 64;     // 六套课的课数，母本加了课就要同步这个数
const STAGES_EACH = 3;       // 切法按「每项 3 个阶段」设计，阶段数变了要先和用户重新定口径

// id = 母本目录名（也是图片目录名，ASCII）；cn = 二级分类名（用户给的措辞，「象棋」不是「中国象棋」）
// slug = 文章 URL 前缀，后面再拼阶段号（-1 / -2 / -3），一篇阶段一个 URL
const TOPICS = [
  { id: 'riddle',      cn: '猜灯谜',  slug: 'sh-riddle' },
  { id: 'baduanjin',   cn: '八段锦',  slug: 'sh-baduanjin' },
  { id: 'sudoku',      cn: '数独',    slug: 'sh-sudoku' },
  { id: 'xiangqi',     cn: '象棋',    slug: 'sh-xiangqi' },
  { id: 'gomoku',      cn: '五子棋',  slug: 'sh-gomoku' },
  { id: 'calligraphy', cn: '书法',    slug: 'sh-calligraphy' },
];

// ---------- 读母本 ----------
function readFm(text) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!m) return { fm: {}, body: text };
  const g = (k) => (m[1].match(new RegExp('^' + k + ':[ \\t]*(.*)$', 'm')) || [, ''])[1].trim();
  return {
    fm: { title: g('title'), desc: g('description'), tags: (g('tags').match(/\[(.*)\]/) || [, ''])[1] },
    body: text.slice(m[0].length),
  };
}

// ---------- 归一（与 import-sketch.mjs 同一套判据）----------
const BLOCK = /^(\s{0,3}#{1,6}\s|\s{0,3}>\s?|\s{0,3}[-*+]\s|\s{0,3}\d+\.\s|\||!\[|```|___|\$\$)/;
let hardBreaks = 0;

/** 把导出时留下的软换行拼回一个段落；列表/表格/标题/引用各自成行 */
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

const wanted = new Map();                                    // '专题/文件名' → 母本里的实际路径
function rewriteImgs(line, id) {
  return line.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (all, alt, ref) => {
    if (/^https?:/.test(ref)) return all;
    const name = path.basename(ref);
    const dir = path.join(RAW, id, path.dirname(ref));
    const src = path.join(dir, name);
    if (!fs.existsSync(src)) die(`图片找不到：${ref}（在 ${dir} 下没有 ${name}）`);
    wanted.set(`${id}/${name}`, src);
    return `![${alt}](/images/shenghuo/${id}/${name})`;
  });
}

/** 归一一篇课的正文；shift=true 时把 H2 及更深标题降一级（H1 由外层替换成 `## NN 课名`） */
function normalize(text, id, shift = true) {
  return reflow(text.split('\n')).map((l) => {
    if (l.includes('*')) checkStars(l, id);
    const h = shift ? l.match(/^(#{2,6})\s/) : null;
    const body = rewriteImgs(l, id);
    return h ? '#' + body : strong(body);
  });
}

/** 母本课名去掉「阶段X·NN 」前缀（课号以 manifest 为准） */
const lessonTitle = (t) => t.replace(/^阶段[一二三四五六]·\s*\d+\s*/, '').trim();
const cell = (s) => String(s || '').replace(/\|/g, '｜');      // 别让正文里的竖线打断表格

/** 每套课的 course.manifest.js 是唯一事实来源：课序、课名、阶段名都从它读 */
function readManifest(id) {
  const p = path.join(RAW, id, 'course.manifest.js');
  if (!fs.existsSync(p)) die(`manifest 不存在：${p}`);
  const m = fs.readFileSync(p, 'utf8').match(/module\.exports = ([\s\S]*?)\s*;?\s*$/);
  if (!m) die(`manifest 读不出 module.exports：${p}`);
  const data = new Function('return ' + m[1])();
  if (!data.course || !Array.isArray(data.stages)) die(`manifest 结构不对：${p}`);
  return data;
}

// ---------- 生成 ----------
const [PY, PM, PD] = DATE.split('-');                     // _config.yml 的 permalink 是 :year/:month/:day/:name/
const postUrl = (slug) => `/${PY}/${PM}/${PD}/${slug}/`;
const IMG_URL = (id) => `/images/shenghuo/${id}/`;
const imgRefs = (ls, id) => new Set(
  ls.flatMap((l) => [...l.lines.join('\n').matchAll(/!\[[^\]]*\]\(([^)\s]+)\)/g)].map((m) => m[1]))
    .filter((u) => u.startsWith(IMG_URL(id))));
const hanOf = (ls) => (ls.map((l) => l.lines.join('\n')).join('')
  .replace(/!\[[^\]]*\]\([^)]*\)/g, '').match(/[㐀-鿿]/g) || []).length;
const wan = (n) => Math.round(n / 1000) / 10;

const arts = [];
for (const [ti, tp] of TOPICS.entries()) {
  const dir = path.join(RAW, tp.id);
  if (!fs.existsSync(dir)) die(`母本目录不存在：${dir}`);
  const man = readManifest(tp.id);
  const listed = man.stages.flatMap((s) => s.lessons.map((l) => ({ ...l, stageName: s.name, stageNo: s.no })));
  const files = fs.readdirSync(dir).filter((f) => /^\d\d-.*\.md$/.test(f)).sort();
  if (files.length !== listed.length) die(`${tp.id}：manifest 说 ${listed.length} 课，母本目录里有 ${files.length} 个课文件`);
  if (man.stages.length !== STAGES_EACH) die(`${tp.id}：这套课有 ${man.stages.length} 个阶段，而切法是按每项 ${STAGES_EACH} 个阶段设计的——先和用户重新定分类口径再改脚本`);

  const lessons = listed.map((l) => {
    const f = `${l.n}-${path.basename(l.file, '.html')}.md`;
    if (!fs.existsSync(path.join(dir, f))) die(`${tp.id}：manifest 里的课在母本找不到：${f}`);
    const { fm, body } = readFm(fs.readFileSync(path.join(dir, f), 'utf8'));
    const title = lessonTitle(fm.title || l.title || '') || l.title;
    if (title !== lessonTitle(l.title)) die(`${tp.id}/${f}：md 里的标题和 manifest 不一致`);
    const lines = normalize(body, tp.id).filter((x) => !x.startsWith('# '));
    const h2 = (body.match(/^## /gm) || []).length;
    return { no: l.n, title, desc: fm.desc || l.desc || '', stage: l.stageName, tags: fm.tags || '', lines, h2, file: f };
  });

  const courseImgs = imgRefs(lessons, tp.id), courseHan = hanOf(lessons);

  // 一个阶段一篇：阶段名、课序都来自 manifest；标题沿用素描那套「X阶段二 · 名字」
  for (const [si, st] of man.stages.entries()) {
    const mine = lessons.filter((l) => l.stage === st.name);
    if (mine.length !== st.lessons.length) die(`${tp.id}/${st.name}：manifest 说这一阶段 ${st.lessons.length} 课，按阶段名只归到 ${mine.length} 课（母本里阶段名和课上的 stage 标号对不上）`);
    const slug = `${tp.slug}-${si + 1}`;
    const imgs = imgRefs(mine, tp.id), han = hanOf(mine);
    const sib = man.stages.map((s, i) => ({ s, i })).filter((x) => x.i !== si)
      .map((x) => `[${tp.cn}${x.s.no} ${x.s.name} →](${postUrl(`${tp.slug}-${x.i + 1}`)})`);

    const head = [
      `<strong>这套课</strong>：${man.course.title}，${man.stages.length} 个阶段共 ${lessons.length} 课、` +
        `约 ${wan(courseHan)} 万汉字、${courseImgs.size} 张矢量示意图，` +
        '每课都是「示意图 + 分步做法 + 练习 + 自查表」，零基础起步，不带任何前置知识。',
      '',
      `<strong>本篇</strong>：${st.no}「${st.name}」${mine.length} 课（${mine.map((l) => l.no).join('、')}）、` +
        `约 ${wan(han)} 万汉字、${imgs.size} 张图。另两篇：${sib.join('、')}。`,
      '',
      '| 课 | 标题 | 这一课干什么 |',
      '| --- | --- | --- |',
      ...mine.map((l) => `| ${l.no} | ${cell(l.title)} | ${cell(l.desc)} |`),
      '',
    ];

    const bodyLines = [...head];
    for (const l of mine) {
      bodyLines.push(`## ${l.no} ${l.title}`, '');
      if (l.desc) bodyLines.push(`<strong>这一课干什么</strong>：${l.desc}`, '');
      bodyLines.push(...l.lines, '');
    }

    const tags = ['生活', tp.cn];
    for (const l of mine) for (const t of l.tags.split(',').map((s) => s.trim()).filter(Boolean)) {
      if (t !== tp.cn && !tags.includes(t)) tags.push(t);
    }

    arts.push({
      id: tp.id, cn: tp.cn, slug, cat3: st.name, stageNo: st.no, lessons: mine,
      title: `${tp.cn}${st.no} · ${st.name}`,
      desc: `${man.course.title} · ${st.no}「${st.name}」：${mine.length} 课、${imgs.size} 张示意图，从零基础到能自己上手、自己纠错。`,
      han, imgCount: imgs.size, lines: bodyLines, tags: tags.slice(0, 8),
      date: `${DATE} 09:${String(ti * STAGES_EACH + si + 1).padStart(2, '0')}:00`,
      h3Want: mine.reduce((s, l) => s + l.h2, 0),
    });
  }
}

// ---------- 落盘 ----------
if (CLEAN) {
  fs.rmSync(POSTS, { recursive: true, force: true });
  fs.rmSync(IMG, { recursive: true, force: true });
}
fs.mkdirSync(POSTS, { recursive: true });
for (const id of new Set([...wanted.keys()].map((w) => w.split('/')[0]))) {
  fs.mkdirSync(path.join(IMG, id), { recursive: true });
}

const slugs = new Set();
for (const a of arts) {
  if (slugs.has(a.slug)) die(`slug 撞了：${a.slug}`);
  slugs.add(a.slug);
  const fm = ['---', `title: "${a.title}"`, `slug: ${a.slug}`, `date: ${a.date}`,
    'categories:', '  - "生活"', `  - "${a.cn}"`, `  - "${a.cat3}"`, 'tags:', ...a.tags.map((t) => `  - "${t}"`),
    `description: "${a.desc}"`, '---'].join('\n');
  fs.writeFileSync(path.join(POSTS, `${a.slug}.md`), fm + '\n\n' + a.lines.join('\n') + '\n');
}
let copied = 0;
for (const [w, src] of wanted) {
  const [id, name] = w.split('/');
  fs.copyFileSync(src, path.join(IMG, id, name));
  copied++;
}

// ---------- 自检 ①：母本逐行都要在文章里 ----------
let lost = 0;
for (const a of arts) {
  const gen = fs.readFileSync(path.join(POSTS, `${a.slug}.md`), 'utf8');
  for (const l of a.lessons) {
    const { body } = readFm(fs.readFileSync(path.join(RAW, a.id, l.file), 'utf8'));
    for (const line of normalize(body, a.id)) {
      if (!line.trim() || line.startsWith('#')) continue;      // H1 被外层课标题替代，自检②里查
      if (!gen.includes(line)) {
        lost++;
        if (lost <= 6) console.error(`✗ 母本行没进文章 [${a.id}/${l.file}] ${line.slice(0, 60)}`);
      }
    }
  }
}
if (lost) die(`自检①：${lost} 行母本内容在生成的文章里找不到`);

// ---------- 自检 ②：结构 ----------
const problems = [];
for (const a of arts) {
  const gen = fs.readFileSync(path.join(POSTS, `${a.slug}.md`), 'utf8');
  const gotH2 = (gen.match(/^## \d\d /gm) || []).length;
  if (gotH2 !== a.lessons.length) problems.push(`${a.slug} 里 ${gotH2} 个课标题，这一阶段有 ${a.lessons.length} 课`);
  const gotH3 = (gen.match(/^### /gm) || []).length;
  if (gotH3 !== a.h3Want) problems.push(`${a.slug} 里 ${gotH3} 个 H3，母本这些课有 ${a.h3Want} 个 H2（降一级应相等）`);
  if (!gen.includes('  - "生活"') || !gen.includes(`  - "${a.cn}"`) || !gen.includes(`  - "${a.cat3}"`)) {
    problems.push(`${a.slug} 的分类不是 生活 / ${a.cn} / ${a.cat3}`);
  }
  for (const l of gen.split('\n')) {
    if (/\*\*/.test(l)) problems.push(`${a.slug} 残留 **：${l.slice(0, 40)}`);
    if (/\]\(images\//.test(l)) problems.push(`${a.slug} 残留相对图片路径`);
    if (new RegExp(`src="images/`).test(l)) problems.push(`${a.slug} 残留相对图片路径`);
  }
  for (const [id, name] of wanted) {
    if (id !== a.id) continue;
    if (!fs.existsSync(path.join(IMG, id, name))) problems.push(`图片没落盘：${id}/${name}`);
  }
}
// 拆篇不能把课拆丢：每项的三篇合起来 == manifest 的全部课，图片合起来 == 被引用的全部图
for (const [ti, tp] of TOPICS.entries()) {
  const mine = arts.filter((a) => a.id === tp.id);
  if (mine.length !== STAGES_EACH) problems.push(`${tp.cn} 应该有 ${STAGES_EACH} 篇（一阶段一篇），现在 ${mine.length} 篇`);
  const nos = mine.flatMap((a) => a.lessons.map((l) => l.no)).sort();
  const want = [...Array(nos.length).keys()].map((i) => String(i + 1).padStart(2, '0'));
  if (JSON.stringify(nos) !== JSON.stringify(want)) problems.push(`${tp.cn} 课号不连续或重复：${nos.join(',')}`);
}
const totalLessons = arts.reduce((s, a) => s + a.lessons.length, 0);
if (totalLessons !== LESSON_TOTAL) problems.push(`六套课应该 ${LESSON_TOTAL} 课，现在 ${totalLessons} 课`);
if (arts.length !== TOPICS.length * STAGES_EACH) problems.push(`应该 ${TOPICS.length * STAGES_EACH} 篇，现在 ${arts.length} 篇`);
const rawImgs = [];
for (const tp of TOPICS) {
  const d = path.join(RAW, tp.id, 'images', 'svg');
  if (fs.existsSync(d)) rawImgs.push(...fs.readdirSync(d).map((f) => `${tp.id}/${f}`));
}
const referenced = new Set(wanted.keys());
const orphans = rawImgs.filter((k) => !referenced.has(k));
if (orphans.length) problems.push(`有 ${orphans.length} 张母本图没被任何课文引用（例：${orphans.slice(0, 3).join('、')}）`);

console.log(`生成文章 ${arts.length} 篇 -> ${path.relative(ROOT, POSTS)}；图片 ${copied} 张 -> ${path.relative(ROOT, IMG)}`);
for (const a of arts) {
  console.log(`  ${a.slug.padEnd(18)} 生活 / ${a.cn} / ${a.cat3}　${a.lessons.length} 课、${String(a.imgCount).padStart(3)} 图、约 ${wan(a.han)} 万汉字`);
}
console.log(`课合计 ${totalLessons}；段落硬换行 ${hardBreaks} 处；单个星号可疑行 ${oddStars.length} 处${oddStars.length ? '：' + oddStars.slice(0, 3).join(' | ') : ''}`);
console.log(`三级分类 ${new Set(arts.map((a) => `${a.cn}/${a.cat3}`)).size} 个：${[...new Set(arts.map((a) => `${a.cn}/${a.cat3}`))].join('、')}`);
if (problems.length) die('自检②：\n  ' + [...new Set(problems)].slice(0, 10).join('\n  '));
console.log(`自检通过：${LESSON_TOTAL} 课全部入 ${arts.length} 篇、母本逐行都在文章里、引用图片全部落盘`);
