# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:/Workspaces/sadadtsp.ir/applications/sadadtsp.ir_monorepo/tmp/gitreport/gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['jdatetime', 'jalali_core', 'openpyxl', 'et_xmlfile'],
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
    a.binaries,
    a.datas,
    [],
    name='GitActivityReport',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
