# -*- coding: utf-8 -*-
"""把 D:\\AI跑数据\\数据 里更新过的文件同步进 data/xingce-raw（源只读；复制后核 md5）。"""
import io, sys, os, shutil, hashlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SRC = r'D:\AI跑数据\数据'
DST = os.path.join('data', 'xingce-raw')


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


done = same = bad = 0
for r, ds, fs in os.walk(SRC):
    for name in fs:
        if name.lower().endswith('.pdf'):
            continue                        # PDF 是讲义原件，不复制
        sp = os.path.join(r, name)
        rel = os.path.relpath(sp, SRC)
        dp = os.path.join(DST, *rel.split(os.sep))
        if os.path.exists(dp) and md5(sp) == md5(dp):
            same += 1
            continue
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        shutil.copy2(sp, dp)
        if md5(sp) != md5(dp):
            bad += 1
            print('MD5 不一致：', rel.replace('\\', '/'))
        else:
            done += 1
            print('已同步：', rel.replace('\\', '/'), os.path.getsize(sp), '字节')
print('未变 %d 个；新复制/覆盖 %d 个；不一致 %d 个' % (same, done, bad))
sys.exit(1 if bad else 0)
