import os
import datetime
import asyncio
from email.utils import formatdate
import edge_tts

PODCAST_TITLE = "My Daily Executive Briefing"
PODCAST_DESCRIPTION = "Daily audio news on Global Macro, Singapore, India, and AI/Agentic Commerce."
PODCAST_AUTHOR = "Executive AI"
BASE_URL = os.environ.get("BASE_URL", "https://YOUR_GITHUB_USERNAME.github.io/daily-morning-podcast")
VOICE = "en-US-AndrewNeural"  # Professional, natural neural broadcast voice

def get_today_script():
    today_str = datetime.date.today().strftime("%B %d, %Y")
    
    # This text can be customized or linked to your preferred RSS/API sources
    return f"""
    Good morning. Here is your executive news digest for {today_str}.
    
    In Global Macro and Geopolitics, markets continue to digest the latest central banking commentary from the Jackson Hole Economic Policy Symposium, emphasizing data dependency and structural inflation monitoring.
    
    In Singapore and Southeast Asian markets, full-year growth projections remain resilient, supported by strong non-oil domestic exports and enduring global demand for AI server hardware and semiconductor manufacturing.
    
    In India Digital Public Infrastructure, monthly transaction volumes on UPI have surpassed twenty-three billion transactions, while the National Payments Corporation of India expands bilateral cross-border linkage pilots with Japan, Malaysia, and ASEAN partners.
    
    In AI, Agentic Commerce, and Payments, industry intelligence projects the agentic commerce market to cross one point five trillion dollars globally by 2030. Financial institutions and card schemes across the US and Asia-Pacific are publishing formal rules of the road for machine-initiated checkout, focusing on tokenized credentials, delegated spending limits, and automated settlement switches.
    
    Have a productive day ahead.
    """.strip()

async def generate_audio(text: str, output_path: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_path)

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
    today_slug = datetime.date.today().strftime("%Y_%m_%d")
    today_title = f"Daily Executive Briefing — {datetime.date.today().strftime('%B %d, %Y')}"
    audio_file = f"daily_briefing_{today_slug}.mp3"
    audio_path = os.path.join("episodes", audio_file)
    
    script_text = get_today_script()
    asyncio.run(generate_audio(script_text, audio_path))
    update_podcast_rss(audio_file, today_title, script_text)

if __name__ == "__main__":
    main()
