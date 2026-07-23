#!/usr/bin/env python3
"""
bump_patch_version.py — Automatyczna inkrementacja wersji patch (1.7.x -> 1.7.x+1).
Aktualizuje wersję w src/main.py, src/static/index.html, README.md i CHANGELOG.md.
"""

import sys
import re
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MAIN_PY_PATH = PROJECT_ROOT / "src" / "main.py"
INDEX_HTML_PATH = PROJECT_ROOT / "src" / "static" / "index.html"
README_PATH = PROJECT_ROOT / "README.md"
CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.md"

def bump_version():
    msg = sys.argv[1] if len(sys.argv) > 1 else None

    if not MAIN_PY_PATH.exists():
        print(f"Error: {MAIN_PY_PATH} not found.")
        sys.exit(1)

    content = MAIN_PY_PATH.read_text(encoding="utf-8")
    
    # Znajdź obecną wersję z main.py
    match = re.search(r'version="(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        match = re.search(r'"version":\s*"(\d+)\.(\d+)\.(\d+)"', content)
    
    if not match:
        print("Error: Could not determine current version from src/main.py")
        sys.exit(1)

    major, minor, patch = map(int, match.groups())
    old_version = f"{major}.{minor}.{patch}"
    new_patch = patch + 1
    new_version = f"{major}.{minor}.{new_patch}"

    # 1. Update src/main.py
    new_main_content = re.sub(
        r'version="' + re.escape(old_version) + r'"',
        f'version="{new_version}"',
        content
    )
    new_main_content = re.sub(
        r'"version":\s*"' + re.escape(old_version) + r'"',
        f'"version": "{new_version}"',
        new_main_content
    )
    MAIN_PY_PATH.write_text(new_main_content, encoding="utf-8")

    # 2. Update src/static/index.html
    if INDEX_HTML_PATH.exists():
        html_content = INDEX_HTML_PATH.read_text(encoding="utf-8")
        new_html_content = re.sub(
            r'OSINT v' + re.escape(old_version),
            f'OSINT v{new_version}',
            html_content
        )
        new_html_content = re.sub(
            r'styles\.css\?v=' + re.escape(old_version),
            f'styles.css?v={new_version}',
            new_html_content
        )
        new_html_content = re.sub(
            r'app\.js\?v=' + re.escape(old_version),
            f'app.js?v={new_version}',
            new_html_content
        )
        INDEX_HTML_PATH.write_text(new_html_content, encoding="utf-8")

    # 3. Update README.md
    if README_PATH.exists():
        readme_content = README_PATH.read_text(encoding="utf-8")
        new_readme_content = re.sub(
            r'"version":\s*"' + re.escape(old_version) + r'"',
            f'"version": "{new_version}"',
            readme_content
        )
        README_PATH.write_text(new_readme_content, encoding="utf-8")

    # 4. Update CHANGELOG.md
    if CHANGELOG_PATH.exists():
        changelog_content = CHANGELOG_PATH.read_text(encoding="utf-8")
        version_header = f"## [{new_version}]"
        
        if version_header not in changelog_content:
            today_str = datetime.now().strftime("%Y-%m-%d")
            entry_title = f"{version_header} - {today_str}"
            note_text = msg if msg else f"Automatyczna inkrementacja wersji do {new_version}."
            entry_body = f"\n{entry_title}\n\n### Added\n- {note_text}\n"
            
            if "## [Unreleased]" in changelog_content:
                changelog_content = changelog_content.replace(
                    "## [Unreleased]",
                    f"## [Unreleased]\n{entry_body}"
                )
            else:
                old_header_match = re.search(r'## \[\d+\.\d+\.\d+\]', changelog_content)
                if old_header_match:
                    pos = old_header_match.start()
                    changelog_content = changelog_content[:pos] + entry_body.lstrip() + "\n" + changelog_content[pos:]
                else:
                    changelog_content += f"\n{entry_body}"
                    
            CHANGELOG_PATH.write_text(changelog_content, encoding="utf-8")

    print(f"[Version Bump] Updated version: {old_version} -> {new_version}")

if __name__ == "__main__":
    bump_version()
