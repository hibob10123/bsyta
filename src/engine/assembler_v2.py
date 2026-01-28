import os
import sys
import PIL.Image

# --- 1. THE "MONKEY PATCH" (Crucial for Manim/MoviePy compatibility) ---
# This tricks MoviePy into working with the new Pillow version Manim installed.
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# -----------------------------------------------------------------------

from moviepy.editor import *
from moviepy.config import change_settings

# --- 2. CONFIGURATION ---
# If you needed to set the path before, uncomment and paste it here:
IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

def find_manim_video(scene_name):
    """Helper to find where Manim hid the video file."""
    # Manim likes to hide files in folders like '480p15' or '1080p60'
    search_dir = os.path.join("data", "temp", "manim_renders", "videos")
    
    for root, dirs, files in os.walk(search_dir):
        for file in files:
            if file == f"{scene_name}.mp4":
                return os.path.join(root, file)
    return None

def create_pro_scene(brawler_name, scene_name, evidence_path):
    print(f"🎬 Assembling PRO scene for {brawler_name}...")

    # A. GET BACKGROUND (The Graph)
    manim_path = find_manim_video(scene_name)
    if not manim_path:
        print(f"❌ Could not find Manim video for '{scene_name}'")
        print("   Did you run visualizer.py first?")
        return

    print(f"   ↳ Found background: {manim_path}")
    base_clip = VideoFileClip(manim_path)
    duration = base_clip.duration

    # B. GET BRAWLER (The Subject)
    brawler_path = f"data/assets/{brawler_name}.png"
    if not os.path.exists(brawler_path):
        print(f"❌ Missing brawler image: {brawler_path}")
        return

    # Effect: "Breathing" (Zooms from 1.0x to 1.05x size)
    brawler_img = (ImageClip(brawler_path)
                   .resize(height=900)
                   .set_position(("left", "bottom"))
                   .set_duration(duration))
    
    brawler_anim = brawler_img.resize(lambda t: 1 + (0.02 * t))

    # C. GET EVIDENCE (The Screenshot)
    # Effect: Slides in from the right side
    evidence_img = (ImageClip(evidence_path)
                    .resize(width=800)
                    .set_duration(duration - 1) # Starts 1 second late
                    .set_start(1))
    
    def slide_in(t):
        target_x = 1000  # Final X position
        start_x = 2000   # Start off-screen
        if t < 0.5:
            # Math to slide smoothly over 0.5 seconds
            return (start_x + (target_x - start_x) * (t / 0.5), "center")
        else:
            return (target_x, "center")

    evidence_anim = evidence_img.set_position(slide_in)

    # D. THE TITLE (The Overlay)
    # We add a semi-transparent black bar so text pops
    header_bar = (ColorClip(size=(1920, 150), color=(0,0,0))
                  .set_opacity(0.7)
                  .set_position(("center", "top"))
                  .set_duration(duration))

    title_text = (TextClip(f"IS {brawler_name.upper()} BROKEN?", 
                           font='Arial-Bold', 
                           fontsize=90, 
                           color='white', 
                           stroke_color='black', 
                           stroke_width=3)
                  .set_position(("center", 35))
                  .set_duration(duration)
                  .crossfadein(0.5))

    # E. COMPOSE
    # Order matters! First in list = Bottom layer. Last in list = Top layer.
    final_clip = CompositeVideoClip([
        base_clip,      # 1. Background (Graph)
        header_bar,     # 2. Black Bar
        title_text,     # 3. Text
        evidence_anim,  # 4. Screenshot (Mid)
        brawler_anim    # 5. Brawler (Front)
    ], size=(1920, 1080))

    # F. RENDER
    output_path = "data/temp/pro_render.mp4"
    final_clip.write_videofile(output_path, fps=30, codec="h264_nvenc")
    print(f"✅ Pro video saved to {output_path}")

if __name__ == "__main__":
    # Make sure these match YOUR file names!
    create_pro_scene(
        brawler_name="Fang",
        scene_name="BrawlerWinRateChart", # The class name from visualizer.py
        evidence_path="data/assets/Fang_evidence.png"
    )