#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
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
import io
import time
import socket
import hashlib
from collections import defaultdict
from google.auth.transport.requests import Request

# Increase global timeout for slow Drive downloads
socket.setdefaulttimeout(300)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# ============================================================================
# CONFIGURATION
# ============================================================================

CHARTS_FOLDER_ID = '1DjkbZ9YMC5fS-zZvIpDiP9dCkUL120nK'  # UPDATE THIS!
OUTPUT_DIR = 'docs'
CHARTS_DOWNLOAD_DIR = os.path.join(OUTPUT_DIR, 'charts_data')
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
    # CE Range
    'CEN4': 'High River Regional',

    # CJ Range
    'CJB3': 'Steinbach',

    # CN Range
    'CNF4': 'Lindsay Kawartha Lakes Municipal',
    'CNP3': 'Arnprior',

    # CY Range
    'CYAB': 'Arctic Bay',
    'CYAC': 'Cat Lake',
    'CYAD': 'La Grande-3',
    'CYAG': 'Fort Frances',
    'CYAH': 'La Grande-4',
    'CYAM': 'Sault Ste Marie',
    'CYAQ': 'Kasabonika',
    'CYAS': 'Kangirsuk',
    'CYAT': 'Attawapiskat',
    'CYAU': 'South Shore',
    'CYAV': 'Winnipeg St Andrews',
    'CYAW': 'CFB Shearwater',
    'CYAX': 'Lac du Bonnet',
    'CYAY': 'St. Anthony',
    'CYAZ': 'Tofino-Long Beach',
    'CYBB': 'Kugaaruk',
    'CYBC': 'Baie-Comeau',
    'CYBE': 'Uranium City',
    'CYBF': 'Bonnyville',
    'CYBG': 'CFB Bagotville',
    'CYBK': 'Baker Lake',
    'CYBL': 'Campbell River',
    'CYBP': 'Brooks',
    'CYBQ': 'Tadoule Lake',
    'CYBR': 'Brandon Municipal',
    'CYBT': 'Brochet',
    'CYBU': 'Nipawin',
    'CYBV': 'Berens River',
    'CYBW': 'Calgary Springbank',
    'CYBX': 'Lourdes-de-Blanc-Sablon',
    'CYCA': 'Cartwright',
    'CYCB': 'Cambridge Bay',
    'CYCC': 'Cornwall',
    'CYCD': 'Nanaimo',
    'CYCE': 'Centralia/James T. Field',
    'CYCG': 'West Kootenay Regional',
    'CYCH': 'Miramichi',
    'CYCK': 'Chatham-Kent',
    'CYCL': 'Charlo',
    'CYCN': 'Cochrane',
    'CYCO': 'Kugluktuk',
    'CYCQ': 'Chetwynd',
    'CYCR': 'Cross Lake',
    'CYCS': 'Chesterfield Inlet',
    'CYCY': 'Clyde River',
    'CYCZ': 'Fairmont Hot Springs',
    'CYDA': 'Dawson City',
    'CYDB': 'Burwash',
    'CYDC': 'Princeton',
    'CYDF': 'Deer Lake Regional',
    'CYDL': 'Dease Lake',
    'CYDM': 'Ross River',
    'CYDN': 'Dauphin',
    'CYDO': 'Lac-Saint-Jean',
    'CYDP': 'Nain',
    'CYDQ': 'Dawson Creek',
    'CYED': 'CFB Edmonton',
    'CYEE': 'Huronia Midland',
    'CYEG': 'Edmonton',
    'CYEK': 'Arviat',
    'CYEL': 'Elliot Lake',
    'CYEM': 'Manitoulin East',
    'CYEN': 'Estevan Regional',
    'CYER': 'Fort Severn',
    'CYES': 'Edmundston',
    'CYET': 'Edson',
    'CYEU': 'Eureka',
    'CYEV': 'Inuvik Mike Zubko',
    'CYEY': 'Amos/Magny',
    'CYFA': 'Fort Albany',
    'CYFB': 'Iqaluit',
    'CYFC': 'Fredericton',
    'CYFD': 'Brantford',
    'CYFH': 'Fort Hope',
    'CYFJ': 'Mont-Tremblant International',
    'CYFO': 'Flin Flon',
    'CYFR': 'Fort Resolution',
    'CYFS': 'Fort Simpson',
    'CYFT': 'Makkovik',
    'CYGD': 'Goderich',
    'CYGE': 'Golden',
    'CYGH': 'Fort Good Hope',
    'CYGK': 'Kingston',
    'CYGL': 'La Grande Riviere',
    'CYGM': 'Gimli',
    'CYGO': 'Gods Lake Narrows',
    'CYGP': 'Michel-Pouliot Gaspe',
    'CYGQ': 'Geraldton (Greenstone Regional)',
    'CYGR': 'Iles-de-la-Madeleine',
    'CYGT': 'Igloolik',
    'CYGV': 'Havre Saint-Pierre',
    'CYGW': 'Kuujjuarapik',
    'CYGX': 'Gillam',
    'CYGZ': 'Grise Fiord',
    'CYHA': 'Quaqtaq',
    'CYHB': 'Hudson Bay',
    'CYHD': 'Dryden',
    'CYHF': 'Hearst',
    'CYHH': 'Nemiscau',
    'CYHI': 'Ulukhaktok',
    'CYHK': 'Gjoa Haven',
    'CYHM': 'John C Munro Hamilton Airport',
    'CYHN': 'Hornepayne',
    'CYHO': 'Hopedale',
    'CYHR': 'Chevery',
    'CYHS': 'Saugeen',
    'CYHU': 'Montreal Saint-Hubert',
    'CYHY': 'Hay River',
    'CYHZ': 'Halifax',
    'CYIB': 'Atikokan',
    'CYID': 'Digby',
    'CYIF': 'Saint-Augustin',
    'CYIK': 'Ivujivik',
    'CYIO': 'Pond Inlet',
    'CYIV': 'Island Lake',
    'CYJF': 'Fort Liard',
    'CYJN': 'Saint-Jean',
    'CYJP': 'Fort Providence',
    'CYJT': 'Stephenville International',
    'CYKA': 'Kamloops',
    'CYKC': 'Collins Bay',
    'CYKD': 'Aklavik Freddie Carmichael',
    'CYKF': 'Kitchener Waterloo',
    'CYKG': 'Kangiqsujuaq',
    'CYKJ': 'Key Lake',
    'CYKL': 'Schefferville',
    'CYKM': 'Kincardine',
    'CYKO': 'Akulivik',
    'CYKP': 'Ogoki Post',
    'CYKQ': 'Waskaganish',
    'CYKX': 'Kirkland Lake',
    'CYKY': 'Kindersley Regional',
    'CYLA': 'Aupaluk',
    'CYLB': 'Lac La Biche',
    'CYLC': 'Kimmirut',
    'CYLD': 'Chapleau',
    'CYLH': 'Lansdowne House',
    'CYLJ': 'Meadow Lake',
    'CYLK': 'Lutselke',
    'CYLL': 'Lloydminster',
    'CYLQ': 'La Tuque',
    'CYLS': 'Lake Simcoe',
    'CYLT': 'Alert',
    'CYLU': 'Kangiqsualujjuaq',
    'CYLW': 'Kelowna',
    'CYMA': 'Mayo',
    'CYME': 'Matane',
    'CYMG': 'Manitouwadge',
    'CYMH': 'Mary\'s Harbour',
    'CYMJ': 'CFB Moose Jaw',
    'CYML': 'Charlevoix',
    'CYMM': 'Fort McMurray',
    'CYMO': 'Moosonee',
    'CYMT': 'Chibougamau Chapais',
    'CYMU': 'Umiujaq',
    'CYMW': 'Maniwaki',
    'CYMX': 'Montreal-Mirabel International',
    'CYNA': 'Natashquan',
    'CYNC': 'Wemindji',
    'CYND': 'Gatineau-Ottawa Executive',
    'CYNE': 'Norway House',
    'CYNJ': 'Langley Regional',
    'CYNL': 'Points North Landing',
    'CYNM': 'Matagami',
    'CYNN': 'Nejanilini Lake',
    'CYNR': 'Fort McKay/Horizon',
    'CYOA': 'Ekati',
    'CYOC': 'Old Crow',
    'CYOD': 'CFB Cold Lake',
    'CYOH': 'Oxford House',
    'CYOJ': 'High Level',
    'CYOO': 'Oshawa Executive',
    'CYOP': 'Rainbow Lake',
    'CYOS': 'Meaford',
    'CYOW': 'Ottawa',
    'CYPA': 'Prince Albert Glass Field',
    'CYPC': 'Paulatuk',
    'CYPD': 'Port Hawkesbury',
    'CYPE': 'Peace River',
    'CYPG': 'Portage la Prairie/Southport',
    'CYPH': 'Inukjuak',
    'CYPK': 'Pitt Meadows',
    'CYPL': 'Pickle Lake',
    'CYPM': 'Pikangikum',
    'CYPN': 'Port-Menier',
    'CYPX': 'Puvirnituq',
    'CYPY': 'Fort Chipewyan',
    'CYPZ': 'Burns Lake',
    'CYQA': 'Muskoka',
    'CYQB': 'Quebec Jean Lesage',
    'CYQD': 'The Pas',
    'CYQF': 'Red Deer Regional',
    'CYQG': 'Windsor',
    'CYQH': 'Watson Lake',
    'CYQI': 'Yarmouth',
    'CYQK': 'Kenora',
    'CYQL': 'Lethbridge',
    'CYQM': 'Greater Moncton Romeo LeBlanc',
    'CYQN': 'Nakina',
    'CYQQ': 'CFB Comox or 19 wing',
    'CYQR': 'Regina',
    'CYQS': 'St. Thomas',
    'CYQT': 'Thunder Bay',
    'CYQU': 'Grande Prairie',
    'CYQV': 'Yorkton',
    'CYQW': 'North Battleford',
    'CYQX': 'Gander International',
    'CYQY': 'JA Douglas McCurdy Sydney',
    'CYQZ': 'Quesnel',
    'CYRA': 'Gamètì/Rae Lakes',
    'CYRB': 'Resolute Bay',
    'CYRC': 'Chicoutimi/Saint-Honoré',
    'CYRI': 'Rivière-du-Loup',
    'CYRJ': 'Roberval',
    'CYRL': 'Red Lake',
    'CYRM': 'Rocky Mountain House',
    'CYRP': 'Carp',
    'CYRQ': 'Trois-Rivieres',
    'CYRS': 'Red Sucker Lake',
    'CYRT': 'Rankin Inlet',
    'CYRV': 'Revelstoke',
    'CYSA': 'Stratford',
    'CYSB': 'Sudbury',
    'CYSC': 'Sherbrooke',
    'CYSF': 'Stony Rapids',
    'CYSG': 'Saint-Georges',
    'CYSH': 'Smiths Falls-Montague',
    'CYSJ': 'Saint John',
    'CYSK': 'Sanikiluaq',
    'CYSL': 'Saint-Léonard',
    'CYSM': 'Fort Smith',
    'CYSN': 'St. Catharines/Niagara',
    'CYSP': 'Marathon',
    'CYSQ': 'Atlin',
    'CYST': 'St Theresa Point',
    'CYSU': 'Summerside',
    'CYSW': 'Sparwood/Elk Valley',
    'CYSY': 'Sachs Harbour',
    'CYSZ': 'Sainte-Anne-des-Monts',
    'CYTA': 'Pembroke',
    'CYTE': 'Kinngait',
    'CYTF': 'Alma',
    'CYTH': 'Thompson',
    'CYTL': 'Big Trout Lake',
    'CYTN': 'Trenton Aerodrome',
    'CYTQ': 'Tasiujaq',
    'CYTR': 'CFB Trenton',
    'CYTS': 'Timmins Victor M Power',
    'CYTZ': 'Toronto Island',
    'CYUB': 'Tuktoyaktuk',
    'CYUL': 'Montreal',
    'CYUT': 'Naujaat',
    'CYUX': 'Sanirajak',
    'CYUY': 'Rouyn-Noranda',
    'CYVB': 'Bonaventure',
    'CYVC': 'La Ronge Barber Field',
    'CYVD': 'Virden',
    'CYVG': 'Vermilion',
    'CYVK': 'Vernon',
    'CYVL': 'Colville Lake',
    'CYVM': 'Qikiqtarjuaq',
    'CYVP': 'Kuujjuaq',
    'CYVQ': 'Norman Wells',
    'CYVR': 'Vancouver',
    'CYVT': 'Buffalo Narrows',
    'CYVV': 'Wiarton',
    'CYVZ': 'Deer Lake (Ontario)',
    'CYWG': 'Winnipeg',
    'CYWJ': 'Déline',
    'CYWK': 'Wabush',
    'CYWL': 'Williams Lake',
    'CYWM': 'Athabasca',
    'CYWP': 'Webequie',
    'CYWV': 'Wainwright',
    'CYWY': 'Wrigley',
    'CYXC': 'Cranbrook Canadian Rockies International',
    'CYXE': 'Saskatoon',
    'CYXH': 'Medicine Hat',
    'CYXJ': 'Fort St. John',
    'CYXK': 'Rimouski',
    'CYXL': 'Sioux Lookout',
    'CYXN': 'Whale Cove',
    'CYXP': 'Pangnirtung',
    'CYXQ': 'Beaver Creek',
    'CYXR': 'Earlton Timiskaming Regional',
    'CYXS': 'Prince George',
    'CYXT': 'Terrace-Kitimat',
    'CYXU': 'London',
    'CYXX': 'Abbotsford',
    'CYXY': 'Erik Nielsen Whitehorse International',
    'CYXZ': 'Wawa',
    'CYYC': 'Calgary',
    'CYYD': 'Smithers',
    'CYYE': 'Fort Nelson',
    'CYYF': 'Penticton Regional',
    'CYYG': 'Charlottetown',
    'CYYH': 'Taloyoak',
    'CYYJ': 'Victoria International',
    'CYYL': 'Lynn Lake',
    'CYYN': 'Swift Current',
    'CYYQ': 'Churchill',
    'CYYR': 'CFB Goose Bay',
    'CYYT': 'St Johns',
    'CYYU': 'Kapuskasing',
    'CYYW': 'Armstrong',
    'CYYY': 'Mont-Joli',
    'CYYZ': 'Toronto Pearson',
    'CYZE': 'Gore Bay-Manitoulin',
    'CYZF': 'Yellowknife',
    'CYZG': 'Salluit',
    'CYZH': 'Slave Lake',
    'CYZP': 'Sandspit',
    'CYZR': 'Sarnia',
    'CYZS': 'Coral Harbour',
    'CYZT': 'Port Hardy',
    'CYZU': 'Whitecourt',
    'CYZV': 'Sept-Iles',
    'CYZW': 'Teslin',
    'CYZX': 'CFB Greenwood',
    'CYZY': 'Mackenzie',

    # CZ Range
    'CZAC': 'York Landing',
    'CZAM': 'Salmon Arm',
    'CZBA': 'Burlington Executive',
    'CZBB': 'Boundary Bay',
    'CZBD': 'Ilford',
    'CZBF': 'Bathurst',
    'CZBM': 'Roland-Désourdy (Bromont)',
    'CZEE': 'Kelsey',
    'CZEM': 'Eastmain River',
    'CZFA': 'Faro',
    'CZFD': 'Fond-du-Lac',
    'CZFG': 'Pukatawagan',
    'CZFM': 'Fort McPherson',
    'CZFN': 'Tulita',
    'CZGF': 'Grand Forks',
    'CZGI': 'Gods River',
    'CZGR': 'Little Grand Rapids',
    'CZHP': 'High Prairie',
    'CZJG': 'Jenpeg',
    'CZJN': 'Swan River',
    'CZKE': 'Kashechewan',
    'CZLQ': 'Thicket Portage',
    'CZMD': 'Muskrat Dam',
    'CZML': 'South Cariboo',
    'CZMN': 'Pikwitonei',
    'CZMT': 'Masset',
    'CZNG': 'Poplar River',
    'CZPB': 'Sachigo Lake',
    'CZPC': 'Pincher Creek',
    'CZPO': 'Pinehouse Lake',
    'CZRJ': 'Round Lake (Weagamow Lake)',
    'CZSJ': 'Sandy Lake',
    'CZSN': 'South Indian Lake',
    'CZTA': 'Bloodvein River',
    'CZTM': 'Shamattawa',
    'CZUM': 'Churchill Falls',
    'CZVL': 'Villeneuve',
    'CZWH': 'Lac Brochet',
    'CZWL': 'Wollaston Lake',

    # EH Range
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

    # EI Range
    'EICK': 'Cork',
    'EIDL': 'Donegal',
    'EIDW': 'Dublin',
    'EIKN': 'Ireland West (Knock)',
    'EIKY': 'Kerry',
    'EINN': 'Shannon',
    'EISG': 'Sligo',
    'EIWF': 'Waterford',
    'EIWT': 'Weston',

    # EN Range
    'ENROUTE': 'ENROUTE',

    # LS Range
    'LSGC': 'Les Eplatures',
    'LSGG': 'Geneva',
    'LSGS': 'Sion',
    'LSMP': 'Payerne',
    'LSZA': 'Lugano',
    'LSZB': 'Bern',
    'LSZC': 'Buochs',
    'LSZG': 'Grenchen',
    'LSZH': 'Zurich',
    'LSZL': 'Locarno',
    'LSZR': 'St. Gallen-Altenrhein',
    'LSZS': 'Samedan',
}

# ============================================================================
# AUTHENTICATION
# ============================================================================

def authenticate_drive():
    """Authenticate with Google Drive API.

    In CI (GitHub Actions): reads GOOGLE_SERVICE_ACCOUNT env var (service account JSON).
    Locally: uses OAuth2 via credentials.json / token.json.
    """
    print("🔐 Authenticating...")

    # Service account path — used in CI
    service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
    if service_account_json:
        from google.oauth2 import service_account as sa
        creds = sa.Credentials.from_service_account_info(
            json.loads(service_account_json),
            scopes=SCOPES
        )
        print("✅ Authenticated via service account!\n")
        return build('drive', 'v3', credentials=creds)

    # OAuth2 path — used locally
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
# STATE MANAGEMENT
# ============================================================================

MANIFEST_FILE = 'manifest.json'

def load_manifest():
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'files': {}, 'airports': {}}
    return {'files': {}, 'airports': {}}

def save_manifest(manifest):
    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f, indent=4)

# ============================================================================
# DRIVE SCANNING & DOWNLOADING
# ============================================================================

def download_file(service, file_id, destination, drive_md5=None, max_retries=3):
    """Download a file from Google Drive if it doesn't exist or has changed"""
    if os.path.exists(destination):
        return True
    
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    
    for attempt in range(max_retries):
        try:
            print(f"   📥 Downloading: {os.path.basename(destination)}...")
            request = service.files().get_media(fileId=file_id)
            fh = io.FileIO(destination, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            return True
        except Exception as e:
            print(f"   ⚠️  Error downloading {file_id} (Attempt {attempt + 1}/{max_retries}): {e}")
            if os.path.exists(destination):
                os.remove(destination)
            time.sleep(2 ** attempt)
            
    print(f"   ❌ Failed to download {file_id} after {max_retries} attempts.")
    return False

def scan_folder_recursive(service, folder_id, path=''):
    """Recursively scan folder, following shortcut folders too"""
    items = []

    try:
        page_token = None
        while True:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageSize=1000,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, parents, shortcutDetails, md5Checksum, size)",
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
                    'path': path,
                    'md5': item.get('md5Checksum'),
                    'size': item.get('size')
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


def organize_by_hierarchy(service, items, manifest):
    """
    Organize files into: Region → Airport → Files
    And download them locally if needed.
    """
    hierarchy = defaultdict(lambda: defaultdict(list))
    
    total_files = sum(1 for item in items if item['mimeType'] != 'application/vnd.google-apps.folder')
    downloaded_count = 0
    skipped_count = 0

    print(f"📦 Processing {total_files} files...")

    for item in items:
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            continue
        
        # Parse path: "Region/Airport/file.pdf"
        path_parts = item['path'].split('/')
        
        if len(path_parts) < 2:
            # print(f"⚠️  Skipping file with unexpected path: {item['path']} / {item['name']}")
            continue
        
        region = path_parts[0]
        airport = path_parts[1]
        
        # Determine local path
        safe_filename = slugify(item['name'])
        if '.' in item['name']:
            parts = item['name'].split('.')
            ext = parts[-1]
            safe_filename = f"{slugify('.'.join(parts[:-1]))}.{ext}"
        
        local_rel_path = f"charts_data/{slugify(region)}/{slugify(airport)}/{safe_filename}"
        local_full_path = os.path.join(OUTPUT_DIR, local_rel_path)
        
        # Incremental Check
        needs_download = True
        if item['id'] in manifest['files']:
            cached = manifest['files'][item['id']]
            if cached.get('md5') == item['md5'] and os.path.exists(local_full_path):
                needs_download = False
        
        download_ok = True
        if needs_download:
            download_ok = download_file(service, item['id'], local_full_path, item['md5'])
            if download_ok:
                downloaded_count += 1
                manifest['files'][item['id']] = {
                    'md5': item['md5'],
                    'path': local_rel_path,
                    'name': item['name']
                }
        else:
            skipped_count += 1

        drive_file_id = item['id']
        drive_view_url = item.get('viewUrl', '#')
        # Only set localUrl if the file actually exists locally
        resolved_local_url = local_rel_path if download_ok and os.path.exists(local_full_path) else '#'
        hierarchy[region][airport].append({
            'id': safe_filename,
            'name': item['name'],
            'url': resolved_local_url,
            'localUrl': resolved_local_url,
            'driveId': drive_file_id,
            'driveUrl': drive_view_url,
            'type': get_file_type(item['mimeType'], item.get('ext', ''))
        })
    
    print(f"✨ Successfully processed {total_files} files.")
    print(f"   📥 Downloaded: {downloaded_count}")
    print(f"   ⏩ Skipped:    {skipped_count} (already on site)\n")
    return hierarchy


# ============================================================================
# HTML GENERATION
# ============================================================================

def create_output_dir():
    """Create output directory"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Disable Jekyll so GitHub Pages serves files as-is
    with open(os.path.join(OUTPUT_DIR, '.nojekyll'), 'w') as f:
        f.write('')

    # Also ensure charts_data exists
    if not os.path.exists(CHARTS_DOWNLOAD_DIR):
        os.makedirs(CHARTS_DOWNLOAD_DIR)


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
            airport_slug = airport_code.split()[0]

            # Add airport to global index
            global_search_index.append({
                'type': 'airport',
                'name': airport_display,
                'code': airport_code,
                'region': region_name,
                'url': f"{airport_slug}/",
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
                    'localUrl': f.get('localUrl', '#'),
                    'driveId': f.get('driveId', ''),
                    'driveUrl': f.get('driveUrl', '#'),
                    'icon': '📄' if f['type'] == 'pdf' else '🖼️',
                    'pageUrl': f"{airport_slug}/"
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

    # Write search index to separate file to keep HTML small
    with open(f"{OUTPUT_DIR}/search_data.json", 'w', encoding='utf-8') as f:
        json.dump(global_search_index, f)

    # Pre-build region cards to avoid nested f-string bracket issues on Python < 3.12
    region_cards_html = f'''
                <a href="worldwide_search.html" class="region-card" style="border-color: var(--accent); background: var(--accent-glow);">
                    <span class="card-icon">🌍</span>
                    <div class="card-title">Worldwide Search</div>
                    <div class="card-count">
                        Search <strong>24,000+</strong> SID/STAR procedures
                    </div>
                </a>'''
    for r in regions:
        region_cards_html += f'''
                <a href="{r['slug']}.html" class="region-card">
                    <span class="card-icon">{r['icon']}</span>
                    <div class="card-title">{r['name']}</div>
                    <div class="card-count">
                        <strong>{r['airportCount']}</strong> airports &bull;
                        <strong>{r['fileCount']}</strong> files
                    </div>
                </a>'''

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
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .card-count {{
            font-size: 0.875rem;
            color: var(--text-dim);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        .card-count strong {{
            color: var(--accent);
        }}

        /* Global Search Styles */
        .results-section {{
            margin-top: 2rem;
        }}

        .search-result-item {{ display: flex; align-items: center; gap: 1rem; padding: 1rem; text-decoration: none; color: var(--text); border-bottom: 1px solid var(--border); transition: all 0.2s; min-width: 0; flex: 1; }}

        .search-result-item:hover {{
            border-color: var(--accent);
            background: var(--surface-hover);
            transform: translateX(4px);
        }}

        .result-icon {{ font-size: 1.25rem; flex-shrink: 0; }}
        .result-info {{ flex: 1; min-width: 0; }}
        .result-name {{ font-weight: 600; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .result-meta {{ font-size: 0.8rem; color: var(--text-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .result-type {{ 
            font-size: 0.6rem; 
            text-transform: uppercase; 
            background: var(--bg); 
            padding: 0.2rem 0.5rem; 
            border-radius: 3px;
            letter-spacing: 0.05em;
            flex-shrink: 0;
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
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div class="subtitle" style="color: var(--accent); margin-bottom: 0;">📌 Pinned Items</div>
                <button onclick="clearAllPins()" class="clear-all-btn">Clear all</button>
            </div>
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
                {region_cards_html}
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
        let searchIndex = [];
        let fuse = null;

        // Load search index asynchronously
        fetch('search_data.json')
            .then(res => res.json())
            .then(data => {{
                searchIndex = data;
                fuse = new Fuse(searchIndex, {{
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
                renderPins(); 
            }});

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
                card.href = a.slug + '/';
                card.style.border = 'none';
                card.style.flex = '1';
                card.style.minWidth = '0';
                card.innerHTML = `
                    <span style="font-size: 1.25rem;">✈️</span>
                    <div class="pin-info">
                        <div class="pin-name">${{a.name}}</div>
                        <div class="pin-meta">${{a.region}}</div>
                    </div>
                `;

                const unpinBtn = document.createElement('button');
                unpinBtn.className = 'unpin-btn';
                unpinBtn.innerHTML = '✕';
                unpinBtn.title = 'Unpin';
                unpinBtn.onclick = (e) => {{
                    e.preventDefault();
                    e.stopPropagation();
                    toggleAirportPin(a);
                    renderPins();
                }};

                wrapper.appendChild(card);
                wrapper.appendChild(unpinBtn);
                grid.appendChild(wrapper);
            }});

            pins.charts.forEach(c => {{
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

                if ((!id || !localUrl) && typeof searchIndex !== 'undefined') {{
                    const found = searchIndex.find(item => 
                        (c.id && item.id === c.id) || 
                        (c.url && item.url.split('?')[0] === c.url.split('?')[0]) ||
                        (item.name === c.name && item.airport === c.airport)
                    );
                    if (found) {{
                        id = id || found.id;
                        localUrl = localUrl || found.localUrl;
                        driveUrl = driveUrl || found.url;
                        console.log('🔄 Recovered pin data for:', name);
                    }}
                }}

                if (localUrl && localUrl !== '#') {{
                    card.href = `#view=${{id}}`;
                    card.onclick = (e) => {{ 
                        e.preventDefault(); 
                        openViewer(id, name, driveUrl, localUrl, false, c.airport);
                    }};
                }} else {{
                    console.warn('⚠️ Pin missing localUrl, falling back to Drive:', name);
                    card.href = driveUrl || '#';
                    card.target = '_blank';
                }}
                card.innerHTML = `
                    <span style="font-size: 1.25rem;">📄</span>
                    <div class="pin-info">
                        <div class="pin-name">${{c.name}}</div>
                        <div class="pin-meta">${{c.airport}} &bull; ${{c.region}}</div>
                    </div>
                `;

                wrapper.appendChild(card);

                if (localUrl && localUrl !== '#') {{
                    const newTabBtn = document.createElement('a');
                    newTabBtn.className = 'new-tab-btn';
                    newTabBtn.href = `${{c.pageUrl}}#view=${{id}}`;
                    newTabBtn.target = '_blank';
                    newTabBtn.title = 'Open in new tab';
                    newTabBtn.innerHTML = '↗️';
                    newTabBtn.style.marginRight = '0.5rem';
                    wrapper.appendChild(newTabBtn);
                }}

                const unpinBtn = document.createElement('button');
                unpinBtn.className = 'unpin-btn';
                unpinBtn.innerHTML = '✕';
                unpinBtn.title = 'Unpin';
                unpinBtn.onclick = (e) => {{
                    e.preventDefault();
                    e.stopPropagation();
                    toggleChartPin(c);
                    renderPins();
                }};

                wrapper.appendChild(unpinBtn);
                grid.appendChild(wrapper);
            }});
        }}

        renderPins();

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

            if (!fuse) return;
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
                const wrapper = document.createElement('div');
                wrapper.style.display = 'flex';
                wrapper.style.alignItems = 'center';
                wrapper.style.gap = '0.5rem';

                const div = document.createElement('a');
                div.className = 'search-result-item';
                div.style.flex = '1';
                div.style.marginBottom = '0';
                div.style.minWidth = '0';

                if (item.type === 'chart') {{
                    div.href = `#view=${{item.id}}`;
                    div.onclick = (e) => {{
                        e.preventDefault();
                        openViewer(item.id, item.name, item.driveUrl || '#', item.localUrl, false, item.airport);
                    }};
                }} else {{
                    div.href = item.url;
                }}

                const meta = item.type === 'airport'
                    ? `${{item.region}}` 
                    : `${{item.airport}} &bull; ${{item.region}}`;

                div.innerHTML = `
                    <span class="result-icon">${{item.icon}}</span>
                    <div class="result-info">
                        <div class="result-name">${{item.name}}</div>
                        <div class="result-meta">${{meta}}</div>
                    </div>
                    <span class="result-type">${{item.type}}</span>
                `;

                wrapper.appendChild(div);

                if (item.type === 'chart') {{
                    const newTabBtn = document.createElement('a');
                    newTabBtn.className = 'new-tab-btn';
                    newTabBtn.href = `${{item.pageUrl}}#view=${{item.id}}`;
                    newTabBtn.target = '_blank';
                    newTabBtn.title = 'Open in new tab';
                    newTabBtn.innerHTML = '↗️';
                    newTabBtn.style.marginRight = '0.5rem';
                    wrapper.appendChild(newTabBtn);
                }}

                const pinBtn = document.createElement('button');
                pinBtn.className = 'pin-btn';
                const pins = getPins();
                const isPinned = item.type === 'airport'
                    ? pins.airports.some(a => a.slug === item.code)
                    : pins.charts.some(c => c.url === item.url);

                if (isPinned) pinBtn.classList.add('pinned');
                pinBtn.innerHTML = '📌';
                pinBtn.onclick = (e) => {{
                    e.preventDefault();
                    e.stopPropagation();
                    if (item.type === 'airport') {{
                        toggleAirportPin({{
                            slug: item.code,
                            name: item.name,
                            region: item.region
                        }});
                    }} else {{
                        toggleChartPin({{
                            id: item.id,
                            name: item.name,
                            url: item.url,
                            localUrl: item.localUrl,
                            type: item.icon === '📄' ? 'pdf' : 'image',
                            airport: item.airport,
                            region: item.region,
                            pageUrl: item.pageUrl
                        }});
                    }}
                    pinBtn.classList.toggle('pinned');
                }};

                wrapper.appendChild(pinBtn);
                resultsList.appendChild(wrapper);
            }});
        }});
    </script>
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
            'slug': airport_code.split()[0],
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
        {get_pinning_js()}
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
                const wrapper = document.createElement('div');
                wrapper.style.cssText = 'position:relative;';

                const card = document.createElement('a');
                card.className = 'airport-card';
                card.href = airport.slug + '/';
                card.style.display = 'block';
                card.innerHTML = `
                    <div class="airport-code">${{airport.displayName}}</div>
                    <div class="airport-stats">
                        <span>📄 <strong>${{airport.fileCount}}</strong> files</span>
                    </div>
                `;

                const pins = getPins();
                const isPinned = pins.airports.some(a => a.slug === airport.slug);
                const pinBtn = document.createElement('button');
                pinBtn.className = 'pin-btn' + (isPinned ? ' pinned' : '');
                pinBtn.innerHTML = '📌';
                pinBtn.title = isPinned ? 'Unpin airport' : 'Pin airport';
                pinBtn.style.cssText = 'position:absolute;top:0.5rem;right:0.5rem;z-index:2;';
                pinBtn.onclick = (e) => {{
                    e.preventDefault();
                    e.stopPropagation();
                    toggleAirportPin({{
                        slug: airport.slug,
                        name: airport.displayName,
                        region: airport.region || ''
                    }});
                    pinBtn.classList.toggle('pinned');
                    pinBtn.title = pinBtn.classList.contains('pinned') ? 'Unpin airport' : 'Pin airport';
                }};

                wrapper.appendChild(card);
                wrapper.appendChild(pinBtn);
                grid.appendChild(wrapper);
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


def group_multipage_files(files):
    """Group _PG_XX continuation files under their base file's 'pages' array."""
    pg_pattern = re.compile(r'^(.+)_pg_(\d+)(\.pdf)$', re.IGNORECASE)
    base_to_pages = {}
    page_file_ids = set()

    for f in files:
        m = pg_pattern.match(f['id'])
        if m:
            base_id = m.group(1) + m.group(3)
            page_num = int(m.group(2))
            base_to_pages.setdefault(base_id, []).append((page_num, f))
            page_file_ids.add(f['id'])

    result = []
    for f in files:
        if f['id'] in page_file_ids:
            continue
        if f['id'] in base_to_pages:
            all_pages = sorted([(1, f)] + base_to_pages[f['id']], key=lambda x: x[0])
            new_f = dict(f, pages=[p for _, p in all_pages])
            new_f['name'] = re.sub(r'\.pdf$', '', f['name'], flags=re.IGNORECASE)
            result.append(new_f)
        else:
            result.append(f)
    return result


def generate_airport_page(region_name, region_slug, airport_code, files, manifest):
    """Generate airport page with file listings if needed"""
    
    name = AIRPORT_NAMES.get(airport_code, airport_code)
    display_title = f"{airport_code} - {name}" if name != airport_code else airport_code
    airport_slug = airport_code.split()[0]

    # Check if we can skip regeneration
    # We use a simple hash of the files list
    airport_data_hash = hashlib.md5(json.dumps(files, sort_keys=True).encode()).hexdigest()
    if manifest['airports'].get(airport_slug) == airport_data_hash and os.path.exists(f"{OUTPUT_DIR}/{airport_slug}/index.html"):
        return airport_slug

    # Adjust file URLs for subdirectory context; rootUrl keeps the root-relative path for pin storage
    adjusted_files = [dict(f, url='../' + f['url'], localUrl='../' + f['localUrl'], rootUrl=f['localUrl'], driveId=f.get('driveId',''), driveUrl=f.get('driveUrl','#')) for f in files]
    adjusted_files = group_multipage_files(adjusted_files)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{display_title} - ATC Charts</title>
    <link rel="icon" type="image/png" href="../favicon.png">
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
            <a href="../index.html">Home</a>
            <span class="breadcrumb-separator">›</span>
            <a href="../{region_slug}.html">{region_name}</a>
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
                <strong>Examples:</strong> <code>star</code> &bull; <code>RWY 04</code> &bull; <code>ILS</code>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-btn active" data-filter="all">All</button>
            <button class="filter-btn" data-filter="pdf">PDF</button>
            <button class="filter-btn" data-filter="image">Images</button>
        </div>
        
        <hr style="margin: 2rem 0; border: none; border-top: 1px solid var(--border);">
        
        <div class="file-count" id="fileCount">Showing {len(adjusted_files)} files</div>
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
            icao: '{airport_slug}',
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

        const files = {json.dumps(adjusted_files, indent=8)};
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
                wrapper.style.minWidth = '0';

                const item = document.createElement('a');
                item.className = 'file-item';
                item.style.minWidth = '0';
                item.href = `#view=${{file.id}}`;
                item.onclick = (e) => {{
                    e.preventDefault();
                    openViewer(file.id, file.name, file.driveUrl || '#', file.localUrl, false, airportCtx.icao);
                }};
                item.style.borderBottom = 'none';
                item.style.flex = '1';
                const pagesBadge = file.pages && file.pages.length > 1
                    ? `<span class="file-type">${{file.pages.length}} pages</span>`
                    : `<span class="file-type">${{file.type}}</span>`;
                item.innerHTML = `
                    <span class="file-icon">${{fileIcons[file.type] || '📄'}}</span>
                    <span class="file-name">${{file.name}}</span>
                    ${{pagesBadge}}
                `;

                const pins = getPins();
                const isPinned = pins.charts.some(c => c.url === file.rootUrl);
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
                        url: file.rootUrl,
                        localUrl: file.rootUrl,
                        type: file.type,
                        airport: airportCtx.name,
                        region: airportCtx.region,
                        pageUrl: `${{airportCtx.slug}}/`
                    }});
                    pinBtn.classList.toggle('pinned');
                    pinBtn.title = pinBtn.classList.contains('pinned') ? 'Unpin from homepage' : 'Pin to homepage';
                }};

                wrapper.appendChild(item);

                const newTabBtn = document.createElement('a');
                newTabBtn.className = 'new-tab-btn';
                newTabBtn.href = `#view=${{file.id}}`;
                newTabBtn.target = '_blank';
                newTabBtn.title = 'Open in new tab';
                newTabBtn.innerHTML = '↗️';
                newTabBtn.style.marginRight = '0.5rem';
                wrapper.appendChild(newTabBtn);

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
    
    os.makedirs(f"{OUTPUT_DIR}/{airport_slug}", exist_ok=True)
    with open(f"{OUTPUT_DIR}/{airport_slug}/index.html", 'w', encoding='utf-8') as f:
        f.write(html)

    manifest['airports'][airport_slug] = airport_data_hash
    return airport_slug


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
            --accent: #79b8ff;
            --accent-glow: rgba(121, 184, 255, 0.15);
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
        
        .header-content { flex: 1; min-width: 0; }

        h1 {
            font-family: 'Rajdhani', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent);
            letter-spacing: 0.02em;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .subtitle {
            font-size: 0.875rem;
            color: var(--text-dim);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .new-tab-btn {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 0.85rem;
            padding: 0.5rem;
            opacity: 0.4;
            transition: all 0.2s;
            flex-shrink: 0;
            line-height: 1;
            border-radius: 4px;
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .new-tab-btn:hover { opacity: 1; background: var(--accent-glow); color: var(--accent); }
        
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

        .unpin-btn {
            background: none;
            border: none;
            cursor: pointer;
            font-size: 0.75rem;
            color: var(--text-dim);
            padding: 0.4rem;
            opacity: 0.6;
            transition: all 0.2s;
            line-height: 1;
            margin-left: auto;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }
        .unpin-btn:hover { 
            opacity: 1; 
            color: var(--warning); 
            background: rgba(210, 153, 34, 0.1);
        }

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

        .pin-card-wrapper {
            min-width: 0;
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
            min-width: 0;
        }

        .pin-card:hover {
            border-color: var(--accent);
            transform: translateY(-2px);
        }

        .pin-info { flex: 1; min-width: 0; }
        .pin-name { font-weight: 600; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .pin-meta { font-size: 0.75rem; color: var(--text-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        .clear-all-btn {
            background: none;
            border: 1px solid var(--border);
            color: var(--text-dim);
            font-family: inherit;
            font-size: 0.65rem;
            padding: 0.3rem 0.75rem;
            border-radius: 4px;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .clear-all-btn:hover {
            border-color: var(--warning);
            color: var(--warning);
            background: rgba(210, 153, 34, 0.1);
            transform: translateY(-1px);
        }
        .clear-all-btn::before {
            content: '🗑️';
            font-size: 0.8rem;
        }

        /* Pro Viewer Modal */
        .viewer-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(13, 17, 23, 0.98);
            z-index: 1000;
            display: none;
            flex-direction: column;
            backdrop-filter: blur(4px);
        }

        .viewer-header {
            padding: 0.75rem 1.5rem;
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 1.5rem;
            z-index: 1001;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }

        .viewer-title {
            flex: 1;
            font-family: 'Rajdhani', sans-serif;
            font-weight: 700;
            color: var(--accent);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 1.1rem;
        }

        .viewer-controls {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .control-btn {
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.4rem 0.75rem;
            border-radius: 4px;
            cursor: pointer;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.7rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            transition: all 0.2s;
            white-space: nowrap;
        }

        .control-btn:hover {
            border-color: var(--accent);
            background: var(--surface-hover);
            transform: translateY(-1px);
        }

        .control-btn.active {
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }

        .viewer-content {
            flex: 1;
            position: relative;
            overflow: hidden;
            background: #05070a;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        #pdfViewerContainer {
            width: 100%;
            height: 100%;
            overflow: auto;
            position: relative;
            display: flex;
            justify-content: center;
            background: #05070a;
            scroll-behavior: smooth;
        }

        #pdfViewer {
            position: relative;
            transform-origin: top center;
            transition: transform 0.1s ease-out;
        }

        .pdf-page-container {
            margin: 20px 0;
            box-shadow: 0 0 50px rgba(0,0,0,0.8);
            position: relative;
            background: white;
        }

        canvas {
            display: block;
            max-width: 100%;
        }

        .textLayer {
            position: absolute;
            left: 0;
            top: 0;
            right: 0;
            bottom: 0;
            overflow: hidden;
            opacity: 1; /* Keep visible for Ctrl+F */
            line-height: 1.0;
            pointer-events: none; /* Let clicks pass through to canvas if needed, but spans will have pointer-events: auto */
        }

        .textLayer > span {
            color: transparent;
            position: absolute;
            white-space: pre;
            cursor: text;
            transform-origin: 0% 0%;
            pointer-events: auto;
        }

        ::selection {
            background: rgba(88, 166, 255, 0.3);
        }

        .viewer-tip {
            position: absolute;
            bottom: 1rem;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.65rem;
            color: var(--text-dim);
            border: 1px solid var(--border);
            z-index: 20;
            pointer-events: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .viewer-tip b { color: var(--accent); }

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
        }
        '''

def get_viewer_html():
    """HTML for the integrated viewer modal"""
    return '''
        <!-- PDF.js library -->
        <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf_viewer.min.css">

        <div id="viewerModal" class="viewer-modal">
            <div class="viewer-header">
                <div class="viewer-title" id="viewerTitle">Chart Viewer</div>

                <div class="viewer-controls">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-right: 0.5rem;">
                        <span style="font-size: 0.6rem; color: var(--text-dim); font-weight: 600;">ZOOM</span>
                        <input type="range" id="zoomRange" class="zoom-slider" min="0.5" max="4" step="0.1" value="1.5">
                        <span id="zoomValue" style="font-size: 0.7rem; color: var(--accent); min-width: 30px;">1.5x</span>
                    </div>

                    <button class="control-btn" id="rotateBtn" title="Rotate Chart">
                        <span>🔄</span> ROTATE
                    </button>

                    <button class="control-btn" id="copyLinkBtn" title="Copy Link to this Chart">
                        <span>🔗</span> COPY LINK
                    </button>

                    <button class="control-btn" id="resetBtn" title="Reset View">
                        <span>🏠</span> RESET
                    </button>

                    <button class="control-btn" id="sidebarToggle" title="Toggle chart list">
                        <span>☰</span> CHARTS
                    </button>

                    <button class="control-btn" id="closeViewer" style="border-color: var(--warning); color: var(--warning);">
                        <span>✖</span> CLOSE
                    </button>                </div>
            </div>
            <div class="viewer-body">
                <div class="viewer-sidebar" id="viewerSidebar">
                    <div class="sidebar-header">
                        <span>ALL CHARTS</span>
                        <span id="sidebarCount" style="opacity: 0.5; font-size: 0.6rem;"></span>
                    </div>
                    <div class="sidebar-list" id="sidebarList"></div>
                </div>
                <div class="viewer-content" id="viewerContent">
                    <div id="viewerLoader" class="viewer-loader">
                        <div class="spinner"></div>
                        <div id="loaderStatus" style="font-size: 0.8rem; font-family: 'IBM Plex Mono', monospace;">INITIALIZING PDF ENGINE...</div>
                    </div>

                    <div id="pageNav" style="display:none; justify-content:center; align-items:center; gap:1rem; padding:0.5rem 1rem; border-bottom:1px solid var(--border); background:var(--surface);">
                        <button class="control-btn" id="prevPageBtn" style="padding:0.25rem 0.75rem;">&#9664; PREV</button>
                        <span id="pageIndicator" style="font-size:0.75rem; font-family:'IBM Plex Mono',monospace; color:var(--text-dim); min-width:100px; text-align:center;">PAGE 1 OF 2</span>
                        <button class="control-btn" id="nextPageBtn" style="padding:0.25rem 0.75rem;">NEXT &#9654;</button>
                    </div>

                    <div id="pdfViewerContainer">
                        <div id="pdfViewer"></div>
                    </div>

                    <div class="viewer-tip">
                        <span>💡 <b>Ctrl+F</b> to search. <b>Mouse Wheel</b> to zoom.</span>
                    </div>
                </div>
            </div>
        </div>
        '''

def get_viewer_js():
    """JS for the integrated viewer logic using PDF.js"""
    return '''
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

            let currentPdf = null;
            let currentRotation = 0;
            let currentZoom = 1.5;
            let visualScale = 1.0;
            let isOpeningFromHash = false;
            let originalPageTitle = document.title;
            let currentFileId = null;
            let currentFilePages = null;
            let currentFilePageIndex = 0;

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
                    item.textContent = file.name.replace(/\.[^.]+$/, '');
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

            async function openViewer(id, name, driveUrl, localUrl, skipHash = false, icao = null) {
                currentFileId = id;
                const fileObj = typeof files !== 'undefined' ? files.find(f => f.id === id) : null;
                currentFilePages = fileObj && fileObj.pages && fileObj.pages.length > 1 ? fileObj.pages : null;
                currentFilePageIndex = 0;
                if (currentFilePages) localUrl = currentFilePages[0].localUrl;
                const modal = document.getElementById('viewerModal');
                const title = document.getElementById('viewerTitle');
                const loader = document.getElementById('viewerLoader');
                const loaderStatus = document.getElementById('loaderStatus');
                const container = document.getElementById('pdfViewer');

                // Update page title
                const displayIcao = icao || (typeof airportCtx !== 'undefined' ? airportCtx.icao : null);
                if (displayIcao) {
                    document.title = `${displayIcao} - ${name}`;
                } else {
                    document.title = name;
                }

                // Update hash for deep linking - now much shorter!
                if (!skipHash) {
                    isOpeningFromHash = true;
                    window.location.hash = `view=${id}`;
                    setTimeout(() => isOpeningFromHash = false, 100);
                }

                // Reset state
                currentRotation = 0;
                currentZoom = 1.5;
                visualScale = 1.0;
                document.getElementById('zoomRange').value = 1.5;
                document.getElementById('zoomValue').textContent = '1.5x';
                title.textContent = name;
                container.innerHTML = '';
                container.style.transform = 'scale(1)';

                modal.style.display = 'flex';
                document.body.style.overflow = 'hidden';
                populateSidebar(id);
                applySidebarState();
                loader.style.display = 'flex';
                loaderStatus.textContent = 'LOADING LOCAL PDF...';

                try {
                    const loadingTask = pdfjsLib.getDocument(localUrl);
                    currentPdf = await loadingTask.promise;
                    loaderStatus.textContent = `INDEXING ${currentPdf.numPages} PAGE(S)...`;
                    await renderAllPages();
                    loader.style.display = 'none';
                    updatePageNav();
                } catch (err) {
                    console.error('PDF Error:', err);
                    // Local file unavailable — embed Drive preview iframe
                    const fileObj2 = typeof files !== 'undefined' ? files.find(f => f.id === id) : null;
                    const embedId = fileObj2 && fileObj2.driveId ? fileObj2.driveId : null;
                    if (embedId) {
                        loader.style.display = 'none';
                        container.innerHTML = `<iframe src="https://drive.google.com/file/d/${embedId}/preview" style="width:100%;height:80vh;border:none;" allow="autoplay"></iframe>`;
                    } else if (driveUrl && driveUrl !== '#') {
                        loaderStatus.textContent = 'OPENING IN DRIVE...';
                        setTimeout(() => { window.open(driveUrl, '_blank'); closeViewer(); }, 1000);
                    } else {
                        loaderStatus.textContent = 'PDF NOT AVAILABLE.';
                    }
                }
            }

            function updatePageNav() {
                const nav = document.getElementById('pageNav');
                if (!nav) return;
                if (currentFilePages && currentFilePages.length > 1) {
                    nav.style.display = 'flex';
                    document.getElementById('prevPageBtn').disabled = currentFilePageIndex === 0;
                    document.getElementById('nextPageBtn').disabled = currentFilePageIndex === currentFilePages.length - 1;
                    document.getElementById('pageIndicator').textContent =
                        `PAGE ${currentFilePageIndex + 1} OF ${currentFilePages.length}`;
                } else {
                    nav.style.display = 'none';
                }
            }

            async function goToFilePage(delta) {
                if (!currentFilePages) return;
                const newIndex = currentFilePageIndex + delta;
                if (newIndex < 0 || newIndex >= currentFilePages.length) return;
                currentFilePageIndex = newIndex;
                const page = currentFilePages[newIndex];
                const loader = document.getElementById('viewerLoader');
                const loaderStatus = document.getElementById('loaderStatus');
                loader.style.display = 'flex';
                loaderStatus.textContent = `LOADING PAGE ${newIndex + 1}...`;
                document.getElementById('pdfViewer').innerHTML = '';
                currentRotation = 0;
                const loadingTask = pdfjsLib.getDocument(page.localUrl);
                currentPdf = await loadingTask.promise;
                await renderAllPages();
                loader.style.display = 'none';
                updatePageNav();
            }

            async function checkHash() {
                const hash = window.location.hash;
                if (hash.startsWith('#view=') && !isOpeningFromHash) {
                    try {
                        const hashValue = hash.substring(6);
                        let found = null;
                        
                        // 1. Try to find in local 'files' array (for airport pages)
                        if (typeof files !== 'undefined') {
                            found = files.find(f => f.id === hashValue);
                        }
                        
                        // 2. Try to find in global 'searchIndex' (for home page)
                        if (!found && typeof searchIndex !== 'undefined') {
                            found = searchIndex.find(item => item.id === hashValue);
                        }
                        
                        if (found) {
                            await openViewer(found.id, found.name, found.driveUrl || '#', found.localUrl, true);
                        } else {
                            // 3. Fallback: Check if it's a legacy Base64 encoded JSON
                            try {
                                const chartData = JSON.parse(decodeURIComponent(atob(hashValue)));
                                if (chartData && chartData.localUrl) {
                                    await openViewer(chartData.id, chartData.name, chartData.driveUrl, chartData.localUrl, true);
                                }
                            } catch (e) {
                                // Not a legacy hash, just not found
                            }
                        }
                    } catch (e) {
                        console.error('Hash parse error:', e);
                    }
                } else if (!hash && document.getElementById('viewerModal').style.display === 'flex') {
                    closeViewer(true);
                }
            }

            window.addEventListener('hashchange', checkHash);
            window.addEventListener('DOMContentLoaded', () => setTimeout(checkHash, 500));

            async function renderAllPages() {
                const container = document.getElementById('pdfViewer');
                container.innerHTML = '';

                for (let i = 1; i <= currentPdf.numPages; i++) {
                    const pageContainer = document.createElement('div');
                    pageContainer.className = 'pdf-page-container';
                    pageContainer.id = `page-${i}`;
                    container.appendChild(pageContainer);
                    await renderPage(i, pageContainer);
                }
                applyVisualTransform();
            }

            async function renderPage(pageNum, container) {
                const page = await currentPdf.getPage(pageNum);
                const viewport = page.getViewport({ scale: currentZoom, rotation: currentRotation });

                container.style.width = `${viewport.width}px`;
                container.style.height = `${viewport.height}px`;

                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d');
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                container.appendChild(canvas);

                const textLayerDiv = document.createElement('div');
                textLayerDiv.className = 'textLayer';
                container.appendChild(textLayerDiv);

                // Render visual content
                await page.render({ canvasContext: context, viewport: viewport }).promise;

                // Render text content for Ctrl+F
                const textContent = await page.getTextContent();
                await pdfjsLib.renderTextLayer({
                    textContent: textContent,
                    container: textLayerDiv,
                    viewport: viewport,
                    textDivs: []
                }).promise;
            }

            function applyVisualTransform() {
                const container = document.getElementById('pdfViewer');
                container.style.transform = `scale(${visualScale})`;
            }

            function closeViewer(skipHash = false) {
                const modal = document.getElementById('viewerModal');
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
                currentPdf = null;
                
                // Restore original title
                document.title = originalPageTitle;

                if (!skipHash && window.location.hash.startsWith('#view=')) {
                    history.pushState("", document.title, window.location.pathname + window.location.search);
                }
            }

            async function updateZoomQuality() {
                await renderAllPages();
                visualScale = 1.0;
                applyVisualTransform();
            }

            document.getElementById('zoomRange').oninput = (e) => {
                const newZoom = parseFloat(e.target.value);
                visualScale = newZoom / currentZoom;
                applyVisualTransform();
                document.getElementById('zoomValue').textContent = `${newZoom.toFixed(1)}x`;
            };

            document.getElementById('zoomRange').onchange = async (e) => {
                currentZoom = parseFloat(e.target.value);
                await updateZoomQuality();
            };

            document.getElementById('rotateBtn').onclick = async () => {
                currentRotation = (currentRotation + 90) % 360;
                await renderAllPages();
            };

            document.getElementById('copyLinkBtn').onclick = () => {
                const url = window.location.href;
                navigator.clipboard.writeText(url).then(() => {
                    const btn = document.getElementById('copyLinkBtn');
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '<span>✅</span> COPIED!';
                    setTimeout(() => btn.innerHTML = originalText, 2000);
                });
            };

            document.getElementById('resetBtn').onclick = async () => {
                currentRotation = 0;
                currentZoom = 1.5;
                visualScale = 1.0;
                document.getElementById('zoomRange').value = 1.5;
                document.getElementById('zoomValue').textContent = '1.5x';
                await renderAllPages();
            };

            document.getElementById('closeViewer').onclick = closeViewer;

            document.getElementById('pdfViewerContainer').onwheel = (e) => {
                if (e.ctrlKey) {
                    e.preventDefault();
                    const delta = e.deltaY > 0 ? -0.1 : 0.1;
                    const newZoom = Math.min(Math.max(0.5, currentZoom * visualScale + delta), 4);

                    visualScale = newZoom / currentZoom;
                    applyVisualTransform();

                    document.getElementById('zoomRange').value = newZoom;
                    document.getElementById('zoomValue').textContent = `${newZoom.toFixed(1)}x`;

                    clearTimeout(window.zoomTimeout);
                    window.zoomTimeout = setTimeout(async () => {
                        currentZoom = newZoom;
                        await updateZoomQuality();
                    }, 500);
                }
            };

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') closeViewer();
            });

            document.getElementById('sidebarToggle').onclick = () => {
                sidebarOpen = !sidebarOpen;
                localStorage.setItem(SIDEBAR_KEY, sidebarOpen);
                applySidebarState();
            };

            document.getElementById('prevPageBtn').onclick = () => goToFilePage(-1);
            document.getElementById('nextPageBtn').onclick = () => goToFilePage(1);
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

        function clearAllPins() {
            savePins({airports: [], charts: []});
            if (typeof renderPins === 'function') renderPins();
            else if (typeof renderPinned === 'function') renderPinned();
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
            color: var(--text);
            margin-bottom: 0.25rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .airport-name {
            font-size: 0.9rem;
            margin-bottom: 0.75rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
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
        
        .file-item { display: flex; align-items: center; gap: 0.75rem; padding: 1rem 1.25rem; text-decoration: none; color: #ffffff; transition: all 0.15s; min-width: 0; }

        .file-item:last-child { border-bottom: none; }

        .file-item:hover {
            background: var(--surface-hover);
            padding-left: 1.5rem;
        }

        .file-icon { font-size: 1.2rem; flex-shrink: 0; }
        .file-name { flex: 1; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; color: #ffffff; }

        .file-type {
            font-size: 0.65rem;            color: var(--text-dim);
            background: var(--bg);
            padding: 0.3rem 0.6rem;
            border-radius: 3px;
            text-transform: uppercase;
            font-weight: 600;
            flex-shrink: 0;
        }
    '''


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  MULTI-PAGE ATC CHARTS DIRECTORY GENERATOR (INCREMENTAL)")
    print("="*70 + "\n")
    
    # Load state
    manifest = load_manifest()
    
    # Authenticate
    service = authenticate_drive()
    if not service:
        return
    
    # Scan Drive
    print(f"📂 Scanning folder: {CHARTS_FOLDER_ID}...\n")
    items = scan_folder_recursive(service, CHARTS_FOLDER_ID)
    
    file_count = sum(1 for item in items if item['mimeType'] != 'application/vnd.google-apps.folder')
    print(f"\n✅ Found {file_count} files on Drive\n")
    
    if file_count == 0:
        print("⚠️  No files found!")
        return
    
    # Organize & Download
    print("🔨 Organizing hierarchy and updating local files...\n")
    create_output_dir()
    hierarchy = organize_by_hierarchy(service, items, manifest)
    
    # Save manifest after downloads
    save_manifest(manifest)
    
    # Generate pages
    print("🎨 Generating pages...\n")
    
    # Index page
    regions = generate_index_page(hierarchy)
    
    # Region and airport pages
    for region_name, airports in hierarchy.items():
        region_slug = slugify(region_name)
        
        # Region page
        generate_region_page(region_name, region_slug, airports)
        
        # Airport pages
        for airport_code, files in airports.items():
            generate_airport_page(region_name, region_slug, airport_code, files, manifest)
    
    # Final save for airport hashes
    save_manifest(manifest)

    print("\n" + "="*70)
    print("  🎉 SUCCESS!")
    print("="*70)
    print(f"\n📁 Site updated in: {OUTPUT_DIR}/")
    print(f"📄 Open: {OUTPUT_DIR}/index.html")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        sys.exit(1)
