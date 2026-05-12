import os
import re

# Target CSS to inject
TARGET_CSS = """
    .pin-card-wrapper { min-width: 0; }
    .pin-card { min-width: 0; }
    .pin-info { flex: 1; min-width: 0; }
    .pin-name { font-weight: 600; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .pin-meta { font-size: 0.75rem; color: var(--text-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .result-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .result-meta { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .file-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
    .file-item { min-width: 0; }
"""

def fix_html_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    filename = os.path.basename(file_path)
    
    # 1. Inject Styles into <style> block
    if '</style>' in content:
        # Check if already injected
        if '.pin-card-wrapper { min-width: 0; }' not in content:
            content = content.replace('</style>', TARGET_CSS + '\n    </style>')

    # 2. Specific for index.html (Main and in subdirectories)
    if filename == 'index.html':
        # Update/Ensure "Clear all" button
        if 'clear-all-btn' not in content:
            # Try to replace old class if exists
            content = content.replace('class="clear-pins-btn"', 'class="clear-all-btn"')
            # If still not there, try to add it next to Pinned title
            if 'clear-all-btn' not in content:
                content = re.sub(r'(📌 Pinned Items|📌 Pinned)(</div>|</span>)', 
                                 r'\1\2\n                <button onclick="clearAllPins()" class="clear-all-btn">Clear all</button>', content)
        
        # Ensure correct onclick
        content = content.replace('onclick="clearPins()"', 'onclick="clearAllPins()"')

        # Update renderPins JS to use the new classes
        # This is a bit complex as the structure might differ. 
        # We want to wrap name/meta in pin-info and use pin-name/pin-meta classes.
        
        # Match the innerHTML assignment in renderPins
        content = re.sub(
            r'card\.innerHTML = `\s*<span[^>]*>(?:✈️|📄)</span>\s*<div class="pin-name">\${([ac])\.name}</div>\s*<div class="pin-meta">\${([ac])\.(?:region|airport)(?: \+ " • " \+ [ac]\.region)?}</div>\s*`;',
            r'card.innerHTML = `\n                    <span style="font-size: 1.25rem;">${\1.type === "airport" ? "✈️" : "📄"}</span>\n                    <div class="pin-info">\n                        <div class="pin-name">${\1.name}</div>\n                        <div class="pin-meta">${\1.type === "airport" ? \1.region : (\1.airport + " • " + \1.region)}</div>\n                    </div>\n                `;',
            content
        )
        
        # Fix for existing structure in docs/index.html
        content = content.replace('<div class="pin-name">${a.name}</div>', '<div class="pin-info"><div class="pin-name">${a.name}</div>')
        if '<div class="pin-info"><div class="pin-info">' not in content: # Avoid double wrap
             content = content.replace('<div class="pin-info"><div class="pin-name">', '<div class="pin-info"><div class="pin-name">') # No-op just for clarity

        # Search results JS loop - add pin button
        # Look for the results.forEach loop
        if 'results.forEach(result => {' in content and 'const pinBtn = document.createElement' not in content:
            search_loop_replacement = """            results.forEach(result => {
                const item = result.item;
                const wrapper = document.createElement('div');
                wrapper.style.display = 'flex';
                wrapper.style.alignItems = 'center';
                wrapper.style.gap = '0.5rem';

                const div = document.createElement('a');
                div.className = 'search-result-item';
                div.style.flex = '1';
                div.style.marginBottom = '0';
                div.style.minWidth = '0';

                if (item.type === 'chart') {
                    div.href = `#view=${item.id}`;
                    div.onclick = (e) => {
                        e.preventDefault();
                        openViewer(item.id, item.name, item.url, item.localUrl);
                    };
                } else {
                    div.href = item.url;
                }

                const meta = item.type === 'airport' 
                    ? `${item.region}` 
                    : `${item.airport} • ${item.region}`;

                div.innerHTML = `
                    <span class="result-icon">${item.icon}</span>
                    <div class="result-info">
                        <div class="result-name">${item.name}</div>
                        <div class="result-meta">${meta}</div>
                    </div>
                    <span class="result-type">${item.type}</span>
                `;

                const pinBtn = document.createElement('button');
                pinBtn.className = 'pin-btn';
                const pins = getPins();
                const isPinned = item.type === 'airport' 
                    ? pins.airports.some(a => a.slug === item.url.replace('.html', ''))
                    : pins.charts.some(c => c.url === item.url);
                
                if (isPinned) pinBtn.classList.add('pinned');
                pinBtn.innerHTML = '📌';
                pinBtn.onclick = (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (item.type === 'airport') {
                        toggleAirportPin({
                            slug: item.url.replace('.html', ''),
                            name: item.name,
                            region: item.region
                        });
                    } else {
                        toggleChartPin({
                            id: item.id,
                            name: item.name,
                            url: item.url,
                            localUrl: item.localUrl,
                            type: item.icon === '📄' ? 'pdf' : 'image',
                            airport: item.airport,
                            region: item.region
                        });
                    }
                    pinBtn.classList.toggle('pinned');
                };

                wrapper.appendChild(div);
                wrapper.appendChild(pinBtn);
                resultsList.appendChild(wrapper);
            });"""
            content = re.sub(r'results\.forEach\(result => \{.*?\}\);', search_loop_replacement, content, flags=re.DOTALL)

    # 3. Airport pages (files with dashes that are not index or enroute)
    elif '-' in filename and 'enroute' not in filename:
        # Ensure pinAirportBtn in header
        if 'pinAirportBtn' not in content and '</header>' in content:
             content = content.replace('</h1>', '</h1>\n            <button id="pinAirportBtn" class="pin-btn" title="Pin airport to homepage">📌</button>')
        
        # Ensure renderFiles has item.style.minWidth = '0'
        if 'renderFiles' in content:
            if "item.style.minWidth = '0';" not in content:
                content = content.replace("item.style.flex = '1';", "item.style.flex = '1';\n                item.style.minWidth = '0';")
            
            # Special check for older atc_directory_site version
            if "wrapper.className = 'file-item';" in content:
                # Fix older structure to match newer one with flex and min-width
                content = content.replace("wrapper.className = 'file-item';", "wrapper.style.display = 'flex';\n                wrapper.style.alignItems = 'center';\n                wrapper.style.borderBottom = '1px solid var(--border)';")
                content = content.replace("const link = document.createElement('a');\n                link.className = 'file-link';", "const link = document.createElement('a');\n                link.className = 'file-item';\n                link.style.flex = '1';\n                link.style.minWidth = '0';\n                link.style.borderBottom = 'none';")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    dirs = ['docs', 'atc_directory_site']
    for d in dirs:
        if not os.path.exists(d):
            continue
        print(f"Processing directory: {d}")
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith('.html'):
                    fix_html_file(os.path.join(root, f))
    print("Done!")

if __name__ == "__main__":
    main()
