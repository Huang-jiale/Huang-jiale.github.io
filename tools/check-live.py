# -*- coding: utf-8 -*-
"""线上核对：push 完等 Actions 绿了再跑，拿 source/_posts 对账 https://huang-jiale.github.io。

跑法：python tools/check-live.py [模块目录名]     # 默认行测题库
      IMG_LIMIT=20 python tools/check-live.py   # 只抽查 20 张图（公网抽风时用，跨目录均匀取样）
和 tools/check-build.py 的分工：那个看本地产物，这个看 CDN 上真的是这版（Pages 有传播延迟，
刚推完可能还是旧版——旧版不会报错，只会少页面，所以这里按源里的 slug 逐个点名）。
GitHub Pages 偶发 TLS 握手超时，每个请求重试几次再判失败。
"""
import io, sys, os, re, glob, urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = 'https://huang-jiale.github.io/'
MOD = sys.argv[1] if len(sys.argv) > 1 else '行测题库'
fail = []


def check(cond, msg, detail=''):
    if not cond:
        fail.append(msg + ' ' + detail)
        print('FAIL', msg, detail)


def get(path, tries=4):
    """返回 (status, body)。404 一拿到就返回（分页到头靠它），只有网络错误才重试。"""
    import urllib.error
    url = urllib.parse.urljoin(BASE, path.lstrip('/'))
    req = urllib.request.Request(url, headers={'User-Agent': 'check-live'})
    last = None
    for _ in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            try:
                return e.code, e.read()
            except Exception:                 # 404 的响应体读不完也算 404，别再耗时间
                return e.code, b''
        except Exception as e:                      # GitHub Pages 偶发 TLS 握手超时
            last = e
    raise RuntimeError(f'{url}: {last}')


def norm(p):
    return p.replace('\\', '/')


def fm_cats(text):
    m = re.search(r'^categories:\n((?:  - .*\n)+)', text, re.M)
    return [re.sub(r'^\s*-\s*["\']?(.*?)["\']?\s*$', r'\1', l) for l in m.group(1).splitlines()] if m else []


posts = {}                       # slug -> (线上路径, 全文, 分类链)
for p in glob.glob(f'source/_posts/{MOD}/**/*.md', recursive=True):
    t = open(p, encoding='utf-8').read()
    m = re.search(r'^slug:\s*(\S+)', t, re.M)
    slug = m.group(1) if m else norm(p).split('/')[-1][:-3]     # 没写 slug 时 permalink 用文件名
    d = re.search(r'^date:\s*(\d{4})-(\d{2})-(\d{2})', t, re.M)
    posts[slug] = (f'{d.group(1)}/{d.group(2)}/{d.group(3)}/{slug}/', t, fm_cats(t))
check(len(posts) >= 5, f'源里 {MOD} 文章 {len(posts)} 篇（slug 取自 front-matter）')
check(all(c for _, _, c in posts.values()), f'{MOD} 每篇都挂了分类')

def safe(path):
    """网络抖动不算内容错误：拿不到就标 None，单独报「没查到」而不是整个脚本崩。"""
    try:
        return get(path)
    except RuntimeError:
        return None, b''


with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(lambda s: (s, safe(posts[s][0])), sorted(posts)))
imgs = set()
for slug, (st, html) in res:
    body = html.decode('utf-8', 'replace').split('post-body', 1)
    check(st == 200 and len(body) > 1, f'{slug} 线上 200 且有正文')
    b = body[1] if len(body) > 1 else ''
    check('**' not in b and 'assets/' not in b, f'{slug} 无渲染残留')
    imgs.update(re.findall(r'src="(/images/[^"]+)"', b))

src_imgs = set()
for _, (_, t, _) in posts.items():
    src_imgs.update(re.findall(r'/images/[^\s")\]]+', t))

imgs = sorted(imgs)
limit = int(os.environ.get('IMG_LIMIT', '0'))          # IMG_LIMIT=12 只抽查一部分（公网抽风时用）
sampled = imgs[::max(1, len(imgs) // limit)][:limit] if limit else imgs   # 跨目录均匀取样，别只抽到前几张
with ThreadPoolExecutor(8) as ex:
    codes = list(ex.map(lambda u: (u, safe(u.lstrip('/'))[0]), sampled))
never = [u for u, c in codes if c is None]
bad = [u for u, c in codes if c is not None and c != 200]
if src_imgs:                       # 时政那种纯文字模块本来就没图，别把 0 当失败
    check(len(imgs) >= len(src_imgs) * 0.8, f'页面里出现图片 {len(imgs)} 张（源里引用 {len(src_imgs)} 张）'
          + (f'，本次抽查 {len(sampled)} 张' if limit else ''))
else:
    check(not imgs, '源里没有图片引用，页面里也不该冒出来', str(imgs[:3]))
check(not bad, '抽查的图片线上全部 200', str(bad[:3]))
check(not never, '抽查没有因网络超时而漏掉', str(never[:3]))

def cat_page(path):
    """翻完一个分类页的全部分页，返回合起来看到的本模块 slug。

    进度只能看「这一页有没有新文章」，不能看「有没有本模块的文章」：分类页现在是 date 升序，
    `/学习/` 第一页全是时政，行测一篇都没有，拿本模块判断会在第一页就 break（曾经误报「收全 0 篇」）。
    """
    mine, seen, page = set(), set(), ''
    for _ in range(20):                                   # 每页 10 条，一级分类 112 篇要翻 12 页
        html = get(f'{path}{page}')[1].decode('utf-8', 'replace')
        arts = set(re.findall(r'href="[^"]*?/\d{4}/\d{2}/\d{2}/([a-z][a-z0-9-]{2,})/"', html))
        if not arts - seen:
            break
        seen |= arts
        mine |= arts & set(posts)
        page = f'page/{int(page.split("/")[1]) + 1}/' if page.startswith('page/') else 'page/2/'
    return mine


# 源里挂过的每条分类链都要有线上分类页；Hexo 把分类名 slug 化后才做目录（空格变成 `-`）
cat_want = {}
for slug, (_, _, cats) in posts.items():
    for i in range(len(cats)):
        cat_want.setdefault(tuple(cats[:i + 1]), set()).add(slug)
paths = {k: 'categories/' + '/'.join(urllib.parse.quote(c.replace(' ', '-')) for c in k) + '/' for k in cat_want}
with ThreadPoolExecutor(8) as ex:
    got = list(ex.map(lambda k: (k, cat_page(paths[k])), sorted(cat_want)))
for k, links in got:
    check(links == cat_want[k], f'分类页 /{" / ".join(k)} 收全 {len(links)} 篇',
          f'期望 {len(cat_want[k])}，缺 {sorted(cat_want[k] - links)[:3]}')

# 前端这一版的「指纹」：Pages 有传播延迟，旧版不会报错、只会少了这些类名，所以逐个点名
home = get('')[1].decode('utf-8', 'replace')
n_cells = home.count('class="heat-cell') - 5          # 图例那 5 格也用 .heat-cell
check(n_cells == 364, f'首页日历 52×7 = 364 格（线上数到 {n_cells} 格）')
check('heat-months' in home and 'heat-legend' in home, '首页日历的月首标签和图例都在')
check('class="months"' not in home, '首页已经没有上一版按月柱状图')
overview = get('categories/')[1].decode('utf-8', 'replace')
check('cat-row cat-row--l0' in overview and 'cat-node--top' in overview, '分类总览页是树状图')
branch_path = paths[max(cat_want, key=lambda k: (len(cat_want[k]), len(k)))]   # 文章最多的那条链
branch = get(branch_path)[1].decode('utf-8', 'replace')
check('cat-node--here' in branch and '<time' not in branch, '分类页顶部有本分支的树，列表不画日期')
css = get('css/main.css')[1].decode('utf-8', 'replace')
# 产物里有好几条 .back-to-top（主题的、我的、移动端的），要找「我那条」= 带 42px 的那一条
mine = [b for b in re.findall(r'\.back-to-top \{([^}]*)\}', css) if '42px' in b]
check(bool(mine) and 'justify-content: center' in mine[0], '一键到顶的箭头居中规则已生效')
check('body:has(.main-inner.post) .reading-progress-bar' in css, '进度条只在文章页画的规则已生效')
art = get(posts[sorted(posts)[0]][0])[1].decode('utf-8', 'replace')
check('back-to-top' in art and 'module-nav' in art and 'class="post-tags"' in art,
      '文章页：一键到顶 + 本模块文章 + 底部标签都在')

print('\n%s' % ('线上核对全部通过' if not fail else f'{len(fail)} 项失败'))
sys.stdout.flush()          # stdout 被我换成 TextIOWrapper 了，sys.exit 时不一定帮你刷管道
sys.exit(1 if fail else 0)
