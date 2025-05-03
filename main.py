from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import json
from datetime import datetime
import threading
import queue
import tempfile
import tkinter as tk
from tkinter import filedialog
import concurrent.futures

app = Flask(__name__)

# İndirme kuyruğu ve durum takibi
download_queue = queue.Queue()
download_status = {}
download_history = []
default_download_path = os.path.expanduser("~/Downloads")  # Varsayılan indirme konumu
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)  # Eşzamanlı indirme için thread havuzu

def load_history():
    try:
        if os.path.exists('download_history.json'):
            with open('download_history.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Geçmiş yüklenirken hata: {str(e)}")
    return []

def save_history():
    try:
        with open('download_history.json', 'w', encoding='utf-8') as f:
            json.dump(download_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Geçmiş kaydedilirken hata: {str(e)}")

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
                save_history()
                
                download_status['status'] = 'completed'
                download_status['message'] = f"Başarıyla indirildi: {video_title}"
                
        except Exception as e:
            download_status['status'] = 'error'
            download_status['message'] = f"Hata oluştu: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html', history=download_history[-10:])

@app.route('/select-folder', methods=['POST'])
def select_folder():
    root = tk.Tk()
    root.attributes('-topmost', True)  # Pencereyi en üstte göster
    root.lift()  # Pencereyi öne getir
    root.focus_force()  # Pencereye odaklan
    folder_path = filedialog.askdirectory(parent=root)
    root.destroy()  # Pencereyi kapat
    if folder_path:
        return jsonify({'path': folder_path})
    return jsonify({'path': default_download_path})

@app.route('/download', methods=['POST'])
def download():
    urls = request.form.get('urls', '').strip().split('\n')
    urls = [url.strip() for url in urls if url.strip()]
    download_path = request.form.get('path', '').strip()
    
    # URL doğrulama kontrolü
    valid_urls = []
    for url in urls:
        if url.startswith(('http://', 'https://')) and 'youtube.com' in url:
            valid_urls.append(url)
    
    if not valid_urls:
        return jsonify({'error': 'Lütfen geçerli YouTube URL\'leri girin!'})
    
    # URL'leri ve indirme konumunu kuyruğa ekle
    for url in valid_urls:
        download_queue.put((url, download_path))
    
    # İndirme işlemini başlat
    download_thread = threading.Thread(target=process_queue)
    download_thread.daemon = True
    download_thread.start()
    
    return jsonify({'message': 'İndirme başlatıldı'})

@app.route('/status')
def status():
    return jsonify(download_status)

@app.route('/history')
def history():
    return jsonify(download_history[-10:])

@app.route('/clear-history', methods=['POST'])
def clear_history():
    try:
        global download_history
        download_history = []
        save_history()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    download_history = load_history()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)