# -*- coding: utf-8 -*-
"""构建产物体检：只看 public/，任何一步采样为空也算失败。

跑法：`pnpm hexo generate && python tools/check-build.py`
期望值（文章数/图片数/题量）写死在下面，导完新内容记得同步；
它们的意义是「探针确实取到了样本」，取到 0 条时一律判失败，不许绿灯放过。
"""
import io, sys, os, re, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.parse

fail = []


def check(cond, msg, detail=''):
    print(('OK   ' if cond else 'FAIL ') + msg + (f'  {detail}' if detail else ''))
    if not cond:
        fail.append(msg)


def norm(p):
    return p.replace('\\', '/')


# 1. 文章页样本非空
posts = [p for p in glob.glob('source/_posts/**/*.md', recursive=True)]
xc_src = [p for p in posts if '/xc-' in norm(p)]
pages = sorted(glob.glob('public/2026/09/22/xc-*/index.html'))
check(len(posts) == 106, f'文章总数 {len(posts)}', '期望 74 时政 + 32 行测')
check(len(xc_src) == 32 and len(pages) == 32, f'行测文章源 {len(xc_src)} 篇，构建出 {len(pages)} 个页面')

bodies = {}
for f in pages:
    slug = norm(f).split('/22/')[1].split('/')[0]
    bodies[slug] = open(f, encoding='utf-8').read().split('post-body', 1)[1]
check(len(bodies) == 32, '成功读到 32 篇正文')

# 2. 渲染残留
star = [s for s, b in bodies.items() if '**' in b]
check(not star, '正文没有残留的 **', str(star[:5]))
assets = [s for s, b in bodies.items() if 'assets/' in b]
check(not assets, '正文没有残留的 assets/ 相对路径', str(assets[:5]))
empty = [s for s, b in bodies.items() if len(re.sub(r'<[^>]+>', '', b).strip()) < 100]
check(not empty, '没有近乎空白的文章页', str(empty[:5]))

# 3. 图片全部落盘
imgs = set()
for b in bodies.values():
    imgs.update(re.findall(r'<img[^>]+src="(/images/xingce/[^"]+)"', b))
missing = [p for p in sorted(imgs) if not os.path.exists(os.path.join('public', *p.lstrip('/').split('/')))]
check(len(imgs) == 84, f'正文引用图片 {len(imgs)} 张（去重）')
check(not missing, '引用的图片在构建产物里都存在', str(missing[:3]))
on_disk = glob.glob('public/images/xingce/*/*')
check(len(on_disk) == 84, f'构建产物里实际有 {len(on_disk)} 张图片')

# 4. 题量对得上母本
tot = sum(len(re.findall(r'答案：([A-D])', b)) for b in bodies.values())
check(tot == 451, f'页面里的「答案」共 {tot} 处', '母本合计 451 题')
cnt_ans = {s: len(re.findall(r'答案：([A-D])', b)) for s, b in bodies.items()}
cnt_q = {s: len(re.findall(r'<strong>\d+\.[（(]', b)) for s, b in bodies.items()}
mismatch = {s: (cnt_q[s], cnt_ans[s]) for s in bodies if cnt_q[s] != cnt_ans[s]}
check(not mismatch, '每篇题数与答案数相等', str(list(mismatch.items())[:3]))

# 5. 分类页齐全（嵌套分类在 public/categories/行测/27考季/… 下，按目录名收）
catpages = {}
for root, dirs, fs in os.walk('public/categories'):
    if 'index.html' in fs:
        key = norm(root).replace('public/categories', '(root)').strip('/')
        key = re.sub(r'/page/\d+$', '', key)          # 同一分类的分页并进来数
        catpages.setdefault(key, []).append(os.path.join(root, 'index.html'))
check(len(catpages) >= 15, f'发现 {len(catpages)} 个分类目录', str(sorted(catpages)))
want = {'行测': 32, '27考季': 32, '判断推理': 12, '数量关系': 5, '言语理解': 6, '资料分析': 8,
        '答案键': 1, '定义判断': 3, '类比推理': 3, '逻辑判断': 3, '图形推理': 3, '逻辑填空': 5, '语句表达': 1}
slugs_by_cat = {}
for name, n in want.items():
    dirs_ = [p for key, pages_ in catpages.items() if key.split('/')[-1] == name for p in pages_]
    if not dirs_:
        check(False, f'分类页 {name} 存在')
        continue
    links = set()
    for p in dirs_:
        links.update(re.findall(r'href="[^"]*?/(xc-[a-z0-9-]+)/"', open(p, encoding='utf-8').read()))
    slugs_by_cat[name] = links
    check(len(links) == n, f'分类页 {name} 翻页合起来 {len(links)} 篇', f'期望 {n}')

check(sum(1 for s in slugs_by_cat.get('行测', ()) if s.startswith('xc-')) == 32, '行测分类页收全 32 篇')
union = set().union(*slugs_by_cat.get('判断推理', set()), slugs_by_cat.get('数量关系', set()),
                    slugs_by_cat.get('言语理解', set()), slugs_by_cat.get('资料分析', set()),
                    slugs_by_cat.get('答案键', set()))
check(len(union) == 32, f'四个模块 + 答案键 的分类页并集 = {len(union)} 篇（= 全部行测）')

# 6. 每个 xc slug 都在首页流里（有分页，合起来看）
idx = [open(f, encoding='utf-8').read() for f in glob.glob('public/index.html') + glob.glob('public/page/*/index.html')]
check(len(idx) >= 11, f'首页 + 分页共 {len(idx)} 页')
joined = '\n'.join(idx)
lost = [s for s in bodies if f'/{s}/' not in joined]
check(not lost, '每篇行测文章都进了首页文章流', str(lost[:5]))

# 7. 文章里除了图片没有别的死链（站内 href 都要能落到 public 里的文件）
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
