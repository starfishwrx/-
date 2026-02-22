# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


def collect_datas():
    import os
    from PyInstaller.utils.hooks import collect_data_files

    datas = collect_data_files("matplotlib", include_py_files=False)
    datas.append(("config.example.yaml", "."))
    datas.append(("hosts_870.example.yaml", "."))
    datas.append(("hosts_505.example.yaml", "."))
    datas.append(("extra_auth.example.json", "."))
    datas.append(("requirements.txt", "."))

    template_root = "templates"
    for dirpath, _, filenames in os.walk(template_root):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, template_root)
            target_path = os.path.join("templates", rel_path)
            datas.append((full_path, target_path))
    return datas


a = Analysis(
    ["generate_daily_report.py"],
    pathex=[],
    binaries=[],
    datas=collect_datas(),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="generate_daily_report",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app.ico",
)
