"""
Test LLM-powered SFX selection with various keywords
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
print("LLM-POWERED SFX SELECTION TEST")
print("=" * 70)

# Test with different types of keywords
test_script = """
Edgar is dominating the meta right now. 
He got a huge buff in the latest update.
But Mortis has been nerfed badly.
The community is clicking share buttons everywhere.
"""

print(f"\nScript: {test_script}")
print("\nExpected SFX choices:")
print("  - 'dominating' -> vineboom (dramatic)")
print("  - 'buff' -> vineboom or whoosh")
print("  - 'nerfed' -> whoosh (most icons)")
print("  - 'clicking' -> click or pop")
print("\nGenerating...\n")

try:
    pipeline = VideoAutomationPipeline()
    
    # Disable reddit/graphs for faster test
    pipeline.config.config['pipeline']['do_reddit_search'] = False
    pipeline.config.config['pipeline']['do_graph_generation'] = False
    
    video_path = pipeline.run_full_pipeline(
        script_text=test_script,
        reddit_urls=None,
        output_name="llm_sfx_test"
    )
    
    if video_path:
        print("\n" + "=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"\nVideo: {video_path}")
        print("\nListen to the SFX - each should match its context!")
    else:
        print("\nFAILED - No video generated")
        
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
