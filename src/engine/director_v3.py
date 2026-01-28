import os
import sys
import random
import time
import numpy as np
import yaml
import PIL.Image
import warnings

# Suppress DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Starting with ImageIO v3.*")

# Monkey patch for PIL/MoviePy compatibility
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# MoviePy 2.x compatible imports
try:
    from moviepy.editor import *
except ImportError:
    # MoviePy 2.x
    from moviepy import (
        VideoFileClip, ImageClip, TextClip, AudioFileClip,
        CompositeVideoClip, CompositeAudioClip, ColorClip,
        concatenate_videoclips, concatenate_audioclips, vfx
    )

try:
    from moviepy.config import change_settings
except ImportError:
    # MoviePy 2.x doesn't have config in the same place
    change_settings = None

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from engine.sfx_engine import SFXEngine

# ImageMagick configuration
IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
if os.path.exists(IMAGEMAGICK_BINARY) and change_settings is not None:
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

class DirectorV3:
    """
    Enhanced director that builds sophisticated multi-element scenes
    based on LLM-generated timeline with precise timing
    """
    
    def __init__(self, gameplay_path="data/assets/gameplay.mp4", music_path=None, config_path="config.yaml"):
        self.gameplay_path = gameplay_path
        self.music_path = music_path  # Override music file (for multi-part videos)
        self.sfx_engine = SFXEngine()
        
        # Load config for background music settings
        self.config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        
        # Reddit screenshots metadata (will be set in render_video)
        self.reddit_screenshots = []
        
        # Graph metadata (will be set in render_video)
        self.graph_metadata = []
        
        # Alternate backgrounds for cycling (paper background, etc.)
        paths_config = self.config.get('paths', {})
        self.alternate_backgrounds = paths_config.get('alternate_backgrounds', [])
        self.alternate_bg_chance = paths_config.get('alternate_background_chance', 0.35)
        self.last_bg_was_alternate = False  # Track to avoid consecutive alternates
        
        # Validate alternate backgrounds exist
        self.alternate_backgrounds = [p for p in self.alternate_backgrounds if os.path.exists(p)]
        if self.alternate_backgrounds:
            print(f"[DIRECTOR] Loaded {len(self.alternate_backgrounds)} alternate background(s): {self.alternate_backgrounds}")
    
    def render_video(self, timeline, voiceover_path, output_path="data/output/final_video.mp4", sentence_timings=None, reddit_screenshots=None, graph_metadata=None, youtube_cards=None):
        """
        Render complete video from timeline and voiceover
        
        Args:
            timeline: Complete timeline from ScenePlanner
            voiceover_path: Path to voiceover audio file
            output_path: Where to save final video
            sentence_timings: Optional list of sentence timing dicts for subtitles
                [{"text": "...", "start_time": 0.0, "duration": 2.5}, ...]
            reddit_screenshots: Optional list of Reddit screenshot metadata dicts
                [{"path": "...", "matched_segment": 1, "relevance_score": 8, ...}, ...]
            graph_metadata: Optional list of graph metadata dicts
                [{"path": "...", "metric": "...", "description": "...", ...}, ...]
            youtube_cards: Optional list of YouTube video evidence card metadata
                [{"path": "...", "title": "...", "channel": "...", ...}, ...]
        
        Returns:
            Path to rendered video
        """
        # Store reddit_screenshots for use in _create_reddit_element
        self.reddit_screenshots = reddit_screenshots or []
        if self.reddit_screenshots:
            print(f"[DIRECTOR] Received {len(self.reddit_screenshots)} Reddit screenshots for rendering:")
            for i, rs in enumerate(self.reddit_screenshots):
                path = rs.get('path', 'No path')
                score = rs.get('relevance_score', 0)
                print(f"   [{i}] {os.path.basename(path)} (score: {score}/10)")
        else:
            print(f"[DIRECTOR] WARNING: No Reddit screenshots provided to director!")

        # Store youtube_cards
        self.youtube_cards = youtube_cards or []
        
        # Apply sync offset to fix visual timing
        # Negative values make elements appear EARLIER (if they feel delayed)
        sync_offset = self.config.get('scenes', {}).get('sync_offset', 0.0)
        if sync_offset != 0.0:
            print(f"[DIRECTOR] Applying sync offset: {sync_offset:+.2f}s to all element timestamps")
            adjusted_count = 0
            clamped_count = 0
            for scene in timeline.get('scenes', []):
                scene_start = scene.get('start_time', 0)
                for element in scene.get('elements', []):
                    # Shift timestamp, but don't go below scene start time
                    # This prevents elements from appearing before their scene starts
                    original = element.get('timestamp', 0)
                    adjusted = original + sync_offset
                    
                    # Clamp to scene boundaries (not below scene_start)
                    if adjusted < scene_start:
                        element['timestamp'] = scene_start + 0.1  # Small offset into scene
                        clamped_count += 1
                    else:
                        element['timestamp'] = adjusted
                    adjusted_count += 1
            
            print(f"[DIRECTOR]   Adjusted {adjusted_count} elements ({'earlier' if sync_offset < 0 else 'later'} by {abs(sync_offset):.2f}s)")
            if clamped_count > 0:
                print(f"[DIRECTOR]   WARNING: {clamped_count} elements were clamped to scene boundaries")
        
        # Store graph metadata for use in _find_graph_video
        self.graph_metadata = graph_metadata or []
        
        print("[DIRECTOR] Starting video render...")
        print(f"[DIRECTOR] Timeline has {len(timeline['scenes'])} scenes")
        if self.reddit_screenshots:
            print(f"[DIRECTOR] Have {len(self.reddit_screenshots)} Reddit screenshot(s) with metadata")
        if self.graph_metadata:
            print(f"[DIRECTOR] Have {len(self.graph_metadata)} graph(s) with metadata")
        
        # Pre-render validation
        self._validate_timeline_before_render(timeline)
        
        # Load voiceover
        voiceover = AudioFileClip(voiceover_path)
        bg_music = None
        composite_audio_from_clips = None
        mixed_audio = None
        total_duration = voiceover.duration
        print(f"[DIRECTOR] Total duration: {total_duration:.1f}s")
        
        # Collect ALL clips that will be composited together
        # This includes scenes AND subtitles to avoid nested composites (which cause timing drift)
        all_clips = []
        
        # Render each scene with proper timing
        # Track scene timings for gap detection
        rendered_scenes = []  # List of (start_time, end_time, clip)
        
        for scene in timeline['scenes']:
            start_time = scene['start_time']
            end_time = scene['end_time']
            duration = end_time - start_time
            
            # CRITICAL FIX: Check for invalid scene duration (negative or zero)
            if duration <= 0:
                print(f"[DIRECTOR] WARNING: Scene {scene.get('scene_number', '?')} has invalid duration: {duration:.2f}s ({start_time:.2f}s - {end_time:.2f}s)")
                
                # Try to fix using element timestamps if available
                elements = scene.get('elements', [])
                if elements:
                    element_times = [e.get('timestamp', 0) for e in elements if e.get('timestamp', 0) > 0]
                    if element_times:
                        # Use element timestamps to determine scene boundaries
                        start_time = max(0, min(element_times) - 0.5)
                        end_time = max(element_times) + 2.5
                        duration = end_time - start_time
                        scene['start_time'] = start_time
                        scene['end_time'] = end_time
                        print(f"[DIRECTOR]   -> Fixed using element timestamps: {start_time:.2f}s - {end_time:.2f}s")
                    else:
                        # Skip this scene entirely
                        print(f"[DIRECTOR]   -> Skipping invalid scene (no valid element timestamps)")
                        continue
                else:
                    # No elements, skip this scene
                    print(f"[DIRECTOR]   -> Skipping invalid scene (no elements)")
                    continue
            
            clip = self._render_scene(scene, total_duration)
            
            # CRITICAL: If scene rendering fails, create a fallback background
            # This prevents black screens during failed scenes
            if clip is None:
                print(f"[DIRECTOR] WARNING: Scene {scene['scene_number']} failed to render - using fallback background")
                clip = self._get_background(duration)
            
            # Set each scene to start at its designated time in the timeline
            clip = clip.set_start(start_time)
            all_clips.append(clip)
            rendered_scenes.append((start_time, end_time, clip))
            print(f"[DIRECTOR] Scene {scene['scene_number']} will start at {start_time:.1f}s, end at {end_time:.1f}s")
        
        if not all_clips:
            print("[ERROR] No scenes rendered!")
            return None
        
        # CRITICAL: Fill ANY gaps in the timeline with background
        # Sort rendered scenes by start time and look for gaps
        rendered_scenes.sort(key=lambda x: x[0])
        gap_fillers = []
        
        # Check for gap at the START (before first scene)
        if rendered_scenes and rendered_scenes[0][0] > 0.1:
            gap_start = 0.0
            gap_end = rendered_scenes[0][0]
            gap_duration = gap_end - gap_start
            print(f"[DIRECTOR] FILLING GAP at start: 0.0s - {gap_end:.2f}s ({gap_duration:.2f}s)")
            gap_bg = self._get_background(gap_duration)
            gap_bg = gap_bg.set_start(0)
            gap_fillers.append(gap_bg)
        
        # Check for gaps BETWEEN scenes
        for i in range(len(rendered_scenes) - 1):
            current_end = rendered_scenes[i][1]
            next_start = rendered_scenes[i + 1][0]
            
            gap = next_start - current_end
            if gap > 0.1:  # More than 100ms gap
                print(f"[DIRECTOR] FILLING GAP: {current_end:.2f}s - {next_start:.2f}s ({gap:.2f}s)")
                gap_bg = self._get_background(gap)
                gap_bg = gap_bg.set_start(current_end)
                gap_fillers.append(gap_bg)
        
        # Check for gap at the END (after last scene to total duration)
        if rendered_scenes:
            last_end = rendered_scenes[-1][1]
            if last_end < total_duration - 0.1:
                gap_duration = total_duration - last_end
                print(f"[DIRECTOR] FILLING GAP at end: {last_end:.2f}s - {total_duration:.2f}s ({gap_duration:.2f}s)")
                gap_bg = self._get_background(gap_duration)
                gap_bg = gap_bg.set_start(last_end)
                gap_fillers.append(gap_bg)
        
        # Add all gap fillers to clips
        if gap_fillers:
            print(f"[DIRECTOR] Added {len(gap_fillers)} background filler(s) to cover gaps")
            all_clips.extend(gap_fillers)
        
        # Validation: Check if scene timeline covers the full video duration
        last_scene = timeline['scenes'][-1]
        if last_scene['end_time'] < total_duration:
            print(f"[WARNING] Scene timeline ends at {last_scene['end_time']:.1f}s but voiceover is {total_duration:.1f}s")
            print(f"[WARNING] Last {total_duration - last_scene['end_time']:.1f}s will show the last scene extended")
        
        # Add subtitles to the SAME list (before creating composite - critical for timing!)
        # This avoids nested composites which can cause progressive timing drift
        if sentence_timings:
            print("[DIRECTOR] Adding scene-aware subtitles...")
            subtitle_clips = self._create_subtitle_clips(sentence_timings, timeline, total_duration)
            if subtitle_clips:
                all_clips.extend(subtitle_clips)  # Add to same list, not nested!
                print(f"[DIRECTOR] Added {len(subtitle_clips)} subtitle clips")
        
        # Composite ALL clips (scenes + subtitles) at their specific timestamps
        # This ensures everything appears at the exact times specified
        print(f"[DIRECTOR] Compositing {len(all_clips)} clips at their designated times...")
        final_video = CompositeVideoClip(all_clips, size=(1920, 1080))
        
        # Trim to exact voiceover duration
        final_video = final_video.set_duration(total_duration)
        
        # Collect all audio tracks to mix together
        audio_tracks = [voiceover]  # Start with voiceover
        
        # Extract audio from the composite (includes meme audio and any other clip audio)
        if final_video.audio:
            print("[DIRECTOR] Found audio in composite (memes, etc.) - will mix with voiceover")
            composite_audio_from_clips = final_video.audio
            audio_tracks.append(composite_audio_from_clips)
        
        # Add background music if enabled
        bg_music_config = self.config.get('background_music', {})
        if bg_music_config.get('enabled', False):
            # Use override music_path if set (for multi-part videos), otherwise use config
            bg_music_path = self.music_path if self.music_path else bg_music_config.get('path')
            bg_volume = bg_music_config.get('volume', 0.15)
            
            if bg_music_path and os.path.exists(bg_music_path):
                print(f"[DIRECTOR] Adding background music: {os.path.basename(bg_music_path)} (volume: {bg_volume})")
                
                # Load background music
                bg_music = AudioFileClip(bg_music_path)
                
                # Loop music to match video duration if needed
                if bg_music.duration < total_duration:
                    loops_needed = int(total_duration / bg_music.duration) + 1
                    bg_music = concatenate_audioclips([bg_music] * loops_needed)
                
                # Trim to exact duration and adjust volume
                bg_music = bg_music.subclip(0, total_duration).volumex(bg_volume)
                audio_tracks.append(bg_music)
                print("[DIRECTOR] Background music added to audio mix")
            else:
                print(f"[WARNING] Background music file not found: {bg_music_path}")
        
        # Mix all audio tracks together
        print(f"[DIRECTOR] Mixing {len(audio_tracks)} audio tracks (voiceover, memes, music, etc.)")
        mixed_audio = CompositeAudioClip(audio_tracks)
        final_video = final_video.set_audio(mixed_audio)
        
        # Subtitles were already added to the composite above (to avoid nested composites)
        
        # Apply sound effects
        sfx_timeline = self.sfx_engine.map_sfx_to_events(timeline)
        final_video = self.sfx_engine.apply_sfx(final_video, sfx_timeline)
        
        # With sentence-level timing, no audio sync compensation needed!
        # The timestamps from voiceover generation are already perfectly accurate
        print("[DIRECTOR] Using precise sentence-level timing (no sync adjustment needed)")
        
        # Render final video
        print("[DIRECTOR] Rendering final video...")
        print("┌" + "─"*68 + "┐")
        print("│" + " "*22 + "ENCODING VIDEO" + " "*32 + "│")
        print("└" + "─"*68 + "┘")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        temp_audio_path = f"data/temp/{os.path.basename(output_path)}_temp_audio.m4a"
        
        try:
            # Use NVIDIA GPU hardware acceleration for much faster encoding
            # Explicitly target NVIDIA GPU (important for laptops with dual GPUs)
            print(f"\n[ENCODING] Starting NVENC GPU encoding...")
            print(f"[ENCODING] Codec: h264_nvenc")
            print(f"[ENCODING] Target GPU: 0 (NVIDIA RTX 5070 Ti)")
            print(f"[ENCODING] ⚠ If encoding pauses or is very slow:")
            print(f"[ENCODING]   - Close Chrome/Discord to free RAM")
            print(f"[ENCODING]   - Disable Windows Defender real-time scanning temporarily")
            print(f"[ENCODING]   - Check Task Manager → Disk (should be < 100%)")
            
            final_video.write_videofile(
                output_path,
                fps=30,
                codec="h264_nvenc",  # NVIDIA hardware encoder (was: libx264)
                audio_codec="aac",
                verbose=True,  # Enable progress bar
                logger='bar',  # Use progress bar logger
                temp_audiofile=temp_audio_path,
                remove_temp=False,  # Don't auto-remove to avoid Windows locking issues
                threads=4,  # Use 4 threads for frame processing (speeds up MoviePy bottleneck)
                write_logfile=False,  # Disable log file for slight speed boost
                audio_bufsize=2000,  # Reduce audio buffer to save memory
                bitrate="5000k",  # Explicit video bitrate (5 Mbps)
                # NVENC optimization parameters - explicitly target NVIDIA GPU
                ffmpeg_params=[
                    "-gpu", "0",      # CRITICAL: GPU 0 = NVIDIA RTX 5070 Ti on YOUR laptop
                    "-preset", "p1",  # p1=fastest (was p4) - MoviePy is the bottleneck, not GPU
                    "-rc:v", "vbr",   # Variable bitrate for better quality
                    "-cq:v", "23",    # Constant quality (lower=better, 23 is good balance)
                    "-b:v", "5M",     # Target bitrate 5 Mbps (good for 1080p)
                    "-maxrate:v", "8M",  # Max bitrate cap
                    "-bufsize:v", "10M",  # Buffer size
                    "-pix_fmt", "yuv420p",  # CRITICAL: Proper pixel format to avoid green tint
                    "-b:a", "192k"  # Audio bitrate for better quality
                ]
            )
            
            print(f"[ENCODING] ✓ Encoding complete!")
        finally:
            # Force garbage collection to free memory immediately
            import gc
            gc.collect()
            
            # Clean up all clips to release file handles
            clips_to_close = [
                mixed_audio,
                composite_audio_from_clips,
                voiceover,
                bg_music,
                getattr(final_video, "_sfx_composite_audio", None)
            ]
            sfx_clips = getattr(final_video, "_sfx_audio_clips", None)
            if sfx_clips:
                clips_to_close.extend(sfx_clips)

            for clip in clips_to_close:
                if clip is None:
                    continue
                try:
                    clip.close()
                except Exception:
                    pass

            try:
                final_video.close()
            except Exception:
                pass
            
            # Manually clean up temp audio with retries (Windows file locking workaround)
            if os.path.exists(temp_audio_path):
                for attempt in range(5):
                    try:
                        time.sleep(0.2)  # Give Windows time to release the file
                        os.remove(temp_audio_path)
                        print(f"[CLEANUP] Removed temp audio file")
                        break
                    except PermissionError:
                        if attempt == 4:
                            print(f"[WARNING] Could not remove temp audio file (will be cleaned up later): {temp_audio_path}")
                        continue
        
        print(f"[SUCCESS] Video saved: {output_path}")
        return output_path
    
    def _render_scene(self, scene, total_duration):
        """Render a single scene based on timeline"""
        scene_type = scene['type']
        start_time = scene['start_time']
        end_time = scene['end_time']
        duration = end_time - start_time
        
        print(f"\n[DIRECTOR] ===== Scene {scene['scene_number']}: {scene_type} =====")
        print(f"[DIRECTOR] Duration: {duration:.1f}s ({start_time:.1f}s - {end_time:.1f}s)")
        print(f"[DIRECTOR] Elements to render: {len(scene.get('elements', []))}")
        
        for elem in scene.get('elements', []):
            print(f"[DIRECTOR]   - {elem['type']}: {elem.get('keyword', elem.get('index', 'N/A'))}")
        
        if scene_type == 'gameplay_icons':
            result = self._create_gameplay_icons_scene(scene, duration)
        elif scene_type == 'data_graph':
            result = self._create_data_graph_scene(scene, duration)
        elif scene_type == 'reddit_evidence':
            result = self._create_reddit_evidence_scene(scene, duration)
        elif scene_type == 'youtube_evidence':
            result = self._create_youtube_evidence_scene(scene, duration)
        elif scene_type == 'mixed_evidence':
            result = self._create_mixed_evidence_scene(scene, duration)
        elif scene_type == 'text_statement':
            result = self._create_text_statement_scene(scene, duration)
        elif scene_type == 'scrolling_comments':
            result = self._create_scrolling_comments_scene(scene, duration)
        elif scene_type == 'split_comparison':
            result = self._create_split_comparison_scene(scene, duration)
        elif scene_type == 'spotlight':
            result = self._create_spotlight_scene(scene, duration)
        elif scene_type == 'broll':
            result = self._create_broll_scene(scene, duration)
        else:
            result = self._create_gameplay_only_scene(duration)
        
        if result:
            print(f"[DIRECTOR] Scene {scene['scene_number']} rendered successfully")
        else:
            print(f"[DIRECTOR] Scene {scene['scene_number']} rendering failed!")
        
        return result
    
    def _create_gameplay_icons_scene(self, scene, duration):
        """
        Scene Type 1: Gameplay background with multiple icons appearing
        """
        print(f"[DIRECTOR] Creating gameplay+icons scene...")
        
        # Background gameplay
        bg = self._get_background(duration)
        clips = [bg]
        icons_added = 0
        
        # Check if scene has elements
        if 'elements' not in scene or not scene['elements']:
            print("[DIRECTOR] No elements in gameplay scene, returning background only")
            return bg
        
        # Sort elements by timestamp to determine overlaps
        sorted_elements = sorted(scene['elements'], key=lambda e: e.get('timestamp', 0))
        
        # Get scene boundaries for proper staggering
        scene_start = scene.get('start_time', 0)
        scene_end = scene.get('end_time', scene_start + duration)
        
        # === PRESERVE ACCURATE TIMING - Only fix EXACT duplicates ===
        # Trust the timeline's timestamps - they match when words are spoken
        # Only adjust if 2+ elements are at the EXACT same time (within 0.15s)
        # This prevents icon spam while keeping timing accurate
        
        center_element_types = ['icon', 'text', 'meme', 'quote']
        
        # Group elements by similar timestamps (within 0.15s = effectively same time)
        time_groups = {}
        for element in sorted_elements:
            if element['type'] in center_element_types:
                elem_time = element.get('timestamp', scene_start)
                # Round to nearest 0.15s to find duplicates
                time_key = round(elem_time / 0.15) * 0.15
                if time_key not in time_groups:
                    time_groups[time_key] = []
                time_groups[time_key].append(element)
        
        # Only stagger if multiple elements at EXACT same time
        stagger_adjustments = 0
        for time_key, elements in time_groups.items():
            if len(elements) > 1:
                # Multiple elements at same time - apply minimal stagger (0.2s apart)
                print(f"[DIRECTOR] {len(elements)} elements at ~{time_key:.2f}s - applying minimal stagger")
                for i, element in enumerate(elements):
                    if i > 0:  # Keep first element at original time
                        new_time = time_key + (i * 0.2)
                        # Don't push beyond scene end
                        if new_time < scene_end - 0.3:
                            old_time = element.get('timestamp', scene_start)
                            element['timestamp'] = new_time
                            stagger_adjustments += 1
                            elem_kw = element.get('keyword', element.get('text', 'element'))
                            print(f"[DIRECTOR]   '{elem_kw}': {old_time:.2f}s -> {new_time:.2f}s")
        
        if stagger_adjustments > 0:
            print(f"[DIRECTOR] Applied {stagger_adjustments} minimal staggers for exact-time duplicates")
        
        # Re-sort after staggering
        sorted_elements = sorted(scene['elements'], key=lambda e: e.get('timestamp', 0))
        
        # Calculate duration for each element based on next element's timing
        # IMPORTANT: Icons, text, and memes all appear CENTER SCREEN now, so we need to prevent
        # ALL center elements from overlapping with each other (not just same type)
        element_durations = {}
        
        print(f"[DIRECTOR] Calculating element durations to prevent overlaps...")
        
        for i, element in enumerate(sorted_elements):
            element_type = element['type']
            element_time = element['timestamp']
            
            # Convert to relative time for duration calculation
            relative_time = element_time - scene_start
            
            # Find next CENTER element (icon, text, meme, or quote) that could overlap
            next_center_element = None
            for j in range(i + 1, len(sorted_elements)):
                next_elem = sorted_elements[j]
                # Check if next element is also a centered element (icon, text, meme, or quote)
                if next_elem['type'] in ['icon', 'text', 'meme', 'quote']:
                    next_center_element = next_elem
                    break
            
            if next_center_element:
                # Duration until next center element appears (use absolute timestamps for gap calc)
                time_until_next = next_center_element['timestamp'] - element_time
                # Add 0.3s overlap for smooth transition (fade out while next fades in)
                # but ensure minimum duration of 0.8s
                adjusted_duration = max(0.8, time_until_next + 0.3)
                
                elem_kw = element.get('keyword', element.get('text', 'element'))
                next_kw = next_center_element.get('keyword', next_center_element.get('text', 'element'))
                print(f"[DIRECTOR]   {element_type} '{elem_kw}' @ {relative_time:.1f}s -> duration {adjusted_duration:.1f}s (next: '{next_kw}' @ {next_center_element['timestamp'] - scene_start:.1f}s)")
            else:
                # No next center element - duration until scene end, min 1.5s, max 3.0s
                time_until_scene_end = scene_end - element_time
                adjusted_duration = max(1.5, min(3.0, time_until_scene_end))
                elem_kw = element.get('keyword', element.get('text', 'element'))
                print(f"[DIRECTOR]   {element_type} '{elem_kw}' @ {relative_time:.1f}s -> duration {adjusted_duration:.1f}s (last element, scene ends in {time_until_scene_end:.1f}s)")
            
            # SAFETY: Ensure duration doesn't exceed remaining scene time
            remaining_scene_time = scene_end - element_time
            if remaining_scene_time > 0:
                adjusted_duration = min(adjusted_duration, remaining_scene_time + 0.3)  # Allow small overflow for fades
            else:
                adjusted_duration = 1.0  # Fallback for edge cases
            
            element_durations[id(element)] = adjusted_duration
        
        # Add each element (icons, text, memes, and quotes) with calculated durations
        text_added = 0
        memes_added = 0
        quotes_added = 0
        for element in scene['elements']:
            # Force centered visuals for gameplay scenes
            if element.get('type') in ['icon', 'text', 'meme', 'quote']:
                element['position'] = 'center'
            if element['type'] == 'icon':
                icon_clip = self._create_icon_element(
                    element, duration, scene['start_time'],
                    override_duration=element_durations.get(id(element))
                )
                if icon_clip:
                    clips.append(icon_clip)
                    icons_added += 1
            elif element['type'] == 'text':
                text_clip = self._create_text_element(
                    element, duration, scene['start_time'],
                    override_duration=element_durations.get(id(element))
                )
                if text_clip:
                    clips.append(text_clip)
                    text_added += 1
            elif element['type'] == 'quote':
                quote_clip = self._create_quote_element(
                    element, duration, scene['start_time'],
                    override_duration=element_durations.get(id(element))
                )
                if quote_clip:
                    clips.append(quote_clip)
                    quotes_added += 1
            elif element['type'] == 'meme':
                meme_clip = self._create_meme_element(
                    element, duration, scene['start_time'],
                    override_duration=element_durations.get(id(element))
                )
                if meme_clip:
                    clips.append(meme_clip)
                    memes_added += 1
        
        print(f"[DIRECTOR] Added {icons_added} icons, {text_added} text, {quotes_added} quotes, and {memes_added} meme elements")
        
        return CompositeVideoClip(clips, size=(1920, 1080))
    
    def _create_data_graph_scene(self, scene, duration):
        """
        Scene Type 2: Graph visualization with black background
        """
        # Create solid black background for graph scenes
        bg = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=duration)
        clips = [bg]
        
        # Check if scene has elements
        if 'elements' not in scene or not scene['elements']:
            print("[DIRECTOR] No elements in graph scene, returning background only")
            return bg
        
        # Add graph elements ONLY (no icons/text in graph scenes)
        for element in scene['elements']:
            if element['type'] == 'graph':
                graph_clip = self._create_graph_element(element, duration, scene['start_time'])
                if graph_clip:
                    clips.append(graph_clip)
            else:
                print(f"[DIRECTOR] Skipping non-graph element in data_graph scene: {element.get('type')}")
        
        return CompositeVideoClip(clips, size=(1920, 1080))
    
    def _create_reddit_evidence_scene(self, scene, duration):
        """
        Scene Type 3: Reddit post on white background
        """
        # Create clean white background for Reddit scenes
        bg = ColorClip(size=(1920, 1080), color=(255, 255, 255), duration=duration)
        clips = [bg]
        
        # Check if scene has elements
        if 'elements' not in scene or not scene['elements']:
            print("[DIRECTOR] No elements in Reddit scene, returning background only")
            return bg
        
        # Add Reddit element first (background), then allow icon/text overlays
        for element in scene['elements']:
            if element['type'] == 'reddit':
                reddit_clip = self._create_reddit_element(element, duration, scene['start_time'])
                if reddit_clip:
                    clips.append(reddit_clip)
        
        for element in scene['elements']:
            if element.get('type') == 'icon':
                element['overlay'] = 'evidence'
                element['position'] = 'center'
                icon_clip = self._create_icon_element(element, duration, scene['start_time'])
                if icon_clip:
                    clips.append(icon_clip)
            elif element.get('type') == 'text':
                element['overlay'] = 'evidence'
                element['position'] = 'center'
                text_clip = self._create_text_element(element, duration, scene['start_time'])
                if text_clip:
                    clips.append(text_clip)
        
        return CompositeVideoClip(clips, size=(1920, 1080))

    def _create_youtube_evidence_scene(self, scene, duration):
        """
        YouTube video evidence card on dark background
        """
        print(f"[DIRECTOR] Creating YouTube evidence scene...")
        
        # Create YouTube dark-mode background
        bg = ColorClip(size=(1920, 1080), color=(24, 24, 24), duration=duration)
        clips = [bg]
        
        # Check if scene has elements
        if 'elements' not in scene or not scene['elements']:
            print("[DIRECTOR] No elements in YouTube scene, returning background only")
            return bg
        
        print(f"[DIRECTOR] Processing {len(scene['elements'])} YouTube scene elements...")
        
        # Add YouTube element first (background), then allow icon/text overlays
        for element in scene['elements']:
            print(f"[DIRECTOR]   Element type: {element['type']}")
            if element['type'] == 'youtube':
                youtube_clip = self._create_youtube_element(element, duration, scene['start_time'])
                if youtube_clip:
                    print(f"[DIRECTOR]   YouTube clip created successfully!")
                    clips.append(youtube_clip)
                else:
                    print(f"[DIRECTOR]   WARNING: YouTube clip creation failed!")
        
        for element in scene['elements']:
            if element.get('type') == 'icon':
                element['overlay'] = 'evidence'
                element['position'] = 'center'
                icon_clip = self._create_icon_element(element, duration, scene['start_time'])
                if icon_clip:
                    clips.append(icon_clip)
            elif element.get('type') == 'text':
                element['overlay'] = 'evidence'
                element['position'] = 'center'
                text_clip = self._create_text_element(element, duration, scene['start_time'])
                if text_clip:
                    clips.append(text_clip)
        
        print(f"[DIRECTOR] YouTube scene has {len(clips)} total clips (including background)")
        return CompositeVideoClip(clips, size=(1920, 1080))
    
    def _create_mixed_evidence_scene(self, scene, duration):
        """
        Scene Type 4: Gameplay background with graphs, Reddit posts, or YouTube cards overlaid
        Combines the best of all worlds - dynamic gameplay with evidence
        """
        print(f"[DIRECTOR] Creating mixed evidence scene (gameplay + graph/reddit/youtube)...")
        
        # Start with dimmed gameplay background (force gameplay for evidence scenes)
        bg = self._get_background(duration, opacity=0.3, force_gameplay=True)  # More dimmed for readability
        clips = [bg]
        
        # Check if scene has elements
        if 'elements' not in scene or not scene['elements']:
            print("[DIRECTOR] No elements in mixed scene, returning background only")
            return bg
        
        # Add all elements (graphs, reddit, youtube, icons, text)
        for element in scene['elements']:
            if element['type'] == 'graph':
                graph_clip = self._create_graph_element(element, duration, scene['start_time'])
                if graph_clip:
                    clips.append(graph_clip)
            elif element['type'] == 'reddit':
                reddit_clip = self._create_reddit_element(element, duration, scene['start_time'])
                if reddit_clip:
                    clips.append(reddit_clip)
            elif element['type'] == 'youtube':
                youtube_clip = self._create_youtube_element(element, duration, scene['start_time'])
                if youtube_clip:
                    clips.append(youtube_clip)
            elif element['type'] == 'icon':
                icon_clip = self._create_icon_element(element, duration, scene['start_time'])
                if icon_clip:
                    clips.append(icon_clip)
            elif element['type'] == 'text':
                text_clip = self._create_text_element(element, duration, scene['start_time'])
                if text_clip:
                    clips.append(text_clip)
        
        return CompositeVideoClip(clips, size=(1920, 1080))
    
    def _create_gameplay_only_scene(self, duration):
        """Simple gameplay background"""
        return self._get_background(duration, opacity=0.7)
    
    def _create_text_element(self, element, scene_duration, scene_start, override_duration=None):
        """Create an animated text overlay element (centered, icon-like)"""
        text_content = element.get('text', element.get('keyword', ''))
        # Use timestamp directly - sentence-level timing is already accurate!
        timestamp = element.get('timestamp', scene_start) - scene_start  # Relative to scene start
        animation = element.get('animation', 'fade_in')
        
        # Fix invalid timestamps - salvage instead of skipping
        if timestamp < 0:
            timestamp = 0.1
        if timestamp >= scene_duration:
            if scene_duration > 1.5:
                timestamp = max(0, scene_duration - 1.5)
            else:
                return None
        
        try:
            overlay = element.get('overlay') == 'evidence'
            position = element.get('position', 'center')

            print(f"[DIRECTOR] Creating text element (centered): '{text_content}' at {timestamp:.1f}s")
            
            # Text styling - BIG, BOLD, CENTERED (like icons)
            # Make it stand out from regular subtitles at bottom
            fontsize = 60 if overlay else 100
            max_width = 900 if overlay else 1600
            text_clip = TextClip(
                text_content,
                fontsize=fontsize,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=4,  # Thicker stroke for emphasis
                method='caption',
                size=(max_width, None)  # Narrower than full width for better centering
            )
            
            # Duration: Use override if provided, otherwise default
            text_display_duration = override_duration if override_duration else 2.5
            
            # Make sure we don't exceed scene duration
            max_duration = scene_duration - timestamp
            if max_duration <= 0:
                print(f"[DIRECTOR] Text duration invalid for '{text_content}'")
                return None
            
            text_duration = min(text_display_duration, max_duration)
            
            text_clip = text_clip.set_duration(text_duration)
            text_clip = text_clip.set_start(timestamp)
            
            # Apply icon-like animations (same as icons for consistency)
            if animation == 'zoom_in':
                # Smooth scale animation with breathing (same as icons)
                def smooth_scale(t):
                    if t < 0.5:
                        # Ease out cubic for smooth start
                        progress = t / 0.5
                        return 0.3 + (1 - (1 - progress) ** 3) * 0.7  # 0.3 -> 1.0
                    else:
                        # Gentle breathing effect (same as icons)
                        return 1.0 + 0.02 * np.sin((t - 0.5) * 3)
                text_clip = text_clip.resize(smooth_scale)
                text_clip = text_clip.set_position('center')
            elif animation == 'slide_up':
                # Slide up from bottom with zoom
                def slide_position(t):
                    if t < 0.5:
                        progress = t / 0.5
                        y_offset = 200 * (1 - progress)
                        return ('center', 540 + y_offset)  # 540 is vertical center of 1080p
                    else:
                        return 'center'
                text_clip = text_clip.set_position(slide_position)
            else:
                # Default: centered with simple scale-in
                def simple_scale(t):
                    if t < 0.3:
                        return 0.3 + (t / 0.3) * 0.7  # 0.3 -> 1.0
                    return 1.0
                text_clip = text_clip.resize(simple_scale)
                # Position handled below
            
            # Positioning (only override if not centered)
            if position == 'top_right':
                x = max(40, 1920 - text_clip.w - 40)
                text_clip = text_clip.set_position((x, 40))
            elif position == 'top_left':
                text_clip = text_clip.set_position((40, 40))
            elif position == 'bottom_right':
                x = max(40, 1920 - text_clip.w - 40)
                text_clip = text_clip.set_position((x, 1080 - text_clip.h - 40))
            elif position == 'bottom_left':
                text_clip = text_clip.set_position((40, 1080 - text_clip.h - 40))
            elif position != 'center':
                text_clip = text_clip.set_position(position)

            # Stronger fade in/out (like icons)
            text_clip = text_clip.crossfadein(0.4)
            text_clip = text_clip.crossfadeout(0.3)
            
            print(f"[DIRECTOR] Text created successfully: '{text_content}'")
            return text_clip
            
        except Exception as e:
            print(f"[WARNING] Failed to create text element '{text_content}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_quote_element(self, element, scene_duration, scene_start, override_duration=None):
        """Create a quote element - large animated text in center (for quoted phrases)"""
        quote_text = element.get('text', element.get('keyword', ''))
        # Use timestamp directly - sentence-level timing is already accurate!
        timestamp = element.get('timestamp', scene_start) - scene_start  # Relative to scene start
        animation = element.get('animation', 'zoom_in')
        
        # Fix invalid timestamps - salvage instead of skipping
        if timestamp < 0:
            timestamp = 0.1
        if timestamp >= scene_duration:
            if scene_duration > 1.5:
                timestamp = max(0, scene_duration - 1.5)
            else:
                return None
        
        try:
            print(f"[DIRECTOR] Creating quote element (center): \"{quote_text}\" at {timestamp:.1f}s")
            
            # Quote styling - LARGE, BOLD, CENTERED with quotation marks for emphasis
            # Similar to emphasized subtitles but stands out even more
            display_text = f'"{quote_text}"'  # Add quotation marks
            
            text_clip = TextClip(
                display_text,
                fontsize=90,  # Large and prominent
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=5,  # Extra thick stroke
                method='caption',
                size=(1500, None)  # Wide enough for quotes
            )
            
            # Duration: Use override if provided, otherwise default
            quote_display_duration = override_duration if override_duration else 2.5
            
            # Make sure we don't exceed scene duration
            max_duration = scene_duration - timestamp
            if max_duration <= 0:
                print(f"[DIRECTOR] Quote duration invalid for \"{quote_text}\"")
                return None
            
            quote_duration = min(quote_display_duration, max_duration)
            
            text_clip = text_clip.set_duration(quote_duration)
            text_clip = text_clip.set_start(timestamp)
            
            # Apply dramatic icon-like animations
            if animation == 'zoom_in' or animation == 'pop':
                # Zoom in from small to large with breathing effect (same as emphasized words)
                def smooth_scale(t):
                    if t < 0.4:
                        # Zoom in from 50% to 100%
                        progress = t / 0.4
                        return 0.5 + (1 - (1 - progress) ** 3) * 0.5  # Ease out cubic
                    else:
                        # Subtle breathing effect
                        return 1.0 + 0.02 * np.sin((t - 0.4) * 3)
                text_clip = text_clip.resize(smooth_scale)
            elif animation == 'bounce':
                # Bounce in effect
                def bounce_scale(t):
                    if t < 0.5:
                        progress = t / 0.5
                        # Overshoot slightly then settle
                        return 0.3 + progress * 1.2 if progress < 0.8 else 1.0 + (1.0 - progress) * 0.2
                    else:
                        return 1.0 + 0.02 * np.sin((t - 0.5) * 3)
                text_clip = text_clip.resize(bounce_scale)
            else:
                # Default: simple zoom in
                def simple_scale(t):
                    if t < 0.4:
                        return 0.5 + (t / 0.4) * 0.5  # 0.5 -> 1.0
                    return 1.0
                text_clip = text_clip.resize(simple_scale)
            
            # Always center quotes
            text_clip = text_clip.set_position('center')
            
            # Dramatic fades (same as emphasized words)
            text_clip = text_clip.crossfadein(0.3)
            text_clip = text_clip.crossfadeout(0.2)
            
            print(f"[DIRECTOR] Quote created successfully: \"{quote_text}\"")
            return text_clip
            
        except Exception as e:
            print(f"[WARNING] Failed to create quote element \"{quote_text}\": {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_icon_element(self, element, scene_duration, scene_start, override_duration=None, override_size=None):
        """Create an animated icon element (or text fallback if icon unavailable)"""
        # Robust keyword extraction: look for 'keyword' then 'text'
        keyword = element.get('keyword', element.get('text', ''))
        
        # Check if this should actually be handled by another creator based on 'type'
        # BUT only if we were called generically. If we need a quick fix, keyword is enough.
        
        # Use timestamp directly - sentence-level timing is already accurate!
        raw_timestamp = element.get('timestamp', scene_start)
        timestamp = raw_timestamp - scene_start  # Relative to scene start
        animation = element.get('animation', 'scale_in')
        
        # Check timing FIRST - if invalid, try to SALVAGE instead of skipping
        max_duration = scene_duration - timestamp
        if max_duration <= 0:
            # Element timestamp is beyond scene - try to place it near the end instead
            if scene_duration > 1.5:
                # Place element 1 second before scene end
                timestamp = max(0, scene_duration - 1.5)
                max_duration = scene_duration - timestamp
                print(f"[DIRECTOR] WARNING: Element '{keyword}' timestamp beyond scene - moved to {timestamp:.1f}s")
            else:
                print(f"[DIRECTOR] WARNING: Element '{keyword}' timestamp beyond scene duration, skipping")
                return None
        
        # Also check if timestamp is negative (before scene start)
        if timestamp < 0:
            timestamp = 0.1  # Place at scene start
            max_duration = scene_duration - timestamp
            print(f"[DIRECTOR] WARNING: Element '{keyword}' had negative timestamp - moved to 0.1s")
        
        # Try to find icon
        icon_path = self._find_icon_asset(keyword)
        use_text_fallback = False
        fallback_reason = ""
        
        if not icon_path:
            use_text_fallback = True
            fallback_reason = "icon not found"
        elif os.path.getsize(icon_path) < 10000:
            use_text_fallback = True
            fallback_reason = "icon too small (placeholder)"
        
        # Use text fallback if icon unavailable or invalid
        if use_text_fallback:
            print(f"[DIRECTOR] Icon '{keyword}' - {fallback_reason}, using TEXT FALLBACK")
            fallback_element = {
                'text': keyword,
                'timestamp': element['timestamp'],
                'animation': 'zoom_in'
            }
            return self._create_text_element(fallback_element, scene_duration, scene_start, override_duration)
        
        try:
            # Calculate actual display duration
            icon_display_duration = override_duration if override_duration else 2.5
            print(f"[DIRECTOR] Creating icon element: {keyword} at {timestamp:.1f}s (duration: {icon_display_duration:.1f}s)")
            
            # Load icon
            icon = ImageClip(icon_path)  # Each icon visible for 2.5 seconds
            
            # Recalculate max_duration in case scene changed
            max_duration = scene_duration - timestamp
            if max_duration <= 0:
                print(f"[DIRECTOR] Icon duration invalid for {keyword}, using text fallback")
                fallback_element = {
                    'text': keyword,
                    'timestamp': element['timestamp'],
                    'animation': 'zoom_in'
                }
                return self._create_text_element(fallback_element, scene_duration, scene_start, override_duration)
            
            icon_duration = min(icon_display_duration, max_duration)
            
            icon = icon.set_duration(icon_duration)
            icon = icon.set_start(timestamp)
            
            # Apply smooth, simple animation - just one style for consistency
            # Simple scale and fade in
            overlay = element.get('overlay') == 'evidence'
            if overlay and not override_size:
                icon_height = 260  # Smaller overlay on evidence scenes
            else:
                icon_height = override_size if override_size else 450
            icon = icon.resize(height=icon_height)  # Consistent size
            
            # Smooth scale from small to full
            def smooth_scale(t):
                if t < 0.5:
                    # Ease out cubic for smooth start
                    progress = t / 0.5
                    return 0.3 + (1 - (1 - progress) ** 3) * 0.7  # 0.3 -> 1.0
                else:
                    # Gentle breathing effect
                    return 1.0 + 0.02 * np.sin((t - 0.5) * 3)
            
            icon = icon.resize(smooth_scale)
            icon = icon.crossfadein(0.4)  # Smooth fade in
            icon = icon.crossfadeout(0.3)  # Smooth fade out at the end

            # Positioning
            position = element.get('position', 'center')
            if position == 'top_right':
                x = max(40, 1920 - icon.w - 40)
                icon = icon.set_position((x, 40))
            elif position == 'top_left':
                icon = icon.set_position((40, 40))
            elif position == 'bottom_right':
                x = max(40, 1920 - icon.w - 40)
                icon = icon.set_position((x, 1080 - icon.h - 40))
            elif position == 'bottom_left':
                icon = icon.set_position((40, 1080 - icon.h - 40))
            else:
                icon = icon.set_position('center')
            
            print(f"[DIRECTOR] Icon created successfully: {keyword}")
            return icon
            
        except Exception as e:
            # ALWAYS return text fallback on exception - never leave user with no visual!
            print(f"[DIRECTOR] ERROR creating icon '{keyword}': {e} - using TEXT FALLBACK")
            import traceback
            traceback.print_exc()
            fallback_element = {
                'text': keyword,
                'timestamp': element['timestamp'],
                'animation': 'zoom_in',
                'overlay': element.get('overlay'),
                'position': element.get('position')
            }
            return self._create_text_element(fallback_element, scene_duration, scene_start, override_duration)
    
    def _create_meme_element(self, element, scene_duration, scene_start, override_duration=None):
        """Create a short meme video clip element"""
        keyword = element.get('keyword', 'random')
        timestamp = element.get('timestamp', scene_start) - scene_start  # Relative to scene start
        
        # Fix invalid timestamps - salvage instead of skipping
        if timestamp < 0:
            timestamp = 0.1
        
        # Check timing validity
        max_duration = scene_duration - timestamp
        if max_duration <= 0:
            if scene_duration > 2.0:
                timestamp = max(0, scene_duration - 2.0)
                max_duration = scene_duration - timestamp
                print(f"[DIRECTOR] WARNING: Meme '{keyword}' timestamp beyond scene - moved to {timestamp:.1f}s")
            else:
                print(f"[DIRECTOR] WARNING: Meme '{keyword}' timestamp beyond scene duration, skipping")
                return None
        
        # Find meme video file
        meme_path = self._find_meme_asset(keyword)
        if not meme_path:
            print(f"[DIRECTOR] No meme found for '{keyword}'")
            return None
        
        try:
            # Calculate display duration - memes should be prominent and last longer
            meme_display_duration = override_duration if override_duration else 3.5  # Default 3.5s for memes (increased from 2.0s)
            meme_display_duration = max(2.5, meme_display_duration)  # Minimum 2.5s (increased from 1.5s)
            # Hard limit: never exceed 5 seconds
            meme_display_duration = min(meme_display_duration, 5.0)
            print(f"[DIRECTOR] Creating meme element: {os.path.basename(meme_path)} at {timestamp:.1f}s (duration: {meme_display_duration:.1f}s)")
            
            # Load meme video WITH AUDIO
            meme_clip = VideoFileClip(meme_path, audio=True)
            
            # Ensure meme isn't too long - trim to max duration
            if meme_clip.duration > meme_display_duration:
                print(f"[DIRECTOR] Trimming meme from {meme_clip.duration:.1f}s to {meme_display_duration:.1f}s")
                meme_clip = meme_clip.subclip(0, meme_display_duration)
            
            # Set duration and timing
            meme_duration = min(meme_display_duration, max_duration, meme_clip.duration)
            meme_clip = meme_clip.set_duration(meme_duration)
            meme_clip = meme_clip.set_start(timestamp)
            
            # Resize meme to be LARGE but not overly zoomed
            # Target: 95% of screen height (1026px) for portrait, or 85% of width (1632px) for landscape
            # Use MoviePy's aspect-preserving resize to avoid cropping
            
            original_aspect = meme_clip.w / meme_clip.h
            
            # Determine target scale factor based on aspect ratio - INCREASED sizes
            # We'll resize FIRST, then apply animations as scale multipliers
            if original_aspect > 1.5:  # Wide landscape (16:9, etc.)
                # Base on width - use 85% of screen width
                target_scale = 1632 / meme_clip.w  # 85% of 1920px
            elif original_aspect < 0.75:  # Portrait (9:16, etc.)
                # Base on height - use 95% of screen height
                target_scale = 1026 / meme_clip.h  # 95% of 1080px
            else:  # Square-ish (0.75 to 1.5 ratio)
                # Use balanced approach - target 1040px height
                target_scale = 1040 / meme_clip.h
            
            # Apply base resize ONCE using scale factor (preserves aspect ratio, no cropping)
            meme_clip = meme_clip.resize(target_scale)
            
            print(f"[DIRECTOR] Meme sizing: original {int(meme_clip.w / target_scale)}x{int(meme_clip.h / target_scale)} (aspect {original_aspect:.2f}) -> resized to {meme_clip.w}x{meme_clip.h}")
            
            # Now apply animation as a MULTIPLIER on the already-resized clip
            def animated_scale(t):
                if t < 0.25:
                    # Very subtle pop in from 95% to 100% over 0.25s
                    progress = t / 0.25
                    return 0.95 + (1 - (1 - progress) ** 3) * 0.05  # Ease out cubic: 0.95 -> 1.0
                else:
                    # No extra breathing to avoid zoomy feel
                    return 1.0
            
            # Apply scale animation (multiplier, not absolute size)
            meme_clip = meme_clip.resize(animated_scale)
            
            # Position at center
            meme_clip = meme_clip.set_position('center')
            
            # Smooth fades
            meme_clip = meme_clip.crossfadein(0.4).crossfadeout(0.3)
            
            # Reduce meme audio to 70% so it doesn't overpower voiceover
            if meme_clip.audio:
                meme_clip = meme_clip.volumex(0.7)
            
            print(f"[DIRECTOR] Meme created (centered, {meme_clip.w}x{meme_clip.h}, WITH AUDIO): {os.path.basename(meme_path)}")
            return meme_clip
            
        except Exception as e:
            print(f"[DIRECTOR] ERROR creating meme '{keyword}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_graph_element(self, element, scene_duration, scene_start):
        """Create graph element from Manim video"""
        graph_index = element.get('index', 0)
        # Use timestamp directly - sentence-level timing is already accurate!
        timestamp = element['timestamp'] - scene_start
        
        # Find graph video (simplified - would need to track graph paths from generator)
        graph_path = self._find_graph_video(graph_index)
        if not graph_path:
            return None
        
        try:
            graph = VideoFileClip(graph_path)
            
            # Fix MoviePy last frame issue by trimming slightly before end
            if graph.duration > 0.1:
                graph = graph.subclip(0, max(0.1, graph.duration - 0.05))
            
            # Trim or loop to match scene duration
            needed_duration = scene_duration - timestamp
            if graph.duration < needed_duration:
                # Loop or extend last frame
                graph = graph.fx(vfx.freeze, t='end', freeze_duration=needed_duration - graph.duration)
            else:
                graph = graph.subclip(0, min(graph.duration, needed_duration))
            
            graph = graph.set_start(timestamp)
            graph = graph.set_position("center")
            
            # Make graph background transparent if possible
            try:
                graph = graph.fx(vfx.mask_color, color=[0, 0, 0], thr=10, s=5)
            except:
                pass
            
            print(f"[DIRECTOR] Graph loaded successfully, duration: {graph.duration:.1f}s")
            return graph
            
        except Exception as e:
            print(f"[WARNING] Failed to load graph: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_reddit_element(self, element, scene_duration, scene_start):
        """Create Reddit post element with pan-down animation for readability"""
        post_index = element.get('post_index', 0)
        # Use timestamp directly - sentence-level timing is already accurate!
        timestamp = element['timestamp'] - scene_start
        
        # Find Reddit screenshot using metadata if available
        reddit_path = self._find_reddit_screenshot_by_metadata(post_index)
        if not reddit_path:
            print(f"[DIRECTOR] Warning: Could not find Reddit screenshot for index {post_index}")
            return None
        
        print(f"[DIRECTOR] Using Reddit screenshot: {os.path.basename(reddit_path)}")
        
        try:
            reddit = ImageClip(reddit_path)
            
            # Make it bigger for readability (1200px width instead of 900)
            reddit = reddit.resize(width=1200)
            
            duration = scene_duration - timestamp
            if duration <= 0:
                return None
            
            reddit = reddit.set_duration(duration)
            reddit = reddit.set_start(timestamp)
            
            # Get image dimensions after resize
            img_height = reddit.h
            
            # Slow slide-up animation: start at bottom, move up to reveal title and content
            def pan_up(t):
                # Calculate start and end positions
                # Start: Bottom of post visible
                start_y = 1080 - 200  # Start with bottom ~200px visible
                # End: Title area visible (top of post)
                end_y = 200  # End with top of post near top of screen
                
                # Smooth slide up over entire duration with ease-out
                if duration > 0:
                    progress = min(1.0, t / duration)
                    # Ease out cubic for smooth deceleration
                    eased_progress = 1 - (1 - progress) ** 3
                    y_pos = start_y - (start_y - end_y) * eased_progress
                else:
                    y_pos = start_y
                
                return ("center", int(y_pos))
            
            reddit = reddit.set_position(pan_up)
            reddit = reddit.crossfadein(0.5)
            
            return reddit
            
        except Exception as e:
            print(f"[WARNING] Failed to create Reddit element: {e}")
            return None

    def _create_youtube_element(self, element, scene_duration, scene_start):
        """Create YouTube video evidence card element with drop shadow and centered zoom"""
        # Robust index extraction: look for 'youtube_index' then 'index'
        youtube_index = element.get('youtube_index', element.get('index', 0))
        timestamp = element['timestamp'] - scene_start
        
        # Find YouTube card using metadata if available
        youtube_path = self._find_youtube_card_by_metadata(youtube_index)
        if not youtube_path:
            print(f"[DIRECTOR] Warning: Could not find YouTube card for index {youtube_index}")
            return None
        
        print(f"[DIRECTOR] Using YouTube card: {os.path.basename(youtube_path)}")
        
        try:
            from PIL import Image, ImageFilter, ImageDraw
            import numpy as np
            
            # Load and add drop shadow to the card
            pil_img = Image.open(youtube_path).convert('RGBA')
            
            # Resize to target width first
            target_width = 1100
            aspect = pil_img.height / pil_img.width
            target_height = int(target_width * aspect)
            pil_img = pil_img.resize((target_width, target_height), Image.LANCZOS)
            
            # Create shadow
            shadow_offset = 20
            shadow_blur = 30
            shadow_opacity = 150
            
            # Create a larger canvas for shadow
            canvas_width = target_width + shadow_blur * 2 + shadow_offset
            canvas_height = target_height + shadow_blur * 2 + shadow_offset
            
            # Create shadow layer
            shadow = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
            shadow_shape = Image.new('RGBA', (target_width, target_height), (0, 0, 0, shadow_opacity))
            shadow.paste(shadow_shape, (shadow_blur + shadow_offset, shadow_blur + shadow_offset))
            shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur))
            
            # Composite: shadow + card
            final_img = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 0))
            final_img = Image.alpha_composite(final_img, shadow)
            final_img.paste(pil_img, (shadow_blur, shadow_blur), pil_img)
            
            # Convert to numpy array for MoviePy
            img_array = np.array(final_img)
            
            youtube_card = ImageClip(img_array, ismask=False)
            
            duration = scene_duration - timestamp
            if duration <= 0:
                return None
            
            youtube_card = youtube_card.set_duration(duration)
            youtube_card = youtube_card.set_start(timestamp)
            
            # Store card dimensions for centered animation
            card_w, card_h = canvas_width, canvas_height
            screen_w, screen_h = 1920, 1080
            
            # Centered pop-in animation (scale from center, not top-left)
            def make_frame_position(t):
                if t < 0.4:
                    progress = t / 0.4
                    # Ease out cubic
                    scale = 0.85 + (1 - (1 - progress) ** 3) * 0.15
                else:
                    scale = 1.0
                
                # Calculate centered position based on current scale
                scaled_w = card_w * scale
                scaled_h = card_h * scale
                x = (screen_w - scaled_w) / 2
                y = (screen_h - scaled_h) / 2
                return (x, y)
            
            def pop_in_scale(t):
                if t < 0.4:
                    progress = t / 0.4
                    scale = 0.85 + (1 - (1 - progress) ** 3) * 0.15
                    return scale
                return 1.0
            
            youtube_card = youtube_card.resize(pop_in_scale)
            youtube_card = youtube_card.set_position(make_frame_position)
            youtube_card = youtube_card.crossfadein(0.3)
            
            return youtube_card
            
        except Exception as e:
            print(f"[WARNING] Failed to create YouTube element: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_text_statement_scene(self, scene, duration):
        """
        Bold text statement on black background with glow effect
        Text appears word by word for dramatic effect
        
        IMPORTANT: Only use short statement_text (max 8 words), NOT the full script_text!
        """
        print(f"[DIRECTOR] Creating text statement scene with word-by-word animation...")
        
        # Get statement text - prefer statement_text, NOT script_text (which can be very long)
        statement_text = scene.get('statement_text', '')
        
        # If no statement_text, extract a SHORT phrase from script_text (max 8 words)
        if not statement_text:
            script_text = scene.get('script_text', 'TEXT HERE')
            # Take only first sentence or max 8 words
            if '.' in script_text:
                statement_text = script_text.split('.')[0].strip()
            else:
                statement_text = script_text
            
            # Limit to 8 words max to avoid repetition/crowding
            words_list = statement_text.split()
            if len(words_list) > 8:
                statement_text = ' '.join(words_list[:8]) + '...'
        
        print(f"[DIRECTOR] Statement text: '{statement_text[:50]}...' ({len(statement_text.split())} words)")
        
        # Create solid black background
        bg = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=duration)
        
        # Split text into words for timing calculation
        words = statement_text.split()
        
        # Limit to max 10 words to prevent the scene from being too long/repetitive
        if len(words) > 10:
            words = words[:10]
            print(f"[DIRECTOR] WARNING: Text too long, truncating to 10 words")
        
        if not words:
            return bg
        
        try:
            # Calculate timing - ensure each word has at least 0.15s
            available_time = duration - 0.8  # Reserve time for start and end
            time_per_word = max(0.15, min(0.25, available_time / len(words)))
            start_delay = 0.3
            
            # Create clips list
            clips = [bg]
            
            # Track word appearance times for click sound effects
            word_click_times = []
            
            # Create SINGLE final text clip (not progressive reveal for long texts)
            # Progressive reveal for ALL statements as requested by user
            if True: # Always use word-by-word reveal
                # Progressive reveal for statements
                for i, word in enumerate(words):
                    current_text = " ".join(words[:i+1])
                    clip_start = start_delay + (i * time_per_word)
                    
                    # Store absolute timestamp for click sound (scene start + relative time)
                    scene_start_time = scene.get('start_time', 0)
                    word_click_times.append(scene_start_time + clip_start)
                    
                    if i == len(words) - 1:
                        clip_end = duration - 0.2
                    else:
                        clip_end = start_delay + ((i + 1) * time_per_word)
                    
                    clip_duration = clip_end - clip_start
                    if clip_duration <= 0:
                        continue
                    
                    text_clip = TextClip(
                        current_text,
                        fontsize=120,
                        color='white',
                        font='Arial-Bold',
                        stroke_color='white',
                        stroke_width=8,
                        method='caption',
                        size=(1600, None),
                        align='center'
                    )
                    
                    text_clip = text_clip.set_duration(clip_duration)
                    text_clip = text_clip.set_start(clip_start)
                    text_clip = text_clip.set_position('center')
                    
                    if i == 0:
                        text_clip = text_clip.fadein(0.2)
                    if i == len(words) - 1:
                        text_clip = text_clip.fadeout(0.3)
                    
                    clips.append(text_clip)
                
                # Store click times in scene for SFX engine to use
                if word_click_times:
                    if 'word_click_times' not in scene:
                        scene['word_click_times'] = []
                    scene['word_click_times'].extend(word_click_times)
                    print(f"[DIRECTOR] Added {len(word_click_times)} click sound cues for word-by-word animation")
            else:
                # For longer text (6+ words), just show the full text with zoom animation
                # This avoids the repetitive word-by-word effect
                full_text = " ".join(words)
                
                text_clip = TextClip(
                    full_text,
                    fontsize=100,  # Slightly smaller for longer text
                    color='white',
                    font='Arial-Bold',
                    stroke_color='white',
                    stroke_width=6,
                    method='caption',
                    size=(1600, None),
                    align='center'
                )
                
                text_clip = text_clip.set_duration(duration - 0.5)
                text_clip = text_clip.set_start(0.3)
                text_clip = text_clip.set_position('center')
                text_clip = text_clip.crossfadein(0.4).crossfadeout(0.3)
                
                clips.append(text_clip)
                print(f"[DIRECTOR] Using single-reveal for {len(words)}-word statement")
            
            # === IMPORTANT: Do NOT render icons/elements on the OPENING TITLE CARD (scene 1) ===
            # The opening title card should be clean, just the text statement
            # Only render elements on later text_statement scenes (scene 2+)
            scene_number = scene.get('scene_number', 1)
            if scene_number > 1:
                # Add support for icons and text elements on non-title text statements
                for element in scene.get('elements', []):
                    etype = element.get('type', 'icon')
                    clip = None
                    
                    if etype == 'icon':
                        clip = self._create_icon_element(element, duration, scene['start_time'])
                    elif etype == 'text':
                        clip = self._create_text_element(element, duration, scene['start_time'])
                    elif etype == 'meme':
                        clip = self._create_meme_element(element, duration, scene['start_time'])
                    elif etype == 'quote':
                        clip = self._create_quote_element(element, duration, scene['start_time'])
                    
                    if clip:
                        clips.append(clip)
            else:
                print(f"[DIRECTOR] Scene 1 (title card) - skipping {len(scene.get('elements', []))} elements to keep it clean")
            
            print(f"[DIRECTOR] Created text statement with {len(words)} words")
            
            return CompositeVideoClip(clips, size=(1920, 1080))
            
        except Exception as e:
            print(f"[WARNING] Could not create animated text: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: simple text
            text_clip = TextClip(
                statement_text,
                fontsize=120,
                color='white',
                font='Arial-Bold',
                stroke_color='white',
                stroke_width=8,
                method='caption',
                size=(1600, None),
                align='center'
            )
            
            text_clip = text_clip.set_duration(duration)
            text_clip = text_clip.set_position('center')
            text_clip = text_clip.crossfadein(0.3).crossfadeout(0.3)
            
            return CompositeVideoClip([bg, text_clip], size=(1920, 1080))
    
    def _create_scrolling_comments_scene(self, scene, duration):
        """
        NEW: Scrolling Reddit comments feed
        Shows multiple community reactions
        """
        print(f"[DIRECTOR] Creating scrolling comments scene...")
        
        # Get comments list from scene
        comments = scene.get('comments', [])
        
        if not comments:
            # Fallback to text if no comments provided
            comments = [
                scene.get('script_text', 'No comments available')
            ]
        
        # Create white background
        bg = ColorClip(size=(1920, 1080), color=(255, 255, 255), duration=duration)
        clips = [bg]
        
        # Create scrolling text
        comments_text = "\n\n".join([
            f"💬 {comment}" for comment in comments
        ])
        
        # Create a tall text clip that will scroll
        text_clip = TextClip(
            comments_text,
            fontsize=60,
            color='black',
            font='Arial',
            method='caption',
            size=(1600, None),  # Allow wrapping, height auto
            align='west'
        )
        
        text_clip = text_clip.set_duration(duration)
        
        # Scroll animation: start below screen, end above screen
        text_height = text_clip.h
        screen_height = 1080
        
        def scroll_position(t):
            # Start at bottom, scroll up
            progress = t / duration
            y_pos = screen_height - (progress * (text_height + screen_height))
            return ('center', y_pos)
        
        text_clip = text_clip.set_position(scroll_position)
        clips.append(text_clip)
        
        # === NEW: Add support for icons and text elements even in scrolling comments ===
        for element in scene.get('elements', []):
            etype = element.get('type', 'icon')
            clip = None
            
            if etype == 'icon':
                clip = self._create_icon_element(element, duration, scene['start_time'])
            elif etype == 'text':
                clip = self._create_text_element(element, duration, scene['start_time'])
            elif etype == 'meme':
                clip = self._create_meme_element(element, duration, scene['start_time'])
            elif etype == 'quote':
                clip = self._create_quote_element(element, duration, scene['start_time'])
            
            if clip:
                clips.append(clip)
        
        return CompositeVideoClip(clips, size=(1920, 1080))
    
    def _create_broll_scene(self, scene, duration):
        """
        NEW: B-roll footage with Ken Burns panning effect
        Uses images with slow pan/zoom for cinematic look
        """
        print(f"[DIRECTOR] Creating b-roll scene...")
        
        # Get b-roll image path from scene
        broll_path = scene.get('broll_path')
        
        if not broll_path or not os.path.exists(broll_path):
            print(f"[WARNING] B-roll image not found: {broll_path}")
            # Fallback to gameplay
            return self._get_background(duration)
        
        try:
            # Load image
            img_clip = ImageClip(broll_path)
            img_clip = img_clip.set_duration(duration)
            
            # First, resize to COVER the entire frame (no black bars)
            # Calculate scale to ensure image fills 1920x1080
            img_w, img_h = img_clip.size
            scale_w = 1920 / img_w
            scale_h = 1080 / img_h
            # Use the larger scale to ensure full coverage
            base_scale = max(scale_w, scale_h)
            
            # Ken Burns effect: 5 different animation styles for variety
            # Seed random with current time + broll path to ensure uniqueness
            random.seed(time.time() + hash(broll_path))
            animation_style = random.randint(1, 5)
            
            print(f"[DIRECTOR] Using Ken Burns style {animation_style} for this b-roll")
            
            if animation_style == 1:
                # ZOOM IN (moderate)
                def zoom_effect(t):
                    progress = t / duration
                    # Start at base_scale * 1.1, zoom to base_scale * 1.4
                    scale = base_scale * (1.1 + (progress * 0.3))
                    return scale
                
                img_clip = img_clip.resize(zoom_effect)
                img_clip = img_clip.set_position('center')
            
            elif animation_style == 2:
                # ZOOM OUT (start wide, end normal)
                def zoom_effect(t):
                    progress = t / duration
                    # Start at base_scale * 1.5, zoom out to base_scale * 1.15
                    scale = base_scale * (1.5 - (progress * 0.35))
                    return scale
                
                img_clip = img_clip.resize(zoom_effect)
                img_clip = img_clip.set_position('center')
            
            elif animation_style == 3:
                # DRAMATIC ZOOM IN
                def zoom_effect(t):
                    progress = t / duration
                    # Start at base_scale * 1.0, zoom to base_scale * 1.6
                    scale = base_scale * (1.0 + (progress * 0.6))
                    return scale
                
                img_clip = img_clip.resize(zoom_effect)
                img_clip = img_clip.set_position('center')
            
            elif animation_style == 4:
                # SLOW ZOOM OUT (very wide start)
                def zoom_effect(t):
                    progress = t / duration
                    # Start at base_scale * 1.6, zoom out to base_scale * 1.2
                    scale = base_scale * (1.6 - (progress * 0.4))
                    return scale
                
                img_clip = img_clip.resize(zoom_effect)
                img_clip = img_clip.set_position('center')
            
            else:  # style 5
                # SUBTLE ZOOM IN
                def zoom_effect(t):
                    progress = t / duration
                    # Start at base_scale * 1.15, zoom to base_scale * 1.35
                    scale = base_scale * (1.15 + (progress * 0.2))
                    return scale
                
                img_clip = img_clip.resize(zoom_effect)
                img_clip = img_clip.set_position('center')
            
            # Add subtle fade in/out
            img_clip = img_clip.crossfadein(0.5).crossfadeout(0.5)
            
            clips = [img_clip]
            
            # === NEW: Add support for icons and text elements even in b-roll ===
            for element in scene.get('elements', []):
                etype = element.get('type', 'icon')
                clip = None
                
                if etype == 'icon':
                    clip = self._create_icon_element(element, duration, scene['start_time'])
                elif etype == 'text':
                    clip = self._create_text_element(element, duration, scene['start_time'])
                elif etype == 'meme':
                    clip = self._create_meme_element(element, duration, scene['start_time'])
                elif etype == 'quote':
                    clip = self._create_quote_element(element, duration, scene['start_time'])
                
                if clip:
                    clips.append(clip)
            
            return CompositeVideoClip(clips, size=(1920, 1080))
            
        except Exception as e:
            print(f"[WARNING] Failed to create b-roll: {e}")
            # Fallback to gameplay
            return self._get_background(duration)
    
    def _create_split_comparison_scene(self, scene, duration):
        """
        NEW: Side-by-side comparison (A vs B)
        Splits screen in half with vertical divider
        """
        print(f"[DIRECTOR] Creating split comparison scene...")
        
        # Two dimmed gameplay backgrounds
        bg_left = self._get_background(duration, opacity=0.3)
        bg_right = self._get_background(duration, opacity=0.3)
        
        # Crop them to halves
        bg_left = bg_left.crop(x1=0, y1=0, x2=960, y2=1080).set_position((0, 0))
        bg_right = bg_right.crop(x1=960, y1=0, x2=1920, y2=1080).set_position((960, 0))
        
        # Divider line
        divider = ColorClip(size=(10, 1080), color=(255, 255, 255), duration=duration).set_position('center')
        
        clips = [bg_left, bg_right, divider]
        
        # Add VS text
        try:
            vs_text = TextClip("VS", fontsize=120, color='gold', font='Arial-Bold', stroke_color='black', stroke_width=5)
            vs_text = vs_text.set_duration(duration).set_position('center').crossfadein(0.5)
            clips.append(vs_text)
        except:
            pass
        
        # Find elements for left and right
        elements = scene.get('elements', [])
        left_elements = [e for e in elements if e.get('position') == 'left']
        right_elements = [e for e in elements if e.get('position') == 'right']
        
        # Fallback if no positions specified: take first two
        if not left_elements and not right_elements and len(elements) >= 2:
            left_elements = [elements[0]]
            right_elements = [elements[1]]
        
        # Add left elements
        for element in left_elements:
            etype = element.get('type', 'icon')
            clip = None
            
            if etype == 'icon':
                clip = self._create_icon_element(element, duration, scene['start_time'])
            elif etype == 'text':
                clip = self._create_text_element(element, duration, scene['start_time'])
            elif etype == 'meme':
                clip = self._create_meme_element(element, duration, scene['start_time'])
            elif etype == 'quote':
                clip = self._create_quote_element(element, duration, scene['start_time'])
            
            if clip:
                clip = clip.set_position((480 - clip.w//2, 540 - clip.h//2))
                clips.append(clip)
                
        # Add right elements
        for element in right_elements:
            etype = element.get('type', 'icon')
            clip = None
            
            if etype == 'icon':
                clip = self._create_icon_element(element, duration, scene['start_time'])
            elif etype == 'text':
                clip = self._create_text_element(element, duration, scene['start_time'])
            elif etype == 'meme':
                clip = self._create_meme_element(element, duration, scene['start_time'])
            elif etype == 'quote':
                clip = self._create_quote_element(element, duration, scene['start_time'])
            
            if clip:
                clip = clip.set_position((1440 - clip.w//2, 540 - clip.h//2))
                clips.append(clip)
        
        return CompositeVideoClip(clips, size=(1920, 1080))

    def _create_spotlight_scene(self, scene, duration):
        """
        NEW: Dramatic spotlight focus on a single asset
        Dark vignette background with center focus
        """
        print(f"[DIRECTOR] Creating spotlight scene...")
        
        # Very dark background
        bg = self._get_background(duration, opacity=0.1)
        
        # Add a "glow" behind the center
        glow = ColorClip(size=(800, 800), color=(255, 255, 255), duration=duration)
        glow = glow.set_opacity(0.1).set_position('center')
        
        clips = [bg, glow]
        
        # Add the main focus element
        elements = scene.get('elements', [])
        if elements:
            # Take the first element as the spotlight focus
            element = elements[0]
            etype = element.get('type', 'icon')
            clip = None
            
            # Use appropriate creator based on type
            if etype == 'icon':
                clip = self._create_icon_element(element, duration, scene['start_time'], override_size=600)
            elif etype == 'text':
                clip = self._create_text_element(element, duration, scene['start_time'])
            elif etype == 'meme':
                clip = self._create_meme_element(element, duration, scene['start_time'])
            elif etype == 'quote':
                clip = self._create_quote_element(element, duration, scene['start_time'])
            
            if clip:
                clip = clip.set_position('center')
                clips.append(clip)
        
        return CompositeVideoClip(clips, size=(1920, 1080))

    def _get_background(self, duration, opacity=0.4, force_gameplay=False):
        """
        Get background footage - cycles between gameplay and alternate backgrounds
        
        Args:
            duration: Duration of the clip needed
            opacity: Darkness level (lower = darker)
            force_gameplay: If True, always use gameplay (for mixed evidence scenes, etc.)
        """
        # Decide which background to use
        use_alternate = False
        bg_path = self.gameplay_path
        
        if not force_gameplay and self.alternate_backgrounds and not self.last_bg_was_alternate:
            # Chance to use alternate background (but never twice in a row)
            if random.random() < self.alternate_bg_chance:
                use_alternate = True
                bg_path = random.choice(self.alternate_backgrounds)
                print(f"[DIRECTOR] Using alternate background: {os.path.basename(bg_path)}")
        
        # Track what we used
        self.last_bg_was_alternate = use_alternate
        
        if os.path.exists(bg_path):
            try:
                # Load WITHOUT audio - we only want the visual
                bg = VideoFileClip(bg_path, audio=False)
                
                # Random start point if video is longer than needed
                if bg.duration > duration:
                    start = random.uniform(0, bg.duration - duration)
                    bg = bg.subclip(start, start + duration)
                else:
                    # Loop if needed
                    bg = bg.loop(duration=duration)
                
                # Resize and darken
                bg = bg.resize(newsize=(1920, 1080))
                bg = bg.fx(vfx.colorx, opacity)
                
                return bg
            except Exception as e:
                print(f"[WARNING] Could not load background {bg_path}: {e}")
        
        # Fallback: solid color
        return ColorClip(size=(1920, 1080), color=(50, 50, 80), duration=duration)
    
    def _find_icon_asset(self, keyword):
        """Find icon file for keyword"""
        # Check icons directory
        paths_to_try = [
            f"data/assets/icons/{keyword.lower()}.png",
            f"data/assets/icons/{keyword.lower().replace(' ', '_')}.png",
            f"data/assets/{keyword}.png",
            f"data/assets/{keyword}.png".replace(' ', '_')
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                return path
        
        return None
    
    def _find_meme_asset(self, keyword='random'):
        """
        Find meme video file
        If keyword provided, tries to match filename
        Otherwise picks a random meme from the directory
        """
        meme_dir = "data/assets/memes"
        
        if not os.path.exists(meme_dir):
            return None
        
        # Get all mp4/webm files in memes directory
        meme_files = []
        for file in os.listdir(meme_dir):
            if file.lower().endswith(('.mp4', '.webm', '.mov', '.avi')):
                meme_files.append(os.path.join(meme_dir, file))
        
        if not meme_files:
            print(f"[DIRECTOR] No meme files found in {meme_dir}")
            return None
        
        # Try to find meme matching keyword
        if keyword and keyword != 'random':
            keyword_lower = keyword.lower().replace(' ', '_')
            for meme_path in meme_files:
                filename = os.path.basename(meme_path).lower()
                if keyword_lower in filename:
                    return meme_path
        
        # If no match or random requested, pick a random meme
        import random
        return random.choice(meme_files)
    
    def _find_graph_video(self, index):
        """Find graph video file by index, using metadata if available"""
        
        # Method 1: Use graph metadata if available (most accurate!)
        if hasattr(self, 'graph_metadata') and self.graph_metadata:
            if index < len(self.graph_metadata):
                graph_data = self.graph_metadata[index]
                
                # Handle both old format (string path) and new format (dict with 'path' key)
                if isinstance(graph_data, str):
                    # Old format: just a path string
                    path = graph_data
                    description = 'N/A'
                else:
                    # New format: dict with metadata
                    path = graph_data.get('path', '')
                    description = graph_data.get('description', 'N/A')
                
                if path and os.path.exists(path):
                    print(f"[DIRECTOR] Found graph via metadata: {os.path.basename(path)}")
                    print(f"[DIRECTOR]   Description: {description[:50]}...")
                    return path
                else:
                    print(f"[DIRECTOR] WARNING: Graph metadata path not found: {path}")
        
        # Method 2: Fallback to searching manim renders directory
        print(f"[DIRECTOR] Using fallback method for graph index {index}")
        search_dir = "data/temp/manim_renders/videos"
        
        if os.path.exists(search_dir):
            videos = []
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if file.endswith('.mp4'):
                        videos.append(os.path.join(root, file))
            
            # Sort by modification time (most recent first) to get newly generated graphs
            videos.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            print(f"[DIRECTOR] Found {len(videos)} graph videos in fallback search")
            if videos:
                print(f"[DIRECTOR]   -> Most recent: {os.path.basename(videos[0])}")
            
            if index < len(videos):
                selected_graph = videos[index]
                print(f"[DIRECTOR]   -> Selected: {os.path.basename(selected_graph)}")
                return selected_graph
            else:
                print(f"[DIRECTOR] WARNING: Graph index {index} out of range (only {len(videos)} available)")
        
        return None
    
    def _find_reddit_screenshot_by_metadata(self, index):
        """
        Find Reddit screenshot using metadata (if available) or fall back to old method
        
        Args:
            index: Reddit post index from timeline
        
        Returns:
            Path to screenshot file or None
        """
        # If we have metadata, use it (most accurate!)
        if self.reddit_screenshots and index < len(self.reddit_screenshots):
            reddit_data = self.reddit_screenshots[index]
            path = reddit_data.get('path', '')
            
            if path and os.path.exists(path):
                print(f"[DIRECTOR]   Found via metadata: {os.path.basename(path)}")
                print(f"[DIRECTOR]     Matched to segment: {reddit_data.get('matched_segment', '?')}")
                print(f"[DIRECTOR]     Relevance: {reddit_data.get('relevance_score', 0)}/10")
                return path
            else:
                print(f"[DIRECTOR]   WARNING: Metadata path not found: {path}")
        
        # Fallback: old method (find by modification time)
        print(f"[DIRECTOR]   Using fallback method (no metadata or path not found)")
        return self._find_reddit_screenshot_fallback(index)
    
    def _find_reddit_screenshot_fallback(self, index):
        """Fallback: Find Reddit screenshot file by modification time (most recent first)"""
        search_dir = "data/assets"
        
        if os.path.exists(search_dir):
            screenshots = []
            for file in os.listdir(search_dir):
                if 'reddit' in file.lower():  # Only files with 'reddit' in name
                    if file.endswith(('.png', '.jpg')):
                        full_path = os.path.join(search_dir, file)
                        screenshots.append(full_path)
            
            # Sort by modification time (most recent first)
            screenshots.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            if index < len(screenshots):
                selected = screenshots[index]
                print(f"[DIRECTOR]   Fallback: Using {os.path.basename(selected)}")
                return selected
        
        return None

    def _find_youtube_card_by_metadata(self, index):
        """
        Find YouTube card using metadata (if available) or fall back
        """
        print(f"[DIRECTOR] Looking for YouTube card index {index}...")
        
        # If we have metadata, use it
        if hasattr(self, 'youtube_cards') and self.youtube_cards and index < len(self.youtube_cards):
            youtube_data = self.youtube_cards[index]
            path = youtube_data.get('path', '')
            print(f"[DIRECTOR]   Metadata path: {path}")
            
            if path and os.path.exists(path):
                print(f"[DIRECTOR]   Found YouTube card via metadata: {os.path.basename(path)}")
                return path
            else:
                print(f"[DIRECTOR]   Metadata path not found on disk, trying fallback...")
        else:
            print(f"[DIRECTOR]   No metadata available (have {len(self.youtube_cards) if hasattr(self, 'youtube_cards') else 0} cards)")
        
        # Fallback: search assets dir for files with 'youtube' in name
        search_dir = "data/assets"
        if os.path.exists(search_dir):
            cards = []
            for file in os.listdir(search_dir):
                if 'youtube' in file.lower() or 'yt_' in file.lower():
                    if file.endswith(('.png', '.jpg')):
                        cards.append(os.path.join(search_dir, file))
            
            print(f"[DIRECTOR]   Fallback found {len(cards)} YouTube-related files")
            
            # Sort by modification time (most recent first)
            cards.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            if index < len(cards):
                print(f"[DIRECTOR]   Using fallback: {cards[index]}")
                return cards[index]
        
        print(f"[DIRECTOR]   WARNING: No YouTube card found!")
        return None


    def _validate_timeline_before_render(self, timeline):
        """
        Validate timeline before rendering to catch obvious issues
        """
        print("\n[DIRECTOR] Pre-render validation...")
        issues = []
        
        scenes = timeline.get('scenes', [])
        if not scenes:
            issues.append("No scenes in timeline!")
            
        # Check for scene type distribution
        scene_types = {}
        for scene in scenes:
            stype = scene.get('type', 'unknown')
            scene_types[stype] = scene_types.get(stype, 0) + 1
        
        # Warn if one scene type dominates (>70%)
        total_scenes = len(scenes)
        for stype, count in scene_types.items():
            if count / total_scenes > 0.7 and stype not in ['gameplay_icons']:
                issues.append(f"WARNING: {stype} scenes dominate ({count}/{total_scenes} = {count/total_scenes*100:.0f}%)")
        
        # Check for duplicate graph/reddit/youtube indices
        graph_indices = []
        reddit_indices = []
        youtube_indices = []
        
        for scene in scenes:
            for elem in scene.get('elements', []):
                if elem.get('type') == 'graph':
                    idx = elem.get('index', 0)
                    if idx in graph_indices:
                        issues.append(f"CRITICAL: Graph index {idx} used multiple times!")
                    graph_indices.append(idx)
                elif elem.get('type') == 'reddit':
                    idx = elem.get('post_index', 0)
                    if idx in reddit_indices:
                        issues.append(f"CRITICAL: Reddit index {idx} used multiple times!")
                    reddit_indices.append(idx)
                elif elem.get('type') == 'youtube':
                    idx = elem.get('youtube_index', 0)
                    if idx in youtube_indices:
                        issues.append(f"CRITICAL: YouTube index {idx} used multiple times!")
                    youtube_indices.append(idx)
        
        # Check graph indices against available graphs
        if self.graph_metadata:
            max_graph_idx = len(self.graph_metadata) - 1
            for idx in graph_indices:
                if idx > max_graph_idx:
                    issues.append(f"CRITICAL: Graph index {idx} out of range (only {len(self.graph_metadata)} available)")
        
        # Check reddit indices against available screenshots
        if self.reddit_screenshots:
            max_reddit_idx = len(self.reddit_screenshots) - 1
            for idx in reddit_indices:
                if idx > max_reddit_idx:
                    issues.append(f"CRITICAL: Reddit index {idx} out of range (only {len(self.reddit_screenshots)} available)")
        
        # Check youtube indices against available cards
        if self.youtube_cards:
            max_youtube_idx = len(self.youtube_cards) - 1
            for idx in youtube_indices:
                if idx > max_youtube_idx:
                    issues.append(f"CRITICAL: YouTube index {idx} out of range (only {len(self.youtube_cards)} available)")
        
        # Check for scene duration issues
        for scene in scenes:
            duration = scene['end_time'] - scene['start_time']
            if duration <= 0:
                issues.append(f"CRITICAL: Scene {scene['scene_number']} has invalid duration: {duration:.2f}s ({scene['start_time']:.2f}s - {scene['end_time']:.2f}s)")
                # Auto-fix: extend scene to have at least 2s duration
                scene['end_time'] = scene['start_time'] + 2.0
                print(f"[DIRECTOR] AUTO-FIX: Extended scene {scene['scene_number']} to end at {scene['end_time']:.2f}s")
            elif duration > 60:
                issues.append(f"WARNING: Scene {scene['scene_number']} is {duration:.1f}s long (type: {scene.get('type')})")
        
        # Check for element timestamps outside their scenes
        for scene in scenes:
            scene_start = scene['start_time']
            scene_end = scene['end_time']
            for elem in scene.get('elements', []):
                elem_time = elem.get('timestamp', 0)
                if elem_time < scene_start:
                    issues.append(f"WARNING: Element '{elem.get('keyword', elem.get('text', '?'))}' timestamp {elem_time:.2f}s before scene start {scene_start:.2f}s")
                    elem['timestamp'] = scene_start + 0.1
                elif elem_time >= scene_end:
                    issues.append(f"WARNING: Element '{elem.get('keyword', elem.get('text', '?'))}' timestamp {elem_time:.2f}s at/after scene end {scene_end:.2f}s")
                    elem['timestamp'] = max(scene_start + 0.1, scene_end - 0.5)
        
        # Report issues
        if issues:
            print("[DIRECTOR] Timeline issues found:")
            for issue in issues:
                print(f"  - {issue}")
            print("[DIRECTOR] Proceeding with render (issues may affect output quality)")
        else:
            print("[DIRECTOR] Timeline validation passed!")
        
        print()
    
    def _split_subtitle_into_chunks(self, text, max_words=6):
        """
        Split a sentence into smaller chunks for more readable subtitles
        
        Args:
            text: Full sentence text
            max_words: Maximum words per chunk (default 6)
        
        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            # Split at natural breaks or when reaching max words
            if len(current_chunk) >= max_words or word.endswith((',', ';', '—', '–')):
                chunks.append(' '.join(current_chunk))
                current_chunk = []
        
        # Add remaining words
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [text]
    
    def _create_subtitle_clips(self, sentence_timings, timeline, total_duration):
        """
        Create scene-aware subtitle clips based on sentence timings
        
        IMPORTANT: These are REGULAR NARRATION SUBTITLES (continuous speech)
        - Positioned at BOTTOM of screen (like normal subtitles)
        - Show sentence-by-sentence narration text
        
        SEPARATE from emphasized keyword text which:
        - Appears at CENTER via _create_text_element()
        - Acts like icons (big, bold, animated)
        - Shows individual keywords/phrases for emphasis
        
        Args:
            sentence_timings: List of {"text": "...", "start_time": 0.0, "duration": 2.5}
            timeline: Timeline dict with scenes
            total_duration: Total video duration
        
        Returns:
            List of TextClip objects positioned and styled based on active scene
        """
        subtitle_clips = []
        last_subtitle_end = 0.0  # Track when last subtitle ends to prevent overlap
        
        # Subtitle styling presets
        # NOTE: These are for CONTINUOUS NARRATION SUBTITLES (sentence-by-sentence)
        # Emphasized keyword text appears separately via _create_text_element() at CENTER
        STYLES = {
            'bottom_default': {
                'fontsize': 42,
                'color': 'white',
                'stroke_color': 'black',
                'stroke_width': 2.5,
                'font': 'Arial-Bold',
                'method': 'caption',
                'size': (1600, None),  # Width, auto height
                'position': ('center', 920)  # Bottom area (normal subtitles)
            },
            'bottom_small': {
                'fontsize': 36,
                'color': 'white',
                'stroke_color': 'black',
                'stroke_width': 2,
                'font': 'Arial-Bold',
                'method': 'caption',
                'size': (1500, None),
                'position': ('center', 950)  # Even lower (for graphs/reddit)
            },
            'middle_icon': {
                'fontsize': 70,  # Larger like an icon
                'color': 'white',
                'stroke_color': 'black',
                'stroke_width': 4,
                'font': 'Arial-Bold',
                'method': 'caption',
                'size': (1400, None),
                'position': 'center',  # True center (540 for 1080p)
                'animate': True  # Flag to add icon-like animations
            }
        }
        
        for sent in sentence_timings:
            text = sent['text'].strip()
            start = sent['start_time']
            duration = sent['duration']
            
            if not text or duration <= 0:
                continue
            
            # Find which scene is active at this time
            active_scene = None
            for scene in timeline.get('scenes', []):
                if scene['start_time'] <= start < scene['end_time']:
                    active_scene = scene
                    break
            
            # Choose style based on scene type
            if active_scene:
                scene_type = active_scene.get('type', 'gameplay_icons')
                
                if scene_type == 'text_statement':
                    # Skip subtitles for text_statement scenes (already has big text)
                    continue
                elif scene_type in ['data_graph', 'reddit_evidence']:
                    # Use smaller bottom subtitles for graph/reddit scenes
                    style = STYLES['bottom_small']
                elif scene_type == 'gameplay_icons':
                    # Use normal bottom subtitles (regular continuous narration)
                    # Emphasized keywords appear as separate text elements in center
                    style = STYLES['bottom_default']
                else:
                    # gameplay_only, broll, scrolling_comments - use bottom subtitles
                    style = STYLES['bottom_default']
            else:
                # Default fallback
                style = STYLES['bottom_default']
            
            # Split sentence into smaller chunks for better readability
            chunks = self._split_subtitle_into_chunks(text, max_words=6)
            chunk_duration = duration / len(chunks)
            
            # Create subtitle clip for each chunk
            for i, chunk in enumerate(chunks):
                chunk_start = start + (i * chunk_duration)
                chunk_end = chunk_start + chunk_duration
                
                # PREVENT OVERLAP: Ensure minimum 0.3s gap between subtitles
                MIN_GAP = 0.3
                if chunk_start < last_subtitle_end + MIN_GAP:
                    # Delay this chunk to avoid overlap
                    overlap_delay = (last_subtitle_end + MIN_GAP) - chunk_start
                    chunk_start = last_subtitle_end + MIN_GAP
                    
                    # Recalculate duration (may be shorter now due to delay)
                    remaining_time = (start + duration) - chunk_start
                    if remaining_time <= 0.1:  # Skip if no meaningful time left
                        print(f"[DIRECTOR] Skipping subtitle chunk '{chunk[:20]}...' due to timing overlap")
                        continue
                    
                    # Adjust duration for remaining chunks
                    remaining_chunks = len(chunks) - i
                    chunk_duration = min(chunk_duration, remaining_time / remaining_chunks)
                    chunk_end = chunk_start + chunk_duration
                
                try:
                    subtitle = TextClip(
                        chunk,
                        fontsize=style['fontsize'],
                        color=style['color'],
                        stroke_color=style['stroke_color'],
                        stroke_width=style['stroke_width'],
                        font=style['font'],
                        method=style['method'],
                        size=style['size']
                    )
                    
                    # Set timing and position
                    subtitle = subtitle.set_start(chunk_start).set_duration(chunk_duration)
                    subtitle = subtitle.set_position(style['position'])
                    
                    # Add icon-like animations if this is a middle_icon style
                    if style.get('animate', False):
                        # Zoom in animation like icons
                        def zoom_scale(t):
                            if t < 0.4:
                                # Zoom in from 0.5 to 1.0
                                progress = t / 0.4
                                # Ease out cubic
                                return 0.5 + (1 - (1 - progress) ** 3) * 0.5
                            else:
                                # Subtle breathing effect
                                return 1.0 + 0.03 * np.sin((t - 0.4) * 4)
                        
                        subtitle = subtitle.resize(zoom_scale)
                        # Stronger fade in/out for dramatic effect
                        subtitle = subtitle.crossfadein(0.3).crossfadeout(0.2)
                    else:
                        # Normal subtle fade for bottom subtitles
                        subtitle = subtitle.crossfadein(0.1).crossfadeout(0.1)
                    
                    subtitle_clips.append(subtitle)
                    
                    # Update last subtitle end time
                    last_subtitle_end = chunk_end
                    
                except Exception as e:
                    print(f"[WARNING] Failed to create subtitle for '{chunk[:30]}...': {e}")
                    continue
        
        return subtitle_clips


if __name__ == "__main__":
    # Test the director
    print("=" * 60)
    print("Testing Director V3")
    print("=" * 60)
    
    # Mock timeline
    test_timeline = {
        'scenes': [
            {
                'scene_number': 1,
                'start_time': 0,
                'end_time': 3,
                'type': 'gameplay_icons',
                'script_text': 'Test scene',
                'elements': [
                    {'type': 'icon', 'keyword': 'Edgar', 'timestamp': 0.5, 'animation': 'scale_in'},
                    {'type': 'icon', 'keyword': 'skull_emoji', 'timestamp': 1.0, 'animation': 'scale_in'}
                ]
            }
        ],
        'transitions': []
    }
    
    director = DirectorV3()
    
    # Would need actual voiceover to test fully
    print("\nDirector initialized and ready for rendering")
    print("Run the full pipeline from main.py to see it in action!")
