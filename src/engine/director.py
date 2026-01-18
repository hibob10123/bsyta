import os
import random
import PIL.Image

# --- MONKEY PATCH ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import *
from moviepy.config import change_settings
from voiceover import generate_voiceover

# --- CONFIGURATION (YOUR MAGICK PATH) ---
IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

def get_background(duration):
    gameplay_path = "data/assets/gameplay.mp4"
    if os.path.exists(gameplay_path):
        bg = VideoFileClip(gameplay_path)
        if bg.duration > duration:
            start = random.uniform(0, bg.duration - duration)
            bg = bg.subclip(start, start + duration)
        # Resize to 1080p and darken
        return bg.resize(newsize=(1920, 1080)).fx(vfx.colorx, 0.4)
    else:
        return ColorClip(size=(1920, 1080), color=(50, 50, 80), duration=duration)

def attach_voice(clip, text, filename):
    audio_path = generate_voiceover(text, filename)
    if audio_path and os.path.exists(audio_path):
        print(f"   [AUDIO] Attaching audio: {filename}")
        audio_clip = AudioFileClip(audio_path)
        
        # Set video duration to match audio + small padding
        final_duration = audio_clip.duration + 0.5
        clip = clip.set_duration(final_duration)
        
        # Attach the audio
        clip = clip.set_audio(audio_clip)
        print(f"   [AUDIO] Audio duration: {audio_clip.duration}s, Video duration: {clip.duration}s")
        return clip
    else:
        print(f"   [WARNING] No audio found for {filename}")
        return clip

# --- SCENE 1 ---
def create_icon_scene(brawler, script_text):
    print("   ...Rendering Scene 1")
    bg = get_background(duration=4)
    clips = [bg]
    
    icon_path = f"data/assets/{brawler}.png"
    if os.path.exists(icon_path):
        icon = (ImageClip(icon_path).resize(height=600).set_position(("left", "center")).set_duration(4))
        icon = icon.resize(lambda t: max(0.01, min(1, t * 5)))
        clips.append(icon)

    txt = (TextClip(f"IS {brawler.upper()}\nBROKEN?", fontsize=110, color='white', font='Arial-Bold', stroke_color='black', stroke_width=4).set_position(("right", "center")).set_duration(4))
    clips.append(txt)
    
    return attach_voice(CompositeVideoClip(clips), script_text, "scene_1")

# --- SCENE 2 (Graph Overlay) ---
def create_graph_scene(manim_path, script_text):
    print("   ...Rendering Scene 2")
    if not os.path.exists(manim_path): return None
        
    graph_clip = VideoFileClip(manim_path)
    # Remove black background from graph so gameplay shows through
    graph_clip = graph_clip.fx(vfx.mask_color, color=[0,0,0], thr=10, s=5)
    
    bg = get_background(duration=graph_clip.duration)
    # Center the graph on the background
    graph_clip = graph_clip.set_position("center")
    
    return attach_voice(CompositeVideoClip([bg, graph_clip]), script_text, "scene_2")

# --- SCENE 3 ---
def create_reddit_scene(evidence_path, script_text):
    print("   ...Rendering Scene 3")
    bg = get_background(duration=5)
    
    if os.path.exists(evidence_path):
        evidence = (ImageClip(evidence_path).resize(width=900).set_duration(5))
        # Slide up to Center
        def slide_up(t):
            start_y = 1200 
            target_y = "center" 
            if t < 0.7: return ("center", int(1200 - (1200 - 540) * (t / 0.7)))
            else: return ("center", "center")

        evidence = evidence.set_position(slide_up)
        return attach_voice(CompositeVideoClip([bg, evidence]), script_text, "scene_3")
    
    return attach_voice(bg, script_text, "scene_3")

def render_video(brawler_name, full_script):
    print(f"[RENDER] STARTING RENDER FOR: {brawler_name}")
    
    # 1. SPLIT SCRIPT AUTOMATICALLY
    # We split the long text into 3 parts for the 3 scenes
    # If the script is too short, we just repeat it (safe fallback)
    sentences = full_script.split('.')
    sentences = [s.strip() for s in sentences if len(s) > 5]
    
    # Safety logic: Ensure we have at least 3 chunks
    while len(sentences) < 3:
        sentences.append(sentences[0]) # Repeat if too short
        
    script_1 = sentences[0] + "."
    script_2 = sentences[1] + "."
    # Join the rest for the final scene
    script_3 = ". ".join(sentences[2:]) + "."

    # 2. DEFINE PATHS
    manim_file = "data/temp/manim_renders/videos/BrawlerWinRateChart.mp4"
    evidence_file = f"data/assets/{brawler_name}_evidence.png" # Dynamic Filename

    # 3. GENERATE SCENES
    scene1 = create_icon_scene(brawler_name, script_1)
    scene2 = create_graph_scene(manim_file, script_2)
    scene3 = create_reddit_scene(evidence_file, script_3)
    
    # 4. RENDER - Concatenate with proper audio handling
    final_clips = [s for s in [scene1, scene2, scene3] if s is not None]
    
    # Check if each clip has audio
    for i, clip in enumerate(final_clips):
        has_audio = clip.audio is not None
        print(f"[DEBUG] Scene {i+1} audio: {has_audio}")
    
    # Concatenate videos
    final_movie = concatenate_videoclips(final_clips, method="chain")
    
    # Explicitly concatenate and re-attach audio
    audio_clips = [clip.audio for clip in final_clips if clip.audio is not None]
    if audio_clips:
        print(f"[DEBUG] Found {len(audio_clips)} audio clips to merge")
        final_audio = concatenate_audioclips(audio_clips)
        final_movie = final_movie.set_audio(final_audio)
        print(f"[DEBUG] Audio merged and attached to video")
    else:
        print(f"[WARNING] No audio clips found")
    
    output_filename = f"data/output_{brawler_name}.mp4"
    
    # Ensure audio is properly included
    if final_movie.audio is not None:
        print(f"[SUCCESS] Audio detected in final video")
        print(f"[DEBUG] Final movie audio duration: {final_movie.audio.duration}s")
    else:
        print(f"[WARNING] No audio detected in final concatenated video")
    
    final_movie.write_videofile(
        output_filename, 
        fps=30, 
        codec="libx264", 
        audio_codec="aac",
        verbose=False,
        logger=None
    )
    print(f"[SUCCESS] VIDEO SAVED: {output_filename}")

if __name__ == "__main__":
    # Test mode
    render_video("Fang", "Test script. This is line two. This is line three.")