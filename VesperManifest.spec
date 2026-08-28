# PyInstaller build recipe. One spec, both platforms.
#
#   macOS    python3 -m PyInstaller VesperManifest.spec
#   Windows  py -m PyInstaller VesperManifest.spec
#
# PyInstaller cannot cross-compile: run it on the OS you want to ship for.

import sys
from pathlib import Path

ROOT = Path(SPECPATH)
RPG = ROOT / "rpg"

# The font is the only file the game reads from disk. Everything else — every
# sprite, tile and sound — is generated in code at startup.
datas = [(str(RPG / "PressStart2P.ttf"), ".")]

icon = None
if sys.platform == "darwin" and (RPG / "icon.icns").exists():
    icon = str(RPG / "icon.icns")
elif sys.platform == "win32" and (RPG / "icon.ico").exists():
    icon = str(RPG / "icon.ico")

a = Analysis(
    [str(RPG / "main.py")],
    pathex=[str(RPG)],  # the modules import each other flatly (import art, ...)
    binaries=[],
    datas=datas,
    hiddenimports=["numpy"],
    hookspath=[],
    runtime_hooks=[],
    # Trim the heavyweights pygame and numpy pull in but this game never opens.
    # Do not add `email` or `http` here: urllib.request imports both, and the
    # game needs urllib to reach LM Studio.
    excludes=[
        "tkinter", "unittest", "pydoc", "doctest", "pdb",
        "matplotlib", "PIL", "setuptools", "pip",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VesperManifest",
    debug=False,
    strip=False,
    upx=False,
    # No console window: this is a game, not a command line tool.
    console=False,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="VesperManifest",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="The Vesper Manifest.app",
        icon=icon,
        bundle_identifier="com.harrowsreach.vespermanifest",
        info_plist={
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
            # The game talks to LM Studio on localhost over plain HTTP.
            "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
        },
    )
