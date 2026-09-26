import subprocess
import tarfile
import zipfile
import re
import json
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from st_graph_workbench.component import component, styles
from st_graph_workbench.component.icons import SUPPORTED_ICONS
from st_graph_workbench.component._warnings import GraphWorkbenchDeprecationWarning


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_REPOSITORY_URL = (
    "https://raw.githubusercontent.com/ayhaidar/st-graph-workbench/main/"
)


def _archive_name(path: str) -> str:
    return PurePosixPath(path).name


def test_streamlit_dependency_floor_matches_components_v2_usage():
    pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    installation = (
        ROOT_DIR / "docs" / "getting-started" / "installation.md"
    ).read_text(encoding="utf-8")

    assert '"streamlit >= 1.57"' in pyproject
    assert "Streamlit 1.57 or newer" in installation


def test_pandas_dependency_floor_avoids_numpy_2_binary_incompatibility():
    pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    installation = (
        ROOT_DIR / "docs" / "getting-started" / "installation.md"
    ).read_text(encoding="utf-8")

    assert '"pandas >= 2.2.2"' in pyproject
    assert "pandas 2.2.2 or newer" in installation


def test_readme_leads_with_package_install_commands():
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")

    assert "uv add st-graph-workbench" in readme
    assert "python -m pip install st-graph-workbench" in readme
    assert "Install the current checkout" not in readme


def test_package_metadata_links_to_the_manual_and_project():
    pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        'Documentation = "https://ayhaidar.github.io/st-graph-workbench/"' in pyproject
    )
    assert 'Homepage = "https://github.com/ayhaidar/st-graph-workbench"' in pyproject


def test_docs_use_material_symbols_wording():
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    styles = (ROOT_DIR / "st_graph_workbench" / "component" / "styles.py").read_text(
        encoding="utf-8"
    )

    assert "Material Symbols" in readme
    assert "Material Symbols-style SVG assets" in styles
    assert "Material Icons" not in readme
    assert "Material Icons" not in styles


def test_examples_logo_assets_are_documented_and_packaged():
    pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    app = (ROOT_DIR / "examples" / "app.py").read_text(encoding="utf-8")
    readme_page = (ROOT_DIR / "examples" / "docs" / "project_overview.py").read_text(
        encoding="utf-8"
    )

    assert (ROOT_DIR / "images" / "logo.png").is_file()
    assert (ROOT_DIR / "images" / "logo_icon.png").is_file()
    assert '"images/logo.png"' in pyproject
    assert '"images/logo_icon.png"' in pyproject
    assert "images/logo.png" in readme
    assert "images/logo_icon.png" in (ROOT_DIR / "examples/README.md").read_text(
        encoding="utf-8"
    )
    assert 'LOGO_PATH = ROOT_DIR / "images" / "logo.png"' in app
    assert 'LOGO_ICON_PATH = ROOT_DIR / "images" / "logo_icon.png"' in app
    assert "SIDEBAR_LOGO_PATH = LOGO_ICON_PATH if LOGO_ICON_PATH.exists()" in app
    assert "page_icon=APP_ICON" in app
    assert "st.logo(" in app
    assert "str(SIDEBAR_LOGO_PATH)" in app
    assert "icon_image=APP_ICON" in app
    assert 'LOGO_PATH = ROOT_DIR / "images" / "logo.png"' in readme_page
    assert 'with st.container(horizontal_alignment="center"):' in readme_page
    assert "st.image(str(LOGO_PATH), width=400)" in readme_page
    assert "render_library_badges(" in readme_page


def test_local_streamlit_review_artifacts_are_ignored():
    gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")

    assert ".tmp/" in gitignore


def test_library_badges_cover_runtime_stack():
    page_overview = (ROOT_DIR / "examples" / "page_overview.py").read_text(
        encoding="utf-8"
    )
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")

    for label in (
        "Cytoscape.js",
        "Streamlit",
        "Python",
        "Pandas",
        "Components v2",
        "Material Symbols",
    ):
        assert label in page_overview
        assert label in readme
    assert "columns_per_row: int = 3" in page_overview
    assert "st.badge(label, icon=icon, color=color)" in page_overview


def test_component_manifest_matches_python_registration():
    package_manifest = (ROOT_DIR / "st_graph_workbench" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    wrapper = (
        ROOT_DIR / "st_graph_workbench" / "component" / "component.py"
    ).read_text(encoding="utf-8")

    assert 'name = "st_graph_workbench"' in package_manifest
    assert 'name = "graph_workbench"' in package_manifest
    assert 'asset_dir = "frontend/build"' in package_manifest
    assert '_COMPONENT_NAME = "st_graph_workbench.graph_workbench"' in wrapper
    assert 'asset_dir="frontend/build"' in wrapper
    assert 'css="style.css"' in wrapper
    assert 'js="index-*.js"' in wrapper


def test_release_version_is_consistent_across_package_boundaries():
    root_pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    component_manifest = (ROOT_DIR / "st_graph_workbench" / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    wrapper = (
        ROOT_DIR / "st_graph_workbench" / "component" / "component.py"
    ).read_text(encoding="utf-8")
    frontend_package = json.loads(
        (ROOT_DIR / "st_graph_workbench" / "frontend" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    [version] = re.findall(r'^version = "([^"]+)"$', root_pyproject, re.MULTILINE)

    assert f'version = "{version}"' in component_manifest
    assert f'version="{version}"' in wrapper
    assert frontend_package["version"] == version
    assert f"## [{version}]" in (ROOT_DIR / "CHANGELOG.md").read_text(encoding="utf-8")


def test_component_instance_keys_are_lossless():
    key_with_underscores = component._component_instance_key("case__left")
    key_with_hyphens = component._component_instance_key("case--left")

    assert key_with_underscores == "st-graph-workbench-v2-636173655f5f6c656674"
    assert key_with_hyphens == "st-graph-workbench-v2-636173652d2d6c656674"
    assert "__" not in key_with_underscores
    assert "__" not in key_with_hyphens
    assert key_with_underscores != key_with_hyphens
    assert component._elements_sync_state_key(
        key_with_underscores
    ) != component._elements_sync_state_key(key_with_hyphens)


def test_component_source_uses_components_v2_only():
    wrapper = (
        ROOT_DIR / "st_graph_workbench" / "component" / "component.py"
    ).read_text(encoding="utf-8")
    frontend_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT_DIR / "st_graph_workbench" / "frontend" / "src").rglob("*")
        if path.suffix in {".html", ".js"}
    )

    assert "st.components.v2.component" in wrapper
    for banned in ("components.v1", "declare_component("):
        assert banned not in wrapper
    for banned in (
        "Streamlit.setComponentValue",
        "Streamlit.setFrameHeight",
        "Streamlit.setComponentReady",
        "window.Streamlit",
        "window.parent.postMessage",
    ):
        assert banned not in frontend_source


def test_frontend_build_has_single_component_entry_bundle():
    build_dir = ROOT_DIR / "st_graph_workbench" / "frontend" / "build"

    assert (build_dir / "component.html").is_file()
    assert (build_dir / "style.css").is_file()
    assert len(list(build_dir.glob("index-*.js"))) == 1
    assert any(
        path.name[0].isdigit() and path.suffix == ".js"
        for path in build_dir.glob("*.js")
    )


def test_frontend_entry_bundle_stays_under_configured_budget():
    build_dir = ROOT_DIR / "st_graph_workbench" / "frontend" / "build"
    webpack_config = (
        ROOT_DIR / "st_graph_workbench" / "frontend" / "webpack.config.js"
    ).read_text(encoding="utf-8")
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    [entry_bundle] = list(build_dir.glob("index-*.js"))

    assert "maxAssetSize: 512000" in webpack_config
    assert "maxEntrypointSize: 512000" in webpack_config
    assert entry_bundle.stat().st_size <= 512000
    assert "512 KB entry and asset budget" in readme
    assert "asynchronous chunks" in readme


def test_wheel_configuration_ships_component_manifest_and_build_assets():
    pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    development_docs = (ROOT_DIR / "docs" / "advanced" / "development.md").read_text(
        encoding="utf-8"
    )

    assert '"st_graph_workbench/pyproject.toml"' in pyproject
    assert '"st_graph_workbench/frontend/build/**"' in pyproject
    assert "async chunks" in development_docs


def test_mkdocs_dependencies_and_ci_build_are_configured():
    pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    workflow = (ROOT_DIR / ".github" / "workflows" / "pr_checks.yml").read_text(
        encoding="utf-8"
    )

    assert '"mkdocs >= 1.6, < 2"' in pyproject
    assert '"mkdocs-material >= 9.7, < 10"' in pyproject
    assert '"mkdocstrings[python] >= 1, < 2"' in pyproject
    assert "uv run mkdocs build --strict" in workflow
    assert "mkdocs gh-deploy" not in workflow


def test_ci_covers_release_refs_and_supported_python_versions():
    workflow = (ROOT_DIR / ".github" / "workflows" / "pr_checks.yml").read_text(
        encoding="utf-8"
    )

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert 'tags: ["v*"]' in workflow
    assert 'PY_VERSION: ["3.10", "3.11", "3.12", "3.13", "3.14"]' in workflow
    assert "verify_minimum_dependencies.py" in workflow
    assert '"pandas==2.2.2"' in workflow
    assert '"streamlit==1.57.0"' in workflow


def test_public_actions_are_pinned_to_commit_shas():
    workflow_paths = [
        ROOT_DIR / ".github" / "workflows" / "pr_checks.yml",
        ROOT_DIR / ".github" / "actions" / "setup-python" / "action.yml",
        ROOT_DIR / ".github" / "actions" / "setup-node" / "action.yml",
    ]
    uses_pattern = re.compile(r"uses:\s+([^\s]+)")
    sha_pattern = re.compile(r"^[^@]+@[0-9a-f]{40}$")

    external_uses = []
    for path in workflow_paths:
        for value in uses_pattern.findall(path.read_text(encoding="utf-8")):
            if not value.startswith("./"):
                external_uses.append(value)

    assert external_uses
    assert [value for value in external_uses if not sha_pattern.fullmatch(value)] == []


def test_contributor_and_security_policies_are_present():
    assert (ROOT_DIR / "CONTRIBUTING.md").is_file()
    assert (ROOT_DIR / "SECURITY.md").is_file()


def test_local_build_artifacts_ship_runtime_and_source_assets(tmp_path):
    subprocess.run(
        ["uv", "build", "--out-dir", str(tmp_path)],
        cwd=ROOT_DIR,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(tmp_path.glob("st_graph_workbench-*.whl"))
    sdist = next(tmp_path.glob("st_graph_workbench-*.tar.gz"))

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = set(archive.namelist())
        [metadata_name] = [
            name for name in wheel_names if name.endswith(".dist-info/METADATA")
        ]
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
        assert metadata["License-Expression"] == "Apache-2.0"
        description = metadata.get_payload()
        assert RAW_REPOSITORY_URL in description
        assert 'src="images/' not in description
        assert "](docs/assets/screenshots/" not in description
        license_paths = {
            "LICENSE",
            "NOTICE",
            "THIRD_PARTY_NOTICES.md",
            "licenses/st-link-analysis.txt",
            "licenses/material-symbols.txt",
        }
        assert set(metadata.get_all("License-File", [])) == license_paths
        metadata_dir = PurePosixPath(metadata_name).parent
        for path in license_paths:
            packaged = archive.read(f"{metadata_dir}/licenses/{path}").decode("utf-8")
            assert packaged.replace("\r\n", "\n") == (ROOT_DIR / path).read_text(
                encoding="utf-8"
            )

    build_prefix = "st_graph_workbench/frontend/build/"
    wheel_index_bundles = [
        name
        for name in wheel_names
        if name.startswith(f"{build_prefix}index-") and name.endswith(".js")
    ]
    wheel_extra_chunks = [
        name
        for name in wheel_names
        if name.startswith(build_prefix)
        and _archive_name(name)[0].isdigit()
        and name.endswith(".js")
    ]
    wheel_icon_names = {
        PurePosixPath(name).stem
        for name in wheel_names
        if name.startswith(f"{build_prefix}icons/") and name.endswith(".svg")
    }

    assert "st_graph_workbench/pyproject.toml" in wheel_names
    assert f"{build_prefix}component.html" in wheel_names
    assert f"{build_prefix}style.css" in wheel_names
    assert len(wheel_index_bundles) == 1
    assert wheel_extra_chunks
    assert wheel_icon_names == set(SUPPORTED_ICONS)
    assert "st_graph_workbench/py.typed" in wheel_names
    assert f"{build_prefix}THIRD_PARTY_LICENSES.txt" in wheel_names
    assert any(name.endswith("/licenses/st-link-analysis.txt") for name in wheel_names)
    assert any(name.endswith("/licenses/material-symbols.txt") for name in wheel_names)
    assert any(name.endswith("/THIRD_PARTY_NOTICES.md") for name in wheel_names)
    assert not any(name.startswith("examples/") for name in wheel_names)
    assert not any("/frontend/src/" in name for name in wheel_names)

    with tarfile.open(sdist, mode="r:gz") as archive:
        sdist_names = set(archive.getnames())
        [metadata_name] = [name for name in sdist_names if name.endswith("/PKG-INFO")]
        with archive.extractfile(metadata_name) as metadata_file:
            metadata = BytesParser().parsebytes(metadata_file.read())
        assert metadata["License-Expression"] == "Apache-2.0"
        assert set(metadata.get_all("License-File", [])) == license_paths
        archive_root = PurePosixPath(metadata_name).parent
        for path in license_paths:
            with archive.extractfile(f"{archive_root}/{path}") as license_file:
                packaged = license_file.read().decode("utf-8")
            assert packaged.replace("\r\n", "\n") == (ROOT_DIR / path).read_text(
                encoding="utf-8"
            )

    assert any(name.endswith("/README.md") for name in sdist_names)
    assert any(name.endswith("/CONTRIBUTING.md") for name in sdist_names)
    assert any(name.endswith("/SECURITY.md") for name in sdist_names)
    assert any(name.endswith("/hatch_build.py") for name in sdist_names)
    assert any(name.endswith("/CHANGELOG.md") for name in sdist_names)
    assert any(name.endswith("/st_graph_workbench/py.typed") for name in sdist_names)
    assert any(name.endswith("/licenses/st-link-analysis.txt") for name in sdist_names)
    assert any(name.endswith("/licenses/material-symbols.txt") for name in sdist_names)
    assert any(name.endswith("/scripts/verify_release.py") for name in sdist_names)
    assert any(
        name.endswith("/scripts/verify_minimum_dependencies.py") for name in sdist_names
    )
    assert any(
        name.endswith("/frontend/scripts/write_licenses.cjs") for name in sdist_names
    )
    assert any(name.endswith("/mkdocs.yml") for name in sdist_names)
    assert any(name.endswith("/mkdocs.local.yml") for name in sdist_names)
    assert any(name.endswith("/docs/index.md") for name in sdist_names)
    assert not any(
        name.endswith("/docs/advanced/publishing.md") for name in sdist_names
    )
    assert not any("/.maintainer/" in name for name in sdist_names)
    assert any(
        name.endswith("/docs/getting-started/tutorials.md") for name in sdist_names
    )
    assert any(
        name.endswith("/examples/tutorials/first_graph.py") for name in sdist_names
    )
    assert any(name.endswith("/examples/page_links.py") for name in sdist_names)
    assert any(
        name.endswith("/scripts/capture_docs_screenshots.py") for name in sdist_names
    )
    assert any(
        name.endswith("/docs/assets/screenshots/showcase.png") for name in sdist_names
    )
    assert any(name.endswith("/images/logo.png") for name in sdist_names)
    assert any(name.endswith("/images/logo_icon.png") for name in sdist_names)
    assert any(
        name.endswith("/examples/data/intelligence_case.json") for name in sdist_names
    )
    assert not any(name.endswith("/examples/data/company.json") for name in sdist_names)
    assert any(
        name.endswith("/st_graph_workbench/frontend/src/index.js")
        for name in sdist_names
    )
    assert any(
        name.endswith("/st_graph_workbench/frontend/build/component.html")
        for name in sdist_names
    )
    assert not any("/node_modules/" in name for name in sdist_names)
    assert not any("/docs/" in name for name in wheel_names)
    assert not any(name.startswith("examples/") for name in wheel_names)
    assert not any("/frontend/scripts/" in name for name in wheel_names)


def test_frontend_notices_cover_locked_production_dependencies():
    frontend = ROOT_DIR / "st_graph_workbench/frontend"
    lock = json.loads((frontend / "package-lock.json").read_text(encoding="utf-8"))
    notices = (frontend / "build/THIRD_PARTY_LICENSES.txt").read_text(encoding="utf-8")
    for directory, package in lock["packages"].items():
        if not directory or package.get("dev"):
            continue
        name = directory.split("node_modules/")[-1]
        assert f"{name}@{package['version']}" in notices
    assert "Permission is hereby granted" in notices
    assert "Copyright (c) 2024 AlrasheedA" in (
        ROOT_DIR / "licenses/st-link-analysis.txt"
    ).read_text(encoding="utf-8")
    assert "Apache License" in (ROOT_DIR / "licenses/material-symbols.txt").read_text(
        encoding="utf-8"
    )


def test_project_license_and_documentation_are_consistent():
    frontend = ROOT_DIR / "st_graph_workbench/frontend"
    package = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((frontend / "package-lock.json").read_text(encoding="utf-8"))
    assert package["license"] == "Apache-2.0"
    assert lock["packages"][""]["license"] == "Apache-2.0"
    license_text = (ROOT_DIR / "LICENSE").read_text(encoding="utf-8")
    assert "Version 2.0, January 2004" in license_text
    assert "END OF TERMS AND CONDITIONS" in license_text
    assert "Copyright 2026 Ali Haidar" in (ROOT_DIR / "NOTICE").read_text(
        encoding="utf-8"
    )
    for path in ("README.md", "docs/index.md", "docs/license.md"):
        assert "Apache License" in (ROOT_DIR / path).read_text(encoding="utf-8")
    docs = (ROOT_DIR / "docs/license.md").read_text(encoding="utf-8")
    assert '--8<-- "LICENSE"' in docs
    assert '--8<-- "NOTICE"' in docs


def test_readme_links_and_banner_resolve_from_the_checkout():
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\]\(([^)]+)\)", readme)
    targets.extend(re.findall(r'<img[^>]+src="([^"]+)"', readme))
    assert targets
    for target in targets:
        if target.startswith("#"):
            continue
        if target.startswith(("https://", "http://")):
            if "/blob/main/" in target:
                file_path = urlsplit(target).path.split("/blob/main/", 1)[1]
                assert (ROOT_DIR / file_path).is_file()
            continue
        local_target = target.split("#", 1)[0]
        assert local_target, target
        assert (ROOT_DIR / local_target).is_file(), target
    overview = (ROOT_DIR / "examples/docs/project_overview.py").read_text(
        encoding="utf-8"
    )
    [banner] = re.findall(r'<img[^>]+src="([^"]+)"', readme)
    assert banner in overview


def test_ci_installs_documentation_for_full_suite_without_retries():
    setup = (ROOT_DIR / ".github/actions/setup-python/action.yml").read_text(
        encoding="utf-8"
    )
    workflow = (ROOT_DIR / ".github/workflows/pr_checks.yml").read_text(
        encoding="utf-8"
    )
    pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert "uv sync --extra dev --extra docs --frozen" in setup
    assert "uv run pytest --reruns=0" in workflow
    assert "uv run python scripts/verify_release.py" in workflow
    assert "uv run playwright install --with-deps chromium" in setup
    assert 'addopts = "--reruns=0"' in pyproject


def test_built_icon_assets_match_supported_icons():
    icons_dir = ROOT_DIR / "st_graph_workbench" / "frontend" / "build" / "icons"
    built_icon_names = {path.stem for path in icons_dir.glob("*.svg")}

    assert built_icon_names == set(SUPPORTED_ICONS)


def test_deprecation_warning_category_is_shared():
    assert styles.GraphWorkbenchDeprecationWarning is GraphWorkbenchDeprecationWarning
    assert (
        component.GraphWorkbenchDeprecationWarning is GraphWorkbenchDeprecationWarning
    )
