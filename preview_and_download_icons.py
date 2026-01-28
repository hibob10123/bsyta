#!/usr/bin/env python3
"""
Icon Preview & Download Tool

This script analyzes your video script and downloads ALL icons WITHOUT generating video.
Perfect for reviewing icon quality and identifying which keywords need manual overrides.

Usage:
    python preview_and_download_icons.py

Features:
- Shows which keyword/phrase triggered each icon download
- Lists all downloaded icon paths
- Generates a report of bad/incorrect icons
- Helps you identify what to add to manual_icons/
"""

import os
import sys
import json
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from analysis.script_analyzer import ScriptAnalyzer
from scrapers.asset_gatherer import AssetGatherer

def main():
    print("=" * 70)
    print("  ICON PREVIEW & DOWNLOAD TOOL")
    print("=" * 70)
    print()
    
    # ============================================================
    # STEP 1: PASTE YOUR SCRIPT HERE
    # ============================================================
    
    # CONFIGURATION: Which part to analyze?
    # Options:
    #   None      = Analyze the ENTIRE script (all parts)
    #   "Part 1"  = Only analyze Part 1
    #   "Part 2"  = Only analyze Part 2
    #   "Part 3"  = Only analyze Part 3
    #   etc.
    PART_TO_ANALYZE = "Part 5"  # Change this to target specific parts
    
    script = """
Part 5: The Pattern
This isn't an accident. Supercell has a documented history of aggressive monetization that follows a predictable cycle. In 2021, Clash Royale introduced Level 14, which invalidated years of player progression overnight. The community revolted, but Supercell held firm. Then in 2022, they introduced Level 15 only one year after Level 14. Content creators like B-rad made videos titled "I Will Never Upgrade to Level 15," which hit massive view counts. The subreddit was on fire with threads calculating how the update devalued maxed accounts by 40 to 50 percent.
Brawl Stars avoided this for years by keeping progression relatively fair. But in 2024, they removed Masteries and replaced them with Records, a system that requires winning 300 games with a single Brawler for minimal rewards. Players were furious, but that was just the setup. Update 65 is the payoff. Buffies represent the most aggressive monetization shift in Brawl Stars history.
The update inflated the economy by approximately 50 percent by introducing a massive new resource sink. It segregated competitive gameplay into a Buffie Tier that free-to-play players cannot access. And it obfuscated the fixed cost of 37 dollars per Brawler behind complex gacha mechanics like the Claw Machine and Chaos Drops. Supercell didn't just raise prices. They fundamentally restructured the game to make free-to-play players second-class citizens.
And the worst part? They marketed it as "fun." As "collectibles." The Brawl Talk for Update 65 showed developers playing the Claw Machine and laughing as cute Buffies popped out. There was no mention of the 108,000 Power Point cost. No mention of the mechanical advantages locked behind the paywall. No mention that competitive Ranked would become unplayable without spending hundreds of dollars.
Supercell has proven over the years that they know exactly when to push monetization and exactly how far they can go before the community breaks. Update 65 is that breaking point for Brawl Stars. The game isn't dying because of bad updates or boring content. It's dying because Supercell chose profit over the players who built the game. And unless something changes, the only people left will be the whales who can afford the 475 dollar entry fee to competitive play.
The data doesn't lie. The interactions don't lie. Buffies are Power Level 12 hidden behind a slot machine. And Supercell is betting you won't do the math.

"""
    
    # ============================================================
    # STEP 2: SET YOUR CONTEXT (for icon search)
    # ============================================================
    search_context = "Clash Royale"  # What game/topic are icons for?
    
    # ============================================================
    # EXTRACT SPECIFIC PART (if specified)
    # ============================================================
    original_script = script
    if PART_TO_ANALYZE is not None:
        print(f"🎯 Extracting: {PART_TO_ANALYZE}")
        print()
        
        analyzer = ScriptAnalyzer()
        sections = analyzer.detect_sections(script)
        
        # Find the specified part
        target_section = None
        for section in sections:
            section_title = section.get('title', '').lower()
            target_lower = PART_TO_ANALYZE.lower()
            
            if target_lower in section_title or section_title.startswith(target_lower):
                target_section = section
                break
        
        if target_section:
            script = target_section['text']
            print(f"✓ Found: {target_section['title']}")
            print(f"✓ Section length: {target_section.get('word_count', len(script.split()))} words")
            print()
        else:
            print(f"⚠ WARNING: Could not find '{PART_TO_ANALYZE}' in script")
            print(f"Available sections: {[s.get('title') for s in sections]}")
            print(f"Analyzing entire script instead...")
            print()
    else:
        print(f"🎯 Analyzing: ENTIRE SCRIPT (all parts)")
        print()
    
    print(f"📝 Script length: {len(script.split())} words")
    print(f"🎮 Search context: {search_context}")
    print()
    
    # ============================================================
    # ANALYZE SCRIPT
    # ============================================================
    print("=" * 70)
    print("STEP 1: Analyzing script for keywords...")
    print("=" * 70)
    
    analyzer = ScriptAnalyzer()
    analysis = analyzer.analyze_script(script)
    
    keywords = analysis.get('keywords', [])
    print(f"✓ Found {len(keywords)} keywords to visualize")
    print()
    
    # Show keyword breakdown
    icon_keywords = [k for k in keywords if k.get('display_type') == 'icon']
    text_keywords = [k for k in keywords if k.get('display_type') == 'text']
    
    print(f"  - {len(icon_keywords)} will use ICONS (images)")
    print(f"  - {len(text_keywords)} will use TEXT (numbers/dates)")
    print()
    
    # ============================================================
    # DOWNLOAD ICONS
    # ============================================================
    print("=" * 70)
    print("STEP 2: Downloading icons...")
    print("=" * 70)
    print()
    
    gatherer = AssetGatherer()
    
    download_results = []
    manual_override_used = []
    web_downloaded = []
    already_cached = []
    
    for i, keyword_obj in enumerate(icon_keywords, 1):
        keyword = keyword_obj.get('word', '')
        display_type = keyword_obj.get('display_type', 'icon')
        sentence = keyword_obj.get('sentence', '')[:80] + "..."
        
        print(f"\n[{i}/{len(icon_keywords)}] Keyword: \"{keyword}\"")
        print(f"     Display: {display_type}")
        print(f"     Context: {sentence}")
        
        # Download icon
        icon_path = gatherer.find_icon(
            keyword,
            context=search_context,
            sentence_context=sentence,
            force_redownload=False
        )
        
        # Categorize result
        result = {
            'keyword': keyword,
            'sentence': sentence,
            'icon_path': icon_path,
            'display_type': display_type
        }
        
        if 'manual_icons' in icon_path:
            result['source'] = 'MANUAL_OVERRIDE'
            manual_override_used.append(result)
            print(f"     ✓ Used MANUAL override: {os.path.basename(icon_path)}")
        elif 'placeholder' in icon_path:
            result['source'] = 'PLACEHOLDER'
            print(f"     ⚠ PLACEHOLDER created (no icon found)")
        elif os.path.exists(icon_path):
            # Check if it was just downloaded or was cached
            file_age = datetime.now().timestamp() - os.path.getmtime(icon_path)
            if file_age < 60:  # Less than 60 seconds old = just downloaded
                result['source'] = 'WEB_DOWNLOAD'
                web_downloaded.append(result)
                print(f"     ✓ Downloaded: {os.path.basename(icon_path)}")
            else:
                result['source'] = 'CACHED'
                already_cached.append(result)
                print(f"     ✓ Using cached: {os.path.basename(icon_path)}")
        
        download_results.append(result)
    
    # ============================================================
    # SUMMARY REPORT
    # ============================================================
    print("\n")
    print("=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    print()
    print(f"Total keywords processed: {len(icon_keywords)}")
    print(f"  ✓ Manual overrides used: {len(manual_override_used)}")
    print(f"  ✓ Downloaded from web:   {len(web_downloaded)}")
    print(f"  ✓ Already cached:        {len(already_cached)}")
    print(f"  ⚠ Placeholders created:  {len([r for r in download_results if r['source'] == 'PLACEHOLDER'])}")
    print()
    
    # ============================================================
    # DETAILED REPORTS
    # ============================================================
    
    if manual_override_used:
        print("\n" + "=" * 70)
        print("✓ MANUAL OVERRIDES USED (These are your custom icons)")
        print("=" * 70)
        for r in manual_override_used:
            print(f"\n  Keyword: {r['keyword']}")
            print(f"  Path:    {r['icon_path']}")
        print()
    
    if web_downloaded:
        print("\n" + "=" * 70)
        print("⚠ NEWLY DOWNLOADED ICONS (Review these for quality!)")
        print("=" * 70)
        print("\nThese icons were just downloaded from the web.")
        print("Check them to see if they're correct. If not, add manual overrides.\n")
        
        for r in web_downloaded:
            print(f"\n  Keyword:  \"{r['keyword']}\"")
            print(f"  Sentence: {r['sentence']}")
            print(f"  Path:     {r['icon_path']}")
            print(f"  To fix:   Add correct image to: data/assets/manual_icons/{r['keyword'].lower().replace(' ', '_').replace('-', '_')}.png")
    
    # ============================================================
    # SAVE DETAILED REPORT
    # ============================================================
    report_path = "data/icon_download_report.json"
    os.makedirs("data", exist_ok=True)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'script_word_count': len(script.split()),
        'total_keywords': len(keywords),
        'icon_keywords': len(icon_keywords),
        'text_keywords': len(text_keywords),
        'search_context': search_context,
        'downloads': download_results,
        'summary': {
            'manual_overrides': len(manual_override_used),
            'web_downloads': len(web_downloaded),
            'cached': len(already_cached),
            'placeholders': len([r for r in download_results if r['source'] == 'PLACEHOLDER'])
        }
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Detailed report saved to: {report_path}")
    
    # ============================================================
    # REVIEW INSTRUCTIONS
    # ============================================================
    print("\n" + "=" * 70)
    print("NEXT STEPS: Review Your Icons")
    print("=" * 70)
    print()
    print("1. Open the icons folder: data/assets/icons/")
    print("2. Look at the newly downloaded images")
    print("3. For any INCORRECT icons:")
    print("   a) Find the correct image online")
    print("   b) Save it to: data/assets/manual_icons/[keyword_name].png")
    print("   c) Follow naming rules in: data/assets/manual_icons/HOW_TO_USE.txt")
    print()
    print("4. Re-run this script to verify manual overrides work")
    print()
    print("Common issues to fix:")
    print("  - Real people (YouTubers/streamers): Need actual photos")
    print("  - Specific game items: Need official icons")
    print("  - Brand names: Need official logos")
    print()
    print("=" * 70)
    print()

if __name__ == "__main__":
    main()
