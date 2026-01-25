"""
Full LLM-Powered Pipeline Test
Tests the complete system with Claude API
"""
import os
import sys

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'src'))
sys.path.append(os.path.join(current_dir, 'src', 'engine'))
sys.path.append(os.path.join(current_dir, 'src', 'scrapers'))
sys.path.append(os.path.join(current_dir, 'src', 'analysis'))
sys.path.append(os.path.join(current_dir, 'src', 'utils'))

from main import VideoAutomationPipeline

print("=" * 70)
print("FULL LLM-POWERED PIPELINE TEST")
print("=" * 70)
print("\nThis will:")
print("  1. Analyze script with Claude")
print("  2. Search Reddit for evidence (optional - may need manual CAPTCHA)")
print("  3. Generate graphs from statistics")
print("  4. Find icons for keywords")
print("  5. Create timeline with Claude")
print("  6. Generate voiceover with ElevenLabs")
print("  7. Render final video with SFX")
print("\nEstimated cost: ~$0.50-0.80")
print("Estimated time: 2-5 minutes")
print("")

# Test script
test_script = """
Is Edgar completely broken right now? This character has dominated the meta for weeks.
He has a win rate of over 60 percent in Showdown and it is ruining the game for everyone.
Players are frustrated because Edgar requires zero skill to use effectively.
Reddit users are constantly sharing clips of him jumping on enemies with his super.
The community has been begging for a nerf, but Supercell hasn't responded yet.
Compare this to characters like Spike who sit at 49 percent win rate - perfectly balanced.
Will Edgar finally get the nerf he deserves? Only time will tell.
"""

print("Script to analyze:")
print("-" * 70)
print(test_script.strip())
print("-" * 70)
print("")

response = input("Ready to start? This will use API credits. (y/n): ")

if response.lower() != 'y':
    print("Test cancelled.")
    sys.exit(0)

print("\n" + "=" * 70)
print("STARTING PIPELINE...")
print("=" * 70)

try:
    # Initialize pipeline
    pipeline = VideoAutomationPipeline()
    
    # Optional: Provide specific Reddit URLs to avoid auto-search
    reddit_urls = [
        # Add any specific Reddit URLs here if you want to skip auto-search
        # "https://www.reddit.com/r/BrawlStars/comments/..."
    ]
    
    # Run full pipeline
    video_path = pipeline.run_full_pipeline(
        script_text=test_script,
        reddit_urls=reddit_urls if reddit_urls else None,
        output_name="edgar_llm_test"
    )
    
    if video_path:
        print("\n" + "=" * 70)
        print("SUCCESS! Video generated!")
        print("=" * 70)
        print(f"\nFinal video: {video_path}")
        print("\nCheck the following files:")
        print("  - Video: data/output/edgar_llm_test.mp4")
        print("  - Analysis: data/scripts/edgar_llm_test_analysis.json")
        print("  - Timeline: data/scripts/edgar_llm_test_timeline.json")
        print("\nYou can review the JSON files to see what Claude extracted!")
    else:
        print("\n[ERROR] Pipeline failed. Check error messages above.")
        
except Exception as e:
    print(f"\n[ERROR] Pipeline crashed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
