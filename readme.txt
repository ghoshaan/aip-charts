ATC CHARTS DIRECTORY - PROJECT SUMMARY
========================================

WHAT YOU BUILT:
A multi-page searchable web directory for your Google Drive ATC charts.
- Hosted on GitHub Pages: https://ghoshaan.github.io/atc-charts/
- Three-level navigation: Region → Airport → Files
- Fuzzy search with Fuse.js (search "kenez" finds "KINES")
- Dark GitHub-style theme

FOLDER STRUCTURE IN GOOGLE DRIVE:
Charts/
  ├── Netherlands/
  │   ├── EHAM/
  │   │   └── chart_files.pdf
  │   └── EHRD/
  ├── Switzerland/
  │   └── LSGG/
  └── etc...

REQUIRED FILES IN YOUR ATC_Scanner FOLDER:
- generate_multipage_directory.py (main script)
- credentials.json (Google Drive API credentials)
- token.json (auto-generated, saves login)

GOOGLE DRIVE API SETUP (already done):
- Project: https://console.cloud.google.com/
- OAuth credentials downloaded as credentials.json
- You're added as test user
- Folder ID in script: 1DjkbZ9YMC5fS-zZvIpDiP9dCkUL120nK

FUTURE UPDATES WORKFLOW:
1. Add new charts to Google Drive (maintain Region/Airport/files structure)
2. Run: python generate_multipage_directory.py
   - Scans Drive, regenerates all HTML in atc_directory_site/
3. Copy files from atc_directory_site/ to your GitHub repo folder
4. Open GitHub Desktop:
   - Write commit message
   - Click "Commit to main"
   - Click "Push origin"
5. Site updates in 1-2 minutes

SEARCH FEATURES:
- Index: Browse regions only
- Region page: Search all airports in that region
- Airport page: Fuzzy search within that airport only
  Example: On LSGG page, search "star" or "kenez" to find specific procedures

TROUBLESHOOTING:
- If script fails: Check credentials.json is in same folder
- If no files found: Verify Drive folder structure matches Region/Airport/files
- If site doesn't update: Wait 2-5 minutes, check GitHub Actions tab

GITHUB REPO: https://github.com/ghoshaan/atc-charts