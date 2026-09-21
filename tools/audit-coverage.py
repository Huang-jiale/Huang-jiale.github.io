#!/usr/bin/env python
"""内容完整性审计：源文件的正文是否原样出现在它对应的生成文章里

判据是**最长连续缺失段**而不是覆盖率百分比：源文件里挤在一行、文章里被拆成两节的文本，
拼接处会对不上一两个窗口，那是噪声；真正丢内容一定是一长段连续窗口都不在。

清洗规则用正则从 tools/import-shenlun.mjs 里现抓，避免同一套规则写两份、改一边忘改另一边。
书本 .txt 源还要额外剔掉「被搬去文章标题 / 分类」的行（■题目行、篇章节分隔页），
它们本来就不该出现在正文里。

    python tools/audit-coverage.py
"""
import io
import os
import re
import sys
import json
import glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MJS = os.path.join('tools', 'import-shenlun.mjs')
W = 30


def js_rules(src, names):
    """把导入脚本里的 `const 名字 = /正则/flags;` 抓出来直接用，规则只有一份"""
    out = {}
    for name in names:
        m = re.search(r'^const %s = (/(?:\\.|\[[^\]]*\]|[^/\n\\])+/([gimsuy]*));' % re.escape(name),
                      src, re.M)
        if not m:
            sys.exit('导入脚本里找不到规则 %s（必须是 `const %s = /…/flags;` 的单行写法）' % (name, name))
        flags = 0
        for c in m.group(2):
            flags |= {'i': re.I, 'm': re.M, 's': re.S}.get(c, 0)
        out[name] = re.compile(m.group(1)[1:-1], flags)     # 去掉两侧的 /
    return out


JS_SRC = open(MJS, encoding='utf-8').read()
R = js_rules(JS_SRC, ['PAGE_MARK', 'BARE_PAGE_NUM', 'CHAT_MARK', 'SCAN_MARK', 'TOC_ENTRY',
                      'DECOR_ONLY', 'BOOK_HEAD', 'BOOK_FRAGMENT', 'BOOK_WATER',
                      'BOOK_PIVOT', 'BOOK_CHAPTER', 'BOOK_MARK', 'PUNCT_ONLY', 'TOC_LINE'])
# 导入脚本把标记行升格成 `### 标记行` 时剥掉的行首装饰符，比对时两侧都要剥
BULLET = re.compile(r'^[\s●·○?？]+')
HEAD_WORDS = {'答题演示', '思维导图', '粉笔思维', '参考答案', '参考范文',
              '要点总结', '话题梳理', '话题及要素梳理', '要素及话题梳理',
              '逻辑梳理', '观点总结', '做法总结'}
HEAD_PAT = re.compile(r'^(?:资料\d{1,2}|第[一二三四五六]步([-—–一\s]*\S{0,20})?)$')


def is_pivot(lines, i):
    """镜像 isPivot()：分隔页后面是正文，目录里的同名行后面是题目索引；页眉靠 dropRunHeads 处理"""
    t = lines[i]
    if not (R['BOOK_PIVOT'].match(t) or R['BOOK_CHAPTER'].match(t)):
        return False
    for j in range(i + 1, min(i + 10, len(lines))):
        n = lines[j]
        if n == '' or R['BOOK_PIVOT'].match(n) or R['BOOK_CHAPTER'].match(n):
            continue
        return not (R['TOC_LINE'].match(n) or R['BOOK_HEAD'].match(n))
    return True


def book_lines(text):
    """镜像 bookLines() + parseBook()：滤噪声，再丢掉 ■题目行和分隔页行"""
    out = []
    for raw in text.splitlines():
        t = raw.strip()
        if (R['PAGE_MARK'].match(t) or R['BARE_PAGE_NUM'].match(t) or R['BOOK_HEAD'].match(t)
                or R['BOOK_FRAGMENT'].match(t) or R['BOOK_WATER'].match(t)
                or R['PUNCT_ONLY'].match(t)):
            continue
        if t == '':
            if out and out[-1] != '':
                out.append('')
            continue
        out.append(t)
    keep, started = [], False
    for i, t in enumerate(out):
        pv = is_pivot(out, i)
        if not started and not pv and not R['BOOK_MARK'].match(t):
            continue                    # 扉页、版权页、目录：整段丢弃
        started = True
        if pv or R['BOOK_MARK'].match(t):
            continue                    # 分隔页搬去了分类，■题目行搬去了文章标题
        keep.append(t)
    return keep


def clean_body(text):
    """镜像 cleanBody()：分页标记、孤立页码、翻页提示、引流行、段首目录残留、空代码块"""
    kept = [l for l in text.splitlines()
            if not R['PAGE_MARK'].match(l) and not R['BARE_PAGE_NUM'].match(l)
            and not R['CHAT_MARK'].match(l) and not R['SCAN_MARK'].match(l)
            and not R['DECOR_ONLY'].match(l)]
    i = next((k for k, l in enumerate(kept) if l.strip()), 0)
    j, hits = i, 0
    while j < len(kept):
        t = kept[j].strip()
        if R['TOC_ENTRY'].match(t):
            hits += 1
            j += 1
        elif t == '' and j + 1 < len(kept) and R['TOC_ENTRY'].match(kept[j + 1].strip()):
            j += 1
        else:
            break
    if hits >= 3:
        del kept[i:j]
    out = '\n'.join(kept)
    out = re.sub(r'^```[a-z]*\s*\n\s*\n?```\s*$', '', out, flags=re.M | re.I)
    return re.sub(r'[ \t]+$', '', re.sub(r'\n{3,}', '\n\n', out)).strip()


# 以下 constructs 在渲染时被换掉了位置，不该按正文比对
H2 = re.compile(r'^##[ \t][^\n]*\n', re.M)      # 只有 h2 是文章自造的小节名；h3 来自源文件，要参与比对
SEP = re.compile(r'^-{3,}\s*$', re.M)
MARK = re.compile(r'[【\[]?(参考答案|参考范文)[】\]]?')   # 去重时刻意剪掉的重复标记
# 两边一致剥掉的字符，要和导入脚本 normalizeWithMap() 的过滤集是同一套
NORM = r'[\s`#*>●·○]+'


def expected(text, path):
    """源文件里真正应当出现在文章正文中的内容（逐行，升格行只剥行首装饰符）"""
    if path.endswith('.txt'):
        lines = book_lines(text)
    else:
        i = text.find('\n## ')
        if i < 0:                      # 没有小节结构：整个文件都是标题+元信息，不进正文
            lines = []
        else:                          # 第一个 `## ` 之前是标题+元信息
            lines = clean_body(text[i:]).splitlines()
    out = []
    for l in lines:
        if m2 := BULLET.sub('', re.sub(r'[:：\s]+$', '', l.strip())):
            out.append(m2 if (m2 in HEAD_WORDS or HEAD_PAT.match(m2)) else l.strip())
        else:
            out.append(l.strip())
    return '\n'.join(out)


def flat(s):
    """两边共用的归一化：h2 小节名、分隔线、被剪掉的标记都不参与比对"""
    return re.sub(NORM, '', MARK.sub('', SEP.sub('', H2.sub('', s))))


man = json.load(open('data/shenlun-manifest.json', encoding='utf-8'))

gen = {}
for p in glob.glob('source/_posts/申论知识库/**/*.md', recursive=True):
    t = open(p, encoding='utf-8').read()
    m = re.search(r'^slug: (\S+)$', t, re.M)
    if m:
        gen[m.group(1)] = flat(t.split('---', 2)[2])

cover, whole = {}, []
for e in man:
    joined = ''.join(gen.get(e['slug'], '') for _ in e['sources'])
    for s in e['sources']:
        cover.setdefault(s.split('#')[0], []).append(joined)
        whole.append(joined)
hay_all = ''.join(whole)

bad, moved = [], []
for src, bodies in cover.items():
    path = os.path.join('data/shenlun-raw', src.replace('/', os.sep))
    if not os.path.exists(path):
        bad.append((src, '源文件未找到映射', '', []))
        continue
    text = flat(expected(open(path, encoding='utf-8').read(), path))
    ws = [text[i:i + W] for i in range(0, len(text) - W, W)]
    if not ws:
        continue
    hay = ''.join(bodies)
    run = best = end = 0
    for i, w in enumerate(ws):
        run = 0 if w in hay else run + 1
        if run > best:
            best, end = run, i + 1
    if best < 3:
        continue
    miss = ''.join(ws[end - best:end])
    # 整站找得到、只是不在这篇文章里 —— 不是丢内容，是错放（比如页眉被当成分隔页截断）
    if miss in hay_all:
        moved.append((src, '%d 段 ≈%d 字' % (best, best * W), miss))
        continue
    bad.append((src, '%d 段 ≈%d 字' % (best, best * W), miss, bodies))

unmapped = []
for ext in ('md', 'txt'):
    for p in glob.glob('data/shenlun-raw/**/*.' + ext, recursive=True):
        rel = os.path.relpath(p, 'data/shenlun-raw').replace(os.sep, '/')
        if rel in cover or rel.endswith('README.md') or '/00-总索引/' in rel:
            continue
        n = flat(expected(open(p, encoding='utf-8').read(), p))
        if len(n) >= 60 and n[:W * 3] not in hay_all:
            unmapped.append((rel, len(n)))

print('源文件纳入映射: %d   生成文章: %d' % (len(cover), len(gen)))
print('正文错位到别的文章(>=90字)的源文件: %d' % len(moved))
for src, size, frag in moved[:5]:
    print('    %s  错位 %s' % (src, size))
    print('      ' + frag[:180])
print('有连续正文缺失(>=90字)的源文件: %d' % len(bad))
for src, size, frag, _ in bad[:10]:
    print('    %s  缺失 %s' % (src, size))
    print('      ' + frag[:180])
print('未纳入任何文章的源文件: %d' % len(unmapped))
for u in unmapped[:10]:
    print('   ', u)
