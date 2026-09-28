#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""行测/素描的位图转 WebP：一张 754KB 的扫描页 → 142KB，同一台机器上从 7~18 秒变成 1~3 秒。

为什么单独一个脚本、而不是写进导入脚本里：母本副本 `data/*-raw` 是他给的原件的拷贝，
一个字节都不能改（导入脚本靠它做 md5 对照），所以转换只能发生在「已经复制进 source/ 之后」这一步。
代价就是**重跑导入脚本之后要再跑一次这个**（README 的导入 SOP 里写了这条）。

幂等：已经转过的（有 .webp、原件没了）跳过；导入脚本重新吐出 .png 时再跑一次就会补上。
只动 source/ 下的拷贝，像素尺寸一个不改，只换编码。

    cd /d/blog && python tools/to-webp.py            # 转
    cd /d/blog && python tools/to-webp.py --report   # 只报当前状态，不写文件
"""
import os
import sys
import glob
import json
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, 'source', 'images')
POSTS = os.path.join(ROOT, 'source', '_posts')
QUALITY = 80          # 2026-09-28 拿 pd-xia/p29 做过样张：q80 是原 PNG 的 18.9%，肉眼和 q70 看不出差别
RASTER = ('.png', '.jpg', '.jpeg')
report = '--report' in sys.argv


def flatten_white(im):
    """扫描页的 PNG 偶尔带 alpha（整页其实是不透明的）。convert('RGB') 会把透明区合成**黑色**，
    所以先看清有没有真透明像素，有就贴到白底上——纸底本来就该是白的。"""
    if im.mode in ('RGBA', 'LA', 'PA') or (im.mode == 'P' and 'transparency' in im.info):
        rgba = im.convert('RGBA')
        if rgba.getextrema()[3][0] < 255:          # 存在非完全不透明的像素
            base = rgba.copy()
            base.load()
            flat = Image.new('RGB', rgba.size, (255, 255, 255))
            flat.paste(base, mask=base.split()[3])
            return flat
        return rgba.convert('RGB')
    return im.convert('RGB')


try:
    from PIL import Image
except ImportError:
    sys.exit('要装 Pillow：pnpm 不管这个，用 pip install pillow（本机已验证 12.3.0）')

# ---- 1. 转图片，记下每张的前后字节 ---------------------------------------
jobs = []                                    # (原件绝对路径, webp 绝对路径)
for f in sorted(glob.glob(os.path.join(IMG, '**', '*'), recursive=True)):
    if not os.path.isfile(f):
        continue
    ext = os.path.splitext(f)[1].lower()
    if ext not in RASTER:
        continue
    webp = os.path.splitext(f)[0] + '.webp'
    jobs.append((f, webp))

done, freed, rows = 0, 0, []
for f, webp in jobs:
    before = os.path.getsize(f)
    if report:
        rows.append([os.path.relpath(f, ROOT).replace(os.sep, '/'), before,
                     os.path.getsize(webp) if os.path.exists(webp) else None])
        continue
    with Image.open(f) as im:
        flat = flatten_white(im)
        flat.save(webp, 'WEBP', quality=QUALITY, method=6)
    after = os.path.getsize(webp)
    if after >= before:                      # 极小图可能转完反而变大（矢量感的图标就是这样）
        os.remove(webp)                      # 那就留原样，别为了统一格式把文件变大
        continue
    os.remove(f)
    done += 1
    freed += before - after
    rows.append([os.path.relpath(f, ROOT).replace(os.sep, '/'), before, after])

# ---- 2. 改写文章里的引用 -------------------------------------------------
# 判据不看文件名表（各模块都有 p29.png 这种同名的页，按名字会串），只看磁盘：
# 「原件没了、同名 .webp 在」才换扩展名；被跳过的小图（转完更大）两个条件都不满足，引用原样留着。
refs = 0
for md in glob.glob(os.path.join(POSTS, '**', '*.md'), recursive=True):
    text = open(md, encoding='utf-8').read()

    def sub(m):
        global refs
        path = m.group(1)
        if not path.lower().endswith(RASTER):
            return m.group(0)
        disk = os.path.join(ROOT, 'source', path.lstrip('/').replace('/', os.sep))
        webp = os.path.splitext(disk)[0] + '.webp'
        if os.path.exists(webp) and not os.path.exists(disk):
            refs += 1
            return m.group(0)[:m.start(1) - m.start(0)] + os.path.splitext(path)[0] + '.webp)'
        return m.group(0)

    new = re.sub(r'!\[[^\]]*\]\((/images/[^)\s"]+)\)', sub, text)
    if new != text and not report:
        open(md, 'w', encoding='utf-8', newline='\n').write(new)

# ---- 3. 对账：不该再有位图残留，每条引用都要指到真实文件 ----------------
left = [f for f in glob.glob(os.path.join(IMG, '**', '*'), recursive=True)
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in RASTER]
dangling = []
for md in glob.glob(os.path.join(POSTS, '**', '*.md'), recursive=True):
    for m in re.finditer(r'!\[[^\]]*\]\((/images/[^)\s"]+)\)', open(md, encoding='utf-8').read()):
        if not os.path.exists(os.path.join(ROOT, 'source', m.group(1).lstrip('/'))):
            dangling.append(m.group(1))
out = {'mode': 'report' if report else 'convert', 'converted': done,
       'freed_bytes': freed, 'freed_MB': round(freed / 1048576, 2),
       'refs_rewritten': refs, 'raster_left': len(left),
       'dangling_refs': len(dangling), 'examples': sorted(dangling)[:5],
       'per_image': [[r[0], r[1], r[2]] for r in rows]}
open(os.path.join(ROOT, 'data', 'webp-report.json'), 'w',
     encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
print('report -> data/webp-report.json（data/ 不入库）')
print('converted=%d freed_MB=%.2f refs=%d raster_left=%d dangling=%d' % (
    done, freed / 1048576, refs, len(left), len(dangling)))
sys.exit(0 if not dangling else 1)
