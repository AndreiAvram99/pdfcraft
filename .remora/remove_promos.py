#!/usr/bin/env python3
"""Personal overlay: remove upstream community and promotional UI from Craft apps."""
from pathlib import Path
import re
import sys

slug, root_arg = sys.argv[1:3]
root = Path(root_arg)
check = '--check' in sys.argv[3:]
changes = []

def edit(path, fn):
    file = root / path
    old = file.read_text()
    new = fn(old)
    if new == old:
        raise RuntimeError(f'{slug}: no changes in {path}')
    if not check:
        file.write_text(new)
    changes.append(path)

def rep(s, old, new=''):
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f'{slug}: expected one anchor ({n}) {old[:90]!r}')
    return s.replace(old, new)

def cut(s, start, end, keep_end=True):
    i = s.find(start)
    if i < 0 or s.find(start, i+1) >= 0:
        raise RuntimeError(f'{slug}: start anchor missing/nonunique {start[:70]!r}')
    j = s.find(end, i + len(start))
    if j < 0:
        raise RuntimeError(f'{slug}: end anchor missing {end[:70]!r}')
    return s[:i] + (s[j:] if keep_end else s[j+len(end):])

def drop_lines(s, needles):
    for needle in needles:
        matches = [line for line in s.splitlines(keepends=True) if needle in line]
        if len(matches) != 1:
            raise RuntimeError(f'{slug}: expected one line ({len(matches)}) for {needle!r}')
        s = s.replace(matches[0], '')
    return s

if slug == 'photocraft':
    edit('crates/engine/src/shell_commands.rs', lambda s: drop_lines(s, [f'("{x}",' for x in ['help.discord','help.website','help.artcraftWebsite','help.github','help.reportIssue']]))

elif slug == 'vectorcraft':
    def menus(s):
        s = rep(s, 'vec![c("About VectorCraft", "help.about"), c("Join Our Discord", "help.discord")]', 'vec![c("About VectorCraft", "help.about")]')
        s = drop_lines(s, ['c("Join Our Discord", "help.discord"),','c("ArtCraft Website", "help.website"),','c("VectorCraft on getartcraft.com", "help.appPage"),','c("VectorCraft on GitHub", "help.github"),'])
        return rep(s, '            "Help",\n            vec![\n                Sep,\n                c("Search Commands', '            "Help",\n            vec![\n                c("Search Commands')
    edit('crates/ui-egui/src/menus.rs', menus)
    def commands(s):
        if 'cmd!(query "help.discord"' not in s or 'pub fn specs() -> Vec<CommandSpec>' not in s:
            raise RuntimeError('VectorCraft help commands changed')
        return '//! Personal build: no promotional Help commands.\n\nuse super::*;\n\npub fn specs() -> Vec<CommandSpec> {\n    Vec::new()\n}\n'
    edit('crates/engine/src/cmd/help.rs',commands)

elif slug == 'filmcraft':
    edit('crates/ui-egui/src/menus.rs', lambda s: drop_lines(s, [f'uic!("{x}",' for x in ['help.discord','help.website','help.appPage','help.github','help.reportIssue']]))
    def native(s):
        s = rep(s, '    let discord = MenuItem::with_id("help.discord", label("help.discord", "Join the ArtCraft Discord…"), true, None);\n')
        s = rep(s, 'for (id, mi) in [("app.about", &about), ("help.discord", &discord)] {', 'for (id, mi) in [("app.about", &about)] {')
        return rep(s, '        &discord,\n')
    edit('apps/filmcraft/src/native_menu.rs', native)
    def header(s):
        start = '    // Community: a labelled Discord button, always one click away.\n'
        end = '    let popup_id = egui::Id::new("workspaces-popup");\n'
        body = '''    // Centre the document title in the space before the workspace controls.
    let left = left_end + 12.0;
    let right = wr.min.x - 12.0;
    if right > left + 40.0 {
        let mut job = egui::text::LayoutJob::simple_singleline(title, Tokens::ui(14.0), t.tab_text_active);
        job.wrap.max_width = right - left;
        job.wrap.max_rows = 1;
        let galley = p.layout_job(job);
        let half = galley.size().x / 2.0;
        let center = if rect.center().x - half >= left && rect.center().x + half <= right { rect.center().x } else { (left + right) / 2.0 };
        p.with_clip_rect(Rect::from_min_max(pos2(left, rect.min.y), pos2(right, rect.max.y))).galley(
            pos2(center - half, rect.center().y - galley.size().y / 2.0), galley, t.tab_text_active,
        );
    }
'''
        return cut(s,start,end).replace(end,body+end,1)
    edit('crates/ui-egui/src/header.rs', header)
    def import_mode(s):
        s = cut(s, '    let y = recent(app, ui, rect, 90.0 + 150.0 + 36.0);\n', '\n}\n\n/// Recent projects listed', True)
        return rep(s, '\n}\n\n/// Recent projects listed', '    recent(app, ui, rect, 90.0 + 150.0 + 36.0);\n}\n\n/// Recent projects listed')
    edit('crates/ui-egui/src/panels/import_mode.rs', import_mode)
    def about(s):
        s = cut(s, '    let mut link = |ui: &mut egui::Ui', '    ui.add_space(10.0);\n    ui.label(egui::RichText::new(tl!("MIT OR Apache', True)
        s = rep(s, '    use crate::icons::{self, Icon};\n    use crate::links;\n')
        return s
    edit('crates/ui-egui/src/panels/dialogs.rs', about)

elif slug == 'lightcraft':
    def menubar(s):
        s = drop_lines(s,[f'"{x}",' for x in ['app.discord','app.feedback','app.website','app.github','app.artcraft']])
        return rep(s,'        "Help",\n        &[\n            "---",\n            "---",','        "Help",\n        &[')
    edit('crates/ui-egui/src/menubar.rs',menubar)
    edit('crates/ui-egui/src/menus.rs',lambda s: drop_lines(s,[f'("{x}",' for x in ['app.discord','app.feedback','app.website','app.github','app.artcraft']]))
    edit('crates/ui-egui/src/panels/topbar.rs', lambda s: drop_lines(s,['("discord", Icon::Chat,']))
    def about(s):
        return cut(s,'                            ui.add_space(10.0);\n                            let r = crate::button::Button::new("Join the ArtCraft Discord")','                        }\n                    }\n                }\n                Dialog::Shortcuts',True)
    edit('crates/ui-egui/src/panels/dialogs.rs',about)
    edit('apps/lightcraft/src/editors.rs',lambda s: rep(s,'Get it from getartcraft.com/apps/photocraft, or give where it is in Settings ▸ External Editing.','Choose its location in Settings ▸ External Editing.'))

elif slug == 'pdfcraft':
    def home(s):
        return cut(s,'            egui::Frame::NONE\n                .fill(t.card)\n                .stroke(Stroke::new(1.0, t.border))\n                .corner_radius(CornerRadius::same(12))\n                .inner_margin(egui::Margin::same(14))','            ui.add_space(22.0);\n',False)
    edit('crates/ui-egui/src/home.rs',home)
    def chrome(s):
        s = rep(s,'                // Keep the two icon buttons, Discord\'s text/padding and three gaps outside the scrolling tabs.\n                let controls_width = ui.fonts_mut(|f| f.layout_no_wrap("Discord".into(), theme::medium(13.0), t.text).size().x)\n                    + 2.0 * button\n                    + 50.0\n                    + window_controls::width(&controls.right);\n','                let controls_width = 2.0 * button + 32.0 + window_controls::width(&controls.right);\n')
        return cut(s,'                    // One click to the community, from anywhere in the app.\n','                });\n            });\n        });\n}',True)
    edit('crates/ui-egui/src/chrome.rs',chrome)
    def dialogs(s):
        return cut(s,'                        ui.add_space(6.0);\n                        if let Some(cmd) = widgets::community_links(ui) {','                    }\n                }\n            }\n        }\n        ui.add_space(16.0);',True)
    edit('crates/ui-egui/src/dialogs.rs',dialogs)
    edit('crates/engine/src/commands.rs',lambda s: drop_lines(s,[f'c("{x}",' for x in ['help.discord','help.app_page','help.github','help.website']]))

elif slug == 'effectcraft':
    def home(s):
        return cut(s,'    // Community links at the foot (below the pages when the window is short).\n','}\n\n/// The Home page: the welcome',True)
    edit('crates/ui-egui/src/panels/home.rs',home)
    def header(s):
        return cut(s,'    // Right side: community buttons, workspaces.\n','    // Appearance: Sync with System, Light, Dark',True).replace('    // Appearance: Sync with System, Light, Dark','    let mut rx = rect.max.x - 10.0;\n    // Appearance: Sync with System, Light, Dark',1)
    edit('crates/ui-egui/src/header.rs',header)
    def dialogs(s):
        return cut(s,'    ui.add_space(14.0);\n    let links: [(Icon, &str, &str, &\'static str); 4]','}\n\nfn comp_settings',True)
    edit('crates/ui-egui/src/panels/dialogs.rs',dialogs)
    def menu(s):
        s = drop_lines(s,['Join the ArtCraft Discord... | help.discord','Provide Feedback... | help.reportIssue','ArtCraft Website | help.website','EffectCraft Home Page | help.appPage','EffectCraft on GitHub | help.github','Online Tutorials... | help.onlineTutorials'])
        return rep(s,'  Reveal Logging File | help.revealLogFile\n  ---\n  ---\n  Open Demo Project','  Reveal Logging File | help.revealLogFile\n  ---\n  Open Demo Project')
    edit('crates/engine/src/menus.rs',menu)
    def help_commands(s):
        s = drop_lines(s,[f'cmd!("{x}",' for x in ['help.discord','help.website','help.appPage','help.github','help.reportIssue','help.onlineTutorials']])
        return cut(s,'        cmd!(\n            "help.sibling",','    ]\n}',True)
    edit('crates/engine/src/commands/help.rs',help_commands)

elif slug == 'designcraft':
    def chrome(s):
        s = rep(s,'                            // Always one click away: the ArtCraft community Discord.\n                            if crate::about::discord_button(ui, "Discord", vec2(78.0, 22.0)) {\n                                let _ = app.run("help.discord", json!({}));\n                            }\n')
        s = rep(s,'            community_card(app, ui);\n')
        return cut(s,'/// Start screen: the ArtCraft community (Discord first) and project links.\n','#[cfg(test)]\nmod tests {',True)
    edit('crates/ui-egui/src/chrome.rs',chrome)
    def about(s):
        s = cut(s,'            ui.add_space(16.0);\n            if discord_button(ui, crate::i18n::tr(&app.ui.language, "Join the ArtCraft Discord")','            ui.add_space(12.0);\n            ui.label(crate::rtl::widget(\n                ui,\n                egui::RichText::new(crate::i18n::tr(&app.ui.language, "Open source. No telemetry."))',True)
        s = rep(s,'    let mut open: Option<&\'static str> = None;\n')
        s = rep(s,'    if let Some(k) = open {\n        let _ = app.run(&format!("help.{k}"), json!({}));\n    }\n')
        return s
    edit('crates/ui-egui/src/about.rs',about)
    def menus(s):
        s = drop_lines(s,['            "ui:help.discord",','            "ui:help.appPage",','            "ui:help.github",','            "ui:help.issues",','            "ui:help.website",','AppMenuItem::Cmd { id: "dc-discord"'])
        s = drop_lines(s,[f'("{x}",' for x in ['help.discord','help.appPage','help.github','help.issues','help.website','help.app']])
        # The initial separator after the removed Help links is now redundant.
        return rep(s,'        "Help",\n        &[\n            "-",\n            "-",\n            "cmd:file.newSample",','        "Help",\n        &[\n            "cmd:file.newSample",')
    edit('crates/ui-egui/src/menus.rs',menus)
    edit('crates/engine/src/cmd/inspect.rs',lambda s: cut(s,'        cmd!(query "app.links",','        cmd!(query "document.list",',True))

elif slug == 'figcraft':
    def catalog(s):
        return drop_lines(s,['m!("Help", "Help page", "help.page")'])
    edit('crates/engine/src/catalog.rs',catalog)
    edit('crates/engine/src/cmd/view.rs',lambda s: drop_lines(s,['spec!("help.page",']))
    edit('crates/ui-egui/src/toolbar.rs',lambda s: drop_lines(s,['(tr("Help page"), "help.page")']))

elif slug == 'soundcraft':
    def about(s):
        s = drop_lines(s,['ui.hyperlink_to("getartcraft.com/apps/soundcraft"','ui.hyperlink_to("Join us on Discord"'])
        return s
    edit('crates/ui-egui/src/panels.rs',about)

else:
    raise RuntimeError(f'unknown app {slug}')

print(f'{slug}: removed promotional UI in {len(changes)} source files' + (' (check)' if check else ''))
