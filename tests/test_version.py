"""公开版本号的单一来源测试。"""


def test_public_version_is_stable():
    """公开版本号单一来源断言：v2.0.0 正式版。"""
    from src.version import __version__

    assert __version__ == "2.0.0"


def test_build_uses_windows_version_resource_with_public_metadata(tmp_path):
    """Windows 构建必须嵌入可供资源管理器读取的公开版本信息。"""
    from build import build_pyinstaller_args, write_windows_version_info

    version_info = tmp_path / "PastePeek-version-info.txt"
    write_windows_version_info(version_info, version="2.0.0-rc.1")

    resource = version_info.read_text(encoding="utf-8")
    args = build_pyinstaller_args(version_info)

    for field, value in (
        ("FileVersion", "2.0.0-rc.1"),
        ("ProductVersion", "2.0.0-rc.1"),
        ("ProductName", "PastePeek"),
        ("FileDescription", "PastePeek clipboard preview"),
        ("OriginalFilename", "PastePeek.exe"),
        ("CompanyName", "PastePeek contributors"),
        ("LegalCopyright", "Copyright (c) 2026 PastePeek contributors"),
    ):
        assert f"StringStruct('{field}', '{value}')" in resource

    version_flag = args.index("--version-file")
    assert args[version_flag + 1] == str(version_info)


def test_build_writes_standard_sha256_file(tmp_path):
    """发布产物应附带可被常见工具验证的 SHA-256 文件。"""
    import hashlib

    from build import write_sha256

    artifact = tmp_path / "PastePeek.exe"
    artifact.write_bytes(b"PastePeek release artifact")

    checksum_path = write_sha256(artifact)

    expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert checksum_path.name == "PastePeek.exe.sha256"
    assert checksum_path.read_text(encoding="ascii") == (
        f"{expected}  PastePeek.exe\n"
    )


def test_build_creates_release_bundle_with_license_materials(tmp_path):
    """推荐下载包必须同时包含程序、哈希与第三方许可证。"""
    from zipfile import ZipFile

    from build import write_release_bundle, write_sha256

    artifact = tmp_path / "PastePeek.exe"
    artifact.write_bytes(b"PastePeek release artifact")
    checksum = write_sha256(artifact)
    notices = tmp_path / "THIRD_PARTY_NOTICES.md"
    notices.write_text("third-party notices", encoding="utf-8")
    project_license = tmp_path / "LICENSE"
    project_license.write_text("MIT License", encoding="utf-8")
    licenses = tmp_path / "licenses"
    licenses.mkdir()
    (licenses / "LGPL-3.0.txt").write_text(
        "GNU LESSER GENERAL PUBLIC LICENSE",
        encoding="utf-8",
    )

    bundle = write_release_bundle(
        artifact,
        checksum,
        notices,
        licenses,
        project_license,
        version="2.0.0-rc.1",
    )

    with ZipFile(bundle) as archive:
        assert set(archive.namelist()) == {
            "PastePeek.exe",
            "PastePeek.exe.sha256",
            "THIRD_PARTY_NOTICES.md",
            "LICENSE",
            "licenses/LGPL-3.0.txt",
        }
