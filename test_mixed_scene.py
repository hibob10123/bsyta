"""
Test for mixed evidence scene: gameplay + graph + reddit + icons
"""

import os
import sys
sys.path.append('src')

from analysis.script_analyzer import ScriptAnalyzer
from scrapers.reddit_intelligence import RedditIntelligence
from scrapers.asset_gatherer import AssetGatherer
from engine.graph_generator import GraphGenerator
from engine.scene_planner import ScenePlanner
from engine.voiceover import generate_voiceover
from engine.director_v3 import DirectorV3

print("=" * 70)
print("MIXED SCENE TEST")
print("=" * 70)
print()
print("Script: Edgar's win rate dropped from 60% to 48% after the nerf,")
print("        and the community is furious about it.")
print()
print("Reddit URL: https://www.reddit.com/r/BrawlStarsCompetitive/comments/18l80cp/my_honest_thoughts_on_edgar_after_the_nerf/")
print()
print("Expected:")
print("  - ONE mixed_evidence scene with:")
print("    * Dimmed gameplay background")
print("    * Graph showing win rate drop")
print("    * Reddit post sliding up")
print("    * Icons for Edgar, nerf, community")
print("    * Background music playing")
print()
print("Generating...")
print()

# Script with both statistics and community evidence
script = """Edgar's win rate dropped from 60% to 48% after the nerf, and the community is furious about it."""

# Step 1: Analyze script
print("[1/7] Analyzing script...")
analyzer = ScriptAnalyzer()
analysis = analyzer.analyze_script(script)
print(f"  Found {len(analysis['keywords'])} keywords")
print(f"  Found {len(analysis['statistics'])} statistics")
print(f"  Keywords: {', '.join([k['word'] for k in analysis['keywords']])}")

# Step 2: Manual Reddit URL
print("\n[2/7] Using manual Reddit URL...")
reddit_intel = RedditIntelligence()
reddit_url = "https://www.reddit.com/r/BrawlStarsCompetitive/comments/18l80cp/my_honest_thoughts_on_edgar_after_the_nerf/"
screenshot_path = reddit_intel.screenshot_with_highlight(reddit_url, "data/assets/edgar_mixed_test.png")
reddit_posts = [{
    'url': reddit_url,
    'title': 'My honest thoughts on Edgar after the nerf',
    'score': 500,
    'screenshot': screenshot_path
}]
print(f"  Reddit screenshot saved")

# Step 3: Generate graph from statistics
print("\n[3/7] Generating graph...")
graph_gen = GraphGenerator()
# Extract win rate data
graph_data = {
    'type': 'line',
    'title': 'Edgar Win Rate',
    'x_label': 'Time Period',
    'y_label': 'Win Rate (%)',
    'data': {
        'Before Nerf': 60,
        'After Nerf': 48
    }
}
graph_path = graph_gen.create_dynamic_scene(graph_data, "EdgarWinRateScene")
print(f"  Graph generated")

# Step 4: Gather icons
print("\n[4/7] Gathering icons...")
gatherer = AssetGatherer()
icon_keywords = [k['word'] for k in analysis['keywords'][:3]]  # Top 3
gatherer.batch_prepare(icon_keywords)
print(f"  Icons prepared")

# Step 5: Generate voiceover
print("\n[5/7] Generating voiceover...")
voiceover_path = generate_voiceover(script, "mixed_test_voice")
print(f"  Voiceover generated")

# Step 6: Create timeline
print("\n[6/7] Creating timeline...")
planner = ScenePlanner()
timeline = planner.create_timeline(
    script_segments=analysis['segments'],
    keywords=analysis['keywords'],
    reddit_posts=reddit_posts,
    graphs=[graph_path] if graph_path else []
)

print(f"  Timeline created with {len(timeline['scenes'])} scene(s)")
for scene in timeline['scenes']:
    print(f"    - Scene {scene['scene_number']}: {scene['type']} ({len(scene['elements'])} elements)")
    for elem in scene['elements']:
        print(f"      * {elem['type']}: {elem.get('keyword', elem.get('index', 'N/A'))}")

# Step 7: Render video
print("\n[7/7] Rendering video...")
director = DirectorV3()
output_path = director.render_video(
    timeline=timeline,
    voiceover_path=voiceover_path,
    output_path="data/output/mixed_scene_test.mp4"
)

print()
print("=" * 70)
print("SUCCESS!")
print("=" * 70)
print(f"Video saved: {output_path}")
print()
print("Check the video - it should have:")
print("  - Gameplay background (dimmed)")
print("  - Graph showing win rate drop")
print("  - Reddit post sliding up")
print("  - Icons appearing for keywords")
print("  - Background music playing throughout")
print("  - Sound effects for each element")
