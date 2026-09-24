# 个人博客（Hexo 8 + NexT 8.29）

本地骨架已搭好并通过构建与浏览器验证。仓库只存源码，静态页由 GitHub Actions 在云端生成发布。

## 环境说明（重要）

依赖用 **pnpm** 管理，不是 npm：Hexo 8 官方 starter 自带 `pnpm-lock.yaml`，用 `npm install` 会因 node_modules 结构不同而报错。

```bash
pnpm install        # 装依赖
pnpm run server     # 本地预览 http://localhost:4000
pnpm run build      # 生成静态页到 public/
```

主题 **不放在 `themes/`**，而是作为 npm 包 `hexo-theme-next` 由 `package.json` 管理（Hexo 会从 `node_modules/hexo-theme-next` 加载）。好处是仓库里没有嵌套 git 仓库，主题版本被锁文件固定。要改主题配置，只改根目录的 `_config.next.yml`，不要动 `node_modules` 里的文件。

## 站点身份（已填好）

用户名 `Huang-jiale`，站点 `https://Huang-jiale.github.io`，仓库名必须与 `url` 匹配：

| 位置 | 现值 |
|---|---|
| `_config.yml:16` | `url: https://Huang-jiale.github.io` |
| `_config.next.yml:48` | 侧栏 GitHub 链接 → `github.com/Huang-jiale` |
| `_config.next.yml` 的 `utterances.repo` | `Huang-jiale/comment-storage`（**仓库还没建**，评论也还没开，见下） |

`title / author` 用的是 GitHub 显示名「上班笔记随心写」，想换直接改 `_config.yml` 第 6、10 行。

## 上线步骤

首次已经推过了，之后每次改完只要第 2 步。日常加内容看 [以后加内容：供稿约定 + 上线 SOP](#以后加内容供稿约定--上线-sop)。

1. GitHub 仓库 `Huang-jiale.github.io`（public）。仓库名**必须**是 `用户名.github.io`，否则 Pages 不认。
2. 提交并推送：

   ```bash
   cd /d/blog
   git add .
   git commit -m "..."
   git push
   ```

3. 仓库 **Settings → Pages → Build and deployment → Source** = **GitHub Actions**（不是 branch）。首次由 `gh api` 设过；换仓库要手动确认一次。
4. **Actions** 标签页等 `Deploy Hexo to GitHub Pages` 变绿（约 1 分钟）。
5. 打开 `https://Huang-jiale.github.io`。

本地预览和线上是两套：`pnpm run server` 看效果，push 才是发布。


之后每次写完文章只需 `git push`，云端自动重新构建发布。

## 日常写作

```bash
npx hexo new "文章标题"     # 生成 source/_posts/文章标题.md
```

文章头部格式：

```yaml
---
title: 文章标题
date: 2026-09-21 12:00:00
tags:
  - 标签名
categories:
  - 分类名
---
```

`<!-- more -->` 之前的内容作为首页摘要。图片放 `source/images/`，正文里用 `/images/xxx.png` 引用。

`source/_posts/申论知识库/` 下的 259 篇是脚本生成的，改它们等于白改（`--clean` 会整目录重建）；要修内容就改清洗规则或 `data/shenlun-raw/` 里的副本。

## 以后加内容：供稿约定 + 上线 SOP

用户能提供的只有两样：**MD 文件** 和 **一句话的分类要求**。下面约定保证「一个 MD 文件 = 一篇文章」这条链路不需要每次重新商量。

### 分类口径（全站，2026-09-23 定，同日改成三层）

**三层：`顶层模块 / 模块 / 大类`。** 顶层只有三个：**工作 / 学习 / 生活**（用户 2026-09-23：「分类设计为三大模块，工作 生活 学习，现在的都得属于学习，后续知识库会标记属于哪一种」）。第二层还是原来的模块，第三层还是原来的大类：

```
学习 / 行测      / 判断推理 · 数量关系 · 言语理解 · 资料分析 · 答案键        （38 篇）
学习 / 时政要点  / 2025年11月 · 2025年12月 · 2026年1月 · 2026年2月 · 专题 · 速查（74 篇）
工作 / …   （空，等第一篇）
生活 / 素描                                                                  （7 篇，两级）
生活 / 猜灯谜    / 基础认知 · 五大法门 · 实战与精进                          （3 篇）
生活 / 八段锦 · 数独 · 象棋 · 五子棋 · 书法  每项同样三个阶段一篇           （各 3 篇，共 15）
申论知识库、言语理解（等新母本，导入时照这条来，一级挂「学习」）
```

- **「三层」目前只对「学习」是硬要求**：`check-build.py` 第 1b 节查一级必须是 工作/学习/生活、层数 2 或 3，**只有「学习」必须满三层**。「生活」内部允许混层数——六项走三层（用户 2026-09-24：「按素描的结构去分类」，第三层直接用母本的阶段名），素描走两级（同一轮里用户把素描挪进「生活」并要求压成 `生活 / 素描`，原来那三个大类「基础与造型 / 静物写生 / 人物与创作」降到标签，树里不再占一层）。
- **侧栏和分类页还是原来那棵树**，只是上面多了一层模块名；点进模块后自由选下一层，更细的定位（题型、册/组号、年份、星级、大类、阶段号）继续走**标签**。
- 新写一篇文章时 front-matter 要给满这个模块的层数，`check-build.py` 第 1b 节会拦住「一级不是工作/学习/生活」和层数不够的文章。
- 顶层名字要和 `scripts/bento-home.js` 里的 `TOPS` 一致（首页三张卡按它取数，空模块显示占位卡）。
- 分类页 URL 现在形如 `/categories/学习/行测/判断推理/`；`_废弃/申论知识库-2026-09-21/` 里那 259 篇是两级时代的产物，接回来时要补一层。
- **改口径的代价是网址会断**。2026-09-24 这两次调整之后，下面这些 URL 都是 404，微信/聊天记录里发过的旧链接点不开：`/categories/学习/素描/…`（素描换了一级）、`/2026/09/24/sh-riddle/` 那 6 个一项一篇的地址（拆成了 `sh-riddle-1/2/3`）。Hexo 静态站没有 redirect 机制，真要做兼容得自己塞 `migrate` 插件或手写 meta-refresh。

**手绘课程树 `/sketch-map/` 已经在 2026-09-24 删掉了**（用户：「删掉」）。源文件 `source/sketch-map/index.md`、`import-sketch.mjs` 里生成它的那段、还有 `check-build.py` 原来核它 30 个锚点的检查，一起撤了；这个地址从此 404。想找回内容：`git show 165c3fd:source/sketch-map/index.md`。素描 7 篇本身留着，进去的路是分类页 `/categories/生活/素描/` 和文章左侧的「文章目录」。
（历史：2026-09-23 用户说「素描课程不要」，先撤了顶部菜单项和首页模块卡上的链接；2026-09-24 素描从「学习」挪进「生活」，`/categories/学习/素描/…` 那串旧地址同时变 404。以后要给别的模块加总览入口：`_config.next.yml` 的 `menu` 加一项，想在首页卡上下钻就在 `scripts/bento-home.js` 的 `TOPS` 里补 `href` / `hrefTxt`，并在模板 `tools/bento-home.njk` 的模块卡循环里加回 `{% if m.href %}<a class="bento-more" …>{% endif %}`——那段 2026-09-23 删过了。）

### 文件怎么写（越靠上越省事）

- **一个文件一篇**最省事。一个文件里塞多篇（一整册、一个月）就得写切块脚本，切到哪一层由分类需要决定——时政按「一条考点一篇」、行测按「一个难题组一篇」，都是为了分类页能归类；素描和生活六项反过来，**一个阶段一篇**：母本 31 个文件合成 7 篇、64 个课文件合成 18 篇。用户要的是一篇装完一个阶段、后续只在原篇里更新，别拿「一个 MD 一篇」的默认约定去套。
- **文件名用 ASCII**，例如 `xc-001.md`。URL 取的是文件名（`permalink: :year/:month/:day/:name/`），中文名会变成一长串百分号编码。
- 头部（front-matter）可以完全不写，只靠 `title`/`date` 就能发；写了就照它，脚本不会覆盖你显式给的值。
- **别写「详见本页」「见上文」这类引用**——拆分后「本页」就不存在了。要跨文章引用就写完整路径，或者把映射告诉我。
- 紧贴汉字的 `**粗体**` 有 CommonMark 边界问题（`纳入**「四个全面」**` 会把星号原样印出来）。走脚本的会自动转成 `<strong>`；**直接投放的文件请自己写成 `<strong>…</strong>`**。
- 图片：`post_asset_folder` 是关的，图片放 `source/images/<模块>/`，正文里写 `/images/<模块>/xxx.png`。

### 三条投放路径

1. **直接投放**（文件已经一篇一篇、内容干净）——最省事，不用脚本：
   ```bash
   cp 我的文章.md "/d/blog/source/_posts/模块名/xc-001.md"
   cd /d/blog && pnpm hexo clean && pnpm hexo server   # 打开 http://localhost:4000 看一眼
   ```
   Git Bash 里中文路径、带空格的中文文件名当普通参数传是没问题的，但**通配符会挂**（`ls source/_posts/模块名/*/*.md` 会因 GBK 参数错乱报「没有那个文件」），要批量看就用 `find` 或 python。
2. **半自动**（一批文件，分类要按目录/文件名推出来）——照抄 `tools/import-shizheng.mjs` 改解析和元信息，保留它末尾的两道自检。
3. **需要清洗**（OCR、聊天导出的母本，标题正文会错位）——走申论那条链路：`tools/import-shenlun.mjs` + `tools/audit-coverage.py`。

无论哪条，**母本原件永远不改**：先 `cp` 到 `data/<模块>-raw/`（`data/` 已 gitignore），只对副本动手，复制后核对 md5。

### 分类要求怎么写给我

```
模块名：行测常识
母本位置：D:\AI跑数据\学习项目\...
分类：生活 / 数独 / 候选数与结构   ← 写到你想要的层数（1~3 层）；「学习」是三层，「生活」里六项三层、素描两级，别的模块层数不够或想压层我会先问
日期与排序：文件名里的编号 / 文件修改时间 / 统一某天按序号递增分钟
标签：要不要星级、年份、来源老师
要不要清洗：干净 markdown（走路径 1 或 2）/ OCR 产物（走路径 3）
```

### 上线（push 之后就结束了）

```bash
cd /d/blog && git add -A && git commit -m "…" && git push
```

GitHub Actions 约 40 秒建完 → https://huang-jiale.github.io。回滚用 `git revert <sha> && git push`，不要 `reset --hard`。

Actions 成功不等于内容上线（404 常见于 CDN 传播延迟）。跑 `python tools/check-live.py` 从公网核对：文章页按 front-matter 拼 URL 逐个取，正文查 `**`/`assets/` 残留，图片按 `IMG_LIMIT` 跨目录抽样（默认全取，站点图多时设 24），分类页带分页合起来比 slug 集合。网络抖动只重试不算内容错误，404 立即返回。

### 每次导完必须自己看一遍（脚本全绿不算完）

1. `python tools/check-build.py` —— 把下面 1~3 条机器化：文章数、渲染残留 `**`、图片是否落盘、题数==答案数、每个分类页合起来的篇数、站内死链。**它自己先断言采样非空**；期望值全部从 `source/_posts` 现算，导完新内容不用改这个脚本。
2. 抽查 2~3 篇渲染后的正文：有没有露出的 `**`、`<br>` 把句子切碎、正文比母本少一段。
3. 分类页：`/categories/<模块>/<子分类>/` 打开，条数对不对、分页能翻到最后一项。
4. 引用：文内链接的目标页 `curl` 一下是不是 200（中文路径要百分号编码）。
5. 老 URL 是否如预期消失或保留。
6. 自查脚本要先断言「采样数量 == 文章数」再报结论——正则写错导致匹配到 0 个文件时，所有检查都会假绿。

## 前端（换皮 + 首页 52 周热力日历与三大模块 + 答案折叠）

2026-09-23 起，站点不再是「主题默认的样子」。所有改动都走 NexT 官方的覆盖口，**没有 fork 主题**，
所以主题升级不会冲突。三层：

**① token 层：`source/_data/variables.styl`**（在 `_config.next.yml` 里用 `custom_file_path.variable` 指过去）。
主题的 `main.styl` 顺序是 `_variables/base` → `_variables/Pisces` → **injects.variable** → …… → **injects.style**，
所以这里重写的变量一定压过主题自己的：苹果风格的字体栈、17px/1.8 行距、`#1d1d1f` 墨色、`#0071e3` 强调色、
`#f5f5f7` 页面底色、20px 圆角、两级柔和阴影、胶囊按钮。Pisces 原本把 `$border-radius/$box-shadow` 全设成
`initial`（所以之前看着像 2010 年的扁平博客），这里整套换成有层次的值。

**② 规则层：`source/_data/styles.styl`**（`custom_file_path.style`，排在 `main.css` 最后，同优先级不需要 `!important`）。
内容：去掉头部的深色横幅（`.site-brand-container` 透明、站名左对齐）、菜单胶囊、正文排章节奏（h2 上边距、
表格数字 `tabular-nums`、引用条）、`.post-eof { display: none }`、分页胶囊、移动端吸顶毛玻璃头部、
`details.answer` 折叠样式、`.bento-*` + `.heat-*` 首页栅格与 52 周日历、`.module-nav*` 侧栏本模块文章、
`.back-to-top` 一键到顶（搬到右下角、箭头居中）、`.cat-*` 分类页树状图、`reading-progress-bar` 只在文章页画、
`prefers-reduced-motion` 兜底。深色模式统一用
`if (hexo-config('darkmode')) { @media (prefers-color-scheme: dark) { … } }` 包，颜色走 `:root` 自定义属性。

**③ 首页：`scripts/bento-home.js` + `tools/bento-home.njk`**。脚本在 `before_generate`（优先级 10）里
从全站数据库现算四张卡的数据，挂到 `theme.config.bento`，再用 `hexo.theme.setView('index.njk', …)`
换掉首页模板——第 2 页及以后仍渲染主题原来的文章列表，分页没坏。**篇数、题数、日历格子都不写死**，
导完新内容不用改这里（`check-build.py` 会拿 `source/_posts` 现算来对账）：

- **近 52 周入库日历**（整行一张卡，GitHub 贡献图那种）：`grid-auto-flow: column` + `grid-template-rows: repeat(7, 11px)`
  画 52 列 × 7 行的格子，**周一排在第一行**，起点是「本周一往前数 51 周」，所以每列都是完整的一周；
  今天之后还没到的日子渲染成 `.heat-cell.is-future`（比空格子更淡一档，语义是「还没到」不是「没写」）。
  色阶按峰值四等分：`level = Math.min(4, Math.ceil(n * 4 / peak))`，`heat-l4` 直接用 `--accent`。
  **先乘后除**（`n * 4 / peak`，不是 `n / peak * 4`）是为了和校验器里 Python 的 `-(-n*4//peak)` 逐位一致，
  别让浮点误差把边界那一天的颜色挪一档。悬停文本形如 `2026-09-24 · 38 篇 · 行测`（模块取分类第二层），
  0 篇的空格子没有 `title`。月首标签放在格子之上、按 `grid-column` 对齐到换月那一列，与上一枚相隔不足 2 列的丢掉。
  **口径**：它反映**「什么时候导的」，不是「什么时候写的」**——137 篇只落在 9 个日期上（行测/素描的日期就是导入那天，
  时政按月归到每月 1 号），所以整张图 96% 是空的。2026-09-24 一度因为「看着像坏了」换成按月柱状图，
  当天用户点名要回日历形状（「还是要 GitHub 热力图，只读就行，鼠标放上去有显示日期」）：**他要的是日历这个形状，
  不是把图填满**，稀疏是数据的真实样子，别再用聚合去遮。要变成真正的写作频率，得给每篇补真实日期。
  纯只读，没有点击下钻。
- **三张模块卡：工作 / 学习 / 生活**，口径写在脚本顶部的 `TOPS` 里（一行一个模块：名字、文案、可选的下钻链接）。
  卡上的二级分类篇数、行测题数都从数据库现算；**一个模块还没文章时不删卡**，渲染成虚线占位卡
  （`bento-card--empty`），提醒你这一类还空着。
- **最近 6 篇**：`hexo.locals.get('posts')` 排序后取前 6。
- 2026-09-23 这一版把原来的「素描大卡 + 首页封面图（hero / `.bento-covers`）」整套撤掉了，首页不再放图。

踩过的坑，改这套东西前先看：

- `scripts/` 下的**每个文件都会被当 JS 加载**，放 `.njk` 会报 `Script load failed` → 模板放 `tools/`。
- 脚本被包成 `(async function(exports, require, module, __filename, __dirname, hexo){…})`，**`module.exports`
  永远不会被调用** → 顶层直接 `hexo.extend.filter.register(...)`，文件头写 `/* global hexo */`。
- `hexo.locals.get('posts')` 是 Warehouse Query：**不能 `for…of`/展开**（`.toArray()`），
  `Query.sort()` 只吃 `'-date'` 这种字段名，**传比较函数会被静默忽略**（首页曾经因此列出最老的 6 篇）。
- 改了 `source/_data/*.styl` 或 `scripts/*.js`，`hexo generate` 可能报「0 files generated」用缓存的旧产物
  → **先 `npx hexo clean`**，别信增量。
- 日历那一格只有 11px：**移动端不能等分**，`+tablet-mobile()` 里把 `.heat-months, .heat-grid` 的列宽写死成
  `repeat(52, 11px)`，靠外层 `.heat-scroll { overflow-x: auto }` 横滚。桌面用 `repeat(52, minmax(11px, 1fr))`
  摊满卡宽。两行的列数表达式必须一模一样，否则月首标签会跟格子错位（曾经只改了 `.heat-grid`，标签整行漂）。
  月首标签那一行是 `grid-column: N` 定位的，不是 flex —— flex 子项默认 `min-width: auto`，两个字的标签会把
  11px 的槽位撑开、越往右漂得越多。
- 图例（少 ▢▢▢▢▢ 多）里那五格复用 `.heat-cell`，而 `.heat-cell { width: 100% }` 在 flex 容器里意思是
  「占满整行」→ 必须再补一条 `.heat-legend .heat-cell { width: 10px }`。多一层 class 就够，不用 `!important`。
- 答案折叠：`import-xingce.mjs` 把每题的 `**答案：X**` 包成 `<details class="answer"><summary>看答案</summary>
  <div class="answer-body">…` ；markdown 在 `<div>` 里必须**前后空行**才渲染；每组末尾的「答案速览」用
  `class="answer answer-overview"`（否则首页统计题数时会多算 38 题）。
- **`<details>` 折叠在测量时会「假装可见」**：Chrome 隐藏 closed 内容用的是 `::details-content { content-visibility: hidden }`
  ——布局盒子照常存在，`getBoundingClientRect()` 量得到高度，只有 `checkVisibility()` / `innerText` / 命中测试说它不存在。
  所以量折叠一律用 `el.checkVisibility({contentVisibilityProperty:true})` 或看 `.post-body` 的 `innerText` 里有没有答案文本。
  我们自己还是补了一条显式 `> .answer-body { display: none }` + `[open] > .answer-body { display: block }`：
  省掉那个占位盒子，也照顾不支持该伪元素的内核。主题的 `normalize.css` 只写 `details { display: block }`，
  全站 CSS 里没有别的规则碰 `content-visibility / visibility / filter / position`，不会干扰原生折叠。
- `<summary>` 的 UA 默认是 `display: list-item` + `list-style-type: disclosure-closed/open`（那个三角）。我们的
  `details.answer > summary` 改成 `inline-block` + `list-style: none`，所以只剩胶囊文字，箭头由 `[open]` 换底色表示。
- 首屏真需要的图**不要加 `loading="lazy"`**：预览里它可能一次网络请求都不发（`naturalWidth` 一直是 0）。
- 内置预览浏览器（Qoder 的 in-app browser）视口 831px、`window.open` 被拦、不能截图。要看 ≥992px 的桌面布局，
  在页面里注入一个同源 `iframe` 并强制 `width:1280px; max-width:none !important`（主题自带
  `iframe{max-width:100%}`，不覆盖的话内部 `innerWidth` 还是 816，媒体查询按父窗口算）；媒体查询是按 iframe
  自己的视口判的，所以量出来的盒子可信。验证一律用 `evaluate_script` + `getBoundingClientRect()`。

### 布局与容器宽度

`_config.next.yml` 里 `scheme: Pisces` —— 双栏卡片布局，≥992px 时左侧栏 240px（`sidebar.width_dual_column` 可调），正文列宽 `calc(100% - 252px)`。之前的 `Muse` 是单栏宽体，正文列最宽只有 900px，在 1920 屏上两侧各留 ~510px 空白。

NexT 把整块容器宽度写死在主题包里（`$content-desktop-large = 1160px`，≥1600px 时改为视口的 73%），改配置改不动。真要再放宽，就在上面说的 `source/_data/variables.styl` 里重写 `$content-desktop-large`，升级主题不会被覆盖。

### 文章页阅读体验（侧栏目录折叠 / 顶部进度条 / 字数与预计时间）

2026-09-24 加的一层。生活六项和素描那种「一篇 8～10 课、每课还有小标题」的文章，目录拉到几百条能把侧栏撑爆，
所以按用户拍板的口径改成：**课（h2）永远显示，课内小标题（h3）默认折叠、点课才展开**。三层各自是谁：

- **`_config.next.yml`**：`toc.wrap: true`（长标题换行，不再 `nowrap` + 省略号）、`toc.expand_all: true`
  —— 注意这里**不是**「全部展开」的意思，主题把整套「滚到哪个课就自动撑开哪个」的 `.active > .nav-child`
  CSS 包在 `if (not hexo-config('toc.expand_all'))` 里，设成 true 是把主题的折叠**关掉**，让折叠逻辑只剩我们一份，
  不用跟它抢特异性。`reading_progress.enable: true`（3px、`position: top`）用的是主题自带组件，
  颜色在这里填的 `#0071e3` 只影响浅色模式——深色靠下面 CSS 里那条 `.reading-progress-bar { background: var(--accent) }`；
  用户后来说「首页不需要进度条」，画不画改由 CSS 决定（见再下面那节 ④）。
- **折叠样式在 `source/_data/styles.styl` 的「侧栏目录」一节**：`.nav-child` 默认 `height: 0; visibility: hidden`，
  加上 `.toc-open` 才 `height: var(--height, auto)`（高度由 JS 按 `scrollHeight` 现算写进 `--height`，
  这样才有动画，纯 CSS 没法从 0 过渡到 `auto`）。箭头是 `::before` 画的 6px 折角，`rotate(-45deg)` → `45deg`。
- **折叠行为在 `source/js/toc-fold.js`**（发到 `/js/toc-fold.js`）。它不是 Hexo 脚本，靠两个钩子挂进页面：
  `custom_file_path.bodyEnd` 指向 `tools/toc-fold.njk`，那个文件里只有一句 `{{ next_js('toc-fold.js') }}`
  （`next_js` 解析成 `/js/…` 并带 `defer`；pjax 没开，普通 defer 脚本安全）。行为：一次只展开一课、
  再点同一课收起、**点小标题不收起**（`closest('a')?.closest('.nav-item')` 再判 `.toc-parent`，
  别写成 `closest(':scope > .nav-item')`——`closest` 的 `:scope` 是元素自己，语义完全不同，踩过）、
  URL 带 `#锚点` 时自动把那一课展开。
- **字数那一行**：`scripts/read-time.js` 注册 helper `post_readtime`，渲染口是 `custom_file_path.postMeta`
  → `tools/post-readtime.njk`（`is_post()` 判一下，只在文章页出，位置在标题下方的 `.post-meta` 里）。
  **自己数而不装 `hexo-word-counter`**：那插件数的是 markdown 原文，图片路径、表格竖线全算字数。这里数
  `post.content`（渲染好的 HTML）：先剥标签、再把 HTML 实体整段当噪声丢掉（留着 `&mdash;` 里的 `mdash`
  会被英文词正则数成一个字），汉字/假名/谚文各算 1 字，连续英文数字算 1 词。**速度口径 400 字/分钟，
  要改就改 `scripts/read-time.js` 顶部的 `WPZ`**；超过 60 分钟显示成「约 N 小时 M 分钟」。

`tools/check-build.py` 第 11 节把这些钉死：折叠脚本已发布、CSS 里主题那套自动撑开没输出、默认高度 0、
`.toc-open` 才展开、目录换行、进度条颜色是 `var(--accent)`、137 篇文章页**逐篇**把渲染后的正文重新数一遍
对账页面上的字数文案（切片必须从 `itemprop="articleBody"` 的 `>` **之后**开始，从属性名那里切会把
`itemprop` / `articleBody` 各数成一个英文词，每篇虚高 2 字，把真误差盖掉）。

### 侧栏「本模块文章」/ 文章页瘦身 / 一键到顶 / 进度条只在文章页（2026-09-24）

用户口径：「站点概览改为可以选择该模块下的其他文章」「不需要的信息删掉，关注文章」「文章增加一键到顶」
「向上箭头图标不好看，有问题 你检查一下」「首页不需要进度条」。

**① 侧栏那一栏换成同模块的兄弟篇**：`scripts/module-nav.js`（注册 helper `module_nav`）+ `tools/sidebar-module.njk`
（挂在 `custom_file_path.sidebar`）。

- 模块 = 分类第二层（`学习/行测/判断推理` 里的「行测」）。列表按 `date` **升序**，**不按标题**：
  标题里的「（一）（二）（三）」是汉字，Unicode 顺序是 一 < 三 < 二，按标题排会乱；导入脚本给每篇写的是
  当天的不同分钟（`sh-xiangqi-1` 是 09:10、`-2` 是 09:11），所以日期升序就是教学顺序。
- 超过 6 篇（`GROUP_MIN`）才按第三层分类分组（题型 / 月份），三篇一组的六项阶段课就是一条平铺列表。
- **只有当前篇所在那一组默认展开**（服务端写 `.is-open`），点别的组名换 `.is-open`，一次只开一组
  （`source/js/sidebar-module.js`，和目录折叠同一个钩子挂载）。时政 74 篇、行测 38 篇，全铺开侧栏就成了第二篇文章。
- 主题的站点概览（作者名 / 日志统计 / GitHub 链接）不删模板，用 `.site-overview-wrap:has(.module-nav) > :not(.module-nav) { display: none }`
  整块隐藏 —— `.module-nav` 只在文章页渲染，所以首页/分类/归档/标签页的站点概览原样保留（校验器专门查了这条）。
- 格子上方的标签「站点概览」是主题模板里 `__('sidebar.overview')` 写死的，不改 `node_modules` 就只能运行时改 DOM：
  `sidebar-module.js` 看到 `.module-nav` 才把它换成「本模块文章」。别用 CSS `font-size: 0` 藏原文再 `::after` 补字——
  `.sidebar-nav li` 的高度、下划线位置都跟字号相关，会歪。（主题的 tab 点击事件绑在 `<li>` 元素上，
  `next-boot.js` 只在加载时 `querySelectorAll('.sidebar-nav li')` 拿引用，换 `textContent` 不影响。）

**② 文章页瘦身**：全在 `_config.next.yml`，不碰模板 —— `post_meta.created_at: false`、
`post_meta.updated_at.enable: false`、`post_meta.categories: false`（标题下那一行只剩字数/时长），
`footer.powered: false`（页脚只剩版权行）。**底部标签按用户的意思留着**（他勾的三项里没有删标签）。
侧栏本来就有目录和兄弟篇，分类面包屑在正文里是重复信息，所以关掉不亏。

**③ 一键到顶**：主题的 `back2top.enable: true` 早就开着，但在 Pisces 桌面版上它落在**左下角**
（`left: 30px`、26px、`#222`）正好压在 240px 宽的侧栏上，等于没有。现在只在 CSS 里覆写成右下角 42px 圆角按钮
（`left: auto; right: 30px`，移动端 `right: 20px`），点击和「滚过 5% 才 `.back-to-top-on` 浮出来」都还用主题
`source/js/utils.js` 里现成的逻辑，**没有新写脚本**。图标带主题的 `.fa-lg`，所以覆写选择器写成 `.back-to-top i.fa`
多一层才压得住（产物里确认我的规则排在主题规则之后）。

箭头看着歪的根因就在这一步：主题的居中机制只有一条 `.back-to-top .fa { text-align: center; width: 26px }`
——**把图标宽度写成按钮宽度**，26px 的按钮刚好居满。按钮放大到 42px 后那 26px 就成了「靠左的 26px」，
字形停在左边。我上一版给 `i.fa` 加了 `width: auto` 想撒手，但主题 `.back-to-top` 的 `display: flex`
只写了 `align-items: center`（管交叉轴），**主轴没有 `justify-content`**，于是图标仍然贴在左、
右侧空出一截。修法是把居中交给按钮自己：`.back-to-top { justify-content: center }` +
`i.fa { width: auto; font-size: 18px; line-height: 1 }`，实测字形盒左右留白各 15px（42px 按钮 − 12px 字形）对称。
**教训**：改主题的组件尺寸时要顺手查它靠什么机制居中，`width = 容器宽` 这种「假居中」在放大容器后一定坏。

**④ 顶部进度条只在文章页**：`reading_progress.enable: true` 保留（不删 DOM，主题的 `utils.js` 在滚动时
要往 `.reading-progress-bar` 写 `--progress`，删了节点它每个滚动帧都报 null）。CSS 改成默认
`display: none`，只有 `body:has(.main-inner.post)` 时 `display: block`。为什么用 `:has(.main-inner.post)`：
各页的 `<body class="use-motion">` 完全没有区分度，而 `.main-inner` 的第二个 class 就是页面类型
（`post` / `index` / `archive` / `category` / `tag`），一条选择器把首页、分类、归档、标签页全排除掉。

### 分类页：树状图（2026-09-24）

用户口径：「分类的 UI 重新设计一下，给个方案」→ 他自选「思维导图，树状图」，范围「两个都改」：
`/categories/` 总览页 + 点进某个分类后的文章列表页。

**① 数据：`scripts/cat-tree.js`**。`before_generate`（优先级 12）里把全站文章按 `date` **升序**遍历，
逐篇把它的分类链塞进一棵字典树，节点是 `{name, path, url, count, children, last}`；注册两个 helper：
`cat_forest()` 给总览页整棵树，`cat_here(page)` 从 `page.path` 反解出当前分类链（去掉 `categories/` 和
`index.html`，逐段 `decodeURIComponent`），返回 `{total, node, crumbs}`，`node` 为 `null` 时模板回落到主题原来的
`.collection-title` 结构。同一个钩子里 `hexo.theme.setView()` 挂两份模板。
**不缓存 `forest()` 的结果**：`hexo server` 下加了文章要立刻能看到（生成器场景这点开销无所谓）。
**当前形态**：2 个一级有内容（学习 112 = 时政要点 74 + 行测 38；生活 25 = 素描 7 + 六项各 3），
共 40 个分类节点、最深 3 层。`工作` 一篇没有，所以不进树（模块卡上以 `bento-card--empty` 出现）。

**② 模板**：`tools/cat-tree.njk`（总览，`source/categories/index.md` 的 front-matter 加 `layout: cat-tree`
才走它，主题的 `layout/page.njk` 那套 `.category-all-page` 列表就不参与了）+ `tools/cat-branch.njk`
（`setView('category.njk', …)` **顶掉主题的分类页模板**）。两份都 `{% extends '_layout.njk' %}` +
`{% import '_macro/sidebar.njk' as sidebar_template with context %}`，和主题自己的模板同一条路，
所以侧栏、菜单徽章、深色模式全都跟着。

**③ 为什么是「一行一节点、行高固定 30px」的文件树，不是左右展开的思维导图**：
折线的竖段要接住上下两行的中心点，**只有等高才能纯 CSS 算准**（`::before` 画「左下折角」=
`border-bottom + border-left` + `border-bottom-left-radius: 6px`，高 15px 正好半行；`::after` 画折角往下
续到下一行的那 15px，`.is-tail` 时 `content: none` 断尾；父节点没排完时子行左边压一条 `.cat-rail` 穿层竖线
把它和后面的兄弟连起来）。左右展开会让父行被整棵子树撑高，位置只能靠 JS 量 DOM，
一屏 40 个节点不值得引这份复杂度。层级靠 `padding-left`（一级 22px、二级 44px）+ `::before` 的
`left`（11px / 33px）成对写死，两级错位就是这两个数没配套。缩进列在窄屏上会被 `.cat-card { overflow-x: auto }`
接住。三种节点用色区分：一级 = `--accent` 实心、二级模块 = `--surface-2` 底加粗、叶子 = 透明 + 描边，
当前分类在列表页里是 `<h1 class="cat-node--here">`（描 accent 色），面包屑上的祖先用无框灰字。

**④ 排序**：`_config.yml` 里 `category_generator: order_by: date`（默认 `-date` 会把最后一课排最前）。
升序 = 教学顺序，理由和侧栏兄弟篇同一个（导入脚本给每篇写当天的不同分钟）。
**分页在模板之前切**，所以第 2 页自然接着排，跨页顺序也是对的。列表页顶部一句 `.cat-list-note`
交代「几个子分类、共几篇、这一页列几篇、按导入顺序排」，条目不再重复日期（日期在这里没意义）。

**⑤ 两个坑**：
- **nunjucks 的 `loop.parent` 不工作**：模板里写 `loop.parent.value.last` 静默得到 `undefined`，
  结果是所有 29 个叶子行都拿到 `.cat-rail`（应为 21 个）。改成在 `forest()` 里递归给每个节点打
  `n.last = i === list.length - 1`，模板读 `mod.last` / `leaf.last`。**别指望框架模板语言有嵌套循环的父循环变量**。
- 分类页的树画在 `.cat-cards` 网格里，`grid` 默认 `align-items: stretch` 会把两张卡拉到等高，
  「学习」那张 14 行的卡被撑到 26 行高、底下空一大块 → `align-items: start`。

**一个没走的弯路，记一下**：想换掉侧栏模板本来可以 `hexo.theme.setView('_macro/sidebar.njk', …)`，
但主题的 `njk` 渲染器是 `nunjucks.configure(dirname(data.path))` —— `{% import %}` / `{% extends %}`
按**真实文件系统**解析，`setView` 对它们无效；只有 `partial()` 走 `ctx.theme.getView()`，`setView` 才拦得住。
所以选官方 `custom_file_path.sidebar` 注入口 + CSS `:has()`，绕开 `theme.cache.enable` 的 `fragment_cache` 隐患。



### 验证这套前端的机器化检查

`tools/check-build.py`：第 1b 节查三层分类（一级只能是 工作/学习/生活，且每篇的分类路径都建了页）；
第 9 节查 CSS 里 token/字体/折叠/减少动效都在、自定义层排在主题层之后、折叠态规则是显式 `display: none`、
首页没有 `post-block`、1 张日历卡 + 3 张模块卡（名字必须是 工作/学习/生活，空的那些要带 `--empty`）、
**格子正好 52×7 = 364 个、逐日连续、起点是「本周一往前数 51 周」**、每格 `title` 的日期与篇数 == 源里那天的发文数、
色阶 == Python 现算的 `-(-n*4//peak)`、`heat-l4` 的个数 == 峰值那几天的格子数、有 tooltip 的天数 ==
源里有发文的日子数、月首标签互不重叠且等于该列周一的月份、卡顶文案的合计/有内容天数/单日峰值 == 格子上那些数
现算的结果、图例恰好 5 格、`--heat-*` token 浅深两套都在、`grid-auto-flow: column` 和 `overflow-x: auto` 在、
旧的按月柱子（`class="months"` / `month-col`）已经拆干净、
「学习」卡上的题数文案和二级分类芯片与源现算结果一致（芯片按一级模块分开比，「生活」卡单独查那 7 个二级分类——六项 + 素描，都是从 `source/_posts` 现算）、首页每个 href/src 都落盘、
最近更新 == 全站最新 6 篇、`public/page/2/` 还是文章流、每篇行测「折叠块数 == 答案数」且速览恰好 1 块；
第 10 节查生活六项：**期望值全部从六份 manifest 现推**（`sh-<项>-<阶段号>` 18 个 slug、每页课数、每页三级分类名、每页图数），所以母本加课只要重跑导入脚本，校验器会跟着变；逐页查 `<title>`、三级 front-matter、`<h2>` 课数、课标题逐条在渲染页里对得上、兄弟篇链接、四处图片集合（母本 svg / 源 md 引用 / `source/images` / `public/images`）完全相等、每项三段图数相加 == 母本该项目的图数（证明没有跨阶段重复或漏）、汉字 ≥ 母本这一阶段的 0.9 倍、合计 64 课 499 图、站内链接无死链；
第 11 节查上面那三层阅读体验（明细见「文章页阅读体验」一节）；
第 12 节查这一节：137 篇文章页**逐篇**比侧栏（栏目标题 == 该篇的模块名、标的篇数 == 源里该模块的文章数、
列出的条数和源里一样多、恰好一条高亮且高亮那条的链接和文字都是本页、该不该分组和「只开着当前那一组」也对得上源）、
标题下那一行只剩字数项（`class="post-meta-item[\s"]` 数出来恰好 1 个，页面里不含 `<time` / `fa-folder`）、
页脚没有 `powered-by`、底部 `.post-tags` 还在、首页/分类/归档/标签页仍是站点概览且没有 `.module-nav`、
CSS 里 `:has()` 让位规则和折叠/平铺两条都在、一键到顶是 `left: auto; right: 30px` 且覆写排在主题之后、
`.back-to-top` 有 `justify-content: center`、`i.fa` 是 `width: auto`（上一版就是少了前者：主题只靠
「图标宽 = 按钮宽」居中，改按钮尺寸不补 `justify-content` 就偏）、进度条默认 `display: none` 且
`body:has(.main-inner.post)` 才放回来、进度条那个 DOM 还在（删了它主题的滚动脚本每帧写 null）、
每篇文章页都挂着那颗按钮和 `/js/sidebar-module.js`；
第 13 节查分类页树状图：**期望树完全从 `source/_posts` 现算**（分类链 → 字典树 → 逐行层级/顺序/篇数/链接/
`is-tail`/`cat-rail`），13a 比 `/categories/` 总览页的整棵树和卡数（== 一级模块数）、lede 文案逐字对得上；
13b 比 **40 个**分类页各自的「祖先面包屑 + 本页 `<h1>` + 子分类行」，并确认列表里没有 `<time` /
`collection-year` / `post-title-link`（日期和主题的老列表真的不画了）；13c 把 30 个叶子分类页翻页合起来
收全文章且第一页按 `date` 升序；13d 分类页上的链接无死链；再加四条 CSS 断言（第三层折线的 `left: 33px`、
`is-tail` 断尾、`.cat-rail`、`.cat-node--here`）。**共 352 项。**

## 申论知识库导入流水线（第一版 259 篇，已撤回）

> **当前状态：生成物已撤回。** 2026-09-21 第一版 259 篇文章和 `data/shenlun-manifest.json` 移进了
> `_废弃/申论知识库-2026-09-21/`（等重新整理的母本，见该目录的 README），`data/shenlun-raw/` 副本和
> 下面两个脚本原样保留，`--clean` 一跑就能重建。这一节描述的是已经跑通的链路，接新母本时照做。

原始笔记不手改，走「复制 → 脚本转换 → 生成文章」三步：

```
D:\AI跑数据\学习项目\申论知识库\...        ← 原件，永远不动
D:\AI跑数据\8月申论{上,中,下}册*_OCR.txt   ← 粉笔书本的 OCR 原件，永远不动
        ↓ 原样复制
D:\blog\data\shenlun-raw\...              ← 转换输入（.gitignore 已忽略，不入库）
        ↓ node tools/import-shenlun.mjs --clean
D:\blog\source\_posts\申论知识库\...       ← 生成的文章，正常提交
```

```bash
node tools/survey-sources.py        # 摸底：源文件正文字数分布，决定拆分粒度
node tools/import-shenlun.mjs --clean          # 全量重跑（先清空输出目录）
node tools/import-shenlun.mjs --only=决战申论100题 # 只导一个模块，试点用
python tools/audit-coverage.py      # 安全网：有没有正文真的没了
```

审计判据是**最长连续缺失段**（≥90 字才报警），不是覆盖率百分比——源文件里挤在一行的内容被拆成文章两节时，拼接处必然对不上几个窗口，那是噪声。清洗规则用 `js_rules()` 从 `import-shenlun.mjs` 现读现翻译，两边不可能各说各话。改完导入规则务必重跑它。

当前两个来源：`决战申论100题`（粉笔书本 OCR，按 `■…第N题…` 切成 103 篇真题 + 14 段方法导学，每篇含 题目 / 资料原文 / 答题演示 / 思维导图）和 `广东申论`（.md，只有题目+参考答案）。那份「国考申论_完整笔记_含原文重点思维导图.md」与书本同源、是同一批题的聊天导出版，双栏正文被 OCR 串行搅碎，独有内容全是噪声，已移到 `data/不导入/` 不参与生成。


**加第三个模块时**：把新模块原样复制进 `data/shenlun-raw/`；若它也是「01-xxx / 02-xxx」编号目录，往 `MODULE_SLUG` 加一条（key 是中文目录名，value 是拼音，只影响 URL，标题仍是中文）；结构不同就照 `parseBook()` / `importGuangdong()` 再写一个 importer；然后跑上面三条命令。

生成规则要点：

- URL 用 ASCII slug（`2026/09/21/wenti-004/`），`_config.yml` 的 permalink 用 `:name` 而非 `:title`，否则中文子目录会被拼进 URL。
- 清洗掉的 OCR 噪声：`--- 第 N 页 ---`、孤立页码、`【第N题完】回复"继续"` 这类翻页提示、边距引流文案（`打开粉笔APP…扫码`）、只剩 markdown 装饰的空行（`> ****`）、只剩标点的碎屑行、书本页眉和单字符碎片、连续 ≥3 行的书目目录、空的 ``` 代码块。
- 接回排版断行：`unwrapLines()` 把满行（≥36 字）且句末无标点的行与下一行拼成整段——书本和聊天导出都是按印刷栏宽硬换行的，不接就会一句显示两三行。上限 `MAX_PARA` 只当保险丝用（实测书本最长一段 580 字，所以给到 640）：把它压小会在半句话中间砍一刀，「自动测量老人的血压、心」/「步等，协助老人…」这样，比长段落难看得多。它依赖 Hexo 默认的 `breaks: true`（一个换行 = 一个 `<br>`），改成 `false` 段落会糊成一坨。
- 页眉与分隔页：`第N篇单一题`/`第N章问题类` 这种行每页顶部都会重复，`dropRunHeads()` 按「名字和当前篇/章相同=页眉（删掉），不同=真分隔页（切块）」区分。早期版本把页眉当分隔页，导致 10 道题的正文从页眉处被截断、每篇丢两三千字。页眉偶尔和邻近字符粘成一行（`：决战申论100题（下册）`），`BOOK_HEAD` 容忍这一两个粘连字符。
- 去重：题目文件与解析文件、`## 题目` 与 `## 参考答案` 之间大量重复，按 30 字滑窗判断，后节是前节尾部就地切开，否则整节丢弃。

已知的 OCR 固有缺陷（两份母本都缺，脚本猜不回来）：① 少数题干的前半句在印页上就丢了，`## 题目` 从半句开始（`guandian-008`、`dazhu-001` 等约十余篇）；② 文章写作题的给定资料印在 `答题演示` 的 `### 资料N` 里，那 11 篇没有独立 `资料原文` 小节；③ 思维导图是双栏图形，OCR 出来是打乱顺序的短语，只按原样保留；④ 答题演示里「话题梳理/要点总结」两个文本框交替出现，接行时会偶发跨框粘连，文字不缺但语序怪；⑤ 跨页的那一行接不上（页码、页眉、分隔页横在句子中间），书本 117 篇里还剩约 550 处半句，脚本不敢猜下一行是不是同一段。

## 时政要点导入流水线（74 篇）

母本是一份人写的干净 markdown（`时政要点汇总 · 2025年11月 — 2026年2月`，来自 Qoder 会话目录，**只复制不修改**）：

```
C:\Users\lenovo\Documents\Qoder\...\shizheng-summary.md   ← 原件，永远不动
        ↓ cp（复制后核对 md5 一致）
D:\blog\data\shizheng-raw\shizheng-summary.md             ← 转换输入（data/ 已 gitignore）
        ↓ node tools/import-shizheng.mjs --clean
D:\blog\source\_posts\时政要点\sz-*.md                    ← 生成的文章
```

母本三层结构：`#` 一个月（`# 2025年11月　关键词 · 关键词`）、`##` 五大类（重要讲话/文件/事件/科技/纪念日）、`###` 一条考点（标题尾部带 ★ 重要度）。

切法（2026-09-22 返工一次）：**一条考点一篇**，slug `sz-YYMM-序号`，`date` 落在当月 1 号 09:序号 分，所以同一月的文章顺序 = 母本顺序。第一版按「一月一篇」只出 6 篇，一个分类页里根本没法归类，废弃了。分类（2026-09-23 又返工一次，从四级压到两级）：`时政要点 / 2025年11月`，月份就是分类页；**年份、专题类别（`重要讲话与指示`/`重要事件`/`重要文件与文章`/`重要科技`/`周年与纪念日`）、星级**全部降到标签，正文首行那句 `**出处**：2025年11月（关键词…） · 一、重要讲话 / 指示` 仍然原样留着（母本原文，不改）。三个「专题」挂 `时政要点 / 专题`，跨月速查表挂 `时政要点 / 速查`。

跨月的两块另算：**三大专题一个专题一篇**（内部还有小标题，是给一整场会议串讲的，拆开就断了上下文），**跨月速查表整块一篇**（高频数字 + 易混提法 + 来源清单，考前一晚是一起看的）。开头的汇总首页只留两行引言（解释 ★ 与「易错」的来历，抄进跨月那几篇开头），`## 目录` 的锚点在拆分后会失效，整段丢弃。

脚本自带**两道自检**：① 逐行——除声明丢弃的行和标题行，母本每一行都必须在某篇文章正文里原样出现；② 标题——月内每个 `##` 必须是认识的分类、每个 `###` 必须成篇且 slug 不撞。改完规则务必重跑，两绿了才算过。

三个坑：① `**粗体**` 夹在中文字符里会被 CommonMark 判成非边界（`纳入**「四个全面」战略布局**` 会把星号原样印到页面上），生成时统一换成 `<strong>` 标签——母本 391 对 `**` 全部同行成对，替换无损。② 母本里三处「详见本页【专题一】」依赖的是同一份文档，拆分后就成了失效引用，`xref()` 把它们换成指向对应专题篇的绝对链接。③ 专题的 `###` 里星级有时写两遍（`……（★★★★★） ★★★★★`），`dedupeStars()` 去掉括号里那份。这三处都是唯一允许的文字改写，**自检两侧套同一组函数**，所以别处丢了照样报。

## 行测题库导入流水线（38 篇 / 541 题）

母本：`D:\AI跑数据\数据` 里 27 考季高阶难题精刷的 9 个 md（判断/数量/言语/资料 各上下册 + `_答案键.md`）与 `assets/` 下 152 张原页截图。同样**只复制不修改**：

```
D:\AI跑数据\数据\*.md + assets/            ← 原件，永远不动
        ↓ 复制（逐个核 md5）
D:\blog\data\xingce-raw\                   ← 转换输入（data/ 已 gitignore，152 张图全量留在本地）
        ↓ node tools/import-xingce.mjs --clean
D:\blog\source\_posts\行测题库\<模块>\xc-*.md   +   source\images\xingce\<ascii>\*.png（只搬引用到的 92 张）
```

切法：**一个「难题组」一篇**（`##` 一级 = 一组，如 `## 定义高分必刷难题（一）`）+ 答案键总表 1 篇。不按册切是因为一册混着 2~3 个题型（判断上册有定义和类比），按册分类等于没分类；不按题切是因为组内题号从 1 编号、答案键也按组给，且资料分析一题配一段材料。分类两级 `行测 / 判断推理`（2026-09-23 从四级压下来：`27考季` 和题型都降到标签，五个大类 = 判断推理 / 数量关系 / 言语理解 / 资料分析 / 答案键，就是文章所在的子目录名）；slug `xc-<模块码><册><序号>`：`pd` 判断 / `sl` 数量 / `yy` 言语 / `zl` 资料，`1` 上 `2` 下，如 `xc-pd2-04`。图片路径 `assets/判断下/p20.png` 改写成 `/images/xingce/pd-xia/p20.png`，中文不进 URL。每篇末尾附本组答案速览（从 `_答案键.md` 按 模块+册+题型+组号 对行）。

**两道自检**（和时政同套路）：① 逐行——9 个母本除标题行外每行都必须在某篇文章里原样出现（`**`→`<strong>`、图片路径改写两侧同用）；② 结构——每个 `##` 成篇、每个 `###` 留在正文、每组题数 == 答案数、答案都是单个 A–D、slug 不撞、入库图片存在。另外脚本会**如实报缺口**（不当失败）：答案键里有组在母本找不到题目、正文出现「如下图所示」却一张图都没有、母本里未被引用的图片张数。

**用户补件后怎么增量重跑**（2026-09-22 走过一轮，就三步）：

```bash
python tools/sync-xingce-raw.py        # 源→ data/xingce-raw 的差集复制，逐个核 md5，只报改了哪几个文件
node tools/import-xingce.mjs --clean   # 全量重切（不是打补丁：切法/顺序/slug 都按母本当前状态重来）
pnpm hexo clean && pnpm hexo generate && python tools/check-build.py
git add -A && git commit -m "…" && git push   # Actions 绿了以后
IMG_LIMIT=24 python tools/check-live.py       # 从公网再核一遍：文章页 200、图片能取到、分类页收全
```

`import-xingce.mjs` 是幂等的（`--clean` 先清空输出目录和图库），所以补件不需要维护 diff——直接重跑，再用 `git status` 看落了多少新文件。这一轮的结果：32 篇 → 38 篇、451 题 → 541 题、84 图 → 92 图，`⚠` 缺口提示全部消失。

两个真实踩过的坑：① 新加的 `##` 写成「**中心理解题**高分必刷难题（一）」（答案键那边是「中心理解」），`H2RE` 因此在捕获组外多放了个 `题?`——母本换个措辞脚本会**拒绝猜并报错**，改正则时看清它拒绝的是什么；② 判断上册把「（图片选项，原讲义 p17 为花序示意图）」这类占位换成了真图，说明占位文字是母本自身的产物，别当噪声清洗掉。

剩下的已知事实（不是缺陷）：

- 母本 152 张图里只有 92 张被正文引用，未引用的 60 张（判断上 23、判断下 19、数量上 6、数量下 4、资料上 4、资料下 4）留在 `data/xingce-raw/assets/`，不入库。
- 图片是 PDF 整页截图（1457×2048，单张 ~700KB），一篇资料分析要加载 15~20MB。要瘦身就转 WebP/压宽度，URL 后缀由脚本统一改，重跑即可。

## 素描教程导入流水线（7 篇 / 30 课 / 159 图）

母本：`C:\Users\lenovo\Documents\Qoder\2026-09-21\5a01cf22` 里那套 HTML 课页导出的 markdown（`course/` 30 课一课一 MD、`basics/intro-overview.md` 入门总览、`course.manifest.js` 记录阶段↔课程的对应）。同样**只复制不修改**：

```
C:\Users\lenovo\Documents\Qoder\2026-09-21\5a01cf22\…（原件，永远不动）
        ↓ 复制（diff -r 核过一遍）
D:\blog\data\sketch-raw\{course,basics,course.manifest.js}    ← 转换输入（data/ 已 gitignore）
        ↓ node tools/import-sketch.mjs --clean
D:\blog\source\_posts\素描教程\sk-*.md（7 篇）   +   source\images\sketch\<组>\*（159 张，母本的全部）
```

切法：**一个阶段一篇**（用户 2026-09-23：按大模块分类、不要太多篇、方便后面更新）——`sk-stage1..sk-stage6` + `sk-intro` 共 7 篇，单篇 10~74KB。分类现在两级 **`生活 / 素描`**（用户 2026-09-24：素描挪进「生活」并压成两级）；原来那三个大类「基础与造型 | 静物写生 | 人物与创作」（用户 2026-09-23 从「一阶段一个分类」里挑的三堆：阶段 1+2+入门总览 / 3+4 / 5+6）**降到标签**，连同阶段号一起，树里不再占一层，标题里还是 `素描阶段二 · 几何体与明暗`。每篇正文用 `## NN 课名` 保住母本的课边界（阶段一 5 课 → 二 5 → 三 6 → 四 4 → 五 6 → 六 4，合计 30），文章左侧那份「文章目录」就按课跳。日期错开在 `2026-09-23 12:0N:00`，顺序即阶段顺序；`sk-intro` 单独 12:10:00 排最后。

**锚点规则**（文章左侧目录、以后可能的深链都靠它）：Hexo 给标题生成的 id 是「空格换成 `-`、中文原样保留、`&` 这类符号直接丢掉」——`06 四周练习计划 & 常见毛病自查` 的 id 是 `06-四周练习计划-常见毛病自查`，`04 单体：几何体 → 球体` 是 `04-单体：几何体-→-球体`。所以 `check-build.py` 第 8 节比对时两边都先去掉标点和空白再比，别拿字面相等去判（以前那条检查是挂在课程总览页的 30 个链接上核的，页面删了之后改成直接从 7 篇源文逐课核，覆盖面一样）。

**三处允许的改写**：① 段落软换行合并（HTML 导出把一句话拆多行，而 `hexo-renderer-marked` 默认 `breaks: true`，不合并就是满屏 `<br>`；行尾两空格的硬换行保留）；② `**x**` → `<strong>x</strong>`（紧贴汉字的星号 CommonMark 不闭合，会打印出字面星号）；③ 图片 `images/…` → `/images/sketch/<组>/<文件名>`，中文名不进 URL。除此之外内容与母本逐字一致。

**两道自检**：① 逐行——31 个母本 MD 除 H1 外每一行（同规则归一后）必须在生成的文章里原样出现；② 结构——30 课全部入篇、每篇课标题数 == manifest 该阶段课数、引用图片全部落盘、无 `**` 残留、无 `](images/` 相对路径、`sk-intro` 自己的 H2 不被下沉。

**重跑**（和行测那三步一样，母本更新后照抄）：

```bash
# 1) 重新复制母本到 data/sketch-raw（diff -r 确认只多了改动，没有别的东西）
node tools/import-sketch.mjs --clean
pnpm hexo clean && pnpm hexo generate && python tools/check-build.py
git add -A && git commit -m "…" && git push
python tools/check-live.py 素描教程      # 从公网再核一遍：文章页 200、图片能取到、分类页收全
```

`check-build.py` / `check-live.py` 都已同时覆盖行测和素描（素描量在 check-build 第 7 节写死：7 篇、30 课、159 图，素描改了篇数/课数要同步那三个数）。`check-live.py <模块目录名>` 的分类页核对现在是从源里现算分类链，不再写死行测那几个 URL。

已知事实：图片 149 张 SVG（范画线条图，放大不糊）+ 10 张 JPG，合计 159 张**全部**被正文引用，所以「母本有图没入库」的缺口是 0（和行测那 60 张相反）。母本里跨课引用写的是 `xxx.html`，导入时改成页内锚点（check-build 会拦任何残留的 `.html` 链接）。

核对页内目录时注意选择器：NexT 8.29 渲染出来是 `.post-toc .nav-link`，**没有** `.toc-link` 这个类（文档里两种都出现过），按 `.toc-link` 数会数到 0 误判成目录空的。素描这 7 篇每篇 10~15 万字节，全靠这个侧栏目录导航。

## 生活六项导入流水线（18 篇 / 64 课 / 499 图）

2026-09-24 用户：「将我的：猜灯谜，八段锦，数独，象棋，五子棋，书法，按上面要求push上去」。**当天返工过一次**：第一版按「一项一篇 + 生活/六项 两级」上线（commit `e878391`，6 篇），用户接着说「素描转移到生活中……按素描的结构去分类」，于是六项改成**一个阶段一篇、分类三层**（第三层直接用母本的阶段名），素描自己反倒压成两级 `生活 / 素描`。母本就是他自己的另一套课程产物（和素描同源不同项目）：

```
C:\Users\lenovo\Documents\Qoder\2026-09-21\5a01cf22\courses\*\dist\markdown（原件，永远不动）
        ↓ cp -r + md5 逐文件核（563 个文件，0 处不一致）
D:\blog\data\shenghuo-raw\{riddle,baduanjin,sudoku,xiangqi,gomoku,calligraphy}\
        ↓ node tools/import-shenghuo.mjs --clean
D:\blog\source\_posts\生活六项\sh-<项>-<阶段号>.md（18 篇）   +   source\images\shenghuo\<项>\*.svg（499 张，母本全部）
```

每项固定 3 个阶段（`STAGES_EACH`），阶段名就是第三层分类，slug 是 `sh-riddle-1/2/3` 这种。阶段二的课最多、图也最多：

| 项 | 阶段一 | 阶段二 | 阶段三 | 课数 | 图数 |
|---|---|---|---|---|---|
| 猜灯谜 `sh-riddle` | 基础认知 3 课/21 图 | 五大法门 5/39 | 实战与精进 3/21 | 11 | 81 |
| 八段锦 `sh-baduanjin` | 根基与预备 3/23 | 八式逐课拆解 4/35 | 串联与精进 3/21 | 10 | 79 |
| 数独 `sh-sudoku` | 规则与直觉解法 3/18 | 候选数与结构 5/39 | 链、变体与出题 3/24 | 11 | 81 |
| 象棋 `sh-xiangqi` | 规则与记谱 3/24 | 战术与杀法 5/40 | 中残局与精进 3/22 | 11 | 86 |
| 五子棋 `sh-gomoku` | 规则与棋形 3/19 | 攻防与计算 4/28 | 实战与精进 3/23 | 10 | 70 |
| 书法 `sh-calligraphy` | 工具与笔画 3/26 | 笔画与结构 5/50 | 临帖、章法与五体 3/26 | 11 | 102 |

合计 64 课 / 499 图，六套课各 0.8~2.7 万汉字一篇。分类二级名字用用户写的原词（**「象棋」不是「中国象棋」**，标题里才是全名）；标题形如 `数独阶段二 · 候选数与结构`，每篇里面 3~5 个 `## NN 课名`，文章左侧「文章目录」按课跳（NexT 的选择器还是 `.post-toc .nav-link`，见素描那节末尾的提醒）。日期 `2026-09-24 09:NN:00` 按「六项顺序 × 阶段顺序」递增（09:01…09:18），前台「最近更新」是书法阶段三往上倒着排。

**结构和素描那个脚本是同一套**：读每项的 `course.manifest.js` 拿「阶段↔课」对应（`module.exports = ({…})` 用 `new Function('return …')()` 求值，manifest 和 MD 数量、标题对不上、或者某项不是 3 个阶段就直接 die），课文件名按 `` `${l.n}-${basename(l.file,'.html')}.md` `` 拼；每篇开头自动生成「这套课：…N 个阶段共 X 课、约 Y 万汉字、Z 张图」+「本篇：第几阶段，另外两个阶段点这两个链接」+ 一张 `课 / 标题 / 这一课干什么` 的本篇课表，然后逐课接正文。三处允许的改写和素描完全一样（软换行合并、`**x**` → `<strong>`、图片改绝对路径 `/images/shenghuo/<项>/<文件名>`），另外多做一件：**课内标题整体降一级**（母本的 `##` 变 `###`），把 `##` 留给课号。

**两道自检**：① 逐行——每项每一课除 H1/H2 外每一行（同规则归一后）必须在生成的那篇里原样出现；② 结构——64 课全部入 18 篇、每项恰好 3 篇且课号跨过三篇连续排到 `NN`、每篇 `## NN ` 数 == 该阶段课数、`###` 数 == 母本这些课的 `##` 数、三级分类齐全、引用图片全部落盘且孤儿 svg 按 `<项>/<文件名>` 判为零、无 `**` 残留、无 `](images/` 相对路径、slug 不撞。

```bash
node tools/import-shenghuo.mjs --clean
pnpm hexo clean && pnpm hexo generate && python tools/check-build.py
git add -A && git commit -m "…" && git push
python tools/check-live.py 生活六项
```

**页面重量**：拆篇之后最重的一页是象棋阶段二，HTML 约 150KB、40 张 SVG；`public/` 整站 54MB（未拆前那版是 57MB，因为一项一篇时重复的「这套课」开头和总表被摊薄了）。手机上首屏没问题（图是矢量、按需解码），一页 3~5 课在微信里翻着也不长。母本加了课就改 `LESSON_TOTAL`（脚本顶部会拿它对账），其余不用动。

## 言语理解母本（已入场，尚未导入）

`D:\blog\data\yanyu-raw\yanyu-982-final.md` ← 复制自 `D:\AI跑数据\学习项目\刷题\言语理解_最终版.md`（1.9MB / 982 个题块 / 798 个带解析，md5 `dc866972`）。

那份母本同内容有 6 个近似版本、md5 各不相同（`言语理解_最终版` / `_清理版` 都是 982 题带解析，只差排版；`_按知识点分类*` 三个变体只有 79 题；`知识库\言语理解与表达_完整版.md` 也是 982 题但**解析为零**）。用户 2026-09-23 选定「最终版」这一份，其余重复版本不入 `data/`。文件名已改成 ASCII（`data/` 不进仓库，但保持和 slug 同一套命名习惯）。

母本性质（用户 2026-09-23 明确）：**这是模块练习的书，不是真题套卷，言语理解内部不分「部分」**。题面首行的 `（2024江苏A29）` 只是单题出处，题号重置也不代表分组——**别拿这些当切篇边界，分类口径等用户给**。

已核实的内容事实：

- **982 个题块，798 个带【解析】，184 个没有**（另有 1 个题块里塞了两条解析）。缺的如实报出来，别当成错题清洗掉。
- 982 题**全都带答案**：`**N.【答案】D。粉笔大数据：本题正确率为71.53%，易错项为C。**` —— 正确率、易错项是逐题现成的数据，691 题另有 `【文段出处】《…》`。
- 母本里留着 OCR 页眉噪声：`决战行测5000题·言语理解与表达（上册/下册）` 以及夹在题目中间的 `本部分题目解析见下册第X～Y页。`（题本↔解析的页码交叉引用，上册是题本、下册是解析）。导入时要清掉，但**清洗规则只准删这两种整行**，正文里出现「训练」「部分」这类词是正常的，别顺手放宽。

## 评论（决定不启用）

2026-09-21 用户决定不开评论：`comments.active` 留空、`utterances.enable: false`，`utterances.repo` 指向的 `Huang-jiale/comment-storage` 因此也没建。以下两种方案留档备用。

**Utterances**（主题内置，数据存 Issues）：到 <https://github.com/apps/utterances> 授权仓库，然后在 `_config.next.yml` 把 `utterances.enable` 改 `true`、填好 `repo`，并把 `comments.active` 设为 `utterances`。

**Giscus**（数据存 Discussions，你原先选的方案）：NexT 8.29 **不内置**，需装社区插件 `hexo-next-giscus`，且仓库要先在 Settings 开启 Discussions。步骤见插件 README，配置项写进 `source/_data/`。

## 已开启的功能

深色模式切换、站内搜索（依赖 `hexo-generator-searchdb`，索引生成为 `search.json`）、文章目录 TOC（侧栏，课内小标题点击展开，见「文章页阅读体验」）、侧栏第二格在文章页换成「本模块文章」（同模块兄弟篇，见上一节）、页面顶部阅读进度条（**只在文章页画**，首页/分类/归档/标签页不画）、文章标题下的字数与预计读完时间（标题下只有这一行，日期/分类都关了）、右下角一键到顶（箭头已居中）、代码块复制按钮、菜单数字徽章、分类页 `/categories/`（**树状图**：一行一分类、缩进表父子、括号里是含子分类的篇数，点进去那一页顶部也带本分支的树 + 面包屑，见「分类页：树状图」一节）、首页顶部 52 周入库日历（纯只读、悬停看当天日期与篇数）、标签页 `/tags/`、关于页 `/about/`、页脚只留版权行（`footer.powered: false`）。评论与 pjax 都不开（见「评论（决定不启用）」）。

## 可选扩展

```bash
pnpm add hexo-generator-feed hexo-generator-sitemap --save   # RSS + sitemap
```

自定义域名：仓库 `source/` 下放一个 `CNAME` 文件（内容写你的域名），再到 Settings → Pages 填域名，HTTPS 自动签发。DNS 记录分两种情况——

- **子域名**（如 `blog.example.com`）：加 `CNAME` 记录指向 `你的用户名.github.io`。
- **裸域/顶级域**（如 `example.com`）：DNS 规范不允许根域设 CNAME，需加 GitHub Pages 的四条 `A` 记录（`185.199.108.153`、`185.199.109.153`、`185.199.110.153`、`185.199.111.153`）；若服务商支持 CNAME Flattening（Cloudflare、DNSPod 等）也可直接用 CNAME。
