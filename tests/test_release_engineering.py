"""GitHub 发布工程的可复现性契约测试。"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _requirement_lines(filename: str) -> list[str]:
    """读取去除注释与空行后的依赖声明。"""
    return [
        line.strip()
        for line in (ROOT / filename).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_release_entry_requirements_use_exact_versions():
    """发布与开发入口的顶层依赖必须精确锁定。"""
    runtime = _requirement_lines("requirements.in")
    development = _requirement_lines("requirements-dev.in")

    assert runtime == ["PySide6==6.11.1", "pywin32==311"]
    assert "-r requirements.in" in development
    assert "pytest==9.0.3" in development
    assert "pyinstaller==6.20.0" in development
    assert "ruff==0.15.21" in development
    assert "pip-audit==2.10.1" in development
    assert "pip-tools==7.5.3" in development


def test_third_party_licenses_accompany_release():
    """二进制依赖的许可证与再分发说明必须可供用户查阅。"""
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    normalized = notices.lower()

    for component in (
        "qt",
        "pyside6",
        "shiboken6",
        "python 3.12",
        "pywin32",
        "pyinstaller",
        "lucide",
    ):
        assert component.lower() in normalized
    assert "lgpl-3.0" in normalized
    assert "reverse engineering" in normalized

    lgpl = (ROOT / "licenses" / "LGPL-3.0.txt").read_text(encoding="utf-8")
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in lgpl

    lucide = (ROOT / "licenses" / "Lucide-ISC.txt").read_text(encoding="utf-8")
    assert "ISC License" in lucide

    cpython = (ROOT / "licenses" / "CPython-3.12-LICENSE.txt").read_text(
        encoding="utf-8"
    )
    assert "PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2" in cpython

    pyinstaller = (ROOT / "licenses" / "PyInstaller-COPYING.txt").read_text(
        encoding="utf-8"
    )
    assert "Bootloader Exception" in pyinstaller


def test_ci_runs_release_quality_gates():
    """CI 必须执行静态检查、漏洞审计、测试、编译与构建。"""
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    for required in (
        "requirements-dev.txt",
        "--require-hashes",
        "ruff check",
        "pip_audit",
        "run_tests.py",
        "compileall",
        "build.py",
    ):
        assert required in workflow

    assert "pip_audit -r requirements-dev.txt" in workflow


def test_release_workflow_uploads_licensed_bundle_after_quality_gates():
    """标签发布必须复用质量门禁并附带完整许可证材料。"""
    workflow = (
        ROOT / ".github" / "workflows" / "release.yml"
    ).read_text(encoding="utf-8")

    for required in (
        "--require-hashes",
        "ruff check",
        "pip_audit",
        "run_tests.py",
        "build.py",
        "dist/PastePeek.exe",
        "dist/PastePeek.exe.sha256",
        'dist/PastePeek-$version-win64.zip',
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "licenses/LGPL-3.0.txt",
        "licenses/Lucide-ISC.txt",
        "licenses/CPython-3.12-LICENSE.txt",
        "licenses/PyInstaller-COPYING.txt",
    ):
        assert required in workflow

    assert "pip_audit -r requirements-dev.txt" in workflow
    assert "PastePeek-2.0.0-win64.zip" not in workflow
    assert 'python -c "from src.version import __version__; print(__version__)"' in workflow
    assert "Test-Path -LiteralPath $bundle" in workflow
    assert "PastePeek-*-win64.zip" not in workflow
    assert "Select-Object -First 1" not in workflow
    assert "--prerelease" in workflow
    assert "softprops/action-gh-release" not in workflow


def test_github_actions_are_pinned_to_immutable_commits():
    """具有仓库权限的工作流依赖必须固定到完整提交 SHA。"""
    import re

    for filename in ("ci.yml", "release.yml"):
        workflow = (
            ROOT / ".github" / "workflows" / filename
        ).read_text(encoding="utf-8")
        action_refs = re.findall(r"uses:\s*[^\s@]+@([^\s#]+)", workflow)

        assert action_refs
        assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in action_refs)


def test_release_checkout_does_not_persist_write_credentials():
    """发布构建期间不得把仓库写凭据留给后续步骤。"""
    workflow = (
        ROOT / ".github" / "workflows" / "release.yml"
    ).read_text(encoding="utf-8")

    assert "contents: write" in workflow
    checkout_block = workflow.split("actions/checkout@", 1)[1].split(
        "- uses:", 1
    )[0]
    assert "with:\n          persist-credentials: false" in checkout_block


def test_development_lock_requires_hashes():
    """构建工具链必须和运行依赖一样使用哈希锁定。"""
    lock = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")

    assert "--generate-hashes" in lock
    assert "--allow-unsafe" in lock
    assert "--hash=sha256:" in lock


def test_public_repository_excludes_internal_working_files():
    """本地 Issue、交接和代理说明不得进入公开仓库。"""
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    for path in (
        ".ruff_cache/",
        ".scratch/",
        "AGENTS.md",
        "docs/agents/",
        "tasks.md",
        "checklist.md",
        "改动日志.md",
        "交接文档.md",
    ):
        assert path in ignored


def test_github_community_files_are_complete():
    """公开仓库必须提供基本社区协作入口。"""
    required_files = (
        "CODE_OF_CONDUCT.md",
        "SUPPORT.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
    )

    for relative_path in required_files:
        path = ROOT / relative_path
        assert path.is_file()
        assert path.read_text(encoding="utf-8").strip()


def test_english_public_docs_are_complete():
    """公开仓库必须同时提供可独立阅读的英文入口文档。"""
    required_files = (
        "README.en.md",
        "CHANGELOG.en.md",
        "SECURITY.en.md",
        "SUPPORT.en.md",
        "CONTRIBUTING.en.md",
        "CODE_OF_CONDUCT.en.md",
    )

    for relative_path in required_files:
        path = ROOT / relative_path
        assert path.is_file()
        assert path.read_text(encoding="utf-8").strip()

    english_readme = (ROOT / "README.en.md").read_text(encoding="utf-8")
    assert "does not keep clipboard history" in english_readme
    assert "does not need network access at runtime" in english_readme
    assert "SECURITY.en.md" in english_readme


def test_runtime_language_release_materials_match_rc3():
    """rc.3 发布材料必须说明运行时语言切换且保持中英文同步。"""
    chinese_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    english_readme = (ROOT / "README.en.md").read_text(encoding="utf-8")
    chinese_changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    english_changelog = (ROOT / "CHANGELOG.en.md").read_text(encoding="utf-8")

    assert "# PastePeek v2.0.0-rc.3" in chinese_readme
    assert "# PastePeek v2.0.0-rc.3" in english_readme
    assert "## 语言切换" in chinese_readme
    assert "## Runtime Language" in english_readme
    assert "## v2.0.0-rc.3" in chinese_changelog
    assert "## v2.0.0-rc.3" in english_changelog
    assert "语言切换" in chinese_changelog
    assert "runtime language" in english_changelog.lower()


def test_public_metadata_matches_prerelease_scope():
    """许可证署名和构建提示必须与预发布范围一致。"""
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    build_script = (ROOT / "build.py").read_text(encoding="utf-8")

    assert "Copyright (c) 2026 PastePeek contributors" in license_text
    assert "any Windows 10/11 machine" not in build_script


def test_changelog_uses_release_checksum_as_source_of_truth():
    """公开变更日志不得固化本机构建生成的临时 EXE 哈希。"""
    import re

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert not re.search(r"`[0-9a-fA-F]{64}`", changelog)
    assert "以 GitHub Release 附带的 `.sha256` 文件为准" in changelog
