import os
import sys
import time
import json
from datetime import datetime
from typing import Optional

# 強制 stdout 使用 UTF-8，避免 Windows cmd/powershell 印出 Unicode 時崩潰
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import yt_dlp

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.5-flash"

def extract_transcript(video_id: str) -> Optional[str]:
    """嘗試使用 youtube-transcript-api 獲取日文字幕"""
    try:
        print(f"嘗試抓取影片 {video_id} 的自動字幕...")
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ja', 'en'])
        # 將字幕片段組合成單一字串
        full_text = " ".join([t['text'] for t in transcript])
        print("成功獲取字幕文本！")
        return full_text
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        print(f"無法獲取字幕：{e}")
        return None
    except Exception as e:
        print(f"獲取字幕時發生未知錯誤：{e}")
        return None

def extract_audio(video_url: str, output_path: str = "./temp_audio.m4a") -> str:
    """使用 yt-dlp 抓取影片音訊"""
    print(f"開始觸發 Fallback 機制，下載影片音訊: {video_url}")
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    
    # 確保暫存檔案不存在
    if os.path.exists(output_path):
        os.remove(output_path)
        
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
        
    print(f"音訊下載完成，儲存於 {output_path}")
    return output_path

def generate_digest_from_text(text: str) -> str:
    """將文本送交 Gemini 處理"""
    print("使用 Gemini 處理純文本...")
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = "請幫我摘要以下日文影片內容，提取核心觀點、市場洞察與關鍵時間點，並翻譯為中文，特別留意新創術語的精確度：\n\n"
    response = model.generate_content(prompt + text[:50000]) # 避免超過 Token 限制，可依需求調整
    return response.text

def generate_digest_from_audio(audio_path: str) -> str:
    """上傳音訊至 Gemini 並生成摘要"""
    print("上傳音訊至 Gemini...")
    audio_file = genai.upload_file(path=audio_path)
    
    # Gemini 音訊處理需要一點時間，通常在上傳後可以直接使用，但穩妥起見可以檢查狀態
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
    
    # 清理雲端暫存檔
    genai.delete_file(audio_file.name)
    print("雲端音訊檔已清除。")
    
    return response.text

def process_video(video_id: str):
    """處理單一影片的主要邏輯"""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"\n--- 開始處理影片: {video_url} ---")
    
    # 策略 1: 抓取字幕
    transcript_text = extract_transcript(video_id)
    
    if transcript_text:
        # 成功抓取字幕，直接處理文本
        digest = generate_digest_from_text(transcript_text)
    else:
        # 策略 2: Fallback 抓取音訊
        audio_path = extract_audio(video_url)
        digest = generate_digest_from_audio(audio_path)
        
        # 清理本機暫存檔
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
    print("\n[AI 摘要結果]\n")
    print(digest)
    print("\n-----------------------------------\n")
    
    # 儲存到 history.json
    history_file = os.path.join("data", "history.json")
    os.makedirs("data", exist_ok=True)
    
    history_data = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                if not isinstance(history_data, list):
                    history_data = []
        except Exception:
            pass
            
    new_entry = {
        "id": video_id,
        "url": video_url,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "digest": digest
    }
    
    # 如果已存在相同影片的紀錄則更新，否則加在最前面
    existing_idx = next((i for i, item in enumerate(history_data) if item["id"] == video_id), None)
    if existing_idx is not None:
        history_data[existing_idx] = new_entry
    else:
        history_data.insert(0, new_entry)
        
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=4)
        
    print(f"資料已更新至 {history_file}")

if __name__ == "__main__":
    # 測試用 Video ID (請換成實際的新創 YouTube 影片 ID)
    # 如果這個影片有字幕，會直接抓字幕。若無，則會下載音訊處理。
    TEST_VIDEO_ID = "E_qyprnYGAE" # Rick Astley 作為測試 (英文/自動字幕)
    process_video(TEST_VIDEO_ID)
