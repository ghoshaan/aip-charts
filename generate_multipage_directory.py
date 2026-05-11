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
    """Generate main index page with regions"""
    regions = []
    
    for region_name, airports in hierarchy.items():
        file_count = sum(len(files) for files in airports.values())
        regions.append({
            'name': region_name,
            'icon': REGION_ICONS.get(region_name.lower(), REGION_ICONS['default']),
            'slug': slugify(region_name),
            'airportCount': len(airports),
            'fileCount': file_count
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
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ATC Charts Directory</h1>
            <div class="subtitle">Select a region to browse charts</div>
        </header>
        
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
</body>
</html>'''
    
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
            <h1>{display_title}</h1>
            <div class="subtitle">Charts and procedures</div>
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
    
    <script>
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
                const item = document.createElement('a');
                item.className = 'file-item';
                item.href = file.url;
                item.target = '_blank';
                item.innerHTML = `
                    <span class="file-icon">${{fileIcons[file.type] || '📄'}}</span>
                    <span class="file-name">${{file.name}}</span>
                    <span class="file-type">${{file.type}}</span>
                `;
                listEl.appendChild(item);
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
        }
        
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
