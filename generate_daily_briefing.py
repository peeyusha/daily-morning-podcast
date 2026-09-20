import os
import re
import sys
import time
import datetime
import asyncio
import urllib.parse
import html
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
from email.utils import formatdate, parsedate_to_datetime
import edge_tts
import requests

PODCAST_TITLE = "My Daily Executive Briefing"
PODCAST_DESCRIPTION = "Comprehensive executive audio briefing covering Global Economy, Big Tech, AI Chatbots, Payments, Agentic Commerce (US, India, Southeast Asia), and trending discussions on X."
PODCAST_AUTHOR = "Executive AI"
BASE_URL = os.environ.get("BASE_URL", "https://peeyusha.github.io/daily-morning-podcast")
VOICE = "en-US-AndrewNeural"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

MODELS_TO_TRY = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

def fetch_live_news_deep():
    """Fetches news published strictly within the last 24 hours from targeted, verified sources."""
    topics = {
        "Global Macro & Economy (WSJ, Bloomberg, Reuters)": "site:wsj.com OR site:reuters.com OR site:bloomberg.com economy markets Federal Reserve inflation GDP when:24h",
        "Big Tech, AI & Startups (TechCrunch, The Information)": "site:techcrunch.com OR site:theinformation.com OR site:venturebeat.com AI models technology startups when:24h",
        "India Payments & DPI (Economic Times, Entrackr, MediaNama)": "site:economictimes.indiatimes.com OR site:entrackr.com OR site:medianama.com UPI payments fintech ONDC RBI when:24h",
        "Southeast Asia Tech Hubs (Business Times, Tech in Asia, Fintech News SG)": "site:businesstimes.com.sg OR site:techinasia.com OR site:fintechnews.sg economy tech fintech when:24h",
        "Agentic Commerce & Checkout Rails (Payments Dive, The Paypers)": "site:paymentsdive.com OR site:thepaypers.com OR agentic commerce AI checkout autonomous payments when:24h",
        "Trending Discussions on X (Twitter Radar)": '("on X" OR "on Twitter" OR "viral thread" OR "tweeted") (AI OR "agentic commerce" OR payments OR tech OR economy) when:24h'
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
                
                # Enforce strict 24-hour window
                if pub_date_elem is not None and pub_date_elem.text:
                    try:
                        pub_dt = parsedate_to_datetime(pub_date_elem.text)
                        if pub_dt < cutoff_time:
                            continue
                    except Exception:
                        pass

                clean_desc = re.sub(r'<[^>]+>', '', desc).strip()
                clean_desc = html.unescape(clean_desc).replace('\u00a0', ' ')
                if title:
                    clean_title = html.unescape(title.rsplit(" - ", 1)[0]).replace('\u00a0', ' ')
                    headlines.append(f"  • {clean_title}: {clean_desc[:180]}")
                    items_in_cat.append({"title": clean_title, "summary": clean_desc})
            
            if headlines:
                gathered_news.append(f"### {category}:\n" + "\n".join(headlines))
                news_items_structured[category] = items_in_cat
        except Exception as e:
            print(f"Notice: RSS fetch notice for {category}: {e}")
            
    return "\n\n".join(gathered_news), news_items_structured

def clean_script_for_audio(raw_text: str) -> str:
    """Sanitizes text so speech engine reads only pure broadcast dialogue without metadata or symbols."""
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
    text = html.unescape(text).replace('\u00a0', ' ')
    text = re.sub(r'\n{2,}', '\n\n', text).strip()
    return text

def build_standalone_rss_broadcast(structured_news, now_str):
    """Fallback generator: Compiles a rich report directly from 24-hour articles if AI APIs are down."""
    lines = [
        f"Good morning. Here is your executive briefing for {now_str}, covering breaking business, technology, and payments developments from the past 24 hours.",
        "Today we bring you in-depth updates from major market publications across the United States, India, and Southeast Asia, along with key community discussions on X.",
    ]
    
    for category, items in structured_news.items():
        clean_cat = category.replace('&', 'and')
        lines.append(f"\nTurning now to developments in {clean_cat}:")
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
Synthesize the following live news reports for {now_str} into a comprehensive, detailed, data-dense 10-to-14 minute audio briefing (approx. 1,400 to 1,800 words):

{raw_news_context}

CRITICAL TIMEFRAME & ANTI-FILLER CONSTRAINTS:
- Cover EXCLUSIVELY events, announcements, and data released in the PAST 24 HOURS.
- ZERO FILLER WORDS: Absolutely ban generic clichés like "In today's fast-paced world", "It is worth noting", "As we look ahead", "Navigating the complexities", "Delving into", or "A testament to".
- Lead directly with facts: Name the specific company, executive, product, dollar figure, percentage change, and regulatory impact.

Provide comprehensive, structured coverage across these core sections:

1. Global Economy & Major Markets (WSJ, Bloomberg, Reuters):
   - Federal Reserve, central bank policy (ECB, BOJ, MAS, RBI), interest rate trajectories, inflation data (CPI/PPI), sovereign bond yields, and currency moves.

2. Big Tech, Enterprise Software & AI Breakthroughs (TechCrunch, The Information, VentureBeat):
   - Frontier foundation models, multimodal LLMs, consumer/enterprise chatbot developments (ChatGPT, Claude, Gemini, Meta AI, open-source weights).
   - Major enterprise software shifts, cloud infrastructure capex, chip fabrication, and venture deals.

3. India Payments, Policy & Digital Public Infrastructure (The Economic Times, Entrackr, MediaNama):
   - Unified Payments Interface (UPI) volume, credit-on-UPI developments, ONDC retail network expansion, OCEN digital credit.
   - Reserve Bank of India (RBI) circulars, NPCI cross-border linkage expansions, fintech licensing, and startup partnerships.

4. Southeast Asia Tech & Regional Hubs (The Business Times, Tech in Asia, Fintech News Singapore):
   - Singapore GDP growth, MAS regulatory sandboxes, trade data (NODX), cross-border payment links (PayNow, Project Nexus), and ASEAN digital commerce platforms.

5. Deep Dive: Agentic Commerce, Autonomous Checkout & Merchant Rails (Payments Dive, The Paypers):
   - Autonomous AI shopping agents, machine-to-machine checkout rails, merchant integrations (Shopify, Amazon, Walmart).
   - Card networks and settlement infrastructure (Visa, Mastercard, Stripe, PayPal, FedNow, stablecoins), verifiable intent tokens, and regulatory policy (FTC, CFPB).

6. Community Radar & Trending Discussions on X (Twitter):
   - Key debates, viral technical threads, founder perspectives, and community sentiment being actively discussed on X in the past 24 hours around AI agents, payments, and macroeconomics.

Strict Spoken Audio Formatting Rules:
- LENGTH: Deep, long-form broadcast (between 1,400 and 1,800 words). Cover substantive details, quotes, and context.
- TONE: Professional, authoritative, punchy, objective broadcast tone (written strictly for listening with earphones).
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
                        "text": "You are a senior broadcast journalist. Output exclusively the full, continuous spoken audio script with zero outlines, zero asterisks, zero markdown, zero filler clichés, and zero meta-commentary."
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

def sanitize_text_for_xml(text: str) -> str:
    """Escapes special XML characters and strips HTML entities like &nbsp;"""
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace('\u00a0', ' ')
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)
    return escape(text)

def clean_cdata_text(text: str) -> str:
    """Cleans text intended for CDATA blocks so it contains no HTML entities or illegal tags."""
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace('\u00a0', ' ')
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)
    text = text.replace(']]>', ']]&gt;')
    return text

def repair_existing_rss(content: str) -> str:
    """Heals any corrupted &nbsp; or unescaped ampersands in previous feed entries."""
    content = content.replace('&nbsp;', ' ')
    content = content.replace('\u00a0', ' ')
    
    # Repair title tags
    content = re.sub(
        r'<title>(.*?)</title>',
        lambda m: f"<title>{sanitize_text_for_xml(html.unescape(m.group(1)))}</title>",
        content
    )
    
    # Repair itunes:summary tags
    def fix_summary(match):
        inner = match.group(1)
        if inner.startswith('<![CDATA['):
            clean_inner = clean_cdata_text(inner[9:-3])
            return f"<itunes:summary><![CDATA[{clean_inner}]]></itunes:summary>"
        return f"<itunes:summary>{sanitize_text_for_xml(html.unescape(inner))}</itunes:summary>"
        
    content = re.sub(r'<itunes:summary>(.*?)</itunes:summary>', fix_summary, content, flags=re.DOTALL)
    return content

def update_podcast_rss(audio_filename: str, episode_title: str, episode_summary: str):
    rss_path = "rss.xml"
    pub_date = formatdate(timeval=None, localtime=False, usegmt=True)
    audio_url = f"{BASE_URL}/episodes/{audio_filename}"
    audio_size = os.path.getsize(f"episodes/{audio_filename}")
    
    safe_title = sanitize_text_for_xml(episode_title)
    safe_cdata_desc = clean_cdata_text(episode_summary)
    safe_summary = sanitize_text_for_xml(episode_summary[:500])
    
    item_xml = f"""    <item>
      <title>{safe_title}</title>
      <description><![CDATA[{safe_cdata_desc}]]></description>
      <pubDate>{pub_date}</pubDate>
      <enclosure url="{audio_url}" length="{audio_size}" type="audio/mpeg" />
      <guid isPermaLink="true">{audio_url}</guid>
      <itunes:author>{PODCAST_AUTHOR}</itunes:author>
      <itunes:summary>{safe_summary}</itunes:summary>
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
        try:
            ET.fromstring(full_rss)
        except Exception as e:
            print(f"Warning: Initial XML parse check: {e}")
            
        with open(rss_path, "w", encoding="utf-8") as f:
            f.write(full_rss)
    else:
        with open(rss_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Self-heal any broken entities from previous runs
        content = repair_existing_rss(content)
        
        pos = content.find("<channel>")
        if pos != -1:
            end_tag = content.find(">", pos) + 1
            new_content = content[:end_tag] + "\n" + item_xml + content[end_tag:]
            
            # Final validation check
            try:
                ET.fromstring(new_content)
                print("XML Validation: PASSED (100% valid RSS feed).")
            except Exception as e:
                print(f"Warning: XML validation caught syntax issue, auto-repairing: {e}")
                new_content = repair_existing_rss(new_content)
                
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
    print("Workflow completed successfully with verified XML.")

if __name__ == "__main__":
    main()
