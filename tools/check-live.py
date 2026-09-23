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


posts = {}
for p in glob.glob(f'source/_posts/{MOD}/**/*.md', recursive=True):
    t = open(p, encoding='utf-8').read()
    m = re.search(r'^slug:\s*(\S+)', t, re.M)
    d = re.search(r'^date:\s*(\d{4})-(\d{2})-(\d{2})', t, re.M)
    posts[m.group(1)] = (f'{d.group(1)}/{d.group(2)}/{d.group(3)}/{m.group(1)}/', t)
check(len(posts) >= 30, f'源里 {MOD} 文章 {len(posts)} 篇（slug 取自 front-matter）')
check(len(posts) == len(set(posts)), 'slug 无重复')

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

imgs = sorted(imgs)
limit = int(os.environ.get('IMG_LIMIT', '0'))          # IMG_LIMIT=12 只抽查一部分（公网抽风时用）
sampled = imgs[::max(1, len(imgs) // limit)][:limit] if limit else imgs   # 跨目录均匀取样，别只抽到前几张
with ThreadPoolExecutor(8) as ex:
    codes = list(ex.map(lambda u: (u, safe(u.lstrip('/'))[0]), sampled))
never = [u for u, c in codes if c is None]
bad = [u for u, c in codes if c is not None and c != 200]
check(len(imgs) >= 50, f'页面里出现图片 {len(imgs)} 张' + (f'，本次抽查 {len(sampled)} 张' if limit else ''))
check(not bad, '抽查的图片线上全部 200', str(bad[:3]))
check(not never, '抽查没有因网络超时而漏掉', str(never[:3]))

for cat in ['', '27%E8%80%83%E5%AD%A3/', '27%E8%80%83%E5%AD%A3/%E8%A8%80%E8%AF%AD%E7%90%86%E8%A7%A3/',
            '27%E8%80%83%E5%AD%A3/%E8%A8%80%E8%AF%AD%E7%90%86%E8%A7%A3/%E4%B8%AD%E5%BF%83%E7%90%86%E8%A7%A3/']:
    links = set()
    page = ''
    for _ in range(10):                                   # 分类页每页 10 条，翻到没有下一页为止
        html = get(f'categories/%E8%A1%8C%E6%B5%8B/{cat}{page}')[1].decode('utf-8', 'replace')
        found = set(re.findall(r'href="[^"]*?/(xc-[a-z0-9-]+)/"', html))
        if not found or found <= links:
            break
        links |= found
        page = f'page/{int(page.split("/")[1]) + 1}/' if page.startswith('page/') else 'page/2/'
    want = len(posts) if cat in ('', '27%E8%80%83%E5%AD%A3/') else None
    if want:
        check(links == set(posts), f'分类页 /categories/行测/{urllib.parse.unquote(cat)} 收全 {len(links)} 篇', f'期望 {want}')
    else:
        check(len(links) > 0, f'分类页 /categories/行测/{urllib.parse.unquote(cat)} 有 {len(links)} 篇')

print('\n%s' % ('线上核对全部通过' if not fail else f'{len(fail)} 项失败'))
sys.exit(1 if fail else 0)
