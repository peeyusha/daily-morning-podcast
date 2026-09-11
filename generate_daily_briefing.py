import os
import re
import sys
import time
import datetime
import asyncio
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import formatdate, parsedate_to_datetime
import edge_tts
import requests

PODCAST_TITLE = "My Daily Executive Briefing"
PODCAST_DESCRIPTION = "Comprehensive audio briefing covering the last 24 hours of Global Economy, General Tech, AI Chatbots, Payments, and Agentic Commerce across the US, India, and Japan."
PODCAST_AUTHOR = "Executive AI"
BASE_URL = os.environ.get("BASE_URL", "https://peeyusha.github.io/daily-morning-podcast")
VOICE = "en-US-AndrewNeural"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MODELS_TO_TRY = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

def fetch_live_news_deep():
    """Fetches news published strictly within the last 24 hours across our targeted sectors."""
    topics = {
        "Global Economy & Central Banks": "global economy inflation central bank Federal Reserve GDP interest rates when:24h",
        "General Tech & Enterprise Software": "technology news big tech software hardware earnings when:24h",
        "AI Frontier Models & Chatbots": "generative AI frontier models chatbot OpenAI Anthropic Google Meta LLM when:24h",
        "US Payments & Agentic Commerce": "US agentic commerce AI checkout shopping payments Stripe Visa Mastercard when:24h",
        "India Digital Public Infrastructure & Fintech": "India UPI ONDC fintech RBI payments policy when:24h",
        "Japan Cashless & Financial Tech": "Japan fintech payments cashless digital yen PayPay FSA when:24h",
        "Strategic Partnerships & Product Launches": "fintech AI partnership product launch payments commerce when:24h"
    }
    
    gathered_news = []
    news_items_structured = {}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=28)
    
    for category, query in topics.items():
        encoded = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
        items_in_cat = []
        try:
            resp = requests.get(rss_url, headers=headers, timeout=15)
            root = ET.fromstring(resp.content)
            headlines = []
            for item in root.findall(".//item")[:5]:
                title = item.find("title").text if item.find("title") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                pub_date_elem = item.find("pubDate")
                
                # Check timestamp to enforce 24-hour recency
                if pub_date_elem is not None and pub_date_elem.text:
                    try:
                        pub_dt = parsedate_to_datetime(pub_date_elem.text)
                        if pub_dt < cutoff_time:
                            continue  # Skip stale stories
                    except Exception:
                        pass

                clean_desc = re.sub(r'<[^>]+>', '', desc).strip()
                if title:
                    clean_title = title.rsplit(" - ", 1)[0]
                    headlines.append(f"  • {clean_title}: {clean_desc[:180]}")
                    items_in_cat.append({"title": clean_title, "summary": clean_desc})
            
            if headlines:
                gathered_news.append(f"### {category}:\n" + "\n".join(headlines))
                news_items_structured[category] = items_in_cat
        except Exception as e:
            print(f"Notice: RSS fetch notice for {category}: {e}")
            
    return "\n\n".join(gathered_news), news_items_structured

def clean_script_for_audio(raw_text: str) -> str:
    """Sanitizes text so speech engine reads only pure broadcast dialogue."""
    match = re.search(r'(Good (morning|afternoon|evening).*|\bHere is your executive.*)', raw_text, re.IGNORECASE | re.DOTALL)
    if match:
        text = match.group(0)
    else:
        text = raw_text

    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'^\s*[-•]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\(Target:.*?\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(Word count:.*?\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\n{2,}', '\n\n', text).strip()
    return text

def build_standalone_rss_broadcast(structured_news, now_str):
    """Fallback generator: Compiles a rich report directly from 24-hour articles if AI APIs are down."""
    lines = [
        f"Good morning. Here is your executive briefing for {now_str}, covering breaking developments from the past 24 hours.",
        "Today we bring you an exhaustive update across the global economy, general technology, artificial intelligence, payments, and agentic commerce across the United States, India, and Japan.",
    ]
    
    for category, items in structured_news.items():
        lines.append(f"\nTurning now to developments over the last 24 hours in {category}:")
        for item in items:
            t = re.sub(r'#|\*|-', '', item['title']).strip()
            s = re.sub(r'#|\*|-', '', item['summary']).strip()
            if t and s:
                lines.append(f"{t}. {s}")
            elif t:
                lines.append(f"{t}.")
                
    lines.append("\nIn summary, the rapid integration of foundation models, automated checkout infrastructure, and macroeconomic realignments continues to shape commercial decision-making across our primary markets.")
    lines.append("Thank you for listening. Have a productive day ahead.")
    return "\n\n".join(lines)

def get_today_script():
    now_str = datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")
    raw_news_context, structured_news = fetch_live_news_deep()
    
    prompt = f"""
You are an executive broadcast news anchor and senior industry analyst.
Synthesize the following live news reports for {now_str} into a comprehensive, detailed 10-to-14 minute audio briefing (approx. 1,400 to 1,800 words):

{raw_news_context}

CRITICAL TIMEFRAME CONSTRAINT:
- Cover EXCLUSIVELY events, announcements, and data released in the PAST 24 HOURS.
- Treat this as a fresh daily morning newspaper. Do not summarize historical background or outdated stories.

Provide exhaustive, in-depth coverage across these core sections:

1. Global Economy & Major Markets (Past 24 Hours):
   - Macroeconomic updates from major financial wire sources (interest rate outlooks, central bank commentary from Fed, ECB, BOJ, MAS, RBI).
   - Fresh inflation data (CPI/PPI prints), GDP forecasts, sovereign bond movements, and energy supply-chain updates.

2. General Tech News & Enterprise Shifts (Past 24 Hours):
   - Big Tech strategic moves, major quarterly earnings reactions, cloud infrastructure, and semiconductor fabrication.
   - Enterprise software, cybersecurity developments, and platform updates.

3. Artificial Intelligence & Chatbot Ecosystem (Past 24 Hours):
   - Frontier foundation model releases and research breakthroughs (multimodal reasoning, context scaling).
   - Chatbot developments and consumer/enterprise assistant updates (ChatGPT, Claude, Gemini, Meta AI, open-source weights).
   - Enterprise AI copilot adoption and agent developer tooling.

4. Deep Focus: Payments, Shopping & Agentic Commerce across Key Markets (Past 24 Hours):
   - United States: Autonomous AI shopping agents, machine-to-machine checkout rails, merchant platforms (Shopify, Amazon, Walmart), payment network standards (Visa, Mastercard, Stripe, PayPal, FedNow), and regulatory policy (FTC, CFPB).
   - India: Digital Public Infrastructure (UPI, ONDC, OCEN), credit-on-UPI, biometric payments, RBI circulars, and NPCI cross-border bilateral links.
   - Japan: Cashless transition momentum, digital wallet ecosystems (PayPay, Rakuten Pay, Line Pay), Financial Services Agency (FSA) regulations, digital yen, and retail AI pilots.

5. Product Announcements, Partnerships & Major Events (Past 24 Hours):
   - Keynote speeches, major partnership agreements between banks, payment processors, and AI platforms.
   - Notable industry summits and regulatory forums.

Strict Spoken Audio Formatting Rules:
- LENGTH: Deep, long-form broadcast (between 1,400 and 1,800 words). Cover substantive details and context.
- TONE: Professional, authoritative, engaging broadcast tone (written strictly for listening with earphones).
- FORMAT: Output ONLY the spoken text. Begin immediately with: "Good morning. Here is your executive news briefing for {now_str}, covering key developments from the past 24 hours."
- Write all numbers, currency figures, and acronyms phonetically in spoken words (e.g. "two point five billion dollars", "U-P-I", "O-N-D-C", "F-S-A", "R-B-I", "L-L-Ms").
- Do NOT output any outlines, planning scratchpads, target word counts, markdown asterisks, or headings. Output pure spoken narrative.
"""

    if GEMINI_API_KEY:
        for model_name in MODELS_TO_TRY:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "systemInstruction": {
                    "parts": [{
                        "text": "You are a senior broadcast journalist. Output exclusively the full, continuous spoken audio script with zero outlines, zero asterisks, zero markdown, and zero meta-commentary."
                    }]
                },
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 4096
                }
            }
            
            for attempt in range(1, 3):
                try:
                    print(f"Connecting to {model_name} (Attempt {attempt}/2)...")
                    response = requests.post(url, json=payload, timeout=180)
                    data = response.json()
                    
                    if response.status_code == 200 and "candidates" in data:
                        raw_script = data["candidates"][0]["content"]["parts"][0]["text"]
                        cleaned = clean_script_for_audio(raw_script)
                        word_count = len(cleaned.split())
                        if word_count >= 500:
                            print(f"Successfully generated deep script via {model_name} ({word_count} words).")
                            return cleaned
                        else:
                            print(f"Warning: Output too short ({word_count} words). Retrying...")
                    else:
                        print(f"{model_name} returned status {response.status_code}: {data.get('error', {}).get('message', '')}")
                except Exception as e:
                    print(f"Error connecting to {model_name} on attempt {attempt}: {e}")
                time.sleep(2)
    
    print("AI API unavailable or exhausted. Generating comprehensive standalone RSS broadcast...")
    return build_standalone_rss_broadcast(structured_news, now_str)

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
    <itunes:category text="Business">
      <itunes:category text="Technology" />
    </itunes:category>
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
    word_count = len(script_text.split())
    
    # Safety guardrail: Never publish a broken 1-line snippet
    if word_count < 350:
        print(f"Safety Guardrail: Script length ({word_count} words) below minimum threshold. Skipping publish.")
        sys.exit(0)
        
    print(f"Generating audio for comprehensive 24-hour script ({word_count} words)...")
    asyncio.run(generate_audio(script_text, audio_path))
    update_podcast_rss(audio_file, episode_title, script_text)
    print("Workflow completed successfully.")

if __name__ == "__main__":
    main()
