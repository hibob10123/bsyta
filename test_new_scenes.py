"""Test the new scene types: text_statement, scrolling_comments, b-roll"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import VideoAutomationPipeline

script = """
In December 2024, Brawl Stars exploded to 84 million players—up from 
65 million in 2022 and 50 million back in 2020. This massive growth 
was fueled by the Toy Story collaboration. The community erupted in 
celebration, with thousands of posts praising the milestone.
"""

reddit_posts = [
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1hee0vd/2024_was_the_worst_year_for_brawl_stars_ever/",
        "description": "Discussion from December 2024 acknowledging record player numbers and Toy Story collaboration impact"
    }
]

output_name = "new_scenes_test"

print("="*70)
print("TESTING NEW SCENE TYPES")
print("="*70)
print("\nThis test will demonstrate:")
print("  1. text_statement - Bold dramatic text scenes")
print("  2. scrolling_comments - Scrolling Reddit comments feed")  
print("  3. b-roll - Cinematic images with Ken Burns pan effect")
print("\nGenerating...\n")

pipeline = VideoAutomationPipeline()

try:
    video_path = pipeline.run_full_pipeline(
        script_text=script,
        reddit_posts=reddit_posts,
        output_name=output_name
    )
    
    print("\n" + "="*70)
    print("SUCCESS!")
    print("="*70)
    print(f"Video saved: {video_path}")
    print("\nCheck the video for new scene types:")
    print("  📝 text_statement - Dramatic text on colored backgrounds")
    print("  💬 scrolling_comments - Scrolling community reactions")
    print("  🎬 b-roll - Cinematic imagery with slow pan/zoom")
    print("  🎮 gameplay_icons - Traditional icons/text overlays")
    print("  📊 data_graph - Animated statistics visualization")
    print("  📱 reddit_evidence - Reddit post screenshots")
    
except Exception as e:
    print(f"\n[ERROR] Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
