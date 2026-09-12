# -*- mode: python ; coding: utf-8 -*-
# PyInstaller fallback spec (MYXRAY-30): same staged payload contract as Nuitka.

import sys
from pathlib import Path

sys.path.insert(0, SPECPATH)

import build_support

staged = build_support.stage_payload()
datas = [(str(src), arc) for src, arc in build_support.payload_map(staged)]

a = Analysis(
    [str(Path(SPECPATH, "src", "xrayvpn", "__main__.py"))],
    pathex=[str(Path(SPECPATH, "src"))],
    datas=datas,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=build_support.artifact_name(),
    debug=False,
    strip=False,
    upx=False,
    console=True,
)
