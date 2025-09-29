# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_submodules

datas = [('logo.png', '.'), ('icon.icns', '.'), ('crawl.ico', '.')]
binaries = []
hiddenimports = []
datas += collect_data_files('tkinter')
binaries += collect_dynamic_libs('tkinter')
hiddenimports += collect_submodules('tkinter')


a = Analysis(
    ['CrawlSpace.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CrawlSpace',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CrawlSpace',
)
app = BUNDLE(
    coll,
    name='CrawlSpace.app',
    icon='icon.icns',
    bundle_identifier='com.johntotaro.crawlspace',
)
