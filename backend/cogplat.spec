from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata


source = Path(SPECPATH) / "src"
migrations = source / "cogplat" / "db" / "migrations"

analysis = Analysis(
    [str(source / "cogplat" / "__main__.py")],
    pathex=[str(source)],
    datas=[(str(migrations), "cogplat/db/migrations")] + copy_metadata("langgraph"),
    hiddenimports=[
        "uvicorn.lifespan.on",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.websockets_impl",
    ],
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    exclude_binaries=True,
    name="cogplat",
    console=True,
    upx=False,
)
bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    name="cogplat",
    upx=False,
)
