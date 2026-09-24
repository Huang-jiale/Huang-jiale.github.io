# -*- coding: utf-8 -*-
"""构建产物体检：拿 `source/_posts/` 对账 `public/`，任何一步采样为空也算失败。

跑法：`pnpm hexo clean && pnpm hexo generate && python tools/check-build.py`
期望值全部从 source 现算，所以导完新内容不用改这个脚本；它只管一件事：
**构建有没有把源里的东西弄丢/弄坏**（页面数、图片、题数==答案数、分类页收全、死链、渲染残留）。
每一步都先断言「确实取到了样本」，正则写错匹配到 0 个时一律判失败，不许假绿。

2026-09-24 人工核对过的量：74 时政 + 38 行测 = 112 篇在「学习」，7 素描 + 18 生活课 = 25 篇在「生活」；
行测 541 题、92 图；素描 30 课、159 图；生活六项 64 课、499 图（期望课数与图数从母本 manifest 现算，篇数 18 = 六项 × 3 阶段）。
分类层数按模块定：一级只有 工作 / 学习 / 生活；「学习」下面三层（模块 / 子分类），
「生活」下面素描是两层（大类降到标签）、六项是三层（阶段名当三级），所以规则是 2~3 层、只有「学习」强制三层。
"""
import io, sys, os, re, glob
import urllib.parse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

fail = []


def check(cond, msg, detail=''):
    print(('OK   ' if cond else 'FAIL ') + msg + (f'  {detail}' if detail else ''))
    if not cond:
        fail.append(msg)


def norm(p):
    return p.replace('\\', '/')


def fm_categories(text):
    """取 front-matter 里的 categories 列表（和 tags 用同一套 `  - "x"` 写法，所以要在 tags: 处收口）"""
    m = re.search(r'^categories:\n((?:  - .*\n)+)', text, re.M)
    return [re.sub(r'^\s*-\s*["\']?(.*?)["\']?\s*$', r'\1', l) for l in m.group(1).splitlines()] if m else []


def fm_slug(text):
    m = re.search(r'^slug:\s*(\S+)', text, re.M)
    return m.group(1) if m else None


# ---------- 1. 源与产物的数量对得上 ----------

src = {}
for p in glob.glob('source/_posts/**/*.md', recursive=True):
    t = open(p, encoding='utf-8').read()
    src[norm(p)] = t
check(len(src) >= 100, f'源文章 {len(src)} 篇')
xc_src = {k: v for k, v in src.items() if '/xc-' in k}
check(len(xc_src) >= 30, f'其中行测 {len(xc_src)} 篇')

pages, pages_full = {}, {}
for f in glob.glob('public/[0-9]*/[0-9][0-9]/[0-9][0-9]/*/index.html'):   # 文章 URL 形如 /2026/09/22/<slug>/
    slug = norm(f).split('/')[-2]
    full = open(f, encoding='utf-8').read()
    pages_full[slug] = full                              # 整页：查 <title> 用这个
    pages[slug] = full.split('post-body', 1)[1]          # 只留正文：其余检查按正文判
check(len(pages) >= 30, f'构建出的行测以外页面 {len(pages)} 个（含按日期目录铺的全部文章页）')

src_slugs = {fm_slug(v) for v in xc_src.values()}
check(len(src_slugs) == len(xc_src), f'行测 slug 无重复：{len(src_slugs)}')
lost = sorted(s for s in src_slugs if s not in pages)
check(not lost, f'{len(src_slugs)} 篇行测都构建出了页面', str(lost[:5]))

# ---------- 1b. 分类：一级只能出现 工作 / 学习 / 生活；学习三层、生活两层 ----------

TOPS_OK = {'工作', '学习', '生活'}
tops = {}
bad_cat = []
for k, v in src.items():
    cats = fm_categories(v)
    # 学习下面走三层（模块 / 子分类），生活下面用户 2026-09-24 定的口径是两层（六项本身就是二级）
    if cats[0] not in TOPS_OK or len(cats) < 2 or len(cats) > 3 or (cats[0] == '学习' and len(cats) != 3):
        bad_cat.append(f'{norm(k)} -> {cats}')
    tops[cats[0]] = tops.get(cats[0], 0) + 1
check(not bad_cat, f'{len(src)} 篇分类合规（一级 ∈ 工作/学习/生活，学习三层、生活两层）', str(bad_cat[:3]))
check(tops.get('学习', 0) + tops.get('生活', 0) == len(src), f'文章都挂在「学习」或「生活」下：{tops}')
# 二、三级不能撞名（撞了分类页会混在一起，篇数对不上）
path_seen = {}
for k, v in src.items():
    key = ' / '.join(fm_categories(v))
    path_seen.setdefault(key, []).append(norm(k))
check(len(path_seen) >= 18, f'全站分类路径共 {len(path_seen)} 种', str(sorted(path_seen)[:4]))
for name in ('学习', '生活'):
    ok = os.path.isdir(os.path.join('public', 'categories', name))
    check(ok, f'一级分类页 /categories/{name}/ 构建出来了', '' if ok else '目录不在产物里')

# ---------- 2. 渲染残留 ----------

bodies = {s: pages[s] for s in src_slugs}
check(len(bodies) == len(src_slugs), '取到全部行测正文')
for cond, msg, bad in [
    (not [s for s, b in bodies.items() if '**' in b], '正文没有残留的 **', [s for s, b in bodies.items() if '**' in b]),
    (not [s for s, b in bodies.items() if 'assets/' in b], '正文没有残留的 assets/ 相对路径', [s for s, b in bodies.items() if 'assets/' in b]),
    (not [s for s, b in bodies.items() if len(re.sub(r'<[^>]+>', '', b).strip()) < 100], '没有近乎空白的文章页',
     [s for s, b in bodies.items() if len(re.sub(r'<[^>]+>', '', b).strip()) < 100]),
]:
    check(cond, msg, str(bad[:5]))

# ---------- 3. 图片：源里引用几张，产物里就得有几张 ----------

src_imgs = set()
for v in xc_src.values():
    src_imgs.update(re.findall(r'/images/xingce/[^)\s"]+', v))
page_imgs = set()
for b in bodies.values():
    page_imgs.update(re.findall(r'<img[^>]+src="(/images/xingce/[^"]+)"', b))
check(len(src_imgs) >= 50, f'行测源里引用图片 {len(src_imgs)} 张')
check(src_imgs == page_imgs, '页面里的图片集合与源完全一致', str(sorted(src_imgs ^ page_imgs)[:3]))
missing = [p for p in sorted(src_imgs) if not os.path.exists(os.path.join('public', *p.lstrip('/').split('/')))]
check(not missing, '引用的图片在构建产物里都存在', str(missing[:3]))
on_disk = glob.glob('public/images/xingce/*/*')
check(len(on_disk) == len(src_imgs), f'产物里的图片 {len(on_disk)} 张 = 源引用的 {len(src_imgs)} 张（没漏搬也没多搬）')
# 反过来：源 data 目录里没被引用的图不该进仓库
raw_imgs = glob.glob('data/xingce-raw/assets/*/*')
check(len(raw_imgs) > len(on_disk), f'母本图片 {len(raw_imgs)} 张，只把引用到的 {len(on_disk)} 张入库')

# ---------- 4. 题量：源里数一遍，页面里数一遍 ----------

src_ans = sum(len(re.findall(r'<strong>答案：([A-D])</strong>', v)) for v in xc_src.values())
src_q = sum(len(re.findall(r'^<strong>\d+\.[（(]', v, re.M)) for v in xc_src.values())
page_ans = {s: len(re.findall(r'答案：([A-D])', b)) for s, b in bodies.items()}
page_q = {s: len(re.findall(r'<strong>\d+\.[（(]', b)) for s, b in bodies.items()}
check(src_q == src_ans and src_q >= 400, f'行测源：{src_q} 道题、{src_ans} 个答案')
check(sum(page_ans.values()) == src_ans, f'页面里的答案合计 {sum(page_ans.values())} 处 = 源 {src_ans}')
mismatch = {s: (page_q[s], page_ans[s]) for s in bodies if page_q[s] != page_ans[s]}
check(not mismatch, '每篇页面题数与答案数相等', str(list(mismatch.items())[:3]))
bad_ans = [m for b in bodies.values() for m in re.findall(r'答案：([^<\s]{2,})', b) if not re.fullmatch(r'[A-D]', m)]
check(not bad_ans, '答案都是单个 A–D', str(bad_ans[:5]))

# ---------- 5. 分类页收全（分页合并后，每个分类的篇数 = 源里挂这个分类的篇数） ----------

catpages = {}
for root, dirs, fs in os.walk('public/categories'):
    if 'index.html' in fs:
        key = re.sub(r'/page/\d+$', '', norm(root).replace('public/categories', '(root)').strip('/'))
        catpages.setdefault(key, []).append(os.path.join(root, 'index.html'))
check(len(catpages) >= 15, f'发现 {len(catpages)} 个分类目录')

want = {}
for k, v in xc_src.items():
    for c in fm_categories(v):
        want[c] = want.get(c, 0) + 1
check(len(want) >= 5, f'源里的行测分类 {len(want)} 个', str(sorted(want)))
for name, n in sorted(want.items()):
    files = [p for key, ps in catpages.items() if key.split('/')[-1] == name for p in ps]
    if not files:
        check(False, f'分类页 {name} 存在', f'源里有 {n} 篇')
        continue
    links = set()
    for p in files:
        links.update(re.findall(r'href="[^"]*?/(xc-[a-z0-9-]+)/"', open(p, encoding='utf-8').read()))
    check(links == src_slugs if name == '行测' else len(links) == n,
          f'分类页 {name} 合起来 {len(links)} 篇', f'期望 {n}')

# ---------- 6. 归档页收全 + 死链 ----------

# 首页从 2026-09-23 起是 Bento 卡片（scripts/bento-home.js），不再逐篇铺文章流，
# 「文章翻得到翻不到」这件事改由归档页承担：翻遍 /archives/ 的分页，每篇都要出现一次。
idx = [open(f, encoding='utf-8').read() for f in glob.glob('public/index.html') + glob.glob('public/page/*/index.html')]
check(len(idx) >= len(src) // 10, f'首页 + 分页共 {len(idx)} 页（{len(src)} 篇文章）')
all_slugs = {fm_slug(v) or norm(k)[:-3].rsplit('/', 1)[1] for k, v in src.items()}
check(len(all_slugs) == len(src), f'全站 slug/文件名 {len(all_slugs)} 个，与文章数一致')
arch = [open(f, encoding='utf-8').read() for f in
        glob.glob('public/archives/index.html') + glob.glob('public/archives/page/*/index.html')]
check(len(arch) >= 2, f'归档页 + 分页共 {len(arch)} 页')
arch_joined = '\n'.join(arch)
lost_arch = [s for s in sorted(all_slugs) if f'/{s}/' not in arch_joined]
check(not lost_arch, f'{len(all_slugs)} 篇全都出现在归档页里', str(lost_arch[:5]))

dead = set()
for s, b in bodies.items():
    for href in re.findall(r'<a[^>]+href="(/[^"#]+)"', b):
        # 盘上是中文名，href 是百分号编码，两边要对齐再比
        p = os.path.join('public', *urllib.parse.unquote(href).lstrip('/').split('/'))
        if not (os.path.exists(p) or os.path.exists(p + '.html') or os.path.isdir(p)):
            dead.add(f'{s} -> {href}')
check(not dead, '行测文章内没有指向 404 的站内链接', str(sorted(dead)[:3]))

# ---------- 7. 素描教程：7 篇（6 大模块 + 总览）、30 课、SVG 示意图 ----------

sk_src = {norm(k)[len('source/_posts/素描教程/'):-3]: v for k, v in src.items() if '/素描教程/sk-' in k}
check(len(sk_src) == 7, f'素描源 {len(sk_src)} 篇', '期望 6 个阶段 + 1 篇总览')
sk_lost = sorted(s for s in sk_src if s not in pages)
check(not sk_lost, f'{len(sk_src)} 篇素描都构建出了页面', str(sk_lost[:5]))
sk_bodies = {s: pages[s] for s in sk_src if s in pages}
check(len(sk_bodies) == len(sk_src), '取到全部素描正文')

check(not [s for s, b in sk_bodies.items() if '**' in b], '素描正文没有残留的 **',
      str([s for s, b in sk_bodies.items() if '**' in b]))
check(not [s for s, b in sk_bodies.items() if re.search(r'src="images/', b)], '素描没有残留的相对图片路径',
      str([s for s, b in sk_bodies.items() if re.search(r'src="images/', b)][:3]))
thin = [s for s, b in sk_bodies.items() if len(re.sub(r'<[^>]+>', '', b).strip()) < 1500]
check(not thin, '素描每篇正文都不薄（合并 5~6 课，去掉标签后 ≥1500 字符）', str(thin))

# 课标题：源里 `## 06 课名` 的个数 == 页面里 <h2 的个数（总览那篇比 ^## ）。一个阶段一篇，
# 所以 H2 数就是这一篇装了几课——它掉了没人发现，必须两边数。
for s, v in sk_src.items():
    body_md = v.split('---\n', 2)[-1]
    want = len(re.findall(r'^## ', body_md, re.M))
    got = len(re.findall(r'<h2', sk_bodies.get(s, '')))
    check(want == got and want >= 1, f'{s}：{want} 个 H2 全部渲染成 <h2>', f'页面里 {got} 个')
check(sum(len(re.findall(r'^## \d\d ', v, re.M)) for s, v in sk_src.items() if s != 'sk-intro') == 30,
      '六个阶段篇合起来正好 30 课', str({s: len(re.findall(r'^## \d\d ', v, re.M)) for s, v in sk_src.items() if s != 'sk-intro'}))

sk_src_imgs = set()
for v in sk_src.values():
    sk_src_imgs.update(re.findall(r'/images/sketch/[^)\s"]+', v))
sk_page_imgs = set()
for b in sk_bodies.values():
    sk_page_imgs.update(re.findall(r'<img[^>]+src="(/images/sketch/[^"]+)"', b))
check(len(sk_src_imgs) >= 100, f'素描源里引用图片 {len(sk_src_imgs)} 张')
check(sk_src_imgs == sk_page_imgs, '素描页面里的图片集合与源一致', str(sorted(sk_src_imgs ^ sk_page_imgs)[:3]))
check(not [p for p in sk_src_imgs if not os.path.exists(os.path.join('public', *p.lstrip('/').split('/')))], '素描引用的图都在产物里')
sk_disk = glob.glob('public/images/sketch/*/*')
check(len(sk_disk) == len(sk_src_imgs), f'产物里的素描图 {len(sk_disk)} 张 = 引用的 {len(sk_src_imgs)} 张')
check(len(glob.glob('data/sketch-raw/course/images/*')) + len(glob.glob('data/sketch-raw/course/images/svg/*')) >= len(sk_disk) // 2,
      '母本图片目录取到了样本')

sk_cat = {}
for s, v in sk_src.items():
    for c in fm_categories(v):
        sk_cat.setdefault(c, []).append(s)
check(len(sk_cat) == 2, f'素描分类 {len(sk_cat)} 个（生活 + 素描，两级；三个大类已降到标签）', str(sorted(sk_cat)))
for name, slugs_ in sk_cat.items():
    # Hexo 把分类名 slug 化后才做目录：空格变成 `-`（页面标题里还是空格），所以两边要先归一
    dir_ = name.replace(' ', '-')
    files = [p for key, ps in catpages.items() if key.split('/')[-1] == dir_ for p in ps]
    links = set()
    for p in files:
        links.update(re.findall(r'href="[^"]*?/(sk-[a-z0-9-]+)/"', open(p, encoding='utf-8').read()))
    check(links == set(slugs_), f'分类页 {name} 收全 {len(slugs_)} 篇', f'实际 {sorted(links)[:3]}')

lost_idx = [s for s in sk_src if f'/{s}/' not in arch_joined]
check(not lost_idx, '每篇素描都在归档页里翻得到', str(lost_idx[:5]))
sk_dead = set()
for s, b in sk_bodies.items():
    for href in re.findall(r'<a[^>]+href="(/[^"#]+)"', b):
        p = os.path.join('public', *urllib.parse.unquote(href).lstrip('/').split('/'))
        if not (os.path.exists(p) or os.path.exists(p + '.html') or os.path.isdir(p)):
            sk_dead.add(f'{s} -> {href}')
check(not sk_dead, '素描文章内没有指向 404 的站内链接', str(sorted(sk_dead)[:3]))
html_dead = set()
for s, b in sk_bodies.items():
    for href in re.findall(r'href="([^"]+\.html)"', b):
        html_dead.add(f'{s} -> {href}')
check(not html_dead, '素描里没有残留的 .html 链接（母本是 HTML 课程，跨课引用要改成锚点）', str(sorted(html_dead)[:3]))

# ---------- 8. 课程总览页：30 个课链接必须真的落到目标页的标题上 ----------

mapf = 'public/sketch-map/index.html'
check(os.path.exists(mapf), '课程总览页构建出来了', mapf)
if os.path.exists(mapf):
    mh = open(mapf, encoding='utf-8').read().split('</h1>', 1)[-1]
    links = re.findall(r'<a[^>]+href="(/2026/09/23/(sk-stage\d)/#([^"]+))"', mh)
    check(len(links) == 30, f'总览页上 {len(links)} 个课链接', '应该是 30 课一格不少')
    check(len({(s, a) for _, s, a in links}) == len(links), '总览页没有重复的课', f'{len(links)} 个链接 / {len({(s, a) for _, s, a in links})} 种目标')
    target_ids = {}
    for s in {s for _, s, _ in links}:
        target_ids[s] = set(re.findall(r'<h[1-6][^>]*\bid="([^"]+)"', sk_bodies.get(s, '')))
    bad_anchor = [f'{s}#{a}' for _, s, a in links if urllib.parse.unquote(a) not in target_ids.get(s, set())]
    check(not bad_anchor, '总览页每个链接指的锚点都在目标页里存在', str(bad_anchor[:4]))
    stage_links = {s for _, s, _ in links}
    check(stage_links == {f'sk-stage{i}' for i in range(1, 7)}, '六个阶段都被总览页指向', str(sorted(stage_links)))

# ---------- 9. 前端改造：换皮 CSS / 首页 Bento / 行测答案折叠 ----------

css = open('public/css/main.css', encoding='utf-8').read()
for token, why in [('--radius-pill', '自定义 token 层进了产物'),
                   ('-apple-system', '系统字体栈覆盖生效'),
                   ('font-size: 1.0625em', '正文 17px 生效'),
                   ('.bento-card', '首页卡片样式在'),
                   ('details.answer', '答案折叠样式在'),
                   ('prefers-reduced-motion', '减少动效的兜底在')]:
    check(token in css, f'CSS：{why}', token)
# 自定义层必须排在主题自己那套之后，否则同优先级规则会输：主题的 .post-eof 有背景色，
# 我们那条只是 display:none，谁在后面谁说了算。
check(css.rindex('.post-eof') > css.index('.post-eof {'), 'CSS：自定义层在主题层之后（后写才赢）')
# 折叠写成显式的 display:none / [open] display:block：Chrome 默认用 ::details-content 的
# content-visibility 隐藏，盒子还在、老内核或不支持该伪元素时更会直接把答案画出来。
check(re.search(r'details\.answer\s*>\s*\.answer-body\s*\{\s*display:\s*none', css),
      'CSS：折叠是显式规则，不只信浏览器的默认隐藏')
check(re.search(r'details\.answer\[open\]\s*>\s*\.answer-body\s*\{\s*display:\s*block', css),
      'CSS：展开态把答案放回来')

home = open('public/index.html', encoding='utf-8').read()
body_home = home.split('main-inner', 1)[1]
check('post-block' not in body_home, '首页已经不再逐篇铺文章卡')
check('bento-lede' not in body_home and 'bento-cover' not in body_home,
      '首页没有「三个知识库」标题块，也没有素描范画卡')
cards_raw = ['<article class="bento-card' + c for c in body_home.split('<article class="bento-card')[1:]]
card_cls = [re.match(r'<article class="bento-card([^"]*)"', c).group(1) for c in cards_raw]
check(len([c for c in card_cls if 'heat' in c]) == 1, '首页 1 张热力图卡', str(card_cls))
check(len([c for c in card_cls if 'feed' in c]) == 1, '首页 1 张「最近更新」卡')
mod_raw = [c for c, k in zip(cards_raw, card_cls) if 'heat' not in k and 'feed' not in k]
mod_cls = [k for k in card_cls if 'heat' not in k and 'feed' not in k]
check(len(mod_raw) == 3, f'首页 {len(mod_raw)} 张模块卡', str(card_cls))
card_names = [re.search(r'<h3 class="bento-name">(?:<a href="[^"]*">)?([^<]+)', c).group(1) for c in mod_raw]
check(sorted(card_names) == sorted(['工作', '学习', '生活']), f'三张卡是 工作/学习/生活', str(card_names))
# 空模块也要在（占位卡），篇数为 0 的那些挂「还没有内容」
want_empty = sum(1 for n in ('工作', '生活') if not tops.get(n))
got_empty = [n for n, c in zip(card_names, mod_cls) if 'empty' in c]
check(len(got_empty) == want_empty, f'空模块占位卡 {len(got_empty)} 张', f'源里没文章的模块有 {want_empty} 个')

# 热力图：52 列 × 7 格，带悬停文本的格子 = 窗口内真正有发文的日期
heat_card = [c for c, k in zip(cards_raw, card_cls) if 'heat' in k][0]
# 只数网格里的格子：图例那 5 个小方块也是 .heat-cell，别混进来当数据格
heat_grid = heat_card.split('heat-cols', 1)[1].split('heat-foot', 1)[0]
heat_cols = len(re.findall(r'<div class="heat-col">', heat_grid))
heat_cells = len(re.findall(r'class="heat-cell', heat_grid))
check(heat_cols == 52, f'热力图 {heat_cols} 列（一列一周）', '应该 52 周')
check(heat_cells == 52 * 7, f'热力图 {heat_cells} 格', '应该 364 格 = 52 × 7')
titles = re.findall(r'<span class="heat-cell heat-l[1-4]" title="([^"]+)"', heat_grid)
check(len(titles) >= 1, f'有发文的格子 {len(titles)} 个，都带悬停文本', str(titles[:2]))
heat_days = {t.split(' · ')[0] for t in titles}
check(len(heat_days) == len(titles), '悬停文本里的日期不重复', f'{len(titles)} 格 / {len(heat_days)} 个日期')
check(all(re.fullmatch(r'\d{4}-\d\d-\d\d', d) for d in heat_days), '悬停文本以完整日期开头', str(sorted(heat_days)[:2]))
rng = re.search(r'<span class="heat-range">(\d{4}-\d\d-\d\d) → (\d{4}-\d\d-\d\d)</span>', body_home)
check(bool(rng), '热力图标了起止日期', rng.group(0) if rng else '')
if rng:
    src_dates = []
    for v in src.values():
        m = re.search(r'^date:\s*(\d{4}-\d\d-\d\d)', v, re.M)
        if m:
            src_dates.append(m.group(1))
    in_win = [d for d in src_dates if rng.group(1) <= d <= rng.group(2)]
    heat_sum = sum(int(m.group(1)) for m in re.finditer(r'·\s*(\d+) 篇', ' '.join(titles)))
    check(heat_sum == len(in_win), f'热力图格子里的篇数合计 {heat_sum} = 起止区间内的文章数 {len(in_win)}',
          f'{rng.group(1)} → {rng.group(2)}')
    check(len(heat_days) == len(set(in_win)), f'有格子的天数 {len(heat_days)} = 窗口内有发文的日期数 {len(set(in_win))}')

# 模块卡的篇数是从 source 现算的，两边必须一致
learn_card = dict(zip(card_names, mod_raw))['学习']
learn_kicker = re.search(r'<p class="bento-kicker">(.*?)</p>', learn_card).group(1)
check(f'{tops.get("学习", 0)} 篇' in learn_kicker, '学习卡的篇数 = 源里挂在学习下的文章数', f'{learn_kicker} vs {tops}')
kid_want = {}                                # 每个一级模块下的二级分类篇数（卡上的芯片就该是这个）
for v in src.values():
    cats = fm_categories(v)
    kids = kid_want.setdefault(cats[0], {})
    kids[cats[1]] = kids.get(cats[1], 0) + 1
kid_got = dict(re.findall(r'<a href="[^"]*">([^<]+)<span class="bento-count">(\d+)</span>', learn_card))
check({k: int(n) for k, n in kid_got.items()} == kid_want['学习'],
      f'学习卡上的子分类胶囊 = 源里 {len(kid_want["学习"])} 个模块的篇数', f'{kid_got} vs {kid_want["学习"]}')

# 首页上每个站内链接与封面图都要存在
home_dead = set()
for ref in re.findall(r'(?:href|src)="(/[^"#]+)"', body_home):
    p = os.path.join('public', *urllib.parse.unquote(ref).lstrip('/').split('/'))
    if not (os.path.exists(p) or os.path.isdir(p)):
        home_dead.add(ref)
check(not home_dead, '首页上的站内链接和图片都指向真实页面', str(sorted(home_dead)[:4]))

# 「最近更新」必须是全站按 date 最新的 6 篇
dated = []
for k, v in src.items():
    m = re.search(r'^date:\s*(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)', v, re.M)
    if m:
        dated.append((m.group(1), fm_slug(v) or norm(k)[:-3].rsplit('/', 1)[1]))
want6 = [s for _, s in sorted(dated, reverse=True)[:6]]
got6 = re.findall(r'<a class="bento-feed-title" href="/[0-9/]+/([a-z0-9-]+)/"', body_home)
check(len(got6) == 6, f'最近更新列出 {len(got6)} 条')
check(got6 == want6, '最近更新的 6 条 = 全站日期最新的 6 篇', f'{got6[:2]} vs {want6[:2]}')

# 第 2 页起落回主题原来的文章流，老分页链接不坏
p2 = 'public/page/2/index.html'
check(os.path.exists(p2) and 'post-block' in open(p2, encoding='utf-8').read(),
      '第 2 页仍是主题原来的文章列表（分页没坏）', p2)

# 答案折叠：渲染后的 DOM 里每道题一个 details，答案确实被包在块内而不是露在外面
fold_bad, fold_total = [], 0
for slug, html in pages.items():
    if not slug.startswith('xc-') or slug == 'xc-answer':
        continue
    src_text = next((v for k, v in xc_src.items() if fm_slug(v) == slug), None)
    if src_text is None:
        fold_bad.append(f'{slug} 找不到源文件')
        continue
    n_ans = len(re.findall(r'<strong>答案：', src_text))
    n_fold = len(re.findall(r'<details class="answer">', html))
    n_over = len(re.findall(r'<details class="answer answer-overview">', html))
    fold_total += n_fold
    if n_fold != n_ans:
        fold_bad.append(f'{slug} 折叠 {n_fold} != 答案 {n_ans}')
    if n_over != 1:
        fold_bad.append(f'{slug} 速览折叠 {n_over} != 1')
    # 每个折叠块里都得真的装着答案，summary 文案也要在
    for blk in re.findall(r'<div class="answer-body">(.*?)</div>', html, re.S):
        if '<strong>答案：' not in blk and 'DABAB' not in blk and '|' not in blk:
            fold_bad.append(f'{slug} 有个折叠块里没答案')
            break
    if '<summary>看答案</summary>' not in html:
        fold_bad.append(f'{slug} 没有「看答案」的 summary')
    # 块外的裸答案：正文里 <strong>答案： 的总数应该 == 折叠数
    if len(re.findall(r'<strong>答案：', html)) != n_ans:
        fold_bad.append(f'{slug} 渲染出的答案数 {len(re.findall(r"<strong>答案：", html))} != 源里 {n_ans}')
check(fold_total >= 500, f'行测折叠共 {fold_total} 块')
check(not fold_bad, '每道行测题的答案都折在 details 里、点击才露出来', str(fold_bad[:4]))

# ---------- 10. 生活六项：一项一个阶段一篇（18 篇），课数 / 图片 / 汉字全按母本 manifest 现算 ----------

import json

SH_TOPICS = {'riddle': '猜灯谜', 'baduanjin': '八段锦', 'sudoku': '数独',
             'xiangqi': '象棋', 'gomoku': '五子棋', 'calligraphy': '书法'}
CN_NUM = '一二三四五六'
esc = lambda t: (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('/', '&#x2F;'))


def manifest(tid):
    """读母本 course.manifest.js（它是课序/课名/阶段名的唯一事实来源）"""
    t = open(f'data/shenghuo-raw/{tid}/course.manifest.js', encoding='utf-8').read()
    m = re.search(r'module\.exports = (\{[\s\S]*\})\s*;\s*$', t)
    if not m:
        check(False, f'{tid} 的 manifest 读不出 module.exports')
        return None
    return json.loads(m.group(1))


def lesson_title(t):
    """与 import-shenghuo.mjs 一致：课名去掉母本里的「阶段X·NN 」前缀"""
    return re.sub(r'^阶段[一二三四五六]·\s*\d+\s*', '', t).strip()


def lesson_han(tid, l):
    """母本这一课的汉字数（去掉图片引用），用来判生成的页面有没有把内容写薄"""
    p = f"data/shenghuo-raw/{tid}/{l['n']}-{os.path.basename(l['file'])[:-5]}.md"
    t = open(p, encoding='utf-8').read()
    return len(re.findall(r'[一-鿿]', re.sub(r'!\[[^\]]*\]\([^)]*\)', '', t)))


# 期望的 18 篇一篇不差：slug、三级分类名、课号清单全部由 manifest 推出来，不写死
want = {}
for tid_, cn_ in SH_TOPICS.items():
    man_ = manifest(tid_)
    for si_, st_ in enumerate(man_['stages']):
        want[f'sh-{tid_}-{si_ + 1}'] = {'tid': tid_, 'cn': cn_, 'si': si_, 'cat3': st_['name'],
                                        'no': f'阶段{CN_NUM[si_]}', 'lessons': st_['lessons']}
check(len(want) == 18, f'manifest 推出 {len(want)} 篇（六项 × 各 3 阶段）')

sh_src = {fm_slug(v): v for k, v in src.items() if '/生活六项/' in k}
check(set(sh_src) == set(want), f'生活六项 {len(sh_src)} 篇，slug 与「项 + 阶段」一一对应',
      str(sorted(set(sh_src) ^ set(want))[:4]))
sh_pages = {s: pages[s] for s in sh_src if s in pages}
check(len(sh_pages) == len(sh_src), f'{len(sh_src)} 篇全都构建出了页面', str(sorted(set(sh_src) - set(sh_pages))))

sh_total_lessons = sum(len(w['lessons']) for w in want.values())
check(sh_total_lessons == 64, f'六套课合计 {sh_total_lessons} 课', '母本 manifest 应该是 64 课')
per_topic_imgs, sh_total_imgs = {}, 0
for slug, w in sorted(want.items()):
    tid, lessons, html = w['tid'], w['lessons'], sh_pages.get(slug, '')
    check(f'categories:\n  - "生活"\n  - "{w["cn"]}"\n  - "{w["cat3"]}"' in sh_src.get(slug, ''),
          f'{slug}：分类是三层 生活 / {w["cn"]} / {w["cat3"]}')
    check(f'<title>{esc(w["cn"] + w["no"] + " · " + w["cat3"])}' in pages_full.get(slug, ''),
          f'{slug}：页面标题是「{w["cn"]}{w["no"]} · {w["cat3"]}」')
    got_h2 = len(re.findall(r'<h2', html))
    check(got_h2 == len(lessons), f'{slug}：这一阶段 {len(lessons)} 课全部渲染成 <h2>', f'页面里 {got_h2} 个')
    lost_title = [l['n'] for l in lessons if f'>{l["n"]} {esc(lesson_title(l["title"]))}</h2>' not in html]
    check(not lost_title, f'{slug}：每课的标题都作为 H2 出现在页面上', f'缺课号 {lost_title[:4]}')
    # 同项另外两篇要能从这里跳过去（拆篇后靠这个横向链接串成一套课）
    for oi in range(3):
        if oi == w['si']:
            continue
        check(re.search(r'href="/[^"]*sh-%s-%d/"' % (tid, oi + 1), html) is not None,
              f'{slug}：开头有指向本篇 {tid} 第 {oi + 1} 阶段的链接')
    pre = f'/images/shenghuo/{tid}/'
    s_img = set(re.findall(re.escape(pre) + r'[^)\s"]+', sh_src.get(slug, '')))
    p_img = set(re.findall(r'<img[^>]+src="(' + re.escape(pre) + r'[^"]+)"', html))
    check(s_img == p_img, f'{slug}：页面里的图片集合与源一致（{len(s_img)} 张）', str(sorted(s_img ^ p_img)[:2]))
    per_topic_imgs.setdefault(tid, []).append(len(s_img))
    han = len(re.findall(r'[一-鿿]', re.sub(r'<[^>]+>', '', html)))
    exp_han = sum(lesson_han(tid, l) for l in lessons)
    check(han >= exp_han * 0.9, f'{slug}：页面正文 {han} 汉字 ≈ 母本这一阶段 {exp_han}', f'少了 {exp_han - han}')
    check(han > 5000, f'{slug}：页面正文够长（{han} 汉字）')
    sh_total_imgs += len(s_img)
check(sh_total_imgs == 499, f'六套课合计引用 {sh_total_imgs} 张示意图', '母本应该是 499 张')
for tid, cn in SH_TOPICS.items():
    pre = f'/images/shenghuo/{tid}/'
    disk = {pre + f for f in os.listdir(f'source/images/shenghuo/{tid}')}
    pub = {pre + f for f in os.listdir(f'public/images/shenghuo/{tid}')}
    raw = {pre + f for f in os.listdir(f'data/shenghuo-raw/{tid}/images/svg')}
    check(disk == pub == raw, f'{cn}：入库与产物里的图 == 母本 {len(raw)} 张 svg（一张不丢、一张不多）',
          f'入库 {len(disk)} / 产物 {len(pub)} / 母本 {len(raw)}')
    check(sum(per_topic_imgs[tid]) == len(raw),
          f'{cn}：三篇各自引用 {per_topic_imgs[tid]} 张，加起来 == 母本 {len(raw)} 张（阶段之间不重复、不漏）')
sh_dead = set()
for slug, html in sh_pages.items():
    for href in re.findall(r'<a[^>]+href="(/[^"#]+)"', html):
        p = os.path.join('public', *urllib.parse.unquote(href).lstrip('/').split('/'))
        if not (os.path.exists(p) or os.path.exists(p + '.html') or os.path.isdir(p)):
            sh_dead.add(f'{slug} -> {href}')
check(not sh_dead, '生活六项内没有指向 404 的站内链接', str(sorted(sh_dead)[:3]))
# 首页「生活」卡：六项各 3 篇 + 素描 7 篇，芯片和篇数要对得上
sh_card = next((c for c in mod_raw if '生活' in c), '')
kids_got = {k: int(n) for k, n in re.findall(r'<li><a href="[^"]*">([^<]+)<span class="bento-count">(\d+)</span></a></li>', sh_card)}
check(kids_got == kid_want.get('生活'), f'首页「生活」卡的子分类芯片 == 源里 {len(kid_want.get("生活", {}))} 个二级分类的篇数', str(kids_got))
check(set(kids_got) == set(SH_TOPICS.values()) | {'素描'}, '芯片名字 = 六项 + 素描', str(sorted(kids_got)))
check({k: v for k, v in kids_got.items() if k in SH_TOPICS.values()} == {cn: 3 for cn in SH_TOPICS.values()},
      '六项每项 3 篇（一阶段一篇）', str(kids_got))
check(f'bento-kicker">{tops.get("生活", 0)} 篇' in sh_card, f'首页「生活」卡显示 {tops.get("生活")} 篇')

print('\n%s' % ('全部通过' % () if not fail else f'{len(fail)} 项失败：' + '；'.join(fail)))
sys.stdout.flush()          # stdout 被我换成 TextIOWrapper 了，sys.exit 时不一定帮你刷管道
sys.exit(1 if fail else 0)
