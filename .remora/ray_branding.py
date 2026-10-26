#!/usr/bin/env python3
"""Apply the Ray display brand without changing installed apps' stable identifiers."""

from pathlib import Path
import re
import runpy
import sys


if len(sys.argv) != 4:
    raise SystemExit("usage: ray_branding.py OldTitle NewTitle /path/to/checkout")

old_title, new_title, root_arg = sys.argv[1:]
root = Path(root_arg)
old_slug = old_title.lower()
new_slug = new_title.lower()
word = re.compile(rf"(?<!\w){re.escape(old_title)}(?!\w)")


def rewrite(path: Path, transform) -> None:
    if not path.is_file():
        raise SystemExit(f"missing branding source: {path}")
    original = path.read_text(encoding="utf-8")
    updated = transform(original)
    if updated == original:
        raise SystemExit(f"expected {old_title} in {path}")
    path.write_text(updated, encoding="utf-8")


# Keep CFBundleIdentifier, executable and icon names stable so existing installations
# and document associations survive an update. Finder uses CFBundleDisplayName.
def mac_plist(text: str) -> str:
    text = word.sub(new_title, text)
    for key in ("CFBundleExecutable", "CFBundleIconFile", "UTTypeIconFile", "CFBundleTypeIconFile"):
        marker = f"<key>{key}</key>\n  <string>{new_title}</string>"
        if key in ("CFBundleExecutable", "CFBundleIconFile") and marker not in text:
            raise SystemExit(f"missing {key} in Mac plist")
        text = text.replace(marker, f"<key>{key}</key>\n  <string>{old_title}</string>")
    # Document icon declarations use deeper indentation than top-level keys.
    text = re.sub(
        rf"(<key>(?:UTTypeIconFile|CFBundleTypeIconFile)</key>\s*<string>){re.escape(new_title)}(</string>)",
        rf"\g<1>{old_title}\2",
        text,
    )
    # The upstream authors keep their original copyright attribution.
    text = text.replace(f"the {new_title} authors", f"the {old_title} authors")
    return text


rewrite(root / "packaging/macos/Info.plist.in", mac_plist)


def mac_package(text: str) -> str:
    old_dmg = f"{old_slug}-$VERSION-macos-$ARCH.dmg"
    if old_dmg not in text:
        raise SystemExit("Mac DMG output name changed upstream")
    text = text.replace(old_dmg, f"{new_slug}-$VERSION-macos-$ARCH.dmg")
    # Finder uses the .app folder name inside the DMG, not just CFBundleDisplayName.
    # Keep the bundle ID and executable name stable for existing users.
    text = text.replace(f"{old_title}.app", f"{new_title}.app")
    text = text.replace(f'-hfs-volume-name "{old_title}"', f'-hfs-volume-name "{new_title}"')
    text = text.replace(f'-volname "{old_title}"', f'-volname "{new_title}"')
    # Apple's ticket lookup occasionally loses its CloudKit connection even
    # after notarization and stapling succeed. Some forks already retry it.
    direct = 'xcrun stapler validate "$DMG"'
    if direct in text:
        marker = "set -euo pipefail\n"
        if marker not in text:
            raise SystemExit("Mac package script has no strict-mode marker")
        helper = """
validate_staple() {
  local attempt
  for attempt in 1 2 3 4 5; do
    if xcrun stapler validate "$1"; then return 0; fi
    [[ "$attempt" = 5 ]] && return 1
    echo "Stapler lookup failed (attempt $attempt of 5); retrying" >&2
    sleep $((attempt * 5))
  done
}
"""
        text = text.replace(marker, marker + helper, 1)
        text = text.replace('xcrun stapler validate "$APP"', 'validate_staple "$APP"')
        text = text.replace(direct, 'validate_staple "$DMG"')
    elif 'stapler_retry validate "$DMG"' not in text:
        raise SystemExit("Mac package script has no DMG ticket validation")
    return text


rewrite(root / "packaging/macos/package.sh", mac_package)

# Keep the Finder icon position and background alias in sync with the new
# .app folder and volume name. This runs only on the Mac CI job.
dmg_generator = root / "packaging/macos/dmg/generate.py"
if dmg_generator.is_file():
    def dmg_layout(text: str) -> str:
        volume = f'VOLUME = "{old_title}"'
        icon = f'"{old_title}.app":'
        if volume not in text or icon not in text:
            raise SystemExit("DMG layout source changed upstream")
        return text.replace(volume, f'VOLUME = "{new_title}"').replace(
            icon, f'"{new_title}.app":'
        )

    rewrite(dmg_generator, dmg_layout)
    if sys.platform == "darwin":
        layout_dir = dmg_generator.parent
        layout_name = "DS_Store" if (layout_dir / "DS_Store").is_file() else "dmg-layout.DS_Store"
        runpy.run_path(str(dmg_generator))["write_ds_store"](str(layout_dir / layout_name))


def windows_package(text: str) -> str:
    old_installer = f"{old_slug}-$Version-windows-$Arch"
    if old_installer not in text:
        raise SystemExit("Windows installer output name changed upstream")
    text = text.replace(old_installer, f"{new_slug}-$Version-windows-$Arch")
    return word.sub(new_title, text)


rewrite(root / "packaging/windows/package.ps1", windows_package)


def wix(text: str) -> str:
    text = word.sub(new_title, text)
    # The old registry location is used to find and upgrade existing installs.
    text = text.replace(f"Software\\{new_title}", f"Software\\{old_title}")
    # PDF shell verbs and the registered ProgID are stable Windows identities.
    # Changing their keys would orphan an existing install's associations.
    if old_slug == "pdfcraft":
        for suffix in (".Document", ".Edit", ".CreatePdf"):
            text = text.replace(f"{new_title}{suffix}", f"{old_title}{suffix}")
        text = text.replace(f'FileSearch Name="{new_title}.lnk"', f'FileSearch Name="{old_title}.lnk"')
        old_search = f'''        <FileSearch Name="{old_title}.lnk" />
      </DirectorySearch>
    </Property>'''
        new_search = old_search + f'''
    <Property Id="EXISTINGRAYDESKTOPSHORTCUT">
      <DirectorySearch Id="RayDesktopSearch" Path="[DesktopFolder]" Depth="0">
        <FileSearch Name="{new_title}.lnk" />
      </DirectorySearch>
    </Property>'''
        if old_search not in text:
            raise SystemExit("PDF desktop upgrade search changed upstream")
        text = text.replace(old_search, new_search, 1)
        text = text.replace(
            "OR EXISTINGDESKTOPSHORTCUT)",
            "OR EXISTINGDESKTOPSHORTCUT OR EXISTINGRAYDESKTOPSHORTCUT)",
            1,
        )
        text = text.replace(
            f'Name="{new_title}" Value="Software\\{old_title}\\Capabilities"',
            f'Name="{old_title}" Value="Software\\{old_title}\\Capabilities"',
        )
    text = text.replace('Manufacturer="Learning Machines LLC"', 'Manufacturer="Andrei Avram"')
    return text


rewrite(root / "packaging/windows" / f"{old_slug}.wxs", wix)
for extra in (root / "packaging/windows").glob("*.wxs"):
    if extra.name == f"{old_slug}.wxs":
        continue
    original = extra.read_text(encoding="utf-8")
    updated = word.sub(new_title, original)
    if updated != original:
        extra.write_text(updated, encoding="utf-8")

# PdfCraft validates its compiled MSI against the public labels in WiX. Keep
# the assertions current while preserving the old registry keys tested there.
pdf_msi_test = root / "packaging/windows/test-msi.ps1"
if old_slug == "pdfcraft" and pdf_msi_test.is_file():
    original = pdf_msi_test.read_text(encoding="utf-8-sig")
    updated = original
    for label in (
        "must be installed for all users",
        "PDF workbench",
    ):
        updated = updated.replace(f"{old_title} {label}", f"{new_title} {label}")
    updated = updated.replace(f"with {old_title}", f"with {new_title}")
    updated = updated.replace("'Learning Machines LLC' 'MSI manufacturer'", "'Andrei Avram' 'MSI manufacturer'")
    old_upgrade_check = ("Assert-KeptOnUpdate 'INSTALLDESKTOPSHORTCUT' 'WIX_UPGRADE_DETECTED' "
                         "'EXISTINGDESKTOPSHORTCUT' 'C:\\Users\\Public\\Desktop\\PdfCraft.lnk' "
                         "'PdfcraftDesktopShortcut' 'Desktop shortcut'")
    if old_upgrade_check not in updated:
        raise SystemExit("PDF desktop upgrade test changed upstream")
    updated = updated.replace(old_upgrade_check, old_upgrade_check + "\n" +
        "Assert-KeptOnUpdate 'INSTALLDESKTOPSHORTCUT' 'WIX_UPGRADE_DETECTED' "
        "'EXISTINGRAYDESKTOPSHORTCUT' 'C:\\Users\\Public\\Desktop\\PdfRay.lnk' "
        "'PdfcraftDesktopShortcut' 'Ray desktop shortcut'")
    if updated == original:
        raise SystemExit("PDF MSI branding assertions not found")
    pdf_msi_test.write_text(updated, encoding="utf-8-sig")


# Change text shown by the running app, including window titles, menus, dialogs,
# notifications and translated UI. Keep paths, serialized markers, and author credit.
# Stay within one source line. A multiline match can start at the closing
# quote of one Rust string and consume code up to the next opening quote.
string_literal = re.compile(r'"(?:\\.|[^"\\\n])*"')


def ui_source(text: str) -> str:
    def replace_literal(match: re.Match[str]) -> str:
        value = match.group()
        if "authors" in value or "Copyright" in value:
            return value
        if any(token in value for token in (
            f"{old_title}.portable", f"{old_title}.app", f"{old_title}.icns",
            f"{old_title}Data", f"/{old_title}", f"\\\\{old_title}",
        )):
            return value
        return word.sub(new_title, value).replace(f"{old_title}u", new_title)

    return string_literal.sub(replace_literal, text)


for source_dir in (root / "apps" / old_slug / "src", root / "crates/ui-egui/src"):
    if not source_dir.exists():
        continue
    for path in source_dir.rglob("*.rs"):
        # These files hold persistent settings paths. Renaming those would hide
        # existing preferences and break portable installations.
        if path.name in ("app_dirs.rs", "profile.rs"):
            continue
        original = path.read_text(encoding="utf-8")
        updated = ui_source(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")

build_script = root / "apps" / old_slug / "build.rs"
if build_script.is_file():
    original = build_script.read_text(encoding="utf-8")
    updated = ui_source(original)
    if updated != original:
        build_script.write_text(updated, encoding="utf-8")

for path in (root / "crates/ui-egui/src").rglob("*.tsv"):
    original = path.read_text(encoding="utf-8")
    updated = "\n".join(
        line if "authors" in line or "Copyright" in line else word.sub(new_title, line).replace(f"{old_title}u", new_title)
        for line in original.split("\n")
    )
    if updated != original:
        path.write_text(updated, encoding="utf-8")

print(f"{old_title} → {new_title}: display branding applied; bundle, registry and executable IDs unchanged")
