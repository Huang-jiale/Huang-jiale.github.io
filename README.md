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

首次已经推过了，之后每次改完只要第 2 步。

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

## 知识库导入流水线（申论知识库 259 篇）

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

## 评论（默认关闭，二选一）

两者都不需要自建后台，数据存在你自己的 GitHub 仓库里。

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
