#!/usr/bin/env python3
"""
Multi-Page ATC Charts Directory Generator

Generates a hierarchical directory structure:
- index.html → Region selection (Netherlands, Switzerland, etc.)
- region.html → Airport selection (EHAM, EHRD, etc.)
- airport.html → File listings with fuzzy search

Usage:
    python generate_multipage_directory.py

Requirements:
    - Google Drive API credentials (credentials.json)
    - pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
"""

import os
import json
import re
from collections import defaultdict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================================================================
# CONFIGURATION
# ============================================================================

CHARTS_FOLDER_ID = '1DjkbZ9YMC5fS-zZvIpDiP9dCkUL120nK'  # UPDATE THIS!
OUTPUT_DIR = 'docs'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Region icons (add more as needed)
REGION_ICONS = {
    'netherlands': '🇳🇱',
    'switzerland': '🇨🇭',
    'canada': '🇨🇦',
    'united states': '🇺🇸',
    'france': '🇫🇷',
    'germany': '🇩🇪',
    'uk': '🇬🇧',
    'ireland': '🇮🇪',
    'default': '🌍'
}

AIRPORT_NAMES = {
    # Ireland
    'EICK': 'Cork',
    'EIDL': 'Donegal',
    'EIDW': 'Dublin',
    'EIKN': 'Ireland West (Knock)',
    'EIKY': 'Kerry',
    'EINN': 'Shannon',
    'EISG': 'Sligo',
    'EIWF': 'Waterford',
    'EIWT': 'Weston',
    
    # Netherlands
    'EHAL': 'Ameland',
    'EHAM': 'Amsterdam Schiphol',
    'EHBD': 'Budel',
    'EHBK': 'Maastricht Aachen',
    'EHDR': 'Drachten',
    'EHEH': 'Eindhoven',
    'EHGG': 'Groningen Eelde',
    'EHHA': 'Amsterdam FIR',
    'EHHE': 'Heerenveen',
    'EHHO': 'Hoogeveen',
    'EHHV': 'Hilversum',
    'EHJR': 'Arnhem',
    'EHKD': 'De Kooy',
    'EHLE': 'Lelystad',
    'EHMM': 'Maastricht FIR',
    'EHMZ': 'Midden-Zeeland',
    'EHOW': 'Oostwold',
    'EHRD': 'Rotterdam The Hague',
    'EHSE': 'Seppe',
    'EHST': 'Stadskanaal',
    'EHTE': 'Teuge',
    'EHTL': 'Terlet',
    'EHTW': 'Twente',
    'EHTX': 'Texel',
    
    # Switzerland
    'LSGC': 'Les Eplatures',
    'LSGG': 'Geneva',
    'LSGS': 'Sion',
    'LSMP': 'Payerne',
    'LSZA': 'Lugano',
    'LSZB': 'Bern',
    'LSZC': 'Buochs',
    'LSZG': 'Grenchen',
    'LSZH': 'Zurich',
    'LSZR': 'St. Gallen-Altenrhein',
    'LSZS': 'Samedan'
}

# ============================================================================
# AUTHENTICATION
# ============================================================================

def authenticate_drive():
    """Authenticate with Google Drive API"""
    print("🔐 Authenticating...")
    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️  Refresh failed: {e}")
                creds = None
                if os.path.exists('token.json'):
                    os.remove('token.json')
                    print("🗑️  Deleted expired token.json")
        
        if not creds or not creds.valid:
            if not os.path.exists('credentials.json'):
                print("❌ credentials.json not found!")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    print("✅ Authenticated!\n")
    return build('drive', 'v3', credentials=creds)


# ============================================================================
# DRIVE SCANNING
# ============================================================================

def scan_folder_recursive(service, folder_id, path=''):
    """Recursively scan folder, following shortcut folders too"""
    items = []

    try:
        page_token = None
        while True:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, parents, shortcutDetails)",
                pageToken=page_token
            ).execute()

            for item in results.get('files', []):
                is_folder = item['mimeType'] == 'application/vnd.google-apps.folder'
                shortcut_details = item.get('shortcutDetails', {})
                is_shortcut_folder = (
                    item['mimeType'] == 'application/vnd.google-apps.shortcut' and
                    shortcut_details.get('targetMimeType') == 'application/vnd.google-apps.folder'
                )

                item_data = {
                    'id': item['id'],
                    'name': item['name'],
                    'mimeType': item['mimeType'],
                    'viewUrl': item.get('webViewLink', '#'),
                    'parentId': folder_id,
                    'path': path
                }

                if not is_folder and not is_shortcut_folder:
                    ext = item['name'].split('.')[-1] if '.' in item['name'] else ''
                    item_data['ext'] = ext.lower()

                items.append(item_data)

                # Recurse into real folders or shortcut folders
                if is_folder or is_shortcut_folder:
                    new_path = f"{path}/{item['name']}" if path else item['name']
                    print(f"   📁 {new_path}")
                    target_id = shortcut_details.get('targetId', item['id']) if is_shortcut_folder else item['id']
                    items.extend(scan_folder_recursive(service, target_id, new_path))

            page_token = results.get('nextPageToken')
            if not page_token:
                break

    except HttpError as e:
        print(f"❌ Error: {e}")

    return items


# ============================================================================
# DATA ORGANIZATION
# ============================================================================

def get_file_type(mime_type, ext=''):
    """Determine file type"""
    if mime_type.startswith('image/') or ext in ['png', 'jpg', 'jpeg', 'gif']:
        return 'image'
    if ext == 'pdf' or mime_type == 'application/pdf':
        return 'pdf'
    return 'doc'


def slugify(text):
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def organize_by_hierarchy(items):
    """
    Organize files into: Region → Airport → Files
    
    Expected structure:
    - Netherlands/EHAM/file.pdf
    - Switzerland/LSZH/file.pdf
    """
    hierarchy = defaultdict(lambda: defaultdict(list))
    
    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            continue
        
        # Parse path: "Region/Airport/file.pdf"
        path_parts = item['path'].split('/')
        
        if len(path_parts) < 2:
            print(f"⚠️  Skipping file with unexpected path: {item['path']}")
            continue
        
        region = path_parts[0]
        airport = path_parts[1]
        
        hierarchy[region][airport].append({
            'id': item['id'],
            'name': item['name'],
            'url': item['viewUrl'],
            'type': get_file_type(item['mimeType'], item.get('ext', ''))
        })
    
    return hierarchy


# ============================================================================
# HTML GENERATION
# ============================================================================

def create_output_dir():
    """Create output directory"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    print(f"📁 Output directory: {OUTPUT_DIR}/\n")


def generate_index_page(hierarchy):
    """Generate main index page with global search"""
    regions = []
    global_search_index = []
    
    for region_name, airports in hierarchy.items():
        region_slug = slugify(region_name)
        region_icon = REGION_ICONS.get(region_name.lower(), REGION_ICONS['default'])
        
        region_file_count = 0
        region_airports = []
        
        for airport_code, files in airports.items():
            airport_name = AIRPORT_NAMES.get(airport_code, airport_code)
            airport_display = f"{airport_code} - {airport_name}" if airport_name != airport_code else airport_code
            airport_slug = slugify(f"{region_slug}-{airport_code}")
            
            # Add airport to global index
            global_search_index.append({
                'type': 'airport',
                'name': airport_display,
                'code': airport_code,
                'region': region_name,
                'url': f"{airport_slug}.html",
                'icon': '✈️'
            })
            
            # Add each chart to global index
            for f in files:
                global_search_index.append({
                    'type': 'chart',
                    'id': f['id'],
                    'name': f['name'],
                    'airport': airport_display,
                    'region': region_name,
                    'url': f['url'],
                    'icon': '📄' if f['type'] == 'pdf' else '🖼️'
                })
            
            region_file_count += len(files)
            region_airports.append(airport_code)
            
        regions.append({
            'name': region_name,
            'icon': region_icon,
            'slug': region_slug,
            'airportCount': len(airports),
            'fileCount': region_file_count
        })
    
    regions.sort(key=lambda x: x['name'])
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ATC Charts Directory</title>
    <link rel="icon" type="image/png" href="favicon.png">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0"></script>
    <style>
        {get_common_styles()}
        
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
        }}
        
        .region-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 2rem;
            text-decoration: none;
            color: var(--text);
            transition: all 0.2s;
            position: relative;
            display: block;
        }}
        
        .region-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--accent);
            transform: scaleY(0);
            transition: transform 0.2s;
        }}
        
        .region-card:hover {{
            border-color: var(--accent);
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(88, 166, 255, 0.15);
        }}
        
        .region-card:hover::before {{
            transform: scaleY(1);
        }}
        
        .card-icon {{
            font-size: 3rem;
            margin-bottom: 1rem;
            display: block;
        }}
        
        .card-title {{
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}
        
        .card-count {{
            font-size: 0.875rem;
            color: var(--text-dim);
        }}
        
        .card-count strong {{
            color: var(--accent);
        }}

        /* Global Search Styles */
        .results-section {{
            margin-top: 2rem;
        }}

        .search-result-item {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-bottom: 0.5rem;
            text-decoration: none;
            color: var(--text);
            transition: all 0.2s;
        }}

        .search-result-item:hover {{
            border-color: var(--accent);
            background: var(--surface-hover);
            transform: translateX(4px);
        }}

        .result-icon {{ font-size: 1.25rem; }}
        .result-info {{ flex: 1; }}
        .result-name {{ font-weight: 600; font-size: 0.95rem; }}
        .result-meta {{ font-size: 0.75rem; color: var(--text-dim); }}
        .result-type {{ 
            font-size: 0.6rem; 
            text-transform: uppercase; 
            background: var(--bg); 
            padding: 0.2rem 0.5rem; 
            border-radius: 3px;
            letter-spacing: 0.05em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <h1>ATC Charts Directory</h1>
                <div class="subtitle">Search airports, charts, or browse regions</div>
            </div>
        </header>
        
        <div id="pinnedSection" class="pinned-section" style="display: none;">
            <div class="subtitle" style="color: var(--accent); margin-bottom: 0.5rem;">📌 Pinned Items</div>
            <div id="pinnedGrid" class="pinned-grid"></div>
        </div>

        <div class="stats">
            <div class="stat">
                <span class="stat-value">{len(regions)}</span>
                <span class="stat-label">Regions</span>
            </div>
            <div class="stat">
                <span class="stat-value">{sum(r['airportCount'] for r in regions)}</span>
                <span class="stat-label">Airports</span>
            </div>
            <div class="stat">
                <span class="stat-value">{sum(r['fileCount'] for r in regions)}</span>
                <span class="stat-label">Total Files</span>
            </div>
        </div>

        <div class="search-section">
            <div class="search-wrapper">
                <span class="search-icon">🔍</span>
                <input type="text" id="searchInput" class="search-input" 
                       placeholder="Search global directory (e.g. Dublin, star, EHAM)..." autocomplete="off">
            </div>
        </div>
        
        <div id="searchResults" class="results-section" style="display: none;">
            <div class="subtitle" style="margin-bottom: 1rem;">Search Results</div>
            <div id="resultsList"></div>
        </div>

        <div id="defaultView">
            <div class="subtitle" style="margin-bottom: 1rem;">Browse Regions</div>
            <div class="card-grid">
                {''.join([f'''
                <a href="{r['slug']}.html" class="region-card">
                    <span class="card-icon">{r['icon']}</span>
                    <div class="card-title">{r['name']}</div>
                    <div class="card-count">
                        <strong>{r['airportCount']}</strong> airports • 
                        <strong>{r['fileCount']}</strong> files
                    </div>
                </a>
                ''' for r in regions])}
            </div>
        </div>

        <div id="emptyState" class="empty-state" style="display: none;">
            <div style="font-size: 3rem; opacity: 0.3;">🔍</div>
            <p>No results found.</p>
        </div>
    </div>

    {get_viewer_html()}

    <script>
        {get_pinning_js()}
        {get_viewer_js()}
        const searchIndex = {json.dumps(global_search_index, indent=8)};

        function renderPins() {{
            const pins = getPins();
            const section = document.getElementById('pinnedSection');
            const grid = document.getElementById('pinnedGrid');

            if (pins.airports.length === 0 && pins.charts.length === 0) {{
                section.style.display = 'none';
                return;
            }}

            section.style.display = 'block';
            grid.innerHTML = '';

            pins.airports.forEach(a => {{
                const card = document.createElement('a');
                card.className = 'pin-card';
                card.href = a.slug + '.html';
                card.innerHTML = `
                    <span style="font-size: 1.25rem;">✈️</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 0.9rem;">${{a.name}}</div>
                        <div style="font-size: 0.7rem; color: var(--text-dim);">${{a.region}}</div>
                    </div>
                `;
                grid.appendChild(card);
            }});

            pins.charts.forEach(c => {{
                const card = document.createElement('a');
                card.className = 'pin-card';
                card.href = '#';
                card.onclick = (e) => {{ 
                    e.preventDefault(); 
                    if (c.id) openViewer(c.id, c.name, c.url);
                    else window.open(c.url, '_blank');
                }};
                card.innerHTML = `
                    <span style="font-size: 1.25rem;">📄</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; font-size: 0.9rem;">${{c.name}}</div>
                        <div style="font-size: 0.7rem; color: var(--text-dim);">${{c.airport}} • ${{c.region}}</div>
                    </div>
                `;
                grid.appendChild(card);
            }});
        }}

        renderPins();

        const fuse = new Fuse(searchIndex, {{
            keys: [
                {{ name: 'name', weight: 2 }},
                {{ name: 'code', weight: 2 }},
                {{ name: 'airport', weight: 1 }},
                {{ name: 'region', weight: 1 }}
            ],
            threshold: 0.3,
            includeMatches: true,
            limit: 50
        }});
        
        const searchInput = document.getElementById('searchInput');
        const searchResults = document.getElementById('searchResults');
        const resultsList = document.getElementById('resultsList');
        const defaultView = document.getElementById('defaultView');
        const emptyState = document.getElementById('emptyState');

        searchInput.addEventListener('input', (e) => {{
            const query = e.target.value.trim();
            const pinnedSection = document.getElementById('pinnedSection');

            if (query.length < 2) {{
                searchResults.style.display = 'none';
                defaultView.style.display = 'block';
                emptyState.style.display = 'none';
                renderPins(); // Refresh pins when returning to default view
                return;
            }}

            pinnedSection.style.display = 'none';
            const results = fuse.search(query);

            defaultView.style.display = 'none';
            
            if (results.length === 0) {{
                searchResults.style.display = 'none';
                emptyState.style.display = 'block';
                return;
            }}

            emptyState.style.display = 'none';
            searchResults.style.display = 'block';
            resultsList.innerHTML = '';

            results.forEach(result => {{
                const item = result.item;
                const div = document.createElement('a');
                div.className = 'search-result-item';
                div.href = '#';
                div.onclick = (e) => {{
                    e.preventDefault();
                    if (item.type === 'chart') {{
                        openViewer(item.id, item.name, item.url);
                    }} else {{
                        window.location.href = item.url;
                    }}
                }};

                const meta = item.type === 'airport' 
                    ? `${{item.region}}` 
                    : `${{item.airport}} • ${{item.region}}`;

                div.innerHTML = `
                    <span class="result-icon">${{item.icon}}</span>
                    <div class="result-info">
                        <div class="result-name">${{item.name}}</div>
                        <div class="result-meta">${{meta}}</div>
                    </div>
                    <span class="result-type">${{item.type}}</span>
                `;
                resultsList.appendChild(div);
            }});
        }});
    </script>
</body>
</html>'''
    
    with open(f"{OUTPUT_DIR}/index.html", 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Generated: index.html ({len(regions)} regions, {len(global_search_index)} global items)")
    return regions
    
    with open(f"{OUTPUT_DIR}/index.html", 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Generated: index.html ({len(regions)} regions)")
    return regions


def generate_region_page(region_name, region_slug, airports):
    """Generate region page with airport list"""
    airport_list = []
    
    for airport_code, files in airports.items():
        name = AIRPORT_NAMES.get(airport_code, airport_code)
        display_name = f"{airport_code} - {name}" if name != airport_code else airport_code
        
        airport_list.append({
            'icao': airport_code,
            'name': name,
            'displayName': display_name,
            'slug': slugify(f"{region_slug}-{airport_code}"),
            'fileCount': len(files)
        })
    
    airport_list.sort(key=lambda x: x['icao'])
    
    icon = REGION_ICONS.get(region_name.lower(), REGION_ICONS['default'])
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{region_name} - ATC Charts</title>
    <link rel="icon" type="image/png" href="favicon.png">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0"></script>
    <style>
        {get_common_styles()}
        {get_airport_card_styles()}
    </style>
</head>
<body>
    <div class="container">
        <div class="breadcrumb">
            <a href="index.html">Home</a>
            <span class="breadcrumb-separator">›</span>
            <span>{region_name}</span>
        </div>
        
        <header>
            <h1>{icon} {region_name}</h1>
            <div class="subtitle">Select an airport</div>
        </header>
        
        <div class="search-section">
            <div class="search-wrapper">
                <span class="search-icon">🔍</span>
                <input type="text" id="searchInput" class="search-input" 
                       placeholder="Search airports..." autocomplete="off">
            </div>
        </div>
        
        <div class="airport-grid" id="airportGrid"></div>
        <div id="emptyState" class="empty-state" style="display: none;">
            <div style="font-size: 3rem; opacity: 0.3;">🔍</div>
            <p>No airports found.</p>
        </div>
    </div>
    
    <script>
        const airports = {json.dumps(airport_list, indent=8)};
        
        const fuse = new Fuse(airports, {{
            keys: ['icao', 'name', 'displayName'],
            threshold: 0.3,
            includeMatches: true
        }});
        
        function renderAirports(results = null) {{
            const grid = document.getElementById('airportGrid');
            grid.innerHTML = '';
            
            const airportsToShow = results ? results.map(r => ({{...r.item, matches: r.matches}})) : airports;
            
            if (airportsToShow.length === 0) {{
                document.getElementById('emptyState').style.display = 'block';
                return;
            }}
            
            document.getElementById('emptyState').style.display = 'none';
            
            airportsToShow.forEach(airport => {{
                const card = document.createElement('a');
                card.className = 'airport-card';
                card.href = airport.slug + '.html';
                card.innerHTML = `
                    <div class="airport-code">${{airport.displayName}}</div>
                    <div class="airport-stats">
                        <span>📄 <strong>${{airport.fileCount}}</strong> files</span>
                    </div>
                `;
                grid.appendChild(card);
            }});

        }}
        
        document.getElementById('searchInput').addEventListener('input', (e) => {{
            const query = e.target.value.trim();
            renderAirports(query ? fuse.search(query) : null);
        }});
        
        renderAirports();
    </script>
</body>
</html>'''
    
    with open(f"{OUTPUT_DIR}/{region_slug}.html", 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Generated: {region_slug}.html ({len(airport_list)} airports)")
    return airport_list


def generate_airport_page(region_name, region_slug, airport_code, files):
    """Generate airport page with file listings"""
    
    name = AIRPORT_NAMES.get(airport_code, airport_code)
    display_title = f"{airport_code} - {name}" if name != airport_code else airport_code
    airport_slug = slugify(f"{region_slug}-{airport_code}")

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{display_title} - ATC Charts</title>
    <link rel="icon" type="image/png" href="favicon.png">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0"></script>
    <style>
        {get_common_styles()}
        {get_file_list_styles()}
    </style>
</head>
<body>
    <div class="container">
        <div class="breadcrumb">
            <a href="index.html">Home</a>
            <span class="breadcrumb-separator">›</span>
            <a href="{region_slug}.html">{region_name}</a>
            <span class="breadcrumb-separator">›</span>
            <span>{airport_code}</span>
        </div>
        
        <header>
            <div class="header-content">
                <h1>{display_title}</h1>
                <div class="subtitle">Charts and procedures</div>
            </div>
            <button id="pinAirportBtn" class="pin-btn" title="Pin airport to homepage">📌</button>
        </header>
        
        <div class="search-section">
            <div class="search-wrapper">
                <span class="search-icon">🔍</span>
                <input type="text" id="searchInput" class="search-input" 
                       placeholder="Search charts..." autocomplete="off">
            </div>
            <div class="search-help">
                <strong>Examples:</strong> <code>star</code> • <code>RWY 04</code> • <code>ILS</code>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-btn active" data-filter="all">All</button>
            <button class="filter-btn" data-filter="pdf">PDF</button>
            <button class="filter-btn" data-filter="image">Images</button>
        </div>
        
        <hr style="margin: 2rem 0; border: none; border-top: 1px solid var(--border);">
        
        <div class="file-count" id="fileCount">Showing {len(files)} files</div>
        <div class="file-list" id="fileList"></div>
        <div id="emptyState" class="empty-state" style="display: none;">
            <div style="font-size: 3rem; opacity: 0.3;">🔍</div>
            <p>No files found.</p>
        </div>
    </div>
    
    {get_viewer_html()}

    <script>
        {get_pinning_js()}
        {get_viewer_js()}
        
        const airportCtx = {{
            slug: '{airport_slug}',
            name: '{display_title}',
            region: '{region_name}'
        }};

        const pinAirportBtn = document.getElementById('pinAirportBtn');
        const updateAirportPinState = () => {{
            const pins = getPins();
            const isPinned = pins.airports.some(a => a.slug === airportCtx.slug);
            pinAirportBtn.classList.toggle('pinned', isPinned);
            pinAirportBtn.title = isPinned ? 'Unpin from homepage' : 'Pin to homepage';
        }};

        pinAirportBtn.onclick = () => {{
            toggleAirportPin(airportCtx);
            updateAirportPinState();
        }};
        updateAirportPinState();

        const files = {json.dumps(files, indent=8)};
        const fileIcons = {{pdf: '📄', image: '🖼️', doc: '📝'}};
        let currentFilter = 'all';
        
        const fuse = new Fuse(files, {{
            keys: ['name'],
            threshold: 0.4,
            includeMatches: true
        }});
        
        function renderFiles(results = null) {{
            const listEl = document.getElementById('fileList');
            const emptyState = document.getElementById('emptyState');
            const fileCount = document.getElementById('fileCount');
            
            listEl.innerHTML = '';
            
            let filesToShow = results ? results.map(r => ({{...r.item, matches: r.matches}})) : files;
            
            if (currentFilter !== 'all') {{
                filesToShow = filesToShow.filter(f => f.type === currentFilter);
            }}
            
            if (filesToShow.length === 0) {{
                listEl.style.display = 'none';
                emptyState.style.display = 'block';
                fileCount.textContent = 'No files found';
                return;
            }}
            
            listEl.style.display = 'block';
            emptyState.style.display = 'none';
            fileCount.textContent = `Showing ${{filesToShow.length}} of ${{files.length}} files`;
            
            filesToShow.forEach(file => {{
                const wrapper = document.createElement('div');
                wrapper.style.display = 'flex';
                wrapper.style.alignItems = 'center';
                wrapper.style.borderBottom = '1px solid var(--border)';

                const item = document.createElement('a');
                item.className = 'file-item';
                item.href = '#';
                item.onclick = (e) => {{
                    e.preventDefault();
                    openViewer(file.id, file.name, file.url);
                }};
                item.style.borderBottom = 'none';
                item.style.flex = '1';
                item.innerHTML = `
                    <span class="file-icon">${{fileIcons[file.type] || '📄'}}</span>
                    <span class="file-name">${{file.name}}</span>
                    <span class="file-type">${{file.type}}</span>
                `;

                const pins = getPins();
                const isPinned = pins.charts.some(c => c.url === file.url);
                const pinBtn = document.createElement('button');
                pinBtn.className = 'pin-btn' + (isPinned ? ' pinned' : '');
                pinBtn.style.marginRight = '1rem';
                pinBtn.title = isPinned ? 'Unpin from homepage' : 'Pin to homepage';
                pinBtn.innerHTML = '📌';
                pinBtn.onclick = (e) => {{
                    e.preventDefault();
                    toggleChartPin({{
                        id: file.id,
                        name: file.name,
                        url: file.url,
                        type: file.type,
                        airport: airportCtx.name,
                        region: airportCtx.region
                    }});
                    pinBtn.classList.toggle('pinned');
                    pinBtn.title = pinBtn.classList.contains('pinned') ? 'Unpin from homepage' : 'Pin to homepage';
                }};

                wrapper.appendChild(item);
                wrapper.appendChild(pinBtn);
                listEl.appendChild(wrapper);
            }});
        }}
        
        document.getElementById('searchInput').addEventListener('input', (e) => {{
            const query = e.target.value.trim();
            renderFiles(query ? fuse.search(query) : null);
        }});
        
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                
                const query = document.getElementById('searchInput').value.trim();
                renderFiles(query ? fuse.search(query) : null);
            }});
        }});
        
        renderFiles();
    </script>
</body>
</html>'''
    
    slug = slugify(f"{region_slug}-{airport_code}")
    with open(f"{OUTPUT_DIR}/{slug}.html", 'w', encoding='utf-8') as f:
        f.write(html)
    
    return slug


# ============================================================================
# CSS HELPERS
# ============================================================================

def get_common_styles():
    """Common CSS used across all pages"""
    return '''
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        :root {
            --bg: #0d1117;
            --surface: #161b22;
            --surface-hover: #1c2128;
            --border: #30363d;
            --text: #e6edf3;
            --text-dim: #7d8590;
            --accent: #58a6ff;
            --accent-glow: rgba(88, 166, 255, 0.15);
            --warning: #d29922;
        }
        
        body {
            font-family: 'IBM Plex Mono', monospace;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                repeating-linear-gradient(0deg, transparent, transparent 2px, var(--border) 2px, var(--border) 3px),
                repeating-linear-gradient(90deg, transparent, transparent 2px, var(--border) 2px, var(--border) 3px);
            background-size: 60px 60px;
            opacity: 0.15;
            pointer-events: none;
            z-index: 0;
        }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 2rem; position: relative; z-index: 1; }
        
        .breadcrumb {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            font-size: 0.875rem;
            color: var(--text-dim);
        }
        
        .breadcrumb a { color: var(--accent); text-decoration: none; }
        .breadcrumb a:hover { text-decoration: underline; }
        .breadcrumb-separator { opacity: 0.5; }
        
        header {
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }
        
        .header-content { flex: 1; }

        h1 {
            font-family: 'Rajdhani', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent);
            letter-spacing: 0.02em;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
        }
        
        .subtitle {
            font-size: 0.875rem;
            color: var(--text-dim);
        }
        
        .search-section {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .search-wrapper { position: relative; margin-bottom: 0.5rem; }
        
        .search-input {
            width: 100%;
            padding: 0.875rem 1rem 0.875rem 2.75rem;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        
        .search-input:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }
        
        .search-icon {
            position: absolute;
            left: 1rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-dim);
        }
        
        .search-help {
            font-size: 0.75rem;
            color: var(--text-dim);
            margin-top: 0.5rem;
        }
        
        .search-help code {
            background: var(--bg);
            padding: 0.15rem 0.4rem;
            border-radius: 3px;
            color: var(--accent);
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 3rem;
        }
        
        .stat {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1rem;
            text-align: center;
        }
        
        .stat-value {
            font-family: 'Rajdhani', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent);
            display: block;
            margin-bottom: 0.25rem;
        }
        
        .stat-label {
            font-size: 0.7rem;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        
        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-dim);
        }
        
        .filters {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-bottom: 2rem;
        }
        
        .filter-btn {
            padding: 0.5rem 1rem;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text-dim);
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
        }
        
        .filter-btn:hover { border-color: var(--accent); color: var(--text); }
        .filter-btn.active { background: var(--accent); border-color: var(--accent); color: var(--bg); }

        /* Favicon-like icon styling */
        img[src*="favicon"] {
            border-radius: 20%;
        }

        /* Pinning System Styles */
        .pin-btn {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 0.85rem;
            padding: 0.5rem;
            opacity: 0.25;
            transition: all 0.2s;
            flex-shrink: 0;
            line-height: 1;
            border-radius: 4px;
        }
        .pin-btn:hover { opacity: 0.8; background: var(--accent-glow); }
        .pin-btn.pinned { opacity: 1; color: var(--accent); }

        .pinned-section {
            margin-bottom: 3rem;
            padding: 1.5rem;
            background: var(--accent-glow);
            border: 1px solid var(--accent);
            border-radius: 8px;
        }

        .pinned-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        .pin-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            text-decoration: none;
            color: var(--text);
            transition: all 0.2s;
        }

        .pin-card:hover {
            border-color: var(--accent);
            transform: translateY(-2px);
        }

        /* Pro Viewer Modal */
        .viewer-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(13, 17, 23, 0.95);
            z-index: 1000;
            display: none;
            flex-direction: column;
        }

        .viewer-header {
            padding: 1rem 2rem;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 1.5rem;
            z-index: 1001;
        }

        .viewer-title {
            flex: 1;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 700;
            color: var(--accent);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .viewer-controls {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .control-btn {
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }

        .control-btn:hover {
            border-color: var(--accent);
            background: var(--surface-hover);
        }

        .viewer-content {
            flex: 1;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }

        #viewerFrame {
            width: 100%;
            height: 100%;
            border: none;
            background: white;
            border-radius: 4px;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .zoom-slider {
            width: 100px;
            accent-color: var(--accent);
        }
    '''

def get_viewer_html():
    """HTML for the integrated viewer modal"""
    return '''
    <div id="viewerModal" class="viewer-modal">
        <div class="viewer-header">
            <div class="viewer-title" id="viewerTitle">Chart Viewer</div>
            
            <div class="viewer-controls">
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-right: 1rem;">
                    <span style="font-size: 0.7rem; color: var(--text-dim);">ZOOM</span>
                    <input type="range" id="zoomRange" class="zoom-slider" min="0.5" max="2" step="0.1" value="1">
                </div>
                
                <button class="control-btn" id="rotateBtn">
                    <span>🔄</span> ROTATE
                </button>
                
                <a id="externalLink" class="control-btn" target="_blank">
                    <span>🔗</span> DRIVE
                </a>
                
                <button class="control-btn" id="closeViewer" style="border-color: var(--warning); color: var(--warning);">
                    <span>✖</span> CLOSE
                </button>
            </div>
        </div>
        <div class="viewer-content">
            <iframe id="viewerFrame" src=""></iframe>
        </div>
    </div>
    '''

def get_viewer_js():
    """JS for the integrated viewer logic"""
    return '''
        let currentRotation = 0;
        let currentZoom = 1;

        function openViewer(id, name, url) {
            const modal = document.getElementById('viewerModal');
            const frame = document.getElementById('viewerFrame');
            const title = document.getElementById('viewerTitle');
            const externalLink = document.getElementById('externalLink');
            
            currentRotation = 0;
            currentZoom = 1;
            updateFrameTransform();
            document.getElementById('zoomRange').value = 1;

            title.textContent = name;
            externalLink.href = url;
            frame.src = `https://drive.google.com/file/d/${id}/preview`;
            
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }

        function closeViewer() {
            const modal = document.getElementById('viewerModal');
            const frame = document.getElementById('viewerFrame');
            modal.style.display = 'none';
            frame.src = '';
            document.body.style.overflow = 'auto';
        }

        function updateFrameTransform() {
            const frame = document.getElementById('viewerFrame');
            frame.style.transform = `rotate(${currentRotation}deg) scale(${currentZoom})`;
        }

        document.getElementById('closeViewer').onclick = closeViewer;
        
        document.getElementById('rotateBtn').onclick = () => {
            currentRotation = (currentRotation + 90) % 360;
            updateFrameTransform();
        };

        document.getElementById('zoomRange').oninput = (e) => {
            currentZoom = parseFloat(e.target.value);
            updateFrameTransform();
        };

        // Close on Esc
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeViewer();
        });
    '''

def get_pinning_js():
    """Shared JS for pinning logic"""
    return '''
        const PINS_KEY = 'atc_pins';
        function getPins() {
            try { return JSON.parse(localStorage.getItem(PINS_KEY)) || {airports: [], charts: []}; }
            catch(e) { return {airports: [], charts: []}; }
        }
        function savePins(p) { localStorage.setItem(PINS_KEY, JSON.stringify(p)); }
        
        function toggleAirportPin(airport) {
            let pins = getPins();
            let idx = pins.airports.findIndex(a => a.slug === airport.slug);
            if (idx >= 0) pins.airports.splice(idx, 1);
            else pins.airports.push({...airport, pinnedAt: Date.now()});
            savePins(pins);
        }
        
        function toggleChartPin(chart) {
            let pins = getPins();
            let idx = pins.charts.findIndex(c => c.url === chart.url);
            if (idx >= 0) pins.charts.splice(idx, 1);
            else pins.charts.push({...chart, pinnedAt: Date.now()});
            savePins(pins);
        }
    '''


def get_airport_card_styles():
    """Styles for airport cards"""
    return '''
        .airport-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }
        
        .airport-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
            text-decoration: none;
            color: var(--text);
            transition: all 0.2s;
            position: relative;
        }
        
        .airport-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--accent);
            transform: scaleY(0);
            transition: transform 0.2s;
        }
        
        .airport-card:hover {
            border-color: var(--accent);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(88, 166, 255, 0.12);
        }
        
        .airport-card:hover::before { transform: scaleY(1); }
        
        .airport-code {
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent);
            margin-bottom: 0.25rem;
        }
        
        .airport-name {
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
        }
        
        .airport-stats {
            font-size: 0.75rem;
            color: var(--text-dim);
        }
        
        .airport-stats strong { color: var(--accent); }
    '''


def get_file_list_styles():
    """Styles for file listings"""
    return '''
        .file-count {
            font-size: 0.875rem;
            color: var(--text-dim);
            margin-bottom: 1rem;
        }
        
        .file-list {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }
        
        .file-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border);
            text-decoration: none;
            color: var(--text);
            transition: all 0.15s;
        }
        
        .file-item:last-child { border-bottom: none; }
        
        .file-item:hover {
            background: var(--surface-hover);
            padding-left: 1.5rem;
        }
        
        .file-icon { font-size: 1.2rem; flex-shrink: 0; }
        .file-name { flex: 1; font-size: 0.9rem; word-break: break-word; }
        
        .file-type {
            font-size: 0.65rem;
            color: var(--text-dim);
            background: var(--bg);
            padding: 0.3rem 0.6rem;
            border-radius: 3px;
            text-transform: uppercase;
            font-weight: 600;
        }
    '''


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  MULTI-PAGE ATC CHARTS DIRECTORY GENERATOR")
    print("="*70 + "\n")
    
    # Authenticate
    service = authenticate_drive()
    if not service:
        return
    
    # Scan Drive
    print(f"📂 Scanning folder: {CHARTS_FOLDER_ID}\n")
    items = scan_folder_recursive(service, CHARTS_FOLDER_ID)
    
    file_count = sum(1 for item in items if item['mimeType'] != 'application/vnd.google-apps.folder')
    print(f"\n✅ Found {file_count} files\n")
    
    if file_count == 0:
        print("⚠️  No files found!")
        return
    
    # Organize
    print("🔨 Organizing hierarchy...\n")
    hierarchy = organize_by_hierarchy(items)
    
    # Create output directory
    create_output_dir()
    
    # Generate pages
    print("🎨 Generating pages...\n")
    
    # Index page
    regions = generate_index_page(hierarchy)
    
    # Region and airport pages
    for region_name, airports in hierarchy.items():
        region_slug = slugify(region_name)
        
        # Region page
        airport_list = generate_region_page(region_name, region_slug, airports)
        
        # Airport pages
        for airport_code, files in airports.items():
            generate_airport_page(region_name, region_slug, airport_code, files)
    
    print("\n" + "="*70)
    print("  🎉 SUCCESS!")
    print("="*70)
    print(f"\n📁 Site generated in: {OUTPUT_DIR}/")
    print(f"📄 Open: {OUTPUT_DIR}/index.html")
    print("\nNext steps:")
    print("  1. Open index.html in your browser to preview")
    print("  2. Upload entire folder to GitHub Pages")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
