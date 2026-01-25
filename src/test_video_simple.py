import os
import sys

# Setup paths - we're already in src/ so go up one level
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'engine'))

from engine.director import render_video
from engine.voiceover import generate_voiceover

# Simple test script
test_script = """
Edgar is completely broken right now.
He has a win rate of over 60 percent in Showdown.
Reddit users are sharing clips of him dominating games.
"""

print("=" * 60)
print("SIMPLE VIDEO TEST (No Claude Required)")
print("=" * 60)

# Generate voiceover
print("\n[1/2] Generating voiceover...")
voiceover_path = generate_voiceover(test_script, "simple_test")

if voiceover_path:
    print(f"   Success! Audio at: {voiceover_path}")
    
    # Render video (uses your old director.py)
    print("\n[2/2] Rendering video...")
    render_video("Edgar", test_script)
    
    print("\n" + "=" * 60)
    print("DONE! Check data/output_Edgar.mp4")
    print("=" * 60)
else:
    print("\n[ERROR] Voiceover failed. Check your ELEVENLABS_API_KEY")