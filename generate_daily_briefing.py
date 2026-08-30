import os
import datetime
import asyncio
from email.utils import formatdate
import edge_tts
import requests

PODCAST_TITLE = "My Daily Executive Briefing"
PODCAST_DESCRIPTION = "Daily audio news on Global Macro, Singapore, India, and AI/Agentic Commerce."
PODCAST_AUTHOR = "Executive AI"
BASE_URL = os.environ.get("BASE_URL", "https://peeyusha.github.io/daily-morning-podcast")
VOICE = "en-US-AndrewNeural"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def get_today_script():
    now_str = datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    prompt = f"""
    You are an executive broadcast news writer and audio producer.
    Synthesize the latest live news for {now_str} across:
    1. Global Macro & Geopolitics (Overnight developments, major trade/policy shifts)
    2. Singapore & Regional Economy (Trade data, MAS policies, Asian market open, tech sector)
    3. India Digital Public Infrastructure & Policy (UPI, ONDC, RBI guidelines, fintech innovations)
    4. Deep Focus: AI, Agentic Commerce & Payments (US & APAC cross-border rails, machine-to-machine checkout, delegated credentials, multi-rail settlement)

    Strict Spoken Audio Rules:
    - TOTAL LENGTH: Exactly 650 to 750 words (~5 minutes spoken time).
    - TONE: Professional, energetic, objective broadcast style.
    - Write numbers and figures in natural spoken English (e.g. "twenty-four billion dollars", "U-P-I", "O-N-D-C", "M-A-S").
    - Do NOT include markdown tables, bullet asterisks, or raw URLs. Return only the pure spoken script.
    """
    
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not found in environment.")
        return f"Good morning. Here is your executive news briefing for {now_str}."

    # Use production gemini-2.0-flash with search grounding
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        data = response.json()
        
        if response.status_code != 200:
            print(f"Gemini API returned error {response.status_code}: {data}")
            # Fallback to gemini-1.5-flash if needed
            fallback_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            response = requests.post(fallback_url, json=payload, timeout=60)
            data = response.json()

        script = data["candidates"][0]["content"]["parts"][0]["text"]
        print("Successfully generated live news script from Gemini.")
        return script.strip()
    except Exception as e:
        print(f"Error fetching from Gemini: {e}")
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
