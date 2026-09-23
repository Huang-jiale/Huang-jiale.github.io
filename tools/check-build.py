# -*- coding: utf-8 -*-
"""构建产物体检：拿 `source/_posts/` 对账 `public/`，任何一步采样为空也算失败。

跑法：`pnpm hexo clean && pnpm hexo generate && python tools/check-build.py`
期望值全部从 source 现算，所以导完新内容不用改这个脚本；它只管一件事：
**构建有没有把源里的东西弄丢/弄坏**（页面数、图片、题数==答案数、分类页收全、死链、渲染残留）。
每一步都先断言「确实取到了样本」，正则写错匹配到 0 个时一律判失败，不许假绿。

2026-09-23 人工核对过的量：74 时政 + 38 行测 + 7 素描 = 119 篇；行测 541 题、92 图；素描 30 课、159 图。
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

pages = {}
for f in glob.glob('public/[0-9]*/[0-9][0-9]/[0-9][0-9]/*/index.html'):   # 文章 URL 形如 /2026/09/22/<slug>/
    slug = norm(f).split('/')[-2]
    pages[slug] = open(f, encoding='utf-8').read().split('post-body', 1)[1]
check(len(pages) >= 30, f'构建出的行测以外页面 {len(pages)} 个（含按日期目录铺的全部文章页）')

src_slugs = {fm_slug(v) for v in xc_src.values()}
check(len(src_slugs) == len(xc_src), f'行测 slug 无重复：{len(src_slugs)}')
lost = sorted(s for s in src_slugs if s not in pages)
check(not lost, f'{len(src_slugs)} 篇行测都构建出了页面', str(lost[:5]))

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

# ---------- 6. 首页文章流与死链 ----------

idx = [open(f, encoding='utf-8').read() for f in glob.glob('public/index.html') + glob.glob('public/page/*/index.html')]
check(len(idx) >= len(src) // 10, f'首页 + 分页共 {len(idx)} 页（{len(src)} 篇文章）')
joined = '\n'.join(idx)
lost_idx = [s for s in src_slugs if f'/{s}/' not in joined]
check(not lost_idx, '每篇行测文章都进了首页文章流', str(lost_idx[:5]))

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
check(len(sk_cat) == 4, f'素描分类 {len(sk_cat)} 个（素描 + 3 个二级大类）', str(sorted(sk_cat)))
for name, slugs_ in sk_cat.items():
    # Hexo 把分类名 slug 化后才做目录：空格变成 `-`（页面标题里还是空格），所以两边要先归一
    dir_ = name.replace(' ', '-')
    files = [p for key, ps in catpages.items() if key.split('/')[-1] == dir_ for p in ps]
    links = set()
    for p in files:
        links.update(re.findall(r'href="[^"]*?/(sk-[a-z0-9-]+)/"', open(p, encoding='utf-8').read()))
    check(links == set(slugs_), f'分类页 {name} 收全 {len(slugs_)} 篇', f'实际 {sorted(links)[:3]}')

lost_idx = [s for s in sk_src if f'/{s}/' not in joined]
check(not lost_idx, '每篇素描都进了首页文章流', str(lost_idx[:5]))
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

print('\n%s' % ('全部通过' if not fail else f'{len(fail)} 项失败：' + '；'.join(fail)))
sys.stdout.flush()          # stdout 被我换成 TextIOWrapper 了，sys.exit 时不一定帮你刷管道
sys.exit(1 if fail else 0)
