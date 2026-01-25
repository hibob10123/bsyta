"""
Quick test with new voice and icons
"""
import os
import sys

sys.path.append('src')
sys.path.append('src/engine')
sys.path.append('src/scrapers')
sys.path.append('src/analysis')
sys.path.append('src/utils')

from main import VideoAutomationPipeline

print("=" * 70)
print("VOICE TEST - Quick one sentence")
print("=" * 70)

# Simple test sentence
test_script = "Edgar is absolutely dominating the Brawl Stars meta right now."

print(f"\nScript: {test_script}")
print("\nExpected:")
print("  - New voice from config.yaml")
print("  - Icons for 'Edgar', 'dominating', 'Brawl Stars'")
print("  - Whoosh sound effects")
print("\nGenerating...\n")

try:
    pipeline = VideoAutomationPipeline()
    
    # Fast mode - disable reddit and graphs
    pipeline.config.config['pipeline']['do_reddit_search'] = False
    pipeline.config.config['pipeline']['do_graph_generation'] = False
    
    video_path = pipeline.run_full_pipeline(
        script_text=test_script,
        reddit_urls=None,
        output_name="voice_test"
    )
    
    if video_path:
        print("\n" + "=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"\nVideo: {video_path}")
        print("\nCheck the voice - should be the one from config.yaml!")
    else:
        print("\nFAILED - No video generated")
        
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
