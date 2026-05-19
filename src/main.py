import os
import sys
import json
import time
import requests
import feedparser
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# 強制 stdout 使用 UTF-8，避免 Windows 印出 Unicode 時崩潰
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"
HISTORY_FILE = os.path.join("data", "history.json")
FEEDS_FILE = os.path.join("config", "rss_feeds.json")
TEMP_AUDIO = "temp_audio.mp3"

def load_history():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                if not isinstance(history_data, list):
                    return []
                return history_data
        except Exception:
            return []
    return []

def save_history(history_data):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)

def download_audio(url: str, output_path: str) -> str:
    print(f"正在下載音訊: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print("下載完成！")
    return output_path

def generate_digest(audio_path: str) -> str:
    print("上傳音訊至 Gemini...")
    audio_file = genai.upload_file(path=audio_path)
    
    while audio_file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        audio_file = genai.get_file(audio_file.name)
        
    if audio_file.state.name == "FAILED":
        raise ValueError("Gemini 音訊處理失敗")
        
    print("\n音訊就緒，開始分析...")
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = "請聆聽這段音訊（主要為日文），提取核心觀點、市場洞察與關鍵時間點，並摘要為中文，特別留意新創術語（如 PMF, Series A）的精確度。"
    
    response = model.generate_content([prompt, audio_file])
    
    genai.delete_file(audio_file.name)
    print("雲端音訊檔已清除。")
    return response.text

def process_feeds():
    if not os.path.exists(FEEDS_FILE):
        print(f"找不到設定檔 {FEEDS_FILE}")
        return

    with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
        feeds = json.load(f)

    history_data = load_history()
    processed_ids = {item.get("id") for item in history_data}

    for feed_info in feeds:
        feed_url = feed_info.get("url")
        feed_name = feed_info.get("name")
        print(f"\n--- 開始解析 RSS: {feed_name} ---")
        
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            print("找不到任何單集。")
            continue
            
        # 取最新的一集
        latest_entry = feed.entries[0]
        entry_id = latest_entry.get("id", latest_entry.get("link"))
        title = latest_entry.get("title", "Unknown Title")
        link = latest_entry.get("link", feed_url)
        
        print(f"最新單集: {title}")
        
        if entry_id in processed_ids:
            print(f"此單集已經處理過，跳過。")
            continue
            
        # 尋找音訊檔案網址
        audio_url = None
        for enclosure in latest_entry.get("enclosures", []):
            if enclosure.get("type", "").startswith("audio/"):
                audio_url = enclosure.get("href")
                break
                
        if not audio_url:
            print("找不到音訊檔案連結。")
            continue
            
        try:
            download_audio(audio_url, TEMP_AUDIO)
            digest = generate_digest(TEMP_AUDIO)
            
            print("\n[AI 摘要結果]\n")
            print(digest)
            print("\n-----------------------------------\n")
            
            new_entry = {
                "id": entry_id,
                "url": link,
                "title": f"[{feed_name}] {title}",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "digest": digest
            }
            
            history_data.insert(0, new_entry)
            save_history(history_data)
            processed_ids.add(entry_id)
            print(f"資料已更新至 {HISTORY_FILE}")
            
        except Exception as e:
            print(f"處理單集時發生錯誤: {e}")
        finally:
            if os.path.exists(TEMP_AUDIO):
                os.remove(TEMP_AUDIO)

if __name__ == "__main__":
    process_feeds()
