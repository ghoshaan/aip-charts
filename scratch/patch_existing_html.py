import os
import re

# Directory to scan (docs folder in project workspace)
WORKSPACE_DIR = r"C:\Users\ghosh\Desktop\Github Charts Directory"
DOCS_DIR = os.path.join(WORKSPACE_DIR, "docs")

# Define the new HTML and JS snippets we want to insert (as raw strings to prevent syntax warnings)
NEW_ROTATE_AND_REFRESH_HTML = r"""                    <button class="control-btn" id="rotateBtn" title="Rotate Chart">
                        <span>↻</span> ROTATE
                    </button>

                    <button class="control-btn" id="refreshBtn" title="Force Refresh/Bypass Cache">
                        <span>🔄</span> REFRESH
                    </button>"""

OLD_ROTATE_HTML = r"""                    <button class="control-btn" id="rotateBtn" title="Rotate Chart">
                        <span>🔄</span> ROTATE
                    </button>"""

NEW_JS_TEMPLATE = r"""const APPS_SCRIPT_URL = "__APPS_SCRIPT_URL__";
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

            // IndexedDB Cache utility for charts
            const DB_NAME = 'atc_charts_cache';
            const DB_VERSION = 1;
            const STORE_NAME = 'charts';

            function openCacheDB() {
                return new Promise((resolve, reject) => {
                    const request = indexedDB.open(DB_NAME, DB_VERSION);
                    request.onupgradeneeded = (e) => {
                        const db = e.target.result;
                        if (!db.objectStoreNames.contains(STORE_NAME)) {
                            db.createObjectStore(STORE_NAME);
                        }
                    };
                    request.onsuccess = (e) => resolve(e.target.result);
                    request.onerror = (e) => reject(e.target.error);
                });
            }

            async function getCachedChart(id) {
                try {
                    const db = await openCacheDB();
                    return new Promise((resolve, reject) => {
                        const tx = db.transaction(STORE_NAME, 'readonly');
                        const store = tx.objectStore(STORE_NAME);
                        const request = store.get(id);
                        request.onsuccess = () => resolve(request.result);
                        request.onerror = () => reject(request.error);
                    });
                } catch (e) {
                    console.error('IndexedDB get error:', e);
                    return null;
                }
            }

            async function setCachedChart(id, bytes) {
                try {
                    const db = await openCacheDB();
                    return new Promise((resolve, reject) => {
                        const tx = db.transaction(STORE_NAME, 'readwrite');
                        const store = tx.objectStore(STORE_NAME);
                        const request = store.put(bytes, id);
                        request.onsuccess = () => resolve();
                        request.onerror = () => reject(request.error);
                    });
                } catch (e) {
                    console.error('IndexedDB put error:', e);
                }
            }

            async function getPdfData(id, driveId, localUrl, loaderStatus) {
                const cacheKey = driveId || localUrl || id;
                try {
                    const cachedData = await getCachedChart(cacheKey);
                    if (cachedData) {
                        loaderStatus.textContent = 'LOADING FROM CACHE...';
                        return { data: cachedData };
                    }
                } catch (e) {
                    console.warn('Cache read error:', e);
                }

                let pdfData;
                if (localUrl && localUrl !== '#' && !localUrl.endsWith('#')) {
                    loaderStatus.textContent = 'FETCHING LOCAL PDF...';
                    try {
                        const response = await fetch(localUrl);
                        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
                        const arrayBuffer = await response.arrayBuffer();
                        pdfData = new Uint8Array(arrayBuffer);
                        try {
                            await setCachedChart(cacheKey, pdfData);
                        } catch (e) {
                            console.warn('Cache write error:', e);
                        }
                        return { data: pdfData };
                    } catch (err) {
                        console.warn('Local fetch failed, loading via URL:', err);
                        return localUrl;
                    }
                } else {
                    if (!driveId) {
                        throw new Error("No URL or Drive ID available.");
                    }
                    loaderStatus.textContent = 'FETCHING PDF FROM DRIVE...';
                    pdfData = await fetchPdfFromProxy(driveId);
                    try {
                        await setCachedChart(cacheKey, pdfData);
                    } catch (e) {
                        console.warn('Cache write error:', e);
                    }
                    return { data: pdfData };
                }
            }

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

            async function fetchPdfFromProxy(driveId) {
                if (!APPS_SCRIPT_URL) {
                    throw new Error("Apps Script URL is not configured.");
                }
                const response = await fetch(`${APPS_SCRIPT_URL}?id=${driveId}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const json = await response.json();
                if (json.error) {
                    throw new Error(json.error);
                }
                if (!json.data) {
                    throw new Error("No data returned from proxy.");
                }
                const binaryString = atob(json.data);
                const len = binaryString.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {
                    bytes[i] = binaryString.charCodeAt(i);
                }
                return bytes;
            }

            async function openViewer(id, name, driveUrl, localUrl, skipHash = false, icao = null) {
                currentFileId = id;
                let fileObj = null;
                if (typeof files !== 'undefined') {
                    fileObj = files.find(f => f.id === id);
                } else if (typeof searchIndex !== 'undefined') {
                    fileObj = searchIndex.find(f => f.id === id);
                }
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

                // Update hash for deep linking
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

                try {
                    const embedId = fileObj && fileObj.driveId ? fileObj.driveId : null;
                    const loadResult = await getPdfData(id, embedId, localUrl, loaderStatus);
                    
                    loaderStatus.textContent = 'LOADING PDF...';
                    let loadingTask;
                    if (typeof loadResult === 'string') {
                        loadingTask = pdfjsLib.getDocument(loadResult);
                    } else {
                        loadingTask = pdfjsLib.getDocument({ data: loadResult.data });
                    }
                    
                    currentPdf = await loadingTask.promise;
                    loaderStatus.textContent = `INDEXING ${currentPdf.numPages} PAGE(S)...`;
                    await renderAllPages();
                    loader.style.display = 'none';
                    updatePageNav();
                } catch (err) {
                    console.error('PDF Error:', err);
                    loaderStatus.textContent = 'ERROR LOADING PDF. OPENING IN DRIVE...';
                    const embedId = fileObj && fileObj.driveId ? fileObj.driveId : null;
                    if (driveUrl && driveUrl !== '#') {
                        setTimeout(() => { window.open(driveUrl, '_blank'); closeViewer(); }, 1500);
                    } else if (embedId) {
                        setTimeout(() => { window.open(`https://drive.google.com/file/d/${embedId}/view`, '_blank'); closeViewer(); }, 1500);
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
                
                try {
                    const cacheKey = page.driveId || page.localUrl || `${currentFileId}_page_${newIndex}`;
                    const loadResult = await getPdfData(cacheKey, page.driveId, page.localUrl, loaderStatus);
                    
                    let loadingTask;
                    if (typeof loadResult === 'string') {
                        loadingTask = pdfjsLib.getDocument(loadResult);
                    } else {
                        loadingTask = pdfjsLib.getDocument({ data: loadResult.data });
                    }
                    currentPdf = await loadingTask.promise;
                    await renderAllPages();
                    loader.style.display = 'none';
                    updatePageNav();
                } catch (err) {
                    console.error('Error loading page:', err);
                    loaderStatus.textContent = 'ERROR LOADING PAGE.';
                }
            }

            async function checkHash() {
                const hash = window.location.hash;
                if (hash.startsWith('#view=') && !isOpeningFromHash) {
                    try {
                        const hashValue = hash.substring(6);
                        let found = null;
                        
                        if (typeof files !== 'undefined') {
                            found = files.find(f => f.id === hashValue);
                        }
                        
                        if (!found && typeof searchIndex !== 'undefined') {
                            found = searchIndex.find(item => item.id === hashValue);
                        }
                        
                        if (found) {
                            await openViewer(found.id, found.name, found.driveUrl || '#', found.localUrl, true);
                        } else {
                            try {
                                const chartData = JSON.parse(decodeURIComponent(atob(hashValue)));
                                if (chartData && chartData.localUrl) {
                                    await openViewer(chartData.id, chartData.name, chartData.driveUrl, chartData.localUrl, true);
                                }
                            } catch(e) {}
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

                // Render text layer
                try {
                    const textContent = await page.getTextContent();
                    pdfjsLib.renderTextLayer({
                        textContent: textContent,
                        container: textLayerDiv,
                        viewport: viewport,
                        textDivs: []
                    });
                } catch (textErr) {
                    console.error('Text layer render error:', textErr);
                }
            }

            function applyVisualTransform() {
                const container = document.getElementById('pdfViewer');
                container.style.transform = `scale(${visualScale})`;
                container.style.transformOrigin = 'top center';
            }

            async function updateZoomQuality() {
                const container = document.getElementById('pdfViewer');
                const scrollPos = document.getElementById('pdfViewerContainer').scrollTop;
                
                // Re-render all pages at new high-quality zoom
                for (let i = 1; i <= currentPdf.numPages; i++) {
                    const pageContainer = document.getElementById(`page-${i}`);
                    if (pageContainer) {
                        pageContainer.innerHTML = '';
                        await renderPage(i, pageContainer);
                    }
                }
                
                visualScale = 1.0;
                applyVisualTransform();
                document.getElementById('pdfViewerContainer').scrollTop = scrollPos;
            }

            function closeViewer(skipHash = false) {
                const modal = document.getElementById('viewerModal');
                modal.style.display = 'none';
                document.body.style.overflow = '';
                document.title = originalPageTitle;
                
                if (currentPdf) {
                    currentPdf.destroy();
                    currentPdf = null;
                }
                document.getElementById('pdfViewer').innerHTML = '';
                currentFileId = null;

                if (!skipHash) {
                    isOpeningFromHash = true;
                    window.location.hash = '';
                    setTimeout(() => isOpeningFromHash = false, 100);
                }
            }

            document.getElementById('closeViewer').onclick = () => closeViewer();
            
            document.getElementById('zoomRange').oninput = (e) => {
                const targetZoom = parseFloat(e.target.value);
                const delta = targetZoom - (currentZoom * visualScale);
                adjustZoom(delta);
            };

            function adjustZoom(delta) {
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

            document.getElementById('pdfViewerContainer').onwheel = (e) => {
                if (e.ctrlKey) {
                    e.preventDefault();
                    const delta = e.deltaY > 0 ? -0.1 : 0.1;
                    adjustZoom(delta);
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

            document.getElementById('rotateBtn').onclick = async () => {
                currentRotation = (currentRotation + 90) % 360;
                await renderAllPages();
            };

            document.getElementById('refreshBtn').onclick = async () => {
                if (currentFileId) {
                    const loader = document.getElementById('viewerLoader');
                    const loaderStatus = document.getElementById('loaderStatus');
                    loader.style.display = 'flex';
                    loaderStatus.textContent = 'FORCE REFRESHING...';
                    document.getElementById('pdfViewer').innerHTML = '';
                    currentRotation = 0;
                    
                    try {
                        let fileObj = null;
                        if (typeof files !== 'undefined') {
                            fileObj = files.find(f => f.id === currentFileId);
                        } else if (typeof searchIndex !== 'undefined') {
                            fileObj = searchIndex.find(f => f.id === currentFileId);
                        }
                        
                        let localUrl = fileObj ? fileObj.localUrl : '#';
                        const driveId = fileObj ? fileObj.driveId : null;
                        
                        if (currentFilePages) {
                            localUrl = currentFilePages[currentFilePageIndex].localUrl;
                        }
                        
                        const cacheKey = (currentFilePages && currentFilePages[currentFilePageIndex].driveId) || 
                                         (currentFilePages && currentFilePages[currentFilePageIndex].localUrl) ||
                                         driveId || localUrl || currentFileId;
                        
                        let pdfData;
                        if (localUrl && localUrl !== '#' && !localUrl.endsWith('#')) {
                            loaderStatus.textContent = 'FETCHING FRESH LOCAL PDF...';
                            const response = await fetch(localUrl, { cache: 'reload' });
                            if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
                            const arrayBuffer = await response.arrayBuffer();
                            pdfData = new Uint8Array(arrayBuffer);
                        } else {
                            if (!driveId) throw new Error("No Drive ID available.");
                            loaderStatus.textContent = 'FETCHING FRESH PDF FROM DRIVE...';
                            pdfData = await fetchPdfFromProxy(driveId);
                        }
                        
                        try {
                            await setCachedChart(cacheKey, pdfData);
                        } catch (e) {
                            console.warn('Cache write error:', e);
                        }
                        
                        const loadingTask = pdfjsLib.getDocument({ data: pdfData });
                        currentPdf = await loadingTask.promise;
                        await renderAllPages();
                        loader.style.display = 'none';
                        updatePageNav();
                    } catch (err) {
                        console.error('Refresh error:', err);
                        loaderStatus.textContent = 'REFRESH ERROR.';
                        setTimeout(() => loader.style.display = 'none', 1500);
                    }
                }
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

            document.getElementById('viewerModal').onclick = (e) => {
                if (e.target === document.getElementById('viewerModal')) closeViewer();
            };"""

# Regex to find the whole old JS block in generated HTML files
JS_PATTERN = re.compile(
    r'const APPS_SCRIPT_URL = "([^"]*)";\s*pdfjsLib\.GlobalWorkerOptions\.workerSrc = .*?document\.getElementById\(\'viewerModal\'\)\.onclick = \(e\) => \{\s*if \(e\.target === document\.getElementById\(\'viewerModal\'\)\) closeViewer\(\);\s*\};',
    re.DOTALL
)

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Patch HTML Rotate/Refresh button
    patched_html = False
    if OLD_ROTATE_HTML in content:
        content = content.replace(OLD_ROTATE_HTML, NEW_ROTATE_AND_REFRESH_HTML)
        patched_html = True

    # 2. Patch Javascript block
    match = JS_PATTERN.search(content)
    patched_js = False
    if match:
        apps_script_url = match.group(1)
        # Replace placeholders using string replace (avoiding format string template issues with JS {})
        new_js = NEW_JS_TEMPLATE.replace('__APPS_SCRIPT_URL__', apps_script_url)
        content = content[:match.start()] + new_js + content[match.end():]
        patched_js = True

    if patched_html or patched_js:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, patched_html, patched_js
    return False, False, False

def main():
    print(f"Scanning directory: {DOCS_DIR}")
    html_files = []
    for root, dirs, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))

    total = len(html_files)
    print(f"Found {total} HTML files to patch.")
    
    patched_count = 0
    for idx, filepath in enumerate(html_files):
        rel_path = os.path.relpath(filepath, DOCS_DIR)
        success, html_p, js_p = patch_file(filepath)
        if success:
            patched_count += 1
            print(f"Patched {rel_path} (HTML: {html_p}, JS: {js_p})")

    print(f"\nDone! Patched {patched_count} / {total} HTML files.")

if __name__ == "__main__":
    main()
