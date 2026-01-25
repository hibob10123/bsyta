"""
Quick video generation with manual control
Skip problematic parts and use what we have
"""
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'src'))
sys.path.append(os.path.join(current_dir, 'src', 'engine'))

from engine.director import render_video
from engine.voiceover import generate_voiceover

print("=" * 70)
print("QUICK VIDEO - MANUAL MODE")
print("=" * 70)
print("\nThis uses your WORKING old system:")
print("  ✓ ElevenLabs voiceover")
print("  ✓ Simple 3-scene structure")
print("  ✓ Existing assets (Edgar.png, Fang.png, etc.)")
print("  ✓ No Claude/Reddit/Manim complexity")
print("")

# Your script
script = """
Is Edgar completely broken right now? This character has dominated the meta for weeks.
He has a win rate of over 60 percent in Showdown and it is ruining the game for everyone.
Players are frustrated because Edgar requires zero skill to use effectively.
"""

print("Script:")
print("-" * 70)
print(script.strip())
print("-" * 70)
print("")

# Check assets
assets_status = []
for asset in ["data/assets/Edgar.png", "data/assets/Fang.png", "data/assets/gameplay.mp4"]:
    exists = "✓" if os.path.exists(asset) else "✗"
    assets_status.append(f"{exists} {asset}")

print("Asset check:")
for status in assets_status:
    print(f"  {status}")
print("")

response = input("Generate video? (y/n): ")
if response.lower() != 'y':
    print("Cancelled")
    sys.exit(0)

print("\n" + "=" * 70)
print("GENERATING VIDEO...")
print("=" * 70)

try:
    # Use the old working system
    print("\n[1/2] Generating voiceover...")
    voiceover = generate_voiceover(script, "quick_manual")
    
    if voiceover:
        print(f"  ✓ Audio: {voiceover}")
        
        print("\n[2/2] Rendering video...")
        render_video("Edgar", script)
        
        print("\n" + "=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print("\nVideo location: data/output_Edgar.mp4")
        print("\nThis used the simple proven system.")
        print("For LLM features, we need to fix:")
        print("  - Icon downloading (web search)")
        print("  - Reddit CAPTCHA handling")
        print("  - Manim graph generation")
    else:
        print("\n[ERROR] Voiceover failed")
        
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
