import os
import sys

# --- PATH SETUP (The Fix) ---
# 1. Get the current folder
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Add 'src' to path so we can import 'scrapers'
sys.path.append(os.path.join(current_dir, 'src'))

# 3. Add 'src/engine' to path so director.py can find voiceover.py
sys.path.append(os.path.join(current_dir, 'src', 'engine'))
# -----------------------------

from scrapers.reddit_stealth import find_and_screenshot_post
from engine.director import render_video

# List of known Brawlers (You can add more)
KNOWN_BRAWLERS = ["Fang", "Edgar", "Spike", "Crow", "Mortis", "Dynamike"]

def identify_brawler(text):
    """Finds which brawler is mentioned in the script."""
    for brawler in KNOWN_BRAWLERS:
        if brawler.lower() in text.lower():
            return brawler
    return None

def run_pipeline(script_text):
    print("🚀 STARTING AUTOMATION PIPELINE")
    print(f"📜 Script: {script_text[:50]}...")

    # 1. IDENTIFY SUBJECT
    brawler = identify_brawler(script_text)
    if not brawler:
        print("❌ Error: Could not find a Brawler name in your script.")
        print(f"   Please mention one of: {KNOWN_BRAWLERS}")
        return

    print(f"   ✅ Identified Subject: {brawler}")

    # 2. GENERATE ASSETS (Scraping)
    print("   🔍 Looking for Reddit evidence...")
    # This calls your scraper to get "Fang_evidence.png"
    find_and_screenshot_post(brawler)

    # 3. GENERATE GRAPH (Visualizer)
    # We run this as a system command because Manim is complex
    print("   📊 Generating Graph...")
    os.system(f"manim -qh src/engine/visualizer.py BrawlerWinRateChart")

    # 4. ASSEMBLE VIDEO (Director)
    print("   🎬 Directing Final Video...")
    render_video(brawler, script_text)

if __name__ == "__main__":
    # --- PASTE YOUR SCRIPT HERE ---
    user_script = """
    Is Edgar completely broken right now? 
    He has a win rate of over 60 percent in Showdown and it is ruining the game. 
    Reddit users are sharing clips of him jumping on enemies with zero skill required.
    """
    
    run_pipeline(user_script)