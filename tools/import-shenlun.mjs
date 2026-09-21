#!/usr/bin/env node
/**
 * 把 data/shenlun-raw 里的 OCR 母本转换成 Hexo 文章，输出到 source/_posts/申论知识库/。
 * 输入目录只读，绝不写回原知识库（原始知识库在 D:\AI跑数据\学习项目\申论知识库，不要改）。
 *
 *   node tools/import-shenlun.mjs --clean              # 全量重跑（先清空输出目录）
 *   node tools/import-shenlun.mjs --only=决战申论100题  # 只导一个模块，试点用
 *
 * 现在有两个来源：
 *   1. 决战申论100题（粉笔公考书，上/中/下册 OCR .txt）——按 `■…第N题…` 切成 103 篇真题，
 *      每篇含 题目 / 资料原文 / 答题演示 / 思维导图；章·篇分隔页前的方法论单独成篇（方法导学）。
 *   2. 广东申论（.md，按题型分目录）——只有题目+参考答案，没有资料原文，原样导入。
 *
 * data/shenlun-raw 里那份「国考申论_完整笔记_含原文重点思维导图.md」不导入：它和上面三本书同源，
 * 是同一批题的聊天导出版，OCR 把双栏正文串行搅碎了（「入户走劳动力就业状况」这种断句），
 * 独有内容全是噪声，书本版更完整也更好读。
 *
 * 换模块时要做的事：
 *   1. 把新模块原样复制到 data/shenlun-raw/ 下；
 *   2. 参照 parseBook()/importGuangdong() 写一个 importer，产出 {title, sections, sources, …}；
 *   3. 跑本脚本，再跑 python tools/audit-coverage.py 确认没有正文缺失。
 *
 * 与审计脚本的约定（tools/audit-coverage.py 会在运行时把这些正则抓过去，改这里不用同步改那边）：
 *   噪声规则的名字要能被 `const 名字 = /…/flags;` 抓到，且必须是单行正则；
 *   正文里被升格成 `### 小节` 的行只允许去掉行首装饰符（●·?），文字本身不能改写，
 *   否则「源文件有、文章里没有」的判据就失效了。
 */
import { readFileSync, writeFileSync, mkdirSync, readdirSync, statSync, rmSync, existsSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SRC = join(ROOT, 'data', 'shenlun-raw');
const OUT = join(ROOT, 'source', '_posts', '申论知识库');

const onlyArg = process.argv.find(a => a.startsWith('--only='))?.slice(7);
const cleanArg = process.argv.includes('--clean');

const GD_SLUG = {
  '01-单一题-问题类': 'gd-danyi-wenti',
  '02-单一题-概括对策': 'gd-danyi-gaikuo',
  '03-单一题-经验启示': 'gd-danyi-jingyan',
  '04-单一题-提出对策': 'gd-danyi-tichu',
  '05-单一题-影响类': 'gd-danyi-yingxiang',
  '06-单一题-原因类': 'gd-danyi-yuanyin',
  '07-单一题-特殊要素': 'gd-danyi-teshu',
  '08-逻辑专项': 'gd-luoji',
  '09-综合题-词句解释题': 'gd-zonghe-ciju',
  '10-综合题-观点现象分析题': 'gd-zonghe-guandian',
  '11-公文题-方案类': 'gd-gongwen-fangan',
  '12-公文题-总结类': 'gd-gongwen-zongjie',
  '13-公文题-宣传类': 'gd-gongwen-xuanchuan',
  '14-公文题-评论类': 'gd-gongwen-pinglun',
  '15-公文题-特殊格式': 'gd-gongwen-teshu',
  '16-文章写作题': 'gd-wenzhang',
  '17-地方特色题': 'gd-difang',
};

/* ---------- 通用清洗规则（审计脚本会镜像这些正则） ---------- */

const PAGE_MARK = /^---\s*第\s*\d+\s*页\s*---\s*$/;
const BARE_PAGE_NUM = /^\s*\d{1,4}\s*$/;
// 大文件是微信/QQ 聊天导出，每答完一题就有一句翻页提示
const CHAT_MARK = /^\s*[【\[]\s*第\s*\d+\s*题\s*(\/\s*共\s*\d+\s*题|完)\s*[】\]]\s*(回复.*)?$/;
const SCAN_MARK = /^\s*>?\s*\*{0,2}扫一扫\*{0,2}\s*$/;   // 公众号引流残留
// 只剩 markdown 装饰的空行：聊天导出把空段落写成 `> ****`，渲染出来是一片空白
// 反引号故意不在字符类里，否则 ``` 围栏会被吃掉
const DECOR_ONLY = /^[ \t]*[>|*-][>|* \t-]*$/;
const TOC_ENTRY = /^(?:\d{4}[^，。；]*?第[一二三四五六七八九十]+题|\d{4}[^，。；]*?[（(][^）)]+[）)]$|第[一二三四五六七八九十]+[章篇]|第[一二三四五六七八九十]+[章篇].*)/;
// 目录里的题目索引行：「2025浙江（C类）第一题（…）」，年份开头、带题号或括号
const TOC_LINE = /^(?:\d{4}[^，。；]*?(?:第[一二三四五六七八九十]+题|[（(][^）)]+[）)]))/;

/** 去掉 OCR 噪声：分页标记、孤立页码行、空代码块、目录残留 */
function cleanBody(text) {
  const lines = text.split(/\r?\n/);
  const kept = [];
  for (const line of lines) {
    if (PAGE_MARK.test(line)) continue;
    if (BARE_PAGE_NUM.test(line)) continue;
    if (CHAT_MARK.test(line)) continue;
    if (SCAN_MARK.test(line)) continue;
    if (DECOR_ONLY.test(line)) continue;
    kept.push(line);
  }

  // 段首目录残留：连续 >=3 行形如「2023国考（副省级）第二题（文化建设）」的索引行
  let start = 0;
  while (start < kept.length && kept[start].trim() === '') start++;
  let run = 0;
  while (start + run < kept.length) {
    const t = kept[start + run].trim();
    if (t === '') { run++; continue; }
    if (TOC_ENTRY.test(t)) run++;
    else break;
  }
  const realRun = kept.slice(start, start + run).filter(l => TOC_ENTRY.test(l.trim())).length;
  if (realRun >= 3) kept.splice(start, run);

  // 和书本一样，聊天导出的正文也是被排版切断的，先接回整段
  let out = unwrapLines(kept).join('\n');
  // 空的 ``` ``` 代码块（思维导图未导出）
  out = out.replace(/^```[a-z]*\s*\n\s*\n?```\s*$/gmi, '');
  out = out.replace(/\n{3,}/g, '\n\n').replace(/[ \t]+$/gm, '');
  return out.trim();
}

/** 章节体为空则整节丢弃 */
function isMeaningful(body) {
  const stripped = body.replace(/```[a-z]*\s*```/gi, '').trim();
  return stripped.length > 0;
}

/* ---------- 章节去重：后节已包含在前节时，在前节中重复起点处截断 ---------- */

const WIN = 30;

/**
 * 去掉空白、markdown 装饰和列表符后的字符串，并返回 归一化下标 -> 原始下标 的映射。
 * 装饰符必须和审计脚本的 NORM 保持一致：大文件把同一段材料写成 `> **…**`，
 * 不剥 `>` 和 `*` 的话窗口对不上，会被误判成「全是新内容」；`●·` 同理（书本用 `●话题梳理`，
 * 聊天导出用 `·话题梳理`）。
 */
function normalizeWithMap(s) {
  let norm = '';
  const map = [];
  for (let i = 0; i < s.length; i++) {
    if (/[\s`#*>●·○]/.test(s[i])) continue;
    norm += s[i];
    map.push(i);
  }
  return { norm, map };
}

/** 后节有多大比例落在前节里 */
function containment(earlierNorm, laterNorm) {
  if (!laterNorm || !earlierNorm) return 0;
  let hit = 0, total = 0;
  for (let i = 0; i + WIN <= laterNorm.length; i += WIN) {
    total++;
    if (earlierNorm.includes(laterNorm.slice(i, i + WIN))) hit++;
  }
  return total ? hit / total : 0;
}

/** 切开后前节尾部残留的「【参考答案】」这类标记行 */
function trimTrailingMarkers(body) {
  const lines = body.split(/\r?\n/);
  while (lines.length) {
    const last = lines[lines.length - 1].trim();
    if (last === '' || /^[【\[]?(参考答案|参考范文|答案解析|解析|答案)[】\]]?[:：]?$/.test(last)) lines.pop();
    else break;
  }
  return lines.join('\n').trim();
}

/**
 * OCR 母本的分节不可靠：广东申论把「题目+材料+参考答案」全塞进 `## 题目`。
 * 统一规则：后节被前节包含时——
 *   - 若后节恰好是前节的尾部 -> 在尾部起点切开前节（还原出干净的 题目 / 参考答案）
 *   - 否则 -> 丢弃后节（纯重复）
 */
function dedupeSections(sections) {
  const kept = [];
  for (const raw of sections) {
    const later = { ...raw };
    const laterN = normalizeWithMap(later.body).norm;
    let dropped = false;

    for (let i = 0; i < kept.length; i++) {
      const { norm: earlierN, map } = normalizeWithMap(kept[i].body);
      if (containment(earlierN, laterN) < 0.8) continue;

      const anchor = laterN.slice(0, WIN);
      const at = earlierN.indexOf(anchor);
      if (at < 0) continue;

      const cutRaw = map[at];
      const tailLen = earlierN.length - at;
      const isSuffix = Math.abs(tailLen - laterN.length) <= Math.max(20, laterN.length * 0.05);

      if (isSuffix) {
        kept[i].body = trimTrailingMarkers(kept[i].body.slice(0, cutRaw));
        if (!isMeaningful(kept[i].body)) { kept.splice(i, 1); }
      } else {
        dropped = true;                       // 前节已含该内容，整节丢弃
      }
      break;
    }

    if (dropped) continue;
    if (isMeaningful(later.body)) kept.push(later);
  }
  return kept;
}

/* ---------- 元信息 / 渲染 ---------- */

function parseDoc(raw) {
  const lines = raw.split(/\r?\n/);
  const title = (lines.find(l => /^#\s+/.test(l)) || '').replace(/^#\s+/, '').trim();
  const meta = {};
  for (const l of lines) {
    const m = l.match(/^\*\*(.+?)\*\*[：:]\s*(.+)$/);
    if (m) meta[m[1].trim()] = m[2].trim();
  }
  const sections = [];
  let cur = null;
  for (const l of lines) {
    const h = l.match(/^##\s+(.+)$/);
    if (h) { cur = { heading: h[1].trim(), body: [] }; sections.push(cur); continue; }
    if (cur) cur.body.push(l);
  }
  return {
    title,
    meta,
    sections: sections
      .map(s => ({ heading: s.heading, body: cleanBody(s.body.join('\n')) }))
      .filter(s => isMeaningful(s.body)),
  };
}

function ymd(date) {
  const p = n => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())} ${p(date.getHours())}:${p(date.getMinutes())}:${p(date.getSeconds())}`;
}

function esc(s) {
  return String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

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

const firstSentence = (text, n = 60) => {
  const plain = text.replace(/[#*>`\-\[\]()（）]/g, ' ').replace(/\s+/g, ' ').trim();
  return plain.slice(0, n);
};

/** 「2025浙江（C类）第一题（经济高质量发展）」-> 标签 */
function examTags(title) {
  const m = title.match(/^(\d{4})([^（(]+)[（(]([^）)]+)[）)].*?第[一二三四五六七八九十]+题.*?[（(]([^）)]+)[）)]/);
  if (!m) return ['真题'];
  return ['真题', `${m[1]}年`, m[2], m[4]].filter(Boolean);
}

const render = sections => sections.map(s => `## ${s.heading}\n\n${s.body}\n`).join('\n');

/* ---------- 决战申论100题：三册 OCR ---------- */

const BOOK_SUB = '决战申论100题';
const BOOK_FILES = [
  ['上册', '8月申论上册B5_OCR.txt'],
  ['中册', '8月申论中册B5黑白_OCR.txt'],
  ['下册', '8月申论下册B5黑白_OCR.txt'],
];

// B5 小书是双栏排版，OCR 后页眉/边栏/孤立页码都混在正文里
// 页眉偶尔和邻近字符粘在一行（`：决战申论100题（下册）`、`…（下册）一`），多出来的那一两个字符一并丢掉
const BOOK_HEAD = /^[：:、,，.\s]*决战申论100题[（(][上中下]册[）)][\s·]*[一二三四五六七八九十]?[：:]?$/;
// 单字符 OCR 碎片（「?」是章节图标被识别成了问号）
const BOOK_FRAGMENT = /^[?？☆•·◦+]$/;
// 边距引流文案：整行出现，但 OCR 常把它和邻近字符拼在一起、或者截断在行尾。
// 三本书里 `打开粉笔APP` 只出现在这段文案里，正文提到 APP/二维码的句子都不以它开头。
const BOOK_WATER = /^(?:.{0,4}打开粉笔APP.{0,60}|扫一扫|.{0,3}方式扫码。.*|点击“我”一.*)$/;
// 竖线那种是真分隔页，没竖线的是每页顶部的页眉；两者都靠 dropRunHeads() 按名字分辨
const BOOK_PIVOT = /^第([一二三四])篇[|丨｜]?\s*(\S{1,8})$/;
const BOOK_CHAPTER = /^第([一二三四五六七八九十]+)章[|丨「」『』]?\s*(\S{1,10})$/;
const BOOK_MARK = /^■\s*(\S.*?)\s*$/;
// 只剩标点的行：题干被 OCR 掐头时留下的「，，“，，，“，」这类碎屑，正文里偶尔也有
const PUNCT_ONLY = /^[\s,，。.、；;：:！!？?“”‘’'\"()（）\-—~·…]+$/;
// 题目切块标记里混进了 ■【】 之类的识别噪声，「第一题1（…）」这种多出来的数字也要抹掉
const TITLE_JUNK = /[■【】\s]+/g;
const TITLE_DIGIT = /(第[一二三四五六七八九十]+题)[^\u4e00-\u9fa5（(]+(?=[（(])/g;
const examTitle = s => s.replace(TITLE_JUNK, '').replace(TITLE_DIGIT, '$1').trim();

/** 升格为 `###` 的正文标记行：只剥行首装饰符，不改写文字 */
function bookHeading(t) {
  const s = t.replace(/^[\s●·○?？]+/, '').replace(/[:：\s]+$/, '');
  if (!s || s.length > 26) return null;
  if (/^(答题演示|思维导图|粉笔思维|参考答案|参考范文)$/.test(s)) return s;
  if (/^资料\d{1,2}$/.test(s)) return s;
  if (/^第[一二三四五六]步([-—–一\s]*\S{0,20})?$/.test(s)) return s;
  if (/^(要点总结|话题梳理|话题及要素梳理|要素及话题梳理|逻辑梳理|观点总结|做法总结)$/.test(s)) return s;
  return null;
}

/** 页眉、孤立页码、碎片、水印一次性滤掉，返回目录已截断的干净行 */
function bookLines(text) {
  const out = [];
  for (const raw of text.split(/\r?\n/)) {
    const t = raw.trim();
    if (PAGE_MARK.test(t)) continue;
    if (t === '') { if (out.length && out[out.length - 1] !== '') out.push(''); continue; }
    if (BARE_PAGE_NUM.test(t) || BOOK_FRAGMENT.test(t) || BOOK_HEAD.test(t) || BOOK_WATER.test(t)) continue;
    if (PUNCT_ONLY.test(t)) continue;
    out.push(t);
  }
  return out;
}

/**
 * 分辨「第N篇/第N章」是分隔页还是目录行：往后看到正文就是分隔页，看到目录索引就不是。
 * 目录里篇和章是连着排的（`第一篇单一题` 下面就是 `第一章问题类`，再下面是题目索引），
 * 所以前瞻要跳过同类标记行，不然真分隔页后面紧跟章节标记会被误判成目录。
 */
function isPivot(lines, i) {
  const t = lines[i];
  const kind = BOOK_PIVOT.test(t) ? 'pian' : BOOK_CHAPTER.test(t) ? 'chapter' : null;
  if (!kind) return null;
  for (let j = i + 1; j < Math.min(i + 10, lines.length); j++) {
    const n = lines[j];
    if (n === '' || BOOK_PIVOT.test(n) || BOOK_CHAPTER.test(n)) continue;
    if (TOC_LINE.test(n) || BOOK_HEAD.test(n)) return null;
    return kind;
  }
  return kind;
}

/**
 * 丢掉「第一篇单一题」「第一章问题类」这类页眉：它们每页顶部重复一次，
 * 名字和当前篇/章相同的就是页眉，删掉即可；名字变了才是真的换章分隔页，要留着切块。
 * 不这么做，题目中间碰到页眉会被当成分隔页，正文从那里截断、尾巴整段跑掉。
 */
function dropRunHeads(lines) {
  const out = [];
  let pian = null, chapter = null;
  for (let i = 0; i < lines.length; i++) {
    const pv = isPivot(lines, i);
    if (!pv) { out.push(lines[i]); continue; }
    const name = (pv === 'pian' ? BOOK_PIVOT : BOOK_CHAPTER).exec(lines[i])[2];
    if (name === (pv === 'pian' ? pian : chapter)) continue;
    if (pv === 'pian') { pian = name; chapter = name; } else chapter = name;
    out.push(lines[i]);
  }
  return out;
}

// 书本排版右对齐，满行（36~40 字）说明这一行是被排版切断的，不是段落结束
const FULL_LINE = 36;
// 行尾是句末标点就不再接了：真段落末尾几乎都带标点，被切断的半句不带
const PARA_END = /[。！？…”：；】]$/;
// 上限只是防失控的保险丝。书本里最长的一段实测 580 字，压到 160 会把半句话劈开
// （「自动测量老人的血压、心」/「步等，协助老人…」），那比一段长文难看得多。
const MAX_PARA = 640;
// 这些开头自带段落语义，即使上一行是满行也不能接上去
const PARA_START = /^(?:段\d+|[（(]\d+[）)]|[①②③④⑤⑥]|[一二三四五六七八九十]+[、.]|\d+[、.]|[-*|>]|#{1,6}\s)/;

/** 把 OCR 的满行硬换行接回成整段；剩下的单行是真段落，靠 breaks:true 换行显示 */
function unwrapLines(lines) {
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    let cur = lines[i].trim();
    // markdown 结构行（标题、表格、代码围栏）不参与接行
    const structural = l => /^(?:#{1,6}\s|```|[-*|>]|\s*[-*|>])/.test(l);
    while (cur.length >= FULL_LINE && !PARA_END.test(cur) && cur.length < MAX_PARA
           && !structural(cur)) {
      const n = lines[i + 1] === undefined ? undefined : lines[i + 1].trim();
      if (n === undefined || n === '' || structural(n) || PARA_START.test(n)
          || bookHeading(n)) break;
      i++;
      cur += n;
      if (n.length < FULL_LINE) break;    // 接上的是段落末行，这段到此为止
    }
    out.push(cur);
  }
  return out;
}

/**
 * 一册书 -> [{ kind:'question'|'pivot', title, pian, chapter, lines }]
 * 结构：`■题目` 切真题；「第N篇|」「第N章」分隔页之前的整段是该章的方法论。
 */
function parseBook(text) {
  const L = dropRunHeads(bookLines(text));
  const units = [];
  let pian = null, chapter = null;
  let i = 0;
  // 前面的扉页、版权页、目录整段丢弃
  while (i < L.length && !isPivot(L, i) && !BOOK_MARK.test(L[i])) i++;

  while (i < L.length) {
    const pv = isPivot(L, i);
    if (pv) {
      const m = (pv === 'pian' ? BOOK_PIVOT : BOOK_CHAPTER).exec(L[i]);
      if (pv === 'pian') { pian = m[2]; chapter = m[2]; } else chapter = m[2];
      const body = [];
      let j = i + 1;
      while (j < L.length && !BOOK_MARK.test(L[j]) && !isPivot(L, j)) { body.push(L[j]); j++; }
      units.push({ kind: 'pivot', title: L[i], pian, chapter, lines: body });
      i = j;
      continue;
    }
    const mk = BOOK_MARK.exec(L[i]);
    if (mk) {
      const title = examTitle(mk[1]);
      const body = [];
      let j = i + 1;
      while (j < L.length && !BOOK_MARK.test(L[j]) && !isPivot(L, j)) { body.push(L[j]); j++; }
      units.push({ kind: 'question', title, pian, chapter, lines: body });
      i = j;
      continue;
    }
    i++;                      // 残段（正常不会出现）
  }
  return units;
}

/** 一节真题 -> 题目 / 资料原文 / 答题演示 / 思维导图，标记行升格为 `###` */
function bookSections(lines) {
  const isMark = (l, name) => bookHeading(l) === name;
  const isMaterial = l => (bookHeading(l) || '').startsWith('资料');
  const SECT = [
    ['题目', l => isMaterial(l) || isMark(l, '答题演示')],
    ['资料原文', l => isMark(l, '答题演示')],
    ['答题演示', l => isMark(l, '思维导图')],
    ['思维导图', () => false],
  ];
  const secs = [];
  let rest = lines, k = 0;
  for (const [name, splitAt] of SECT) {
    const at = k + 1 < SECT.length ? rest.findIndex(splitAt) : -1;
    const body = at < 0 ? rest : rest.slice(0, at);
    const cleaned = bookBody(body);
    if (isMeaningful(cleaned)) secs.push({ heading: name, body: cleaned });
    if (at < 0) break;
    rest = rest.slice(at);
    k++;
  }
  return secs;
}

/** 标记行 -> `### 标记行`，其余原样，末尾空白收拢 */
function bookBody(lines) {
  const out = [];
  for (const l of unwrapLines(lines)) {
    if (l === '') { if (out.length && out[out.length - 1] !== '') out.push(''); continue; }
    const h = bookHeading(l);
    out.push(h ? `### ${h}` : l);
  }
  return out.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

const PIAN_CODE = { 单一题: '01', 综合题: '02', 公文题: '03', 文章写作题: '04' };
const CHAPTER_SLUG = {
  问题类: 'wenti', 影响类: 'yingxiang', 原因类: 'yuanyin', 对策类: 'duice',
  不常见要素: 'buchangjian', 多要素组合类: 'duoyaosu',
  词句解释: 'ciju', 观点现象分析: 'guandian', 对比分析: 'duibi',
  方案类: 'fangan', 宣传类: 'xuanchuan', 总结类: 'zongjie', 评论类: 'pinglun',
  文章写作题: 'dazhu', 综合题: 'zonghe', 公文题: 'gongwen',
};

function importBooks() {
  const posts = [];
  for (const [vol, file] of BOOK_FILES) {
    const rel = `${BOOK_SUB}/${file}`;
    const path = join(SRC, BOOK_SUB, file);
    if (!existsSync(path)) { console.warn(`跳过缺失的母本：${rel}`); continue; }
    const text = readFileSync(path, 'utf8');
    const mtime = statSync(path).mtime;
    const units = parseBook(text);
    const seq = new Map();
    units.forEach((u, k) => {
      const sections = u.kind === 'pivot'
        ? [{ heading: `${u.chapter}·方法导学`, body: bookBody(u.lines) }]
        : bookSections(u.lines);
      // 篇分隔页后面常常只有边栏识别出来的两三个字（「合宗」「文公」），不算方法论
      if (!sections.some(s => s.body.replace(/\s/g, '').length >= 60)) return;

      const mod = u.pian === u.chapter ? `${PIAN_CODE[u.pian]}-${u.pian}`
        : `${PIAN_CODE[u.pian]}-${u.pian}-${u.chapter}`;
      const prefix = CHAPTER_SLUG[u.chapter] || 'book';
      const isPivot = u.kind === 'pivot';
      let n = 0;
      if (!isPivot) { n = (seq.get(mod) || 0) + 1; seq.set(mod, n); }
      const slug = `${prefix}-${isPivot ? '000' : String(n).padStart(3, '0')}`;
      const tags = [...new Set(isPivot
        ? ['方法论', u.pian, u.chapter, vol]
        : [...examTags(u.title), u.pian, u.chapter, vol])];

      posts.push({
        module: `${BOOK_SUB}/${mod}`,
        file: `${slug}.md`,
        slug,
        date: new Date(mtime.getTime() + posts.length * 1000),
        title: isPivot ? `${u.chapter}·方法导学` : u.title,
        categories: ['申论知识库', BOOK_SUB, u.pian, u.chapter].filter((c, k, a) => c && a.indexOf(c) === k),
        tags,
        description: firstSentence(sections[0].body),
        content: render(sections),
        sections,
        sources: [`${rel}#${k + 1}`],
      });
    });
    console.log(`${vol}：${units.filter(u => u.kind === 'question').length} 题 / ${units.filter(u => u.kind === 'pivot').length} 段方法导学`);
  }
  return posts;
}

/* ---------- 广东申论：按题型子目录 ---------- */

function importGuangdong() {
  const base = join(SRC, '广东申论');
  const posts = [];
  for (const sub of readdirSync(base).sort((a, b) => a.localeCompare(b, 'zh'))) {
    if (!statSync(join(base, sub)).isDirectory()) continue;
    if (sub === '00-总索引') continue;               // 索引页单独处理
    if (onlyArg && onlyArg !== `广东申论/${sub}` && onlyArg !== '广东申论') continue;
    const files = readdirSync(join(base, sub)).filter(f => f.endsWith('.md') && f !== 'README.md');
    let seq = 0;
    for (const f of files.sort((a, b) => a.localeCompare(b, 'zh'))) {
      const full = join(base, sub, f);
      const doc = parseDoc(readFileSync(full, 'utf8'));
      const stem = f.replace(/\.md$/, '');           // 例1_（2024国考副省级）
      const paper = stem.match(/[（(](.+?)[）)]/)?.[1] || doc.title.replace(/[（）()]/g, '');
      const example = stem.match(/^例(\d+)/)?.[1];
      const typeName = sub.replace(/^\d+-/, '');
      const secs = dedupeSections(doc.sections);
      const body = secs.map(s => `## ${s.heading}\n\n${s.body}\n`).join('\n');
      const year = paper.match(/(\d{4})/)?.[1];

      posts.push({
        module: `广东申论/${sub}`,
        file: `${GD_SLUG[sub] || 'gd'}-${String(++seq).padStart(3, '0')}.md`,
        slug: `${GD_SLUG[sub] || 'gd'}-${String(seq).padStart(3, '0')}`,
        date: statSync(full).mtime,
        title: `${paper} · ${typeName}${example ? ` · 例${example}` : ''}`,
        categories: ['申论知识库', '广东申论', typeName],
        tags: ['真题', typeName, year ? `${year}年` : null, paper.replace(/^\d{4}/, '')].filter(Boolean),
        description: firstSentence(body),
        content: `${doc.meta['章节'] ? `**章节：** ${doc.meta['章节']}\n\n` : ''}${body}`,
        sections: secs,
        sources: [`广东申论/${sub}/${f}`],
      });
    }
  }
  return posts;
}

/* ---------- 主流程 ---------- */

let posts = [];
if (!onlyArg || onlyArg === BOOK_SUB) posts.push(...importBooks());
if (!onlyArg || onlyArg.startsWith('广东申论')) posts.push(...importGuangdong());

if (cleanArg && existsSync(OUT)) rmSync(OUT, { recursive: true });
for (const p of posts) {
  mkdirSync(join(OUT, p.module), { recursive: true });
  writeFileSync(join(OUT, p.module, p.file), frontMatter(p) + p.content, 'utf8');
}

const slugs = new Set();
const dup = posts.filter(p => slugs.has(p.slug) ? true : (slugs.add(p.slug), false));

// 审计用清单：每篇文章对应哪些源文件，便于校验没有内容被静默丢弃
writeFileSync(
  join(ROOT, 'data', 'shenlun-manifest.json'),
  JSON.stringify(posts.map(p => ({ slug: p.slug, title: p.title, module: p.module, sources: p.sources })), null, 2),
  'utf8'
);

console.log(`生成文章 ${posts.length} 篇 -> ${relative(ROOT, OUT)}`);
console.log(`slug 冲突: ${dup.length}`);
for (const m of new Set(posts.map(p => p.module))) {
  console.log(`  ${m}: ${posts.filter(p => p.module === m).length}`);
}
