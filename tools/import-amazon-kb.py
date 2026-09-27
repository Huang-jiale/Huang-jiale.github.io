# -*- coding: utf-8 -*-
"""
亚马逊运营知识库（21 篇）→ Hexo 文章

母本：`data/amazon-kb/*.md`（原件 `../wearesellers/kb/`，**只复制不修改**，复制时逐个核 md5；
  data/ 在 .gitignore 里，仓库只存生成出来的文章和这个脚本）
  21 个 md：`00 总纲与索引` + `01 A1 …` ~ `20 E3 …`，每篇是「主题综述 + 该主题全部知识点卡」合并件。

切法：**一个文件一篇**（21 篇），和推给知识库的粒度保持一致，编号也一一对得上（am-kb-00 … am-kb-20）。
  - 为什么不拆成综述一篇、卡片一篇：综述里的「支撑卡片」直接引卡片标题，卡片里的前提又要回看综述的
    口径，拆开后读者要在两个 URL 之间来回跳；一篇 3~6 万字，侧栏目录按二级折叠本来就分得开。
  - 分类三层（工作 / 亚马逊运营 / 板块）：板块沿用《00 总纲与索引》第五节自己给的分组
    ——A 账号与主体｜B 合规与权利｜C 流量与履约｜D 钱与税｜E 经营与人，不另起一套名。
    侧栏「本模块文章」按第三层分组（scripts/module-nav.js），21 篇分 6 组正好翻得动。

正文改写（只有这三类，逐条可查）：
  1. 标题整体降一级（`#`→`##`、`##`→`###`、`###`→`####`）：母本一篇里有两个 `#`（文件标题、
     「· 主题综述」和「全部知识点卡」两个部分标题），Hexo 的文章标题走 front-matter，正文里再留
     `#` 会和页面 H1 打架；降到 h2/h3 正好落进主题 toc 的 max_depth: 3，卡标题落在 h3。
     《00 总纲与索引》没有这个冲突（一、二、… 本来就是 h2），不降。
  2. 去掉站点指向：母本里点名数据源的那几处换成不点名的说法，**帖子编号原样保留**（用户 2026-09-27
     拍板：「保留帖号，去掉站点指向」）。
  3. 《00 总纲与索引》第七节是本地文件清单（阅读器、jsonl、留档 csv），网上发布后读者手上没有这些
     文件，整节换成本系列 21 篇的目录表；正文里两处「见第七节」「本地阅读器」跟着改。

自检（跑完必须全绿）：
  1. 逐行守恒：除被明确删掉的行（文件标题、母本的 `>` 系列行、00 的第七节整块）以外，母本的每一行
     都必须在生成的文章里原样出现（标题行按降级后的形态核）；
  2. 数量对得上：00 主题地图表里每个主题的「卡片 / 子问题」数，必须等于该篇正文里实际数出来的
     `## 卡片标题` 与 `- 子问题:` 行数；
  3. 站点名残留为 0、slug 不撞、21 篇都落盘、每篇正文非空。

  python tools/import-amazon-kb.py [--clean]
"""
import io
import os
import re
import sys
import glob
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'amazon-kb')
OUT = os.path.join(ROOT, 'source', '_posts', '亚马逊运营')

DATE_DAY = '2026-09-27'
BASE_MIN = 1                      # 09:01 起，每篇加一分钟：升序就是阅读顺序
SERIES = '亚马逊运营知识库'

# 板块名取自《00 总纲与索引》第五节的主题分组，不另起口径
BLOCK = {'A': '账号与主体', 'B': '合规与权利', 'C': '流量与履约', 'D': '钱与税', 'E': '经营与人'}
BLOCK_INDEX = '总纲与索引'

# 站点指向：只去名字，不动编号、不动任何结论措辞
SCRUB = [
    ('数据源：知无不言社区（wearesellers.com）Amazon 分区', '数据源：某中文跨境电商卖家问答社区 · Amazon 分区'),
    ('知无不言精华帖', '卖家社区精华帖'),
    ('留档见第七节', '留档在本地，未随本系列发布'),
    ('编号可在本地阅读器粘贴搜索定位原帖', '编号是提问帖的 ID，回站内搜该编号即可定位原帖'),
    ('知无不言', '某卖家社区'),
    ('wearesellers.com', '某卖家社区'),
    ('wearesellers', '某卖家社区'),
]
FORBIDDEN = ('知无不言', 'wearesellers')

POSTS = []                        # 先生成元数据，00 的目录表要用到全部 21 篇的 URL


def scrub(text):
    for a, b in SCRUB:
        text = text.replace(a, b)
    return text


def demote(text):
    return re.sub(r'^(#{1,5})(?= )', r'#\1', text, flags=re.M)


def parse_name(fn):
    base = os.path.basename(fn)[:-3]
    m = re.match(r'^(\d{2})\s+(?:([A-E]\d)\s+)?(.+)$', base)
    num, code, name = m.group(1), m.group(2) or '', m.group(3)
    return num, code, name


def url_of(slug):
    return '/%s/%s/' % (DATE_DAY.replace('-', '/'), slug)


def card_counts(text):
    """卡片正文：`# …全部知识点卡` 之后的 `## 标题` 才是卡，综述部分的 `##` 不算。
    子问题按去重后的值数——多张卡会挂在同一个子问题下，主题地图里那一列就是这个口径。"""
    i = text.find('全部知识点卡')
    part = text[i:] if i >= 0 else ''
    n_cards = len(re.findall(r'^## ', part, re.M))
    n_subs = len(set(re.findall(r'^- 子问题:\s*(.+)$', part, re.M)))
    return n_cards, n_subs


def index_table(rows):
    """00 第七节：本地文件清单 → 本系列 21 篇目录。"""
    L = ['## 七、本系列各篇', '',
         '这套库一共 21 篇：先读总纲（口径与局限都在这一篇），再按板块下钻。', '',
         '| 编号 | 主题 | 卡片 | 子问题 | 板块 |', '|---|---|---|---|---|']
    for r in rows:
        title = '%s %s' % (r['code'], r['name']) if r['code'] else r['name']
        L.append('| %s | [%s](%s) | %s | %s | %s |' % (
            r['num'], title, url_of(r['slug']), r['cards'] or '—', r['subs'] or '—', r['block']))
    L.append('')
    return L


def build(fn):
    num, code, name = parse_name(fn)
    base = os.path.basename(fn)
    raw = io.open(fn, encoding='utf-8').read()
    lines = raw.split('\n')

    title = '%s · %s' % (SERIES, name) if not code else '%s %s · %s' % (SERIES, code, name)
    slug = 'am-kb-%s' % num
    block = BLOCK_INDEX if not code else BLOCK[code[0]]
    n_cards, n_subs = card_counts(raw) if code else (0, 0)
    if code:
        desc = ('%s %s：%s 张知识点卡 / %s 个子问题。含主题综述（该信什么 · 分歧在哪 · 支撑卡片）'
                '与逐条卡片，每张卡标注前提、证据强度、反方口径与出处帖号。' % (code, name, n_cards, n_subs))
    else:
        desc = ('全套口径在这一篇：4,963 个卖家提问、69,209 条可读回答压成 369 张知识点卡的来龙去脉，'
                '字段读法、强度与风险判定标准、20 个主题地图、已知局限清单。')

    POSTS.append(dict(num=num, code=code, name=name, slug=slug, title=title,
                      block=block, cards=n_cards, subs=n_subs, desc=desc))

    # 丢掉母本的文件标题行和紧随其后的 `>` 系列行，正文自己补一行带链接的系列行
    # 按行号丢，不按内容丢：`|---|---|` 这种行在别的表里也出现，按内容丢会把该核的行也一起放过
    body, dropped = [], []
    i = 0
    while i < len(lines) and not lines[i].startswith('# '):
        dropped.append(i)
        i += 1
    dropped.append(i)                              # `# 文件标题`
    i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].startswith('> '):
        dropped.append(i)
        i += 1
    body = lines[i:]

    if not code:                                    # 00：第七节整块换掉
        cut = next((k for k, l in enumerate(body) if l.startswith('## 七、文件清单')), None)
        assert cut is not None, '%s：00 里没找到第七节，母本结构变了，别自动往下跑' % base
        dropped += list(range(i + cut, len(lines)))
        body = body[:cut]

    text = scrub('\n'.join(body))
    if code:
        # 主题篇里 `#` 是「综述 / 卡片」两个部分、`##` 是章节与卡标题，整体降一级刚好
        # 让卡标题落在 h3（主题 toc 收 h1~h3）。00 本身没有 `#` 层级冲突，一、二、… 就是 h2，不动。
        text = demote(text)

    head = ('> %s %s/20 ｜ 证据截至 2026-09-24 ｜ 口径与局限见[总纲与索引](%s)'
            % (SERIES, int(num), url_of('am-kb-00'))) if code else \
           ('> %s ｜ 21 篇一套，编号 00 是总纲 ｜ 证据截至 2026-09-24' % SERIES)

    out = ['---',
           'title: "%s"' % title,
           'slug: %s' % slug,
           'date: %s %02d:%02d:00' % (DATE_DAY, 9, BASE_MIN + int(num)),
           'categories:',
           '  - "工作"',
           '  - "%s"' % SERIES,
           '  - "%s"' % block,
           'tags:',
           '  - "亚马逊运营"',
           '  - "知识点卡"']
    if code:
        out += ['  - "%s"' % code]
    out += ['description: "%s"' % desc.replace('"', "'"), '---', '', head, '']

    tail = []
    if not code:
        # 00 的目录表要等 21 篇的元数据齐了才写得出 URL，main 里第二遍补
        tail = ['@@INDEX_TABLE@@']
    return '\n'.join(out) + text.rstrip('\n') + '\n' + '\n'.join(tail), dropped, raw, code


def main():
    files = sorted(glob.glob(os.path.join(SRC, '*.md')))
    if len(files) != 21:
        sys.exit('母本应是 21 篇，实际 %d 篇：%s' % (len(files), [os.path.basename(f) for f in files]))
    if os.path.isdir(OUT) and '--clean' in sys.argv:
        for p in glob.glob(os.path.join(OUT, '*.md')):
            os.remove(p)
    os.makedirs(OUT, exist_ok=True)

    errs, built = [], []
    for fn in files:
        text, dropped, raw, code = build(fn)
        slug = re.search(r'^slug: (\S+)', text, re.M).group(1)
        built.append([slug, os.path.join(OUT, '%s.md' % slug), text, dropped, raw, code])

    # 21 篇元数据齐了，回填 00 的目录表
    for b in built:
        if '@@INDEX_TABLE@@' in b[2]:
            b[2] = b[2].replace('@@INDEX_TABLE@@', '\n' + '\n'.join(index_table(
                sorted(POSTS, key=lambda r: r['num']))))
    for slug, path, text, dropped, raw, code in built:
        io.open(path, 'w', encoding='utf-8', newline='\n').write(text)

    # ---- 1. 逐行守恒 ----
    for slug, path, text, dropped, raw, code in built:
        keep = [l for k, l in enumerate(raw.split('\n')) if l.strip() and k not in dropped]
        miss = []
        for l in keep:
            want = demote(l) if (code and l.startswith('#')) else l
            want = scrub(want)                     # 改写过的行按改写后的形态核，别把改写当成丢失
            if want not in text:
                miss.append(l[:60])
        if miss:
            errs.append('%s 丢了 %d 行：%s' % (slug, len(miss), miss[:3]))
        for w in FORBIDDEN:
            if w in text:
                errs.append('%s 还留着站点名 %s' % (slug, w))

    # ---- 2. 数量对得上《00 总纲与索引》的主题地图 ----
    idx = io.open(os.path.join(SRC, '00 总纲与索引.md'), encoding='utf-8').read()
    rows = dict((m.group(1), (int(m.group(3)), int(m.group(4))))
                for m in re.finditer(r'^\| ([A-E]\d) \| ([^|]+) \| (\d+) \| (\d+) \|', idx, re.M))
    if len(rows) != 20:
        errs.append('主题地图只认出 %d 行，应为 20' % len(rows))
    for art in POSTS:
        if not art['code']:
            continue
        want = rows.get(art['code'])
        if want != (art['cards'], art['subs']):
            errs.append('%s 主题地图写 %s，正文数出 %d 卡/%d 子问题'
                        % (art['code'], want, art['cards'], art['subs']))

    # ---- 3. 结构 ----
    slugs = [s for s, *_ in built]
    if len(set(slugs)) != len(slugs):
        errs.append('slug 撞了')
    for slug, path, text, dropped, raw, code in built:
        n_h2 = len(re.findall(r'^## ', text, re.M))
        if n_h2 < 2:
            errs.append('%s 只有 %d 个 h2，降级可能没生效' % (slug, n_h2))
        # 卡标题必须是 h3：侧栏目录收到 h3，卡片在页面上才是「一条能点开看的层级」
        n_h3 = len(re.findall(r'^### ', text, re.M))
        art = next(p for p in POSTS if p['slug'] == slug)
        if art['cards'] and n_h3 < art['cards']:
            errs.append('%s 有 %d 张卡，正文只有 %d 个 h3' % (slug, art['cards'], n_h3))
        if len(text) < 3000:
            errs.append('%s 正文只有 %d 字' % (slug, len(text)))

    total = sum(len(b[2]) for b in built)
    print('生成 %d 篇 → %s，合计 %s 字符' % (len(built), os.path.relpath(OUT, ROOT).replace('\\', '/'), format(total, ',')))
    print('板块分布：' + ' ｜ '.join(
        '%s %d 篇' % (b, sum(1 for p in POSTS if p['block'] == b))
        for b in [BLOCK_INDEX] + list(BLOCK.values())))
    print('卡片合计 %d 张 / 子问题合计 %d 个（按正文实数）' % (
        sum(p['cards'] for p in POSTS), sum(p['subs'] for p in POSTS)))
    if errs:
        print('\n'.join('❌ ' + e for e in errs))
        sys.exit(1)
    print('✅ 自检全绿：逐行守恒、站点名残留 0、主题地图数与正文实数一致、slug 唯一')


if __name__ == '__main__':
    main()
