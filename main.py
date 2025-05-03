from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
import yt_dlp
import os
from datetime import datetime
import threading
import queue
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# CORS (gerekirse frontend ayrı sunucuda çalışacaksa)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Statik dosyaları sun (templates klasörünü kök olarak ayarla)
app.mount("/static", StaticFiles(directory="templates", html=True), name="static")

templates = Jinja2Templates(directory="templates")

# İndirme kuyruğu ve durum takibi
download_queue = queue.Queue()
download_status = {}
download_history = []
default_download_path = os.path.expanduser("~/Downloads")  # Varsayılan indirme konumu

def download_progress_hook(d):
    if d['status'] == 'downloading':
        if 'downloaded_bytes' in d and 'total_bytes' in d:
            progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
            download_status['progress'] = f"İndiriliyor... %{progress:.1f}"
    elif d['status'] == 'finished':
        download_status['progress'] = "İndirme tamamlandı, MP3'e dönüştürülüyor..."

def process_queue():
    while not download_queue.empty():
        url, download_path = download_queue.get()
        download_status['current_url'] = url
        download_status['status'] = 'downloading'
        
        # yt-dlp ayarları
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(download_path or default_download_path, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_audio': True,
            'audio_format': 'mp3',
            'audio_quality': '192K',
            'progress_hooks': [download_progress_hook],
            'concurrent_fragment_downloads': 3,  # Paralel indirme için
            'throttledratelimit': 100000,  # İndirme hızını artırmak için
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'},
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Önce video bilgilerini al
                info = ydl.extract_info(url, download=False)
                video_title = info.get('title', 'Unknown Title')
                download_status['current_title'] = video_title
                
                # İndirme işlemini başlat
                ydl.download([url])
                
                # Geçmişe ekle
                download_history.append({
                    'title': video_title,
                    'url': url,
                    'path': download_path or default_download_path,
                    'date': datetime.now().isoformat()
                })
                
                download_status['status'] = 'completed'
                download_status['message'] = f"Başarıyla indirildi: {video_title}"
                
        except Exception as e:
            download_status['status'] = 'error'
            download_status['message'] = f"Hata oluştu: {str(e)}"

@app.post("/download")
async def download(urls: str = Form(...), path: str = Form("")):
    url_list = [url.strip() for url in urls.strip().split('\n') if url.strip()]
    # URL doğrulama kontrolü
    valid_urls = []
    for url in url_list:
        if url.startswith(('http://', 'https://')) and 'youtube.com' in url:
            valid_urls.append(url)
    if not valid_urls:
        return JSONResponse(status_code=400, content={"error": "Lütfen geçerli YouTube URL'leri girin!"})
    # Kuyruğa ekle
    for url in valid_urls:
        download_queue.put((url, path))
    # Thread başlat
    download_thread = threading.Thread(target=process_queue)
    download_thread.daemon = True
    download_thread.start()
    return {"message": "İndirme başlatıldı"}

@app.get("/status")
async def status():
    return download_status

@app.get("/history")
async def history():
    return download_history[-10:]

@app.post("/clear-history")
async def clear_history():
    try:
        global download_history
        download_history = []
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})