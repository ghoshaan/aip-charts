
import os
import re

def fix_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update style block
    style_replacements = {
        r'\.file-item\s*\{[^}]*\}': '.file-item { display: flex; align-items: center; gap: 0.75rem; padding: 1rem 1.25rem; text-decoration: none; color: var(--text); transition: all 0.15s; min-width: 0; }',
        r'\.file-name\s*\{[^}]*\}': '.file-name { flex: 1; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }',
        r'\.search-result-item\s*\{[^}]*\}': '.search-result-item { display: flex; align-items: center; gap: 1rem; padding: 1rem; text-decoration: none; color: var(--text); border-bottom: 1px solid var(--border); transition: all 0.2s; min-width: 0; flex: 1; }',
        r'\.result-info\s*\{[^}]*\}': '.result-info { flex: 1; min-width: 0; }',
        r'\.result-name\s*\{[^}]*\}': '.result-name { font-weight: 600; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }',
        r'\.result-meta\s*\{[^}]*\}': '.result-meta { font-size: 0.8rem; color: var(--text-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }',
        r'\.pin-info\s*\{[^}]*\}': '.pin-info { flex: 1; min-width: 0; }',
        r'\.pin-name\s*\{[^}]*\}': '.pin-name { font-weight: 600; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }',
        r'\.pin-meta\s*\{[^}]*\}': '.pin-meta { font-size: 0.75rem; color: var(--text-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }'
    }

    for pattern, replacement in style_replacements.items():
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
        else:
            # If not found, we might want to add it if it's a style block, but for now let's just replace if exists
            pass

    # Special case for index.html (renderPins)
    if os.path.basename(file_path) == 'index.html':
        render_pins_new = """        function renderPins() {
            const pins = getPins();
            const section = document.getElementById('pinnedSection');
            const grid = document.getElementById('pinnedGrid');

            if (pins.airports.length === 0 && pins.charts.length === 0) {
                section.style.display = 'none';
                return;
            }

            section.style.display = 'block';
            grid.innerHTML = '';

            pins.airports.forEach(a => {
                const wrapper = document.createElement('div');
                wrapper.className = 'pin-card-wrapper';
                wrapper.style.display = 'flex';
                wrapper.style.alignItems = 'center';
                wrapper.style.background = 'var(--surface)';
                wrapper.style.border = '1px solid var(--border)';
                wrapper.style.borderRadius = '6px';
                wrapper.style.transition = 'all 0.2s';

                const card = document.createElement('a');
                card.className = 'pin-card';
                card.href = a.slug + '.html';
                card.style.border = 'none';
                card.style.flex = '1';
                card.style.minWidth = '0';
                card.innerHTML = `
                    <span style="font-size: 1.25rem;">✈️</span>
                    <div class="pin-info">
                        <div class="pin-name">${a.name}</div>
                        <div class="pin-meta">${a.region}</div>
                    </div>
                `;

                const unpinBtn = document.createElement('button');
                unpinBtn.className = 'unpin-btn';
                unpinBtn.innerHTML = '✕';
                unpinBtn.title = 'Unpin';
                unpinBtn.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    toggleAirportPin(a);
                    renderPins();
                };

                wrapper.appendChild(card);
                wrapper.appendChild(unpinBtn);
                grid.appendChild(wrapper);
            });

            pins.charts.forEach(c => {
                const wrapper = document.createElement('div');
                wrapper.className = 'pin-card-wrapper';
                wrapper.style.display = 'flex';
                wrapper.style.alignItems = 'center';
                wrapper.style.background = 'var(--surface)';
                wrapper.style.border = '1px solid var(--border)';
                wrapper.style.borderRadius = '6px';
                wrapper.style.transition = 'all 0.2s';

                const card = document.createElement('a');
                card.className = 'pin-card';
                card.style.border = 'none';
                card.style.flex = '1';
                card.style.minWidth = '0';

                // Robust recovery for old pins
                let id = c.id;
                let localUrl = c.localUrl;
                let driveUrl = c.url;
                let name = c.name;

                if ((!id || !localUrl) && typeof searchIndex !== 'undefined') {
                    const found = searchIndex.find(item => 
                        (c.id && item.id === c.id) || 
                        (c.url && item.url.split('?')[0] === c.url.split('?')[0]) ||
                        (item.name === c.name && item.airport === c.airport)
                    );
                    if (found) {
                        id = id || found.id;
                        localUrl = localUrl || found.localUrl;
                        driveUrl = driveUrl || found.url;
                        console.log('🔄 Recovered pin data for:', name);
                    }
                }

                if (localUrl && localUrl !== '#') {
                    card.href = `#view=${id}`;
                    card.onclick = (e) => { 
                        e.preventDefault(); 
                        openViewer(id, name, driveUrl, localUrl);
                    };
                } else {
                    console.warn('⚠️ Pin missing localUrl, falling back to Drive:', name);
                    card.href = driveUrl || '#';
                    card.target = '_blank';
                }
                card.innerHTML = `
                    <span style="font-size: 1.25rem;">📄</span>
                    <div class="pin-info">
                        <div class="pin-name">${c.name}</div>
                        <div class="pin-meta">${c.airport} • ${c.region}</div>
                    </div>
                `;

                const unpinBtn = document.createElement('button');
                unpinBtn.className = 'unpin-btn';
                unpinBtn.innerHTML = '✕';
                unpinBtn.title = 'Unpin';
                unpinBtn.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    toggleChartPin(c);
                    renderPins();
                };

                wrapper.appendChild(card);
                wrapper.appendChild(unpinBtn);
                grid.appendChild(wrapper);
            });
        }"""
        
        # Replace renderPinned or renderPins
        if 'function renderPinned()' in content:
            content = re.sub(r'function renderPinned\(\) \{.*?\}', render_pins_new, content, flags=re.DOTALL)
            content = content.replace('renderPinned();', 'renderPins();')
            content = content.replace('onclick="clearAllPins()"', 'onclick="clearAllPins()"') # Already matched
        elif 'function renderPins()' in content:
            content = re.sub(r'function renderPins\(\) \{.*?\}', render_pins_new, content, flags=re.DOTALL)

    # 3. Update renderFiles in airport pages
    if 'function renderFiles' in content:
        # We need to find the loop where items are created and set minWidth
        # Looking for item.className = 'file-item';
        
        # Add item.style.minWidth = '0'; and wrapper.style.minWidth = '0';
        # Example:
        # wrapper.appendChild(item);
        # wrapper.appendChild(pinBtn);
        # listEl.appendChild(wrapper);
        
        # Let's find the assignment of item.className = 'file-item'
        if "item.className = 'file-item';" in content:
            if "item.style.minWidth = '0';" not in content:
                content = content.replace("item.className = 'file-item';", "item.className = 'file-item';\n                item.style.minWidth = '0';")
        
        # Also find where wrapper is created for file item
        # const wrapper = document.createElement('div');
        # wrapper.style.display = 'flex';
        # wrapper.style.alignItems = 'center';
        # wrapper.style.borderBottom = '1px solid var(--border)';
        
        if "wrapper.style.alignItems = 'center';" in content and "wrapper.style.minWidth = '0';" not in content:
             content = content.replace("wrapper.style.alignItems = 'center';", "wrapper.style.alignItems = 'center';\n                wrapper.style.minWidth = '0';")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                fix_html_file(os.path.join(root, file))

if __name__ == '__main__':
    process_directory('docs')
    process_directory('atc_directory_site')
    print("Done fixing HTML files.")
