"""
Patches existing docs/ airport HTML pages to:
1. Lighten the blue accent colour (#58a6ff -> #79b8ff)
2. Add a collapsible sidebar to the viewer showing all airport charts
   with the active chart highlighted

Run once; safe to re-run (idempotent guards in place).
"""

import os
import re

SIDEBAR_CSS = """
        /* Viewer sidebar */
        .viewer-body {
            flex: 1;
            display: flex;
            overflow: hidden;
        }

        .viewer-sidebar {
            width: 280px;
            background: var(--surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            transition: width 0.25s ease;
            overflow: hidden;
        }

        .viewer-sidebar.collapsed {
            width: 0;
        }

        .sidebar-header {
            padding: 0.6rem 1rem;
            font-size: 0.65rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--text-dim);
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            white-space: nowrap;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .sidebar-list {
            overflow-y: auto;
            flex: 1;
        }

        .sidebar-list::-webkit-scrollbar { width: 4px; }
        .sidebar-list::-webkit-scrollbar-track { background: transparent; }
        .sidebar-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

        .sidebar-item {
            padding: 0.65rem 1rem 0.65rem 1.1rem;
            cursor: pointer;
            border-bottom: 1px solid var(--border);
            font-size: 0.72rem;
            color: var(--text-dim);
            transition: all 0.12s;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            border-left: 2px solid transparent;
        }

        .sidebar-item:hover {
            background: var(--surface-hover);
            color: var(--text);
        }

        .sidebar-item.active {
            background: var(--accent-glow);
            color: var(--accent);
            border-left-color: var(--accent);
            font-weight: 600;
        }"""

SIDEBAR_TOGGLE_BTN = """
                    <button class="control-btn" id="sidebarToggle" title="Toggle chart list">
                        <span>&#9776;</span> CHARTS
                    </button>

"""

VIEWER_SIDEBAR_HTML = """
                <div class="viewer-sidebar" id="viewerSidebar">
                    <div class="sidebar-header">
                        <span>ALL CHARTS</span>
                        <span id="sidebarCount" style="opacity: 0.5; font-size: 0.6rem;"></span>
                    </div>
                    <div class="sidebar-list" id="sidebarList"></div>
                </div>"""

SIDEBAR_JS = """
            let currentFileId = null;

            const SIDEBAR_KEY = 'atc_sidebar_open';
            let sidebarOpen = localStorage.getItem(SIDEBAR_KEY) !== 'false';

            function applySidebarState() {
                const sidebar = document.getElementById('viewerSidebar');
                const toggleBtn = document.getElementById('sidebarToggle');
                if (!sidebar) return;
                if (sidebarOpen) {
                    sidebar.classList.remove('collapsed');
                    if (toggleBtn) toggleBtn.classList.add('active');
                } else {
                    sidebar.classList.add('collapsed');
                    if (toggleBtn) toggleBtn.classList.remove('active');
                }
            }

            function populateSidebar(activeId) {
                const sidebarList = document.getElementById('sidebarList');
                const sidebarCount = document.getElementById('sidebarCount');
                const sidebar = document.getElementById('viewerSidebar');
                if (!sidebarList) return;

                if (typeof files === 'undefined' || files.length === 0) {
                    if (sidebar) sidebar.style.display = 'none';
                    const toggleBtn = document.getElementById('sidebarToggle');
                    if (toggleBtn) toggleBtn.style.display = 'none';
                    return;
                }

                if (sidebar) sidebar.style.display = '';
                const toggleBtn = document.getElementById('sidebarToggle');
                if (toggleBtn) toggleBtn.style.display = '';

                const chartFiles = files.filter(f => f.type === 'pdf' || f.type === 'image');
                if (sidebarCount) sidebarCount.textContent = chartFiles.length;

                sidebarList.innerHTML = '';
                chartFiles.forEach(file => {
                    const item = document.createElement('div');
                    item.className = 'sidebar-item' + (file.id === activeId ? ' active' : '');
                    item.title = file.name;
                    item.textContent = file.name.replace(/\\.[^.]+$/, '');
                    item.onclick = () => {
                        if (file.id !== currentFileId) {
                            openViewer(file.id, file.name, file.url, file.localUrl, false,
                                typeof airportCtx !== 'undefined' ? airportCtx.icao : null);
                        }
                    };
                    sidebarList.appendChild(item);
                });

                const activeItem = sidebarList.querySelector('.sidebar-item.active');
                if (activeItem) activeItem.scrollIntoView({ block: 'nearest' });
            }

            document.getElementById('sidebarToggle').onclick = () => {
                sidebarOpen = !sidebarOpen;
                localStorage.setItem(SIDEBAR_KEY, sidebarOpen);
                applySidebarState();
            };
"""


def patch_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    changed = False
    filename = os.path.basename(path)

    # 1. Lighter blue accent
    if '#58a6ff' in content:
        content = content.replace('#58a6ff', '#79b8ff')
        content = content.replace('rgba(88, 166, 255, 0.15)', 'rgba(121, 184, 255, 0.15)')
        changed = True

    # --- Viewer sidebar patches (only for pages that already have the viewer) ---
    has_viewer = 'id="viewerModal"' in content

    if has_viewer and 'id="sidebarToggle"' not in content:
        # 2. Add sidebar CSS before </style>
        if SIDEBAR_CSS.strip()[:30] not in content:
            content = content.replace('</style>', SIDEBAR_CSS + '\n    </style>', 1)
            changed = True

        # 3. Add sidebar toggle button before the close button in viewer controls
        close_btn_marker = '<button class="control-btn" id="closeViewer"'
        if close_btn_marker in content:
            content = content.replace(close_btn_marker,
                                      SIDEBAR_TOGGLE_BTN + close_btn_marker, 1)
            changed = True

        # 4. Wrap viewer-content in viewer-body and prepend sidebar
        # Match: <div class="viewer-content" id="viewerContent">
        viewer_content_open = '<div class="viewer-content" id="viewerContent">'
        if viewer_content_open in content and 'class="viewer-body"' not in content:
            content = content.replace(
                viewer_content_open,
                '<div class="viewer-body">' + VIEWER_SIDEBAR_HTML + '\n                ' + viewer_content_open,
                1
            )
            # Close the viewer-body before the outer viewerModal closing div
            # The viewer-content ends just before </div>\n        </div> (viewerModal)
            # We need to add </div> for viewer-body after </div> of viewer-content
            # Find the pattern: end of viewer-content + end of viewerModal
            content = re.sub(
                r'(</div>\s*</div>)\s*\n(\s*</div>\s*\n\s*</div>\s*\n\s*</div>\s*\n\s*</div>\s*\n)',
                lambda m: m.group(0),
                content
            )
            # Simpler: find viewer-tip closing and add viewer-body close after viewer-content close
            # The structure after our change is:
            # <div class="viewer-body">
            #   <div class="viewer-sidebar">...</div>
            #   <div class="viewer-content">
            #     ...
            #     <div class="viewer-tip">...</div>
            #   </div>    <- need to add </div> for viewer-body here
            # </div>  <- viewerModal
            content = re.sub(
                r'(<div class="viewer-tip">[^<]*(?:<[^<]*>)*[^<]*</div>\s*</div>)(\s*\n\s*</div>)',
                r'\1\n            </div>\2',
                content
            )
            changed = True

        # 5. Add sidebar JS before the closing </script> of the viewer
        # Insert after pdfjsLib variable declarations, before openViewer
        if 'let currentFileId = null;' not in content and 'pdfjsLib.GlobalWorkerOptions' in content:
            content = content.replace(
                'let originalPageTitle = document.title;',
                'let originalPageTitle = document.title;' + SIDEBAR_JS,
                1
            )
            changed = True

        # 6. Patch openViewer to set currentFileId and call populateSidebar
        if 'currentFileId = id;' not in content and 'async function openViewer' in content:
            content = content.replace(
                'async function openViewer(id, name, driveUrl, localUrl, skipHash = false, icao = null) {',
                'async function openViewer(id, name, driveUrl, localUrl, skipHash = false, icao = null) {\n                currentFileId = id;',
                1
            )
            content = content.replace(
                "modal.style.display = 'flex';\n                document.body.style.overflow = 'hidden';",
                "modal.style.display = 'flex';\n                document.body.style.overflow = 'hidden';\n                populateSidebar(id);\n                applySidebarState();",
                1
            )
            changed = True

    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    patched = 0
    skipped = 0
    for dirpath in ['docs', 'atc_directory_site']:
        if not os.path.isdir(dirpath):
            continue
        for fname in os.listdir(dirpath):
            if not fname.endswith('.html'):
                continue
            full = os.path.join(dirpath, fname)
            if patch_file(full):
                print(f'  patched: {full}')
                patched += 1
            else:
                skipped += 1

    print(f'\nDone. {patched} files patched, {skipped} unchanged.')


if __name__ == '__main__':
    main()
