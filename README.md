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

### 文件怎么写（越靠上越省事）

- **一个文件一篇**最省事。一个文件里塞多篇（一整册、一个月）就得写切块脚本，切到哪一层由分类需要决定——时政按「一条考点一篇」、行测按「一个难题组一篇」，都是为了分类页能归类。
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
分类：知识库 / 行测 / 常识 / 政治理论   ← 想要几级写几级，顺序就是侧栏分类页的顺序
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

## 外观（布局与留白）

`_config.next.yml` 里 `scheme: Pisces` —— 双栏卡片布局，≥992px 时左侧栏 240px（`sidebar.width_dual_column` 可调），正文列宽 `calc(100% - 252px)`。之前的 `Muse` 是单栏宽体，正文列最宽只有 900px，在 1920 屏上两侧各留 ~510px 空白。

NexT 把整块容器宽度写死在主题包里（`$content-desktop-large = 1160px`，≥1600px 时改为视口的 73%），改配置改不动。真要再放宽，只能在 `_config.next.yml` 开启：

```yaml
custom_file_path:
  variable: source/_data/variables.styl
```

然后在该文件里重写 `$content-desktop-large`。这样升级主题不会被覆盖。

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

切法（2026-09-22 返工一次）：**一条考点一篇**，slug `sz-YYMM-序号`，`date` 落在当月 1 号 09:序号 分，所以同一月的文章顺序 = 母本顺序。分类四级 `时政要点 / 2025年 / 2025年11月 / 重要讲话与指示`，分类页本身就是考点清单；★ 转成标签（`五星必背`…）。第一版按「一月一篇」只出 6 篇，一个分类页里根本没法归类，废弃了。

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

切法：**一个「难题组」一篇**（`##` 一级 = 一组，如 `## 定义高分必刷难题（一）`）+ 答案键总表 1 篇。不按册切是因为一册混着 2~3 个题型（判断上册有定义和类比），按册分类等于没分类；不按题切是因为组内题号从 1 编号、答案键也按组给，且资料分析一题配一段材料。分类四级 `行测 / 27考季 / 模块 / 题型`（题型与模块同名时只到三级）；slug `xc-<模块码><册><序号>`：`pd` 判断 / `sl` 数量 / `yy` 言语 / `zl` 资料，`1` 上 `2` 下，如 `xc-pd2-04`。图片路径 `assets/判断下/p20.png` 改写成 `/images/xingce/pd-xia/p20.png`，中文不进 URL。每篇末尾附本组答案速览（从 `_答案键.md` 按 模块+册+题型+组号 对行）。

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

深色模式切换、站内搜索（依赖 `hexo-generator-searchdb`，索引生成为 `search.json`）、文章目录 TOC、代码块复制按钮、菜单数字徽章、分类页 `/categories/`、标签页 `/tags/`、关于页 `/about/`。

## 可选扩展

```bash
pnpm add hexo-generator-feed hexo-generator-sitemap --save   # RSS + sitemap
```

自定义域名：仓库 `source/` 下放一个 `CNAME` 文件（内容写你的域名），再到 Settings → Pages 填域名，HTTPS 自动签发。DNS 记录分两种情况——

- **子域名**（如 `blog.example.com`）：加 `CNAME` 记录指向 `你的用户名.github.io`。
- **裸域/顶级域**（如 `example.com`）：DNS 规范不允许根域设 CNAME，需加 GitHub Pages 的四条 `A` 记录（`185.199.108.153`、`185.199.109.153`、`185.199.110.153`、`185.199.111.153`）；若服务商支持 CNAME Flattening（Cloudflare、DNSPod 等）也可直接用 CNAME。
