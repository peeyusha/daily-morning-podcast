import os
import re
import time
import datetime
import asyncio
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import formatdate
import edge_tts
import requests

PODCAST_TITLE = "My Daily Executive Briefing"
PODCAST_DESCRIPTION = "Daily audio news on Global Macro, Singapore, India, and AI/Agentic Commerce."
PODCAST_AUTHOR = "Executive AI"
BASE_URL = os.environ.get("BASE_URL", "https://peeyusha.github.io/daily-morning-podcast")
VOICE = "en-US-AndrewNeural"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def fetch_live_news():
    """Fetches breaking news headlines across the 4 core pillars from live RSS feeds."""
    topics = {
        "Global Macro & Geopolitics": "world news politics economy",
        "Singapore & Regional Economy": "Singapore business economy AI",
        "India DPI & Fintech": "India UPI fintech ONDC economy",
        "AI & Agentic Commerce": "agentic commerce AI payments autonomous checkout"
    }
    
    gathered_news = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    for category, query in topics.items():
        encoded = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        try:
            resp = requests.get(rss_url, headers=headers, timeout=15)
            root = ET.fromstring(resp.content)
            headlines = []
            for item in root.findall(".//item")[:4]:
                title = item.find("title").text if item.find("title") is not None else ""
                if title:
                    clean_title = title.rsplit(" - ", 1)[0]
                    headlines.append(f"  • {clean_title}")
            
            if headlines:
                gathered_news.append(f"### {category}:\n" + "\n".join(headlines))
        except Exception as e:
            print(f"Notice: Could not fetch RSS for {category}: {e}")
            
    return "\n\n".join(gathered_news)

def clean_script_for_audio(raw_text: str) -> str:
    """Strips LLM planning scratchpads, target word counts, and markdown symbols."""
    # Find start of actual broadcast
    match = re.search(r'(Good (morning|afternoon|evening).*|\bHere is your executive.*)', raw_text, re.IGNORECASE | re.DOTALL)
    if match:
        text = match.group(0)
    else:
        text = raw_text

    # Strip markdown headers, bold/italic asterisks, bullets, planning tags
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\(Target:.*?\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(Word count:.*?\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?\]', '', text)
    
    # Normalize clean whitespace
    text = re.sub(r'\n{2,}', '\n\n', text).strip()
    return text

def get_today_script():
    now_str = datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")
    live_news_context = fetch_live_news()
    
    prompt = f"""
Write a complete, full-length 5-minute broadcast audio news script (around 700 words) for {now_str} based on these live breaking news developments:

{live_news_context}

Cover these 4 pillars in order:
1. Global Macro & Geopolitics
2. Singapore & Regional Economy
3. India Digital Public Infrastructure & Policy
4. AI, Agentic Commerce & Payments (US & APAC)

Strict Instructions:
- Begin immediately with: "Good morning. Here is your executive news briefing for {now_str}."
- Write the FULL comprehensive spoken script. Do NOT output an outline, planning strategy, target word counts, or bulleted notes.
- Write every number phonetically in spoken words (e.g. "twenty-four billion dollars", "U-P-I", "O-N-D-C", "M-A-S").
- No markdown formatting, asterisks, or headings. Output only the pure spoken words.
"""
    
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not found in environment.")
        return f"Good morning. Here is your executive news briefing for {now_str}."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "systemInstruction": {
            "parts": [{
                "text": "You are a senior radio broadcast news anchor. You output exclusively the complete, continuous spoken news script. You never write outlines, thinking scratchpads, meta-commentary, or markdown asterisks."
            }]
        },
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 3000
        }
    }
    
    for attempt in range(1, 3):
        try:
            print(f"Connecting to Gemini 3.6 Flash (Attempt {attempt}/2)...")
            response = requests.post(url, json=payload, timeout=180)
            data = response.json()
            
            if response.status_code == 200 and "candidates" in data:
                raw_script = data["candidates"][0]["content"]["parts"][0]["text"]
                cleaned_script = clean_script_for_audio(raw_script)
                word_count = len(cleaned_script.split())
                print(f"Successfully generated clean news script ({word_count} words).")
                return cleaned_script
            else:
                print(f"API returned status {response.status_code}: {data}")
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt} timed out. Retrying in 3 seconds...")
            time.sleep(3)
        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            time.sleep(3)

    print("Falling back to standard briefing.")
    return f"Good morning. Here is your executive news briefing for {now_str}."

async def generate_audio(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)
    print(f"Audio saved to: {output_path}")

def update_podcast_rss(audio_filename: str, episode_title: str, episode_summary: str):
    rss_path = "rss.xml"
    pub_date = formatdate(timeval=None, localtime=False, usegmt=True)
    audio_url = f"{BASE_URL}/episodes/{audio_filename}"
    audio_size = os.path.getsize(f"episodes/{audio_filename}")
    
    item_xml = f"""    <item>
      <title>{episode_title}</title>
      <description><![CDATA[{episode_summary}]]></description>
      <pubDate>{pub_date}</pubDate>
      <enclosure url="{audio_url}" length="{audio_size}" type="audio/mpeg" />
      <guid isPermaLink="true">{audio_url}</guid>
      <itunes:author>{PODCAST_AUTHOR}</itunes:author>
      <itunes:summary>{episode_summary}</itunes:summary>
      <itunes:explicit>no</itunes:explicit>
    </item>"""
    
    if not os.path.exists(rss_path):
        full_rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{PODCAST_TITLE}</title>
    <link>{BASE_URL}</link>
    <language>en-us</language>
    <description>{PODCAST_DESCRIPTION}</description>
    <itunes:author>{PODCAST_AUTHOR}</itunes:author>
    <itunes:summary>{PODCAST_DESCRIPTION}</itunes:summary>
    <itunes:explicit>no</itunes:explicit>
    <itunes:category text="News" />
{item_xml}
  </channel>
</rss>"""
        with open(rss_path, "w", encoding="utf-8") as f:
            f.write(full_rss)
    else:
        with open(rss_path, "r", encoding="utf-8") as f:
            content = f.read()
        pos = content.find("<channel>")
        if pos != -1:
            end_tag = content.find(">", pos) + 1
            new_content = content[:end_tag] + "\n" + item_xml + content[end_tag:]
            with open(rss_path, "w", encoding="utf-8") as f:
                f.write(new_content)

def main():
    os.makedirs("episodes", exist_ok=True)
    now = datetime.datetime.now()
    timestamp_slug = now.strftime("%Y_%m_%d_%H%M")
    episode_title = f"Daily Executive Briefing — {now.strftime('%B %d, %Y (%I:%M %p)')}"
    audio_file = f"daily_briefing_{timestamp_slug}.mp3"
    audio_path = os.path.join("episodes", audio_file)
    
    script_text = get_today_script()
    asyncio.run(generate_audio(script_text, audio_path))
    update_podcast_rss(audio_file, episode_title, script_text)

if __name__ == "__main__":
    main()
