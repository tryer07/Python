# -*- mode: python ; coding: utf-8 -*-
import os


def _asset_datas():
    """assets 逐文件进包，剔除仅工具期/备份用的死重。

    下划线开头的工具目录（_old_* 备份、_raw 白底归档）、*_src_*.png
    源图、*/src/ 工具源目录只被 tools/prepare_assets.py 读取；运行时
    代码从不引用、也不遍历 assets（已确认无 listdir/walk 扫描），打进
    exe 纯属浪费体积（_raw 一类就能占数十 MB）。
    """
    out = []
    for root, dirs, files in os.walk('assets'):
        parts = os.path.relpath(root, 'assets').replace(os.sep, '/').split('/')
        if any(p.startswith('_') or p == 'src' for p in parts):
            dirs[:] = []
            continue
        for f in files:
            if f.startswith('_') or '_src_' in f or '_raw' in f:
                continue
            src = os.path.join(root, f)
            dst = os.path.dirname(os.path.join(
                'assets', os.path.relpath(src, 'assets').replace(os.sep, '/')))
            out.append((src, dst))
    out.append(('data', 'data'))
    return out


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=_asset_datas(),
    hiddenimports=['numpy'],   # audio_manager 用 numpy 走矢量化合成快路径（无它回退纯 Python 会卡 6s+）
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# onedir 打包：onefile 每次启动要把 140+MB 资源解压到临时目录、退出再删除，
# 打开/关闭都慢（实测启动 5~7s 大半耗在解包）；onedir 直接读目录，
# 启动 1~2s、关闭即时。产物为 dist\鳞光纪\ 文件夹，分发整夹压缩即可。
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='鳞光纪',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='鳞光纪',
)
