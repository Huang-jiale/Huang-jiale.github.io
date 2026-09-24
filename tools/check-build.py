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
import io, sys, os, re, glob, datetime
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

# ---------- 8. 素描课锚点：每课的标题都要能在页面上被 #锚点 定位到（课程总览页已删，锚点改在这里核） ----------

anchor_bad = []
norm_id = lambda x: re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]', '', x)   # Hexo 的 slugger 会丢掉标点和空白，比对前先归一
for s, v in sk_src.items():
    body_md = v.split('---\n', 2)[-1]
    ids = {norm_id(i) for i in re.findall(r'<h[1-6][^>]*\bid="([^"]+)"', sk_bodies.get(s, ''))}
    for line in body_md.splitlines():
        m = re.match(r'^## (\d\d) (.+)$', line)
        if m and norm_id(m.group(1) + m.group(2).strip()) not in ids:
            anchor_bad.append(f'{s}#{m.group(1)} {m.group(2)}')
check(not anchor_bad, '素描 30 课的标题锚点全部存在（侧栏目录、外部深链靠它）', str(anchor_bad[:4]))

check(not os.path.exists('public/sketch-map'), '课程总览页 /sketch-map/ 已删除（用户 2026-09-24）')
orphan = [s for s, b in pages.items() if 'sketch-map' in b] + \
         [f for f in glob.glob('public/index.html') + glob.glob('public/page/*/index.html') if 'sketch-map' in open(f, encoding='utf-8').read()]
check(not orphan, '没有任何页面还指向 /sketch-map/', str(orphan[:4]))

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

# GitHub 式日历：52 列 × 7 行，一格一天，周一在第一行。
# （2026-09-24 用户点名要回日历，撤了中间那版按月柱状图。它确实「96% 是空白」——
#   137 篇只落在 9 天里，因为导入是挑一天跑完的。这是数据的真实形状，不是 bug，
#   所以脚注老老实实写「一格一天」，空白留白，不靠换口径把图填满。）
heat_card = [c for c, k in zip(cards_raw, card_cls) if 'heat' in k][0]
heat_grid = heat_card.split('class="heat-grid"', 1)[1].split('heat-foot', 1)[0]
# 一行一个格子：class 里要么是 heat-l0..4（有日期的），要么是 is-future（还没到的）
cells = re.findall(r'<span class="heat-cell ([a-z0-9-]+)"(?: title="([^"]*)")?></span>', heat_grid)
check(len(cells) == 364, f'日历 {len(cells)} 格（应为 52 列 × 7 行 = 364）', str(len(cells)))

today = datetime.date.today()
# 末列是本周：本周一往前数 51 周 = 第一格
start = today - datetime.timedelta(days=today.weekday() + 51 * 7)
want_day = {}                                 # 篇数一律回到 source 的 front-matter 现算，不信生成脚本
for v in src.values():
    m = re.search(r'^date:\s*(\d{4}-\d\d-\d\d)', v, re.M)
    if m:
        want_day[m.group(1)] = want_day.get(m.group(1), 0) + 1

peak = max(want_day.values())
bad_seq, bad_count, bad_level, bad_tip = [], [], [], []
for i, (cls, tip) in enumerate(cells):
    day = (start + datetime.timedelta(days=i)).isoformat()
    if day > today.isoformat():               # 还没到的日子：只留白，不标篇数
        if cls != 'is-future' or tip:
            bad_seq.append((i, day, cls, tip))
        continue
    lvl = cls[7:]
    n = want_day.get(day, 0)
    if cls != f'heat-l{n and min(4, -(-n * 4 // peak))}':
        bad_level.append((day, cls, n))
    # 悬停必须报日期（用户原话：鼠标放上去有显示日期），有内容的日子再报篇数和模块
    if not tip.startswith(f'{day} · {n} 篇'):
        bad_tip.append((day, tip))
    if n and f'· {n} 篇' not in tip:
        bad_count.append((day, n, tip))
check(not bad_seq, f'{len(cells)} 格逐日连续，从 {start.isoformat()} 那周的周一排到今天之后', str(bad_seq[:3]))
check(not bad_count, '每格的 tooltip 报出了那天的篇数', str(bad_count[:3]))
check(not bad_level, f'色阶按「单日最多 {peak} 篇」四等分（空格子=l0）', str(bad_level[:3]))
check(not bad_tip, 'tooltip 一律以「日期 · N 篇」开头，没内容的那天也标日期', str(bad_tip[:3]))

got_days = {}
for _, t in cells:
    if t:
        got_days[t.split(' · ')[0]] = int(re.search(r'· (\d+) 篇', t).group(1))
check({k: v for k, v in got_days.items() if v} == want_day,
      f'tooltip 里的 {len(want_day)} 个有内容的日子（及其篇数）= 源里的发文日',
      str(sorted(set(k for k, v in got_days.items() if v) ^ set(want_day))[:3]))
check(len(got_days) == 51 * 7 + today.weekday() + 1, f'带日期的格子 {len(got_days)} 格 = 起点到今天，剩下 {364 - len(got_days)} 格是本周还没到的那几天', '')
check(heat_grid.count('heat-l4') == sum(1 for n in want_day.values() if min(4, -(-n * 4 // peak)) == 4),
      '最深那一档的格子数和「达到峰值档」的天数一致', str(heat_grid.count('heat-l4')))

# 月首标签：贴在自己那一列的头上，两枚之间至少隔两周，不然会叠字
marks = [(int(c) - 1, lab) for c, lab in
         re.findall(r'<span class="heat-month" style="grid-column: (\d+)">([^<]+)</span>', heat_card)]
check(bool(marks), f'日历上方 {len(marks)} 个月首标签', '')
check(all(b[0] - a[0] >= 2 for a, b in zip(marks, marks[1:])), '月首标签不重叠（相邻至少隔 2 列）', str(marks))
for col, lab in marks:
    d = start + datetime.timedelta(days=col * 7)
    check(lab == f'{d.month}月', f'第 {col + 1} 列的标签 {lab} = 那一列周一起始的月份', d.isoformat())

check(heat_card.split('heat-foot', 1)[1].count('heat-cell') == 5, '图例五档（少 → 多）在脚注里', '')

kicker_heat = re.search(r'<p class="bento-kicker">(.*?)</p>', heat_card).group(1)
check(kicker_heat == f'近 52 周入库 {sum(want_day.values())} 篇 · 有内容 {len(want_day)} 天 · 单日最多 {peak} 篇',
      '卡顶文案 = 格子上那些数现算出来的合计', kicker_heat)
rng = re.search(r'<span class="heat-range">(\d{4}-\d\d-\d\d) → (\d{4}-\d\d-\d\d)，一格一天，周一起排</span>', body_home)
check(bool(rng) and rng.group(1) == start.isoformat() and rng.group(2) == today.isoformat(),
      '脚注标了统计区间（起止日 + 一格一天）', rng.group(0) if rng else '')
check('class="months"' not in heat_card and 'month-col' not in heat_card,
      '上一版的 12 根月度柱子已经拆干净', '')

# 日历的 CSS：五档颜色 + 横向滚 + 竖着填的网格，浅色深色各一套 token
for token, why in [('--heat-0', '日历空格那档'), ('--heat-3', '日历第四档'),
                   ('--heat-future', '还没到的那几天'), ('repeat(52, minmax(11px, 1fr))', '52 列网格')]:
    check(css.count(token) >= 1, f'CSS：{why}进了产物', token)
check(css.count('--heat-0:') == 2 and css.count('--heat-future:') == 2,
      '日历色阶在浅色/深色两套 token 里都有（深色不是照搬浅色）', str(css.count('--heat-0:')))
check(re.search(r'\.heat-grid\s*\{[^}]*grid-auto-flow:\s*column', css),
      'CSS：网格是竖着填的（模板按周输出，一列才是一周）')
check(re.search(r'\.heat-scroll\s*\{[^}]*overflow-x:\s*auto', css), 'CSS：窄屏靠横向滚动，不压扁格子')

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

# ---------- 11. 阅读体验：侧栏目录折叠 / 顶部进度条 / 标题下的字数与预计读完时间 ----------

TF = 'public/js/toc-fold.js'
check(os.path.exists(TF), '目录折叠脚本发到了 /js/toc-fold.js（bodyEnd 钩子挂的 tools/toc-fold.njk）')
tj = open(TF, encoding='utf-8').read() if os.path.exists(TF) else ''
check('.toc-parent' in tj and 'scrollHeight' in tj, '折叠脚本确实是加 .toc-open、按真实内容高度展开')

# 主题的折叠靠 .active > .nav-child（滚到哪个课就自己撑开哪个），_config.next.yml 里
# toc.expand_all: true 就是为把它整块关掉 —— 没关掉的话两套折叠会互相打架
check('.active > .nav-child' not in css, 'CSS：主题那套「滚动时自动撑开」的折叠没有输出')
check(re.search(r'\.post-toc \.nav \.nav-child \{[^}]*height: 0', css), 'CSS：课内小标题默认折叠（高度 0）')
check(re.search(r'\.post-toc \.nav \.toc-open > \.nav-child \{[^}]*height: var\(--height, auto\)', css),
      'CSS：只有 JS 加上 .toc-open 的那一课才展开')
check(re.search(r'\.post-toc \.nav \.nav-item \{[^}]*white-space: normal', css),
      'CSS：目录长标题换行，不是 nowrap + 省略号')
check(re.search(r'\.reading-progress-bar \{[^}]*var\(--accent\)', css), 'CSS：进度条颜色跟着 --accent（深色模式换浅蓝）')
# 主题把 .reading-progress-bar 输出在**所有**页面（首页/分类/归档也有一条），
# 那条线在非文章页滚起来毫无意义，所以默认收掉、只有 .main-inner.post 的页面放回来。
# DOM 不删：主题的 utils.js 滚动时要给它写 --progress，找不到元素会报错。
check(re.search(r'\.reading-progress-bar \{[^}]*display: none', css), 'CSS：进度条默认不画')
check(re.search(r'body:has\(\.main-inner\.post\) \.reading-progress-bar \{[^}]*display: block', css),
      'CSS：只有文章页把进度条放回来')
nobar = sorted(s for s, h in pages_full.items() if '<div class="reading-progress-bar">' not in h)
check(not nobar, f'{len(pages_full)} 篇文章页顶部都有进度条那一格（DOM 还在，靠 CSS 决定画不画）', str(nobar[:3]))

# 哪些篇该有折叠：源正文里有 h3 小标题的（toc.max_depth: 3，h4 及以下不进目录）
h3_slugs = {(fm_slug(v) or norm(k)[:-3].rsplit('/', 1)[1]) for k, v in src.items() if re.search(r'^### ', v, re.M)}
fold_pages = {s for s, h in pages_full.items() if 'nav-level-3' in h}
check(fold_pages == h3_slugs & set(pages_full),
      f'{len(fold_pages)} 篇文章的目录里有课内小标题（折叠就是给这些用的）',
      f'源里有 h3 的 {len(h3_slugs)} 篇 / 产物有第三层的 {len(fold_pages)} 篇 / 差集 {sorted(h3_slugs ^ fold_pages)[:3]}')
nojs = sorted(s for s in fold_pages if '/js/toc-fold.js' not in pages_full[s])
check(not nojs, '带小标题的文章页全都挂了折叠脚本', str(nojs[:3]))

# 字数与时长：脚本自己算的那个数，必须在 python 这边拿产物正文再算一遍对得上。
# 两边规则一模一样：剥标签、吃掉 HTML 实体，汉字/假名/谚文各 1 字，一串英文或数字算 1 词。
TAG_RE = re.compile(r'<[^>]*>')
ENT_RE = re.compile(r'&[#A-Za-z0-9]{1,8};')
CJK_RE = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]')
WORD_RE = re.compile(r'[A-Za-z0-9]+')


def body_chars(html):
    # 从 post-body 的 > 之后开始数：从 itemprop= 那里切，残留的 itemprop / articleBody
    # 会被英文词正则各数成一个「字」，整站 137 篇正好每篇虚高 2，把误差全盖掉了。
    i = html.index('>', html.index('itemprop="articleBody"')) + 1
    j = html.index('<footer class="post-footer"', i)      # 只数正文：页脚的分类、标签、上下篇不算
    t = ENT_RE.sub(' ', TAG_RE.sub(' ', html[i:j]))
    return len(CJK_RE.findall(t)) + len(WORD_RE.findall(t))


def want_readtime(chars):
    minutes = max(1, int(chars / 400 + 0.5))              # JS 的 Math.round 是四舍五入，不是银行家舍入
    if minutes < 60:
        span = f'约 {minutes} 分钟读完'
    else:
        h, m = divmod(minutes, 60)
        span = f'约 {h} 小时 {m} 分钟读完' if m else f'约 {h} 小时读完'
    return f'{chars:,} 字 · {span}'


rt_bad = []
for slug, full in sorted(pages_full.items()):
    got = re.search(r'<span class="post-meta-item post-readtime"[^>]*>.*?<span>([^<]+)</span>', full, re.S)
    if not got:
        rt_bad.append(f'{slug} 标题下没有字数行')
        continue
    want = want_readtime(body_chars(full))
    if got.group(1).strip() != want:
        rt_bad.append(f'{slug} 页面上写「{got.group(1).strip()}」，正文现算是「{want}」')
check(len(pages_full) >= 100, f'{len(pages_full)} 篇文章页参与字数核对')
check(not rt_bad, '标题下的字数/时长 == 拿产物正文现算的值（没数进 markdown 噪声，也没漏内容）', str(rt_bad[:3]))
check(any('小时' in want_readtime(body_chars(h)) for h in pages_full.values()),
      '最长的那几篇显示成「约 N 小时」，不是一串几百分钟')

# ---------- 12. 侧栏「本模块文章」/ 文章页瘦身 / 一键到顶 ----------

# 每篇属于哪个模块（分类第二层）、那个模块一共几篇，全部从 source 现算
mod_of = {}
for k, v in src.items():
    slug = fm_slug(v) or norm(k)[:-3].rsplit('/', 1)[1]
    mod_of[slug] = fm_categories(v)
mod_want = {}
for cats in mod_of.values():
    if len(cats) > 1:
        mod_want[cats[1]] = mod_want.get(cats[1], 0) + 1

SM = 'public/js/sidebar-module.js'
check(os.path.exists(SM), '侧栏脚本发到了 /js/sidebar-module.js（bodyEnd 钩子挂的 tools/toc-fold.njk）')
sj = open(SM, encoding='utf-8').read() if os.path.exists(SM) else ''
check('.module-nav' in sj and '本模块文章' in sj and 'is-open' in sj,
      '脚本干的活：有 .module-nav 才改格子标签 + 分组一次只开一组')

check(re.search(r'\.site-overview-wrap:has\(\.module-nav\)\s*>\s*:not\(\.module-nav\)\s*\{[^}]*display: none', css),
      'CSS：文章页把主题的站点概览（作者/统计/GitHub 链接）整块让位')
check(re.search(r'\.module-nav \.module-nav-list \{[^}]*height: 0', css), 'CSS：分组列表默认收起')
check(re.search(r'\.module-nav \.is-open > \.module-nav-list \{[^}]*height: var\(--height\)', css),
      'CSS：只有 JS/服务端标了 .is-open 的那一组展开')
check(re.search(r'\.module-nav > \.module-nav-list \{[^}]*height: auto', css),
      'CSS：没有第三层分类的模块（素描）列表平铺，不会被折叠规则吃掉')
check(re.search(r'\.module-nav \.module-nav-list \.is-current > a \{[^}]*var\(--accent\)', css),
      'CSS：当前这篇有强调色 + 竖线，不靠分割线')
check(re.search(r'\.back-to-top \{[^}]*left: auto[^}]*right: 30px', css), 'CSS：一键到顶在右下角（原来压在左侧栏上）')
check(css.rindex('.back-to-top i.fa') > css.index('.back-to-top .fa'), 'CSS：箭头尺寸的覆写排在主题规则之后')
# 主题的居中靠「图标宽度 = 老按钮宽度 26px + text-align:center」。按钮放大到 42px 后那 26px
# 就偏左了（上一版就是这么坏的：字形盒量出来在按钮里偏左 15px），居中交给 flex 管。
check(re.search(r'\.back-to-top \{[^}]*justify-content: center', css), 'CSS：箭头靠 justify-content 居中')
check(re.search(r'\.back-to-top i\.fa \{[^}]*width: auto', css), 'CSS：主题那 26px 的图标宽度已经交还')

nav_bad, meta_bad = [], []
for slug, full in sorted(pages_full.items()):
    cats = mod_of.get(slug) or []
    if len(cats) < 2:
        nav_bad.append(f'{slug} 源里分类不足两层，侧栏没得可列')
        continue
    mod, grp = cats[1], (cats[2] if len(cats) > 2 else '')
    total = mod_want[mod]
    i = full.find('<nav class="module-nav"')
    if i < 0:
        nav_bad.append(f'{slug} 侧栏没有 .module-nav')
        continue
    seg = full[i:full.find('</nav>', i) + 6]
    name = re.search(r'<a class="module-nav-title" href="([^"]*)">([^<]*)</a>', seg)
    count = re.search(r'class="module-nav-count">([^<]*)</span>', seg)
    items = re.findall(r'<li([^>]*)>\s*<a href="([^"]*)">([^<]*)</a>', seg)
    cur = [u for a, u, t in items if 'is-current' in a]
    secs = re.findall(r'<div class="module-nav-sec( is-open)?">\s*<button[^>]*>\s*<span>([^<]*)</span>', seg)
    grouped = total > 6 and bool(grp)
    open_secs = [c[1] for c in secs if c[0]]
    if not name or name.group(2) != mod:
        nav_bad.append(f'{slug} 栏目标题不是模块名 {mod}：{name.group(2) if name else None}')
    elif count.group(1) != f'{total} 篇':
        nav_bad.append(f'{slug} 「{mod}」标了 {count.group(1)}，源里是 {total} 篇')
    elif len(items) != total:
        nav_bad.append(f'{slug} 列了 {len(items)} 篇，源里 {mod} 有 {total} 篇')
    elif len(cur) != 1 or not cur[0].endswith(f'/{slug}/'):
        nav_bad.append(f'{slug} 当前篇高亮不对：{cur}')
    elif bool(secs) != grouped or (grouped and (len(open_secs) != 1 or open_secs[0] != grp)):
        nav_bad.append(f'{slug} 分组不对：该分组={grouped}，实际 {len(secs)} 组，开着的 {open_secs}')
    elif [t.strip() for a, u, t in items if 'is-current' in a][0] != re.search(r'<h1 class="post-title"[^>]*>([^<]*)</h1>', full).group(1).strip():
        nav_bad.append(f'{slug} 高亮那条的文字跟本页标题不一致')

    # 标题下面那一行只留字数/时长；日期、分类面包屑都不要再出现
    m = re.search(r'<div class="post-meta">(.*?)</div>', full, re.S)
    if not m:
        meta_bad.append(f'{slug} 找不到 .post-meta')
        continue
    line = m.group(1)
    # `post-meta-item-icon` 里也含 "post-meta-item"，所以只认后面紧跟空格或引号的那个类
    n_items = len(re.findall(r'class="post-meta-item[\s"]', line))
    if n_items != 1 or 'post-readtime' not in line:
        meta_bad.append(f'{slug} 标题下不止字数行：{n_items} 项')
    elif '<time' in line or 'fa-folder' in line:
        meta_bad.append(f'{slug} 标题下还有日期或分类')
    if 'class="post-tags"' not in full:
        meta_bad.append(f'{slug} 底部的标签被误删了（用户要保留）')
    if 'powered-by' in full:
        meta_bad.append(f'{slug} 页脚还有「由 Hexo 强力驱动」')

check(len(mod_of) >= 100 and mod_want, f'模块篇数表算出来了：{len(mod_want)} 个模块 / {sum(mod_want.values())} 篇')
check(not nav_bad, f'{len(pages_full)} 篇文章页的侧栏都列全本模块的兄弟篇', str(nav_bad[:3]))
check(not meta_bad, '标题下只剩字数行：日期 / 分类面包屑 / 页脚驱动信息都没了，底部标签留着', str(meta_bad[:3]))

# 首页 / 分类页 / 归档页没有 .module-nav，那一栏还是主题的站点概览
static_pages = ['public/index.html', 'public/categories/index.html', 'public/archives/index.html', 'public/tags/index.html']
left = [p for p in static_pages if not os.path.exists(p)]
check(not left, '对照用的静态页都在', str(left))
keep = [p for p in static_pages if os.path.exists(p) and ('module-nav' in open(p, encoding='utf-8').read()
                                                          or 'site-author-name' not in open(p, encoding='utf-8').read())]
check(not keep, '首页/分类/归档/标签页仍是「站点概览」，没被文章页的规则波及', str(keep))

b2t = sorted(s for s, h in pages_full.items() if '<div class="back-to-top"' not in h)
check(not b2t, f'{len(pages_full)} 篇文章页都挂了「一键到顶」那颗按钮', str(b2t[:3]))

# ---------- 13. 分类页树状图（总览 + 每个分类点进去那一页） ----------

# 整棵树从 source 现算：节点顺序 = 分类链第一次出现的顺序（文章按 date 升序排），
# 篇数是「含全部子孙」的那个数。和 scripts/cat-tree.js 用的是同一套口径，各算各的才对得上。
def cat_date(text):
    m = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?)', text, re.M)
    return (m.group(1).replace('T', ' ') if m else '9999')


def src_tree():
    order, counts = [], {}
    for k, v in sorted(src.items(), key=lambda kv: cat_date(kv[1])):
        cats = fm_categories(v)
        for i in range(1, len(cats) + 1):
            p = tuple(cats[:i])
            if p not in counts:
                counts[p] = 0
                order.append(p)
            counts[p] += 1
    return order, counts


tree_order, tree_counts = src_tree()
children_of = {}
for p in tree_order:
    if len(p) > 1:
        children_of.setdefault(p[:-1], []).append(p)


def cat_href(path):
    return '/categories/' + '/'.join(urllib.parse.quote(n.replace(' ', '-')) for n in path) + '/'


def rows_of(html):
    """把页面上的一行行节点读成 [(深度, 是否收尾, 有没有竖线穿过, 层级样式, href, 文字, 篇数)]"""
    out = []
    for chunk in html.split('<div class="cat-row ')[1:]:
        chunk = chunk[:chunk.index('</div>')] if '</div>' in chunk else chunk
        depth = int(re.match(r'cat-row--l(\d)', chunk).group(1))
        head = chunk.split('<a ', 1)[0] + chunk.split('<h1 ', 1)[0]
        m = re.search(r'class="cat-node cat-node--([a-z]+)"(?: href="([^"]*)")?>([^<]*)<span class="cat-num">(\d+)</span>',
                      chunk)
        if not m:      # 面包屑那几行没有篇数
            m = re.search(r'class="cat-node cat-node--([a-z]+)" href="([^"]*)">([^<]*)</a>', chunk)
            out.append((depth, 'is-tail' in head, 'cat-rail' in head, m.group(1), m.group(2), m.group(3), None))
            continue
        out.append((depth, 'is-tail' in head, 'cat-rail' in head, m.group(1), m.group(2), m.group(3).strip(),
                    int(m.group(4))))
    return out


# 13a. 总览页：/categories/ 应该是整棵树，主题原来那个平铺的 .category-all-page 不该再出现
all_html = open('public/categories/index.html', encoding='utf-8').read()
body_all = all_html[all_html.index('cat-cards'):]
check('category-all' not in all_html and 'cat-cards' in all_html,
      '总览页换成树了（主题的平铺分类列表已经不走）')
got = rows_of(body_all[:body_all.index('</main>')])
want = []
for root in [p for p in tree_order if len(p) == 1]:
    kids = children_of.get(root, [])
    want.append((0, False, False, 'top', cat_href(root), root[-1], tree_counts[root]))
    for mod in kids:
        mod_kids = children_of.get(mod, [])
        want.append((1, mod == kids[-1], False, 'mod', cat_href(mod), mod[-1], tree_counts[mod]))
        for leaf in mod_kids:
            want.append((2, leaf == mod_kids[-1], mod != kids[-1], 'leaf', cat_href(leaf), leaf[-1], tree_counts[leaf]))
check(len(got) == len(want) == len(tree_order), f'总览页 {len(got)} 行 = 源里的 {len(tree_order)} 个分类', f'产物 {len(got)}')
check(got == want, '每一行的层级/顺序/篇数/链接/折线收尾都和源里的树对得上',
      str([(a, b) for a, b in zip(got, want) if a != b][:3]))
check(sum(1 for r in got if r[2]) == sum(len(children_of.get(m, [])) for top in [p for p in tree_order if len(p) == 1]
                                        for m in children_of.get(top, [])[:-1]),
      '竖线穿过的只有「上面还有兄弟的模块」那些子孙行', str(sum(1 for r in got if r[2])))
cards = len(re.findall(r'<section class="cat-card"', body_all))
check(cards == len([p for p in tree_order if len(p) == 1]), f'总览页 {cards} 张卡 = 一级模块数')
lede = re.search(r'<p class="cat-lede">.*?class="cat-lede-strong">([^<]+)<', all_html, re.S).group(1)
check(lede == f'{len(src)} 篇 · {len(tree_order)} 个分类', '卡顶那行统计 = 现算的篇数和分类数', lede)

# 13b. 每个分类点进去的那一页：路径一行、本页一行（<h1>）、子分类各一行
bad_cat_page = []
for path in tree_order:
    f = os.path.join('public', *['categories', *[n.replace(' ', '-') for n in path]], 'index.html')
    if not os.path.exists(f):
        bad_cat_page.append(f'{"/".join(path)} 页面不在产物里')
        continue
    html = open(f, encoding='utf-8').read()
    seg = html[html.index('cat-card--here'):]
    seg = seg[:seg.index('</main>')]
    rows = rows_of(seg)
    exp = [(i, True, False, 'crumb', cat_href(path[:i + 1]), path[i], None) for i in range(len(path) - 1)]
    kids = children_of.get(path, [])
    exp.append((len(path) - 1, True, False, 'here', None, path[-1], tree_counts[path]))
    exp += [(len(path), k == kids[-1], False, 'leaf', cat_href(k), k[-1], tree_counts[k]) for k in kids]
    if rows != exp:
        bad_cat_page.append(f'{"/".join(path)}: {[(a, b) for a, b in zip(rows, exp) if a != b][:2]}')
    if '<time' in seg or 'collection-year' in seg:
        bad_cat_page.append(f'{"/".join(path)}: 列表里还有日期')
    if 'class="post-title-link"' in seg:
        bad_cat_page.append(f'{"/".join(path)}: 还在用主题的 posts-collapse 那套')
check(len(tree_order) >= 30, f'{len(tree_order)} 个分类页都要核对')
check(not bad_cat_page, '每个分类页的树（路径 + 本页 + 子分类）都对，且列表不带日期', str(bad_cat_page[:3]))

# 13c. 文章列表：翻页合起来要收全该分类的篇，顺序按 date 升序（_config.yml 的 category_generator）
src_by_path = {}
for k, v in src.items():
    cats = fm_categories(v)
    for i in range(1, len(cats) + 1):
        src_by_path.setdefault(tuple(cats[:i]), []).append((cat_date(v), fm_slug(v) or norm(k)[:-3].rsplit('/', 1)[1]))
order_bad = []
for path in [p for p in tree_order if len(children_of.get(p, [])) == 0]:
    files = sorted(glob.glob(os.path.join('public', *['categories', *[n.replace(' ', '-') for n in path]],
                                          'index.html')) +
                   sorted(glob.glob(os.path.join('public', *['categories', *[n.replace(' ', '-') for n in path]],
                                                 'page', '*', 'index.html'))))
    listed = []
    for fp in files:
        h = open(fp, encoding='utf-8').read()
        listed += re.findall(r'<ul class="cat-posts">(.*?)</ul>', h, re.S)[0:1]
    slugs = [s for blk in listed for s in re.findall(r'href="[^"]*?/([a-z0-9][a-z0-9-]+)/"', blk)]
    want_slugs = [s for _, s in sorted(src_by_path[path])]
    if sorted(slugs) != sorted(want_slugs):
        order_bad.append(f'{"/".join(path)} 少了/多了 {sorted(set(slugs) ^ set(want_slugs))[:3]}')
    elif slugs != want_slugs:
        order_bad.append(f'{"/".join(path)} 第一页不是按导入顺序排：{slugs[:3]} vs {want_slugs[:3]}')
check(len(order_bad) == 0, f'{len([p for p in tree_order if not children_of.get(p, [])])} 个叶子分类页：文章收全且按升序排',
      str(order_bad[:3]))

# 13d. 分类页里的站内链接不能指到 404
dead_cat = set()
for path in tree_order:
    f = os.path.join('public', *['categories', *[n.replace(' ', '-') for n in path]], 'index.html')
    for href in set(re.findall(r'href="(/[^"#]+)"', open(f, encoding='utf-8').read())):
        p = os.path.join('public', *urllib.parse.unquote(href).lstrip('/').split('/'))
        if not (os.path.exists(p) or os.path.exists(p + '.html') or os.path.isdir(p)):
            dead_cat.add(f'{"/".join(path)} -> {href}')
check(not dead_cat, '分类页上的链接没有 404', str(sorted(dead_cat)[:3]))

for token, why in [('.cat-row--l2::before {\n  left: 33px;', '第三层的折线在自己的那一竖上'),
                   ('.cat-row.is-tail::after {\n  content: none;', '组里最后一个节点不再往下接线'),
                   ('.cat-rail {', '祖先的竖线穿过子孙子行'),
                   ('.cat-node--here', '本页那个节点是 <h1> 长成的胶囊')]:
    check(token in css, f'CSS：{why}', token[:28])

print('\n%s' % ('全部通过' % () if not fail else f'{len(fail)} 项失败：' + '；'.join(fail)))
sys.stdout.flush()          # stdout 被我换成 TextIOWrapper 了，sys.exit 时不一定帮你刷管道
sys.exit(1 if fail else 0)
