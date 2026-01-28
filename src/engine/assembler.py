from moviepy.editor import *
import os
import PIL.Image
# --- THE MONKEY PATCH (Fixes the Pillow 12 Error) ---
# MoviePy uses 'ANTIALIAS' which was renamed to 'LANCZOS' in newer Pillow versions.
# We manually inject the old name back into the library so MoviePy finds it.
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
from moviepy.editor import *
from moviepy.config import change_settings

# --- PASTE YOUR PATH BELOW ---
# 1. Paste the path you copied between the quotes
# 2. Add "\magick.exe" at the end
# 3. KEEP the 'r' before the quote!
IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# Tell MoviePy where to look
if os.path.exists(IMAGEMAGICK_BINARY):
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})
else:
    print(f"⚠️  WARNING: Could not find ImageMagick at: {IMAGEMAGICK_BINARY}")
    print("Please verify the path in src/engine/assembler.py matches your installation.")

def create_scene(brawler_name, sentiment_text, evidence_path):
    print(f"🎬 Assembling scene for {brawler_name}...")

    # 1. Setup Paths
    # We assume you have these from your previous scripts
    brawler_path = f"data/assets/{brawler_name}.png"
    if not os.path.exists(brawler_path):
        print(f"❌ Missing asset: {brawler_path}")
        return

    # 2. Create the Background (1920x1080)
    # We make a simple dark blue solid color background
    background = ColorClip(size=(1920, 1080), color=(20, 20, 40), duration=5)

    # 3. Create the Brawler Image (The Subject)
    # We resize him and put him on the left
    brawler = (ImageClip(brawler_path)
               .resize(height=900) # Scale to 900px tall
               .set_position(("left", "bottom"))
               .set_duration(5)) # Lasts 5 seconds

    # 4. Create the Evidence (The Screenshot)
    # We put this on the right
    evidence = (ImageClip(evidence_path)
                .resize(width=1000) # Scale width
                .set_position(("right", "center"))
                .set_duration(5))

    # 5. Add Text (The "Documentary" Caption)
    # NOTE: If this crashes, it's an ImageMagick issue.
    txt_clip = (TextClip(sentiment_text, fontsize=70, color='white', font='Arial-Bold')
                .set_position(('center', 100)) # Near top
                .set_duration(5))

    # 6. Composite (Layer them together)
    # Think of this like Photoshop layers: Background -> Brawler -> Evidence -> Text
    final_clip = CompositeVideoClip([background, brawler, evidence, txt_clip])

    # 7. Render
    output_path = "data/temp/test_render.mp4"
    os.makedirs("data/temp", exist_ok=True)
    
    print("⚙️  Rendering video... (This might take a moment)")
    final_clip.write_videofile(output_path, fps=24, codec="h264_nvenc")
    print(f"✅ Video saved to {output_path}")

if __name__ == "__main__":
    # Point this to files that ACTUALLY exist in your folder
    # Use the screenshot you generated earlier
    create_scene(
        brawler_name="Fang", 
        sentiment_text="Is Fang Ruining the Meta?", 
        evidence_path="data/assets/Fang_evidence.png" 
    )