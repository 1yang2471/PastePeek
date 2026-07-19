"""PastePeek — PyInstaller build script.

One-command build:
    python build.py

Output:
    dist/PastePeek.exe  — single-file Windows executable, no console window.
"""

import hashlib
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from src.version import __version__

ROOT = Path(__file__).resolve().parent
ENTRY = ROOT / "src" / "main.py"
ICON = ROOT / "assets" / "icon.ico"
DIST = ROOT / "dist"
NAME = "PastePeek"
VERSION_INFO = ROOT / "build" / "PastePeek-version-info.txt"


def _windows_version_tuple(version: str) -> tuple[int, int, int, int]:
    """将公开版本号转换为 Windows 固定版本号的四段整数。"""
    core, separator, prerelease = version.partition("-")
    core_parts = core.split(".")
    if len(core_parts) != 3 or not all(part.isdigit() for part in core_parts):
        raise ValueError(f"无效版本号: {version}")

    revision = 0
    if separator:
        prerelease_numbers = re.findall(r"\d+", prerelease)
        if prerelease_numbers:
            revision = int(prerelease_numbers[-1])
    return *(int(part) for part in core_parts), revision


def write_windows_version_info(path: Path, *, version: str) -> Path:
    """生成 PyInstaller 使用的 Windows 版本资源。"""
    file_version = _windows_version_tuple(version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={file_version},
    prodvers={file_version},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('FileDescription', 'PastePeek clipboard preview'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('CompanyName', 'PastePeek contributors'),
          StringStruct('LegalCopyright', 'Copyright (c) 2026 PastePeek contributors'),
          StringStruct('OriginalFilename', 'PastePeek.exe'),
          StringStruct('ProductName', 'PastePeek'),
          StringStruct('ProductVersion', '{version}'),
        ],
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
""",
        encoding="utf-8",
    )
    return path


def build_pyinstaller_args(version_info: Path) -> list[str]:
    """创建包含 Windows 版本资源的 PyInstaller 参数。"""
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconsole",
        "--clean",
        "--noconfirm",
        "--name",
        NAME,
        "--add-data",
        f"src{';'}src",
        "--add-data",
        f"{ICON}{';'}assets",
        "--hidden-import",
        "win32clipboard",
        "--version-file",
        str(version_info),
    ]


def write_sha256(artifact: Path) -> Path:
    """为发布产物生成标准 SHA-256 校验文件。"""
    digest = hashlib.sha256()
    with artifact.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    checksum_path = artifact.with_suffix(artifact.suffix + ".sha256")
    checksum_path.write_text(
        f"{digest.hexdigest()}  {artifact.name}\n", encoding="ascii"
    )
    return checksum_path


def write_release_bundle(
    artifact: Path,
    checksum: Path,
    notices: Path,
    licenses_dir: Path,
    project_license: Path,
    *,
    version: str,
) -> Path:
    """创建包含程序、校验值和许可证材料的 Windows 发布包。"""
    required = (artifact, checksum, notices, licenses_dir, project_license)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"发布材料缺失: {', '.join(missing)}")

    bundle = artifact.parent / f"PastePeek-{version}-win64.zip"
    with ZipFile(bundle, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(artifact, artifact.name)
        archive.write(checksum, checksum.name)
        archive.write(notices, notices.name)
        archive.write(project_license, "LICENSE")
        for license_path in sorted(licenses_dir.rglob("*")):
            if license_path.is_file():
                relative = license_path.relative_to(licenses_dir).as_posix()
                archive.write(license_path, f"licenses/{relative}")
    return bundle


def main():
    if not ENTRY.exists():
        print(f"ERROR: Entry point not found: {ENTRY}")
        sys.exit(1)

    # Generate icon if missing
    if not ICON.exists():
        print("Icon not found, generating minimal icon...")
        from generate_icon import generate_icon
        generate_icon(ICON)

    version_info = write_windows_version_info(VERSION_INFO, version=__version__)
    args = build_pyinstaller_args(version_info)

    # ── PySide6 依赖检查 ──────────────────────────────────────────
    try:
        import PySide6
    except ImportError:
        print("ERROR: PySide6 not found. Install requirements.txt first.")
        sys.exit(1)
    print(f"PySide6: using declared installation ({PySide6.__version__})")

    if ICON.exists():
        args.extend(["--icon", str(ICON)])

    args.append(str(ENTRY))

    print(f"\nBuilding {NAME} v{__version__} ...")
    result = subprocess.run(args, cwd=ROOT)

    if result.returncode != 0:
        print("\nBuild FAILED. Check PyInstaller output above.")
        sys.exit(result.returncode)

    # ── Verify output ────────────────────────────────────────────────
    exe = DIST / f"{NAME}.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        checksum = write_sha256(exe)
        bundle = write_release_bundle(
            exe,
            checksum,
            ROOT / "THIRD_PARTY_NOTICES.md",
            ROOT / "licenses",
            ROOT / "LICENSE",
            version=__version__,
        )
        print(f"\nBuild SUCCESS: {exe} ({size_mb:.1f} MB)")
        print(f"SHA-256: {checksum}")
        print(f"Release bundle: {bundle}")
        print("Target platform: Windows 10/11. See README.md for verified environments.")
    else:
        print(f"\nBuild completed but .exe not found at expected path: {exe}")
        sys.exit(1)


if __name__ == "__main__":
    main()
