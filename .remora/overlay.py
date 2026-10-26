#!/usr/bin/env python3
"""Apply personal icons to a temporary Craft build checkout."""
from pathlib import Path
from PIL import Image
import re
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: overlay.py AppTitle /path/to/temporary/worktree')
title, root_arg = sys.argv[1:]
root = Path(root_arg)
icons = Path(__file__).resolve().parent
slug = title.lower()
source = icons / f'{title}.png'
if not source.is_file() or not (root / '.git').exists():
    raise SystemExit('icon or temporary checkout missing')
image = Image.open(source).convert('RGBA')
asset_dir = root / 'assets' / 'app-icon'
paths = {}
for path in asset_dir.glob(f'{slug}-*.png'):
    match = re.fullmatch(rf'{re.escape(slug)}-(?:macos-)?(\d+)\.png', path.name)
    if match:
        paths[path] = int(match.group(1))
for path in (asset_dir / 'hicolor').glob(f'*x*/apps/ai.storyteller.{slug}.png'):
    size_text = path.parent.parent.name
    match = re.fullmatch(r'(\d+)x\1', size_text)
    if match:
        paths[path] = int(match.group(1))
updated = []
for path, size in paths.items():
    image.resize((size, size), Image.Resampling.LANCZOS).save(path)
    updated.append(str(path.relative_to(root)))
icns = asset_dir / f'{slug}.icns'
if icns.is_file():
    icns.write_bytes((icons / f'{title}.icns').read_bytes())
    updated.append(str(icns.relative_to(root)))
if not updated:
    raise SystemExit(f'no app icons found in {root}')
print(f'{title}: overlaid {len(updated)} assets: ' + ', '.join(updated))

# PhotoCraft's macOS bundle keeps its .icns in Dock. eframe still needs an
# explicit empty IconData; omitting with_icon makes it draw its default glyph.
# Apply that same behavior to every other locally installed Craft app.
if slug != 'photocraft':
    main = root / 'apps' / slug / 'src' / 'main.rs'
    contents = main.read_text()
    helper = """

/// Prefer the macOS bundle's .icns for the live Dock tile, as PhotoCraft does.
fn use_bundle_dock_icon() -> bool {
    if !cfg!(target_os = "macos") { return false; }
    let Some(exe) = std::env::current_exe().ok() else { return false };
    let Some(macos) = exe.parent() else { return false };
    let Some(contents) = macos.parent() else { return false };
    let Some(bundle) = contents.parent() else { return false };
    macos.file_name() == Some(std::ffi::OsStr::new("MacOS"))
        && contents.file_name() == Some(std::ffi::OsStr::new("Contents"))
        && bundle.extension().and_then(std::ffi::OsStr::to_str).is_some_and(|ext| ext.eq_ignore_ascii_case("app"))
}
"""
    if 'fn use_bundle_dock_icon()' in contents:
        raise SystemExit(f'{title}: bundle icon helper already present')
    if slug in {'vectorcraft', 'filmcraft', 'lightcraft', 'effectcraft'}:
        old = 'fn app_icon() -> egui::IconData {\n'
        new = old + '    if use_bundle_dock_icon() { return egui::IconData::default(); }\n'
    elif slug in {'designcraft', 'soundcraft'}:
        old = 'fn app_icon() -> Option<egui::IconData> {\n'
        new = old + '    if use_bundle_dock_icon() { return Some(egui::IconData::default()); }\n'
    elif slug == 'figcraft':
        old = '    let icon = services::window_icon();'
        new = '    let icon = if use_bundle_dock_icon() { Some(egui::IconData::default()) } else { services::window_icon() };'
    elif slug == 'pdfcraft':
        old = """    match eframe::icon_data::from_png_bytes(APP_ICON_PNG) {
        Ok(icon) => viewport = viewport.with_icon(icon),
        Err(e) => log::warn!("app icon: {e}"),
    }
"""
        new = """    if use_bundle_dock_icon() {
        viewport = viewport.with_icon(egui::IconData::default());
    } else {
        match eframe::icon_data::from_png_bytes(APP_ICON_PNG) {
            Ok(icon) => viewport = viewport.with_icon(icon),
            Err(e) => log::warn!("app icon: {e}"),
        }
    }
"""
    else:
        raise SystemExit(f'{title}: no Dock icon strategy')
    if contents.count(old) != 1:
        raise SystemExit(f'{title}: runtime icon setup changed')
    main.write_text(contents.replace(old, new) + helper)
    print(f'{title}: macOS bundle keeps its .icns in Dock, matching PhotoCraft')

# Personal macOS builds leave the app bar clean; the system Dock/Finder icon remains.
if slug == 'photocraft':
    chrome = root / 'crates' / 'ui-egui' / 'src' / 'panels.rs'
    old = '                if !system {\n                    let side = if t.pro { 18.0 } else { 20.0 };\n                    let (mark, _) = ui.allocate_exact_size(vec2(side, side), Sense::hover());\n                    crate::brand::paint_mark(ui, mark);\n                    ui.add_space(6.0);\n                }\n'
    contents = chrome.read_text()
    if contents.count(old) != 1:
        raise SystemExit('PhotoCraft title-bar layout changed; cannot remove mark safely')
    chrome.write_text(contents.replace(old, ''))
    print('PhotoCraft: removed icon and its spacing from title bar')
elif slug == 'vectorcraft':
    chrome = root / 'crates' / 'ui-egui' / 'src' / 'chrome.rs'
    old = '            // With the system title bar the OS draws its own icon: no in-app brand mark.\n            if !system {\n                let (r, _) = ui.allocate_exact_size(vec2(MARK, MARK), Sense::hover());\n                crate::brand::paint_mark(ui, r);\n                ui.add_space(6.0);\n            }\n'
    contents = chrome.read_text()
    if contents.count(old) != 1:
        raise SystemExit('VectorCraft title-bar layout changed; cannot remove mark safely')
    contents = contents.replace(old, '').replace("/// The brand mark's side.\nconst MARK: f32 = 18.0;\n", '')
    contents = contents.replace('    let system = system_title_bar(app);\n', '')
    chrome.write_text(contents)
    print('VectorCraft: removed icon and its spacing from title bar')
elif slug == 'figcraft':
    tabs = root / 'crates' / 'ui-egui' / 'src' / 'tabs.rs'
    contents = tabs.read_text()
    old = """            icons::paint(
                &painter,
                Rect::from_center_size(pos2(paint_r.min.x + 18.0, paint_r.center().y), vec2(14.0, 14.0)),
                Icon::Logo,
                crate::theme::ACCENT.linear_multiply(progress),
            );
"""
    assert contents.count(old) == 1, 'FigCraft tab mark layout changed'
    contents = contents.replace(old, '')
    contents = contents.replace('pos2(paint_r.min.x + 32.0, paint_r.center().y),', 'pos2(paint_r.min.x + 16.0, paint_r.center().y),', 1)
    contents = contents.replace('(w - mark_w - if dirty { 72.0 } else { 60.0 }).max(0.0),', '(w - mark_w - if dirty { 56.0 } else { 44.0 }).max(0.0),', 1)
    tabs.write_text(contents)
    print('FigCraft: removed logo and its spacing from document tabs')

# Keep the nine locally installed apps free of upstream community promotions.
import subprocess
subprocess.run([sys.executable, str(icons / 'remove_promos.py'), slug, str(root)], check=True)
