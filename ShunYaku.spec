# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import tomllib

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path.cwd()
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
VERSION = PROJECT["version"]

datas = [(str(ROOT / "icon.png"), ".")]
binaries = []
hiddenimports = []

datas += collect_data_files("PySide6")
binaries += collect_dynamic_libs("PySide6")
binaries += collect_dynamic_libs("shiboken6")
hiddenimports += collect_submodules("shunyaku")
hiddenimports += collect_submodules("pynput")
hiddenimports += collect_submodules("huggingface_hub")
hiddenimports += collect_submodules("llama_cpp")

llama_lib_dir = ROOT / ".venv" / "lib" / "python3.12" / "site-packages" / "llama_cpp" / "lib"
for dylib in sorted(llama_lib_dir.glob("*.dylib")):
    binaries.append((str(dylib), "llama_cpp/lib"))

a = Analysis(
    ["run_shunyaku.py"],
    pathex=[str(ROOT / "src")],
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
    name="ShunYaku",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ShunYaku",
)

app = BUNDLE(
    coll,
    name="ShunYaku.app",
    icon=str(ROOT / "icon.png"),
    bundle_identifier="com.shunyaku.app",
    info_plist={
        "CFBundleDisplayName": "ShunYaku",
        "CFBundleName": "ShunYaku",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSApplicationCategoryType": "public.app-category.productivity",
        "LSMinimumSystemVersion": "13.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
)
