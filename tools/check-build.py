# -*- coding: utf-8 -*-
"""构建产物体检：拿 `source/_posts/` 对账 `public/`，任何一步采样为空也算失败。

跑法：`pnpm hexo clean && pnpm hexo generate && python tools/check-build.py`
期望值全部从 source 现算，所以导完新内容不用改这个脚本；它只管一件事：
**构建有没有把源里的东西弄丢/弄坏**（页面数、图片、题数==答案数、分类页收全、死链、渲染残留）。
每一步都先断言「确实取到了样本」，正则写错匹配到 0 个时一律判失败，不许假绿。

2026-09-22 首导人工核对过的量：74 时政 + 38 行测 = 112 篇；行测 541 题、92 张图。
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
check(len(want) >= 12, f'源里的行测分类 {len(want)} 个', str(sorted(want)))
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

print('\n%s' % ('全部通过' if not fail else f'{len(fail)} 项失败：' + '；'.join(fail)))
sys.exit(1 if fail else 0)
