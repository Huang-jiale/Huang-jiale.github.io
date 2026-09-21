"""摸底一个新模块：每个源文件去掉空白/markdown 后的正文字数分布。
导入前先跑它，判断该按「一篇一题」还是「多篇合并」来组织，以及要不要做去重。

    python tools/survey-sources.py
"""
import re, os, glob, json

F = chr(96) * 3
def chars(p):
    t = open(p, encoding='utf-8').read()
    return len(re.sub(r'[\s' + F + r'#*\-]+', '', t))

buckets = {'<300': 0, '300-799': 0, '800-1999': 0, '2000-4999': 0, '>=5000': 0}
groups = {}
files = [p for p in glob.glob('data/shenlun-raw/**/*.md', recursive=True)]
for p in files:
    n = chars(p)
    k = '<300' if n < 300 else '300-799' if n < 800 else '800-1999' if n < 2000 else '2000-4999' if n < 5000 else '>=5000'
    buckets[k] += 1
    g = p.split(os.sep)[1] if p.count(os.sep) > 1 else '?'
    groups.setdefault(g, []).append(n)

print('源文件正文字数分布（%d 个文件）' % len(files))
for k, v in buckets.items():
    print('  %-10s %4d  %s' % (k, v, '#' * (v * 60 // len(files))))
print()
print('按模块：文件数 / 中位字数 / <800字占比')
for g in sorted(groups):
    ns = sorted(groups[g])
    med = ns[len(ns) // 2]
    thin = sum(1 for n in ns if n < 800)
    print('  %-22s %3d 个  中位 %5d  <800字: %3d (%.0f%%)' % (g, len(ns), med, thin, 100 * thin / len(ns)))
