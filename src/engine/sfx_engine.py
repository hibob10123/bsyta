import os
import yaml
import json
import sys

# MoviePy 2.x compatible imports
try:
    from moviepy.editor import AudioFileClip, CompositeAudioClip
except ImportError:
    from moviepy import AudioFileClip, CompositeAudioClip
sys.path.append('src')
sys.path.append('src/utils')
from utils.claude_client import ClaudeClient

class SFXEngine:
    """
    Sound effects engine that syncs sound effects to visual events
    Maps SFX from your library to animations in the timeline
    """
    
    def __init__(self, config_path="config.yaml"):
        self.sfx_library = self._load_sfx_library(config_path)
        self.sfx_descriptions = self._load_sfx_descriptions()
        self.claude = ClaudeClient(model="claude-3-haiku-20240307", max_tokens=200)
        self.whoosh_sounds = self._get_whoosh_sounds()  # For rotation
        self.whoosh_index = 0  # Track which whoosh to use next
        self.usage_count = {}  # Track usage of limited sounds (like vineboom)
        self.video_duration = None  # Set during map_sfx_to_events
        print(f"[SFX] Loaded {len(self.sfx_library)} sound effects ({len(self.whoosh_sounds)} whoosh variants)")
    
    def _load_sfx_library(self, config_path):
        """Load SFX file paths from sfx.json"""
        sfx_json_path = "data/sfx/sfx.json"
        
        # Try to load from sfx.json first
        if os.path.exists(sfx_json_path):
            try:
                with open(sfx_json_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    sfx_list = config.get('sound_effects', [])
                    
                    # Build library: name -> full path
                    library = {}
                    for sfx in sfx_list:
                        file = sfx.get('file', '')
                        name = os.path.splitext(file)[0]  # Remove extension
                        library[name] = os.path.join('data/sfx', file)
                    
                    return library
            except Exception as e:
                print(f"[WARNING] Could not load SFX from {sfx_json_path}: {e}")
        
        # Fallback to default if JSON fails
        default_sfx = {
            'whoosh': 'data/sfx/whoosh.mp3',
            'whoosh2': 'data/sfx/whoosh2.mp3',
            'transition': 'data/sfx/transition.mp3'
        }
        
        return default_sfx
    
    def _load_sfx_descriptions(self):
        """
        Load sound effect descriptions from sfx.json
        
        Returns:
            Dict mapping sfx name to description info
        """
        sfx_config_path = "data/sfx/sfx.json"
        
        if not os.path.exists(sfx_config_path):
            return {}
        
        try:
            with open(sfx_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                sfx_list = config.get('sound_effects', [])
                
                # Create lookup dict: filename (without extension) -> description info
                sfx_dict = {}
                for sfx in sfx_list:
                    file = sfx.get('file', '')
                    name = os.path.splitext(file)[0]  # Remove extension
                    sfx_dict[name] = {
                        'file': file,
                        'description': sfx.get('description', ''),
                        'keywords': sfx.get('keywords', []),
                        'use_for': sfx.get('use_for', []),
                        'volume': sfx.get('volume'),  # Custom volume
                        'type': sfx.get('type'),  # For whoosh rotation
                        'max_duration': sfx.get('max_duration'),  # Duration limit
                        'max_per_video': sfx.get('max_per_video'),  # Static usage limit
                        'max_per_minute': sfx.get('max_per_minute')  # Dynamic usage limit
                    }
                
                print(f"[SFX] Loaded descriptions for {len(sfx_dict)} sound effects")
                return sfx_dict
                
        except Exception as e:
            print(f"[SFX] Warning: Could not load sfx.json: {e}")
            return {}
    
    def _get_whoosh_sounds(self):
        """Get list of all whoosh sound effects for rotation"""
        whoosh_sounds = []
        for sfx_name, sfx_info in self.sfx_descriptions.items():
            if sfx_info.get('type') == 'whoosh':
                whoosh_sounds.append(sfx_name)
        
        # Fallback to library keys if no whoosh types found
        if not whoosh_sounds:
            for key in self.sfx_library.keys():
                if 'whoosh' in key.lower():
                    whoosh_sounds.append(key)
        
        return whoosh_sounds if whoosh_sounds else ['whoosh']  # Default fallback
    
    def map_sfx_to_events(self, timeline):
        """
        Create SFX timeline from video timeline
        Maps sound effects to each visual event
        
        Args:
            timeline: Video timeline from ScenePlanner
        
        Returns:
            List of SFX events with {timestamp, sfx_type, volume}
        """
        print("[SFX] Mapping sound effects to timeline events...")
        
        # Calculate video duration for per-minute limits
        scenes = timeline.get('scenes', [])
        if scenes:
            self.video_duration = max(scene['start_time'] + scene.get('duration', 0) for scene in scenes)
        else:
            self.video_duration = 60  # Default fallback
        
        print(f"[SFX] Video duration: {self.video_duration:.1f}s ({self.video_duration/60:.1f} minutes)")
        
        # Reset usage counters for new video
        self.usage_count = {}
        
        sfx_events = []
        
        # Add SFX for each scene element
        for scene in timeline.get('scenes', []):
            scene_type = scene.get('type', 'gameplay_icons')
            
            # Add scene start SFX for special scene types
            if scene_type in ['data_graph', 'reddit_evidence', 'youtube_evidence', 'text_statement']:
                sfx_events.append({
                    'timestamp': scene['start_time'] + 0.1,
                    'sfx_type': self._get_next_whoosh(),
                    'volume': 0.30,
                    'element_type': 'scene_start'
                })
            
            for element in scene.get('elements', []):
                sfx_type = self._determine_sfx_for_element(element)
                if sfx_type:
                    sfx_events.append({
                        'timestamp': element.get('timestamp', scene['start_time']),
                        'sfx_type': sfx_type,
                        'volume': self._determine_volume(element, sfx_type),
                        'element_type': element['type']
                    })
        
        # Add SFX for transitions (ALL transitions get a subtle whoosh)
        for transition in timeline.get('transitions', []):
            sfx_events.append({
                'timestamp': transition['timestamp'],
                'sfx_type': 'transition' if transition['type'] != 'cut' else self._get_next_whoosh(),
                'volume': 0.25,
                'element_type': 'transition'
            })
        
        # Sort by timestamp
        sfx_events.sort(key=lambda x: x['timestamp'])
        
        print(f"[SFX] Created {len(sfx_events)} sound effect events")
        return sfx_events
    
    def _determine_sfx_for_element(self, element):
        """Use LLM to intelligently choose SFX based on context"""
        element_type = element.get('type')
        animation = element.get('animation', '')
        keyword = element.get('keyword', '').lower()
        
        # Default to whoosh for most icons
        if element_type == 'icon' and not keyword:
            return 'icon_appear'
        
        # Get available SFX with descriptions if available
        available_sfx = list(self.sfx_library.keys())
        available_sfx_desc = []
        for sfx_name in available_sfx:
            sfx_path = self.sfx_library[sfx_name]
            filename = os.path.basename(sfx_path)
            
            # Check if we have descriptions for this SFX
            if sfx_name in self.sfx_descriptions:
                desc_info = self.sfx_descriptions[sfx_name]
                desc = desc_info.get('description', '')
                keywords = desc_info.get('keywords', [])
                
                if desc:
                    available_sfx_desc.append(f"- {sfx_name}: {desc}")
                    if keywords:
                        available_sfx_desc.append(f"  Keywords: {', '.join(keywords)}")
                else:
                    available_sfx_desc.append(f"- {sfx_name}: {filename}")
            else:
                available_sfx_desc.append(f"- {sfx_name}: {filename}")
        
        # Ask Claude to choose the best SFX
        prompt = f"""You are selecting sound effects for a gaming video.

AVAILABLE SOUND EFFECTS (with descriptions):
{chr(10).join(available_sfx_desc)}

ELEMENT TO ADD SOUND TO:
- Type: {element_type}
- Keyword: {keyword if keyword else 'none'}
- Animation: {animation if animation else 'none'}

RULES:
- READ THE DESCRIPTIONS ABOVE - they tell you when each sound effect should be used
- Match the sound effect to the element's context and keyword
- For most icons, "whoosh" is a safe default
- Use "vineboom" ONLY for very dramatic/shocking moments (sparingly!)
- Use "click" for UI elements, Reddit posts, or selections
- Use "ding" for positive achievements or milestones
- Use "booing" for negative/failure moments
- NEVER use long sound effects that would dominate the video
- Pick the SFX whose description best matches this element

Return ONLY the sfx name (like "whoosh", "vineboom", etc.), nothing else."""

        try:
            # Use regular ask instead of ask_json since we want plain text
            response = self.claude.client.messages.create(
                model=self.claude.model,
                max_tokens=50,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            chosen_sfx = response.content[0].text.strip().lower().strip('"\'.,')
            
            # Validate the choice exists in library
            if chosen_sfx in self.sfx_library:
                # Check usage limits (per-video or per-minute based)
                if chosen_sfx in self.sfx_descriptions:
                    sfx_info = self.sfx_descriptions[chosen_sfx]
                    
                    # Check per-minute limit (dynamic based on video duration)
                    max_per_minute = sfx_info.get('max_per_minute')
                    if max_per_minute and self.video_duration:
                        # Calculate max uses based on video length
                        minutes = self.video_duration / 60.0
                        max_uses = max(1, int(minutes * max_per_minute))  # At least 1
                        current_count = self.usage_count.get(chosen_sfx, 0)
                        
                        if current_count >= max_uses:
                            print(f"[SFX] '{chosen_sfx}' already used {current_count} times (max {max_uses} for {minutes:.1f}min video), using whoosh")
                            return self._get_next_whoosh()
                    
                    # Check per-video limit (static)
                    max_per_video = sfx_info.get('max_per_video')
                    if max_per_video:
                        current_count = self.usage_count.get(chosen_sfx, 0)
                        if current_count >= max_per_video:
                            print(f"[SFX] '{chosen_sfx}' already used {current_count} times (max {max_per_video}), using whoosh")
                            return self._get_next_whoosh()
                
                print(f"[SFX] LLM chose '{chosen_sfx}' for {element_type} '{keyword}'")
                self.usage_count[chosen_sfx] = self.usage_count.get(chosen_sfx, 0) + 1
                return chosen_sfx
            else:
                # Fallback to rotating whoosh
                print(f"[SFX] LLM chose '{chosen_sfx}' (not found), using whoosh")
                return self._get_next_whoosh()
                
        except Exception as e:
            print(f"[SFX] LLM selection failed ({e}), using default")
            # If LLM fails, use smart defaults with rotation
            if element_type == 'icon' or element_type == 'text':
                return self._get_next_whoosh()
            elif element_type == 'graph':
                return 'click'
            elif element_type == 'reddit':
                return 'click'
            else:
                return self._get_next_whoosh()
    
    def _get_next_whoosh(self):
        """Get next whoosh sound in rotation for variety"""
        if not self.whoosh_sounds:
            return 'whoosh'
        
        # Rotate through whoosh sounds
        whoosh = self.whoosh_sounds[self.whoosh_index % len(self.whoosh_sounds)]
        self.whoosh_index += 1
        return whoosh
    
    def _determine_volume(self, element, sfx_name=None):
        """Determine appropriate volume for element, using JSON config if available"""
        # Check if this SFX has a custom volume in the JSON
        if sfx_name and sfx_name in self.sfx_descriptions:
            custom_volume = self.sfx_descriptions[sfx_name].get('volume')
            if custom_volume is not None:
                # Scale down custom volumes to be quieter
                return custom_volume * 0.6
        
        # Fallback to element type defaults - QUIETER than before
        element_type = element.get('type')
        volume_map = {
            'icon': 0.25,    # Quieter for icons
            'graph': 0.30,   # Slightly louder for graphs
            'reddit': 0.30,  # Reddit posts
            'text': 0.25,    # Text elements
            'meme': 0.35,    # Memes can be slightly louder
            'quote': 0.25,   # Quotes
            'youtube': 0.30, # YouTube cards
            'transition': 0.25  # Transitions
        }
        
        return volume_map.get(element_type, 0.25)
    
    def apply_sfx(self, video_clip, sfx_timeline):
        """
        Apply sound effects to a video clip
        
        Args:
            video_clip: MoviePy VideoClip
            sfx_timeline: List of SFX events from map_sfx_to_events
        
        Returns:
            VideoClip with SFX added to audio
        """
        print(f"[SFX] Applying {len(sfx_timeline)} sound effects...")
        
        # Get video duration to ensure SFX don't extend beyond it
        video_duration = video_clip.duration
        
        # Load all SFX clips
        sfx_clips = []
        
        for event in sfx_timeline:
            sfx_type = event['sfx_type']
            timestamp = event['timestamp']
            volume = event['volume']
            
            # Get SFX file path
            sfx_path = self.sfx_library.get(sfx_type)
            
            if not sfx_path or not os.path.exists(sfx_path):
                print(f"[WARNING] SFX file not found: {sfx_type} at {sfx_path}")
                continue
            
            try:
                # Load and position the SFX
                sfx_clip = AudioFileClip(sfx_path)
                
                # CRITICAL: Trim SFX if it would extend beyond video duration
                max_sfx_duration = video_duration - timestamp
                if max_sfx_duration <= 0:
                    print(f"[SFX] Skipping {sfx_type} at {timestamp:.1f}s (after video end)")
                    continue
                
                if sfx_clip.duration > max_sfx_duration:
                    print(f"[SFX] Trimming {sfx_type} from {sfx_clip.duration:.1f}s to {max_sfx_duration:.1f}s")
                    sfx_clip = sfx_clip.subclip(0, max_sfx_duration)
                
                # Apply max_duration from JSON if specified
                if sfx_type in self.sfx_descriptions:
                    max_duration = self.sfx_descriptions[sfx_type].get('max_duration')
                    if max_duration and sfx_clip.duration > max_duration:
                        print(f"[SFX] Trimming {sfx_type} to max duration {max_duration:.1f}s")
                        sfx_clip = sfx_clip.subclip(0, max_duration)
                else:
                    # Default: limit to 1.5 seconds for sounds without config
                    if sfx_clip.duration > 1.5:
                        sfx_clip = sfx_clip.subclip(0, 1.5)
                
                sfx_clip = sfx_clip.volumex(volume)
                sfx_clip = sfx_clip.set_start(timestamp)
                
                sfx_clips.append(sfx_clip)
            except Exception as e:
                print(f"[WARNING] Failed to load SFX {sfx_type}: {e}")
        
        if not sfx_clips:
            print("[SFX] No sound effects applied")
            video_clip._sfx_audio_clips = []
            return video_clip
        
        # Combine with existing audio
        if video_clip.audio:
            all_audio = [video_clip.audio] + sfx_clips
            composite_audio = CompositeAudioClip(all_audio)
            # Set duration to match video, not audio (prevents extension)
            composite_audio = composite_audio.set_duration(video_duration)
            video_clip = video_clip.set_audio(composite_audio)
            video_clip._sfx_audio_clips = sfx_clips
            video_clip._sfx_composite_audio = composite_audio
            print(f"[SFX] Applied {len(sfx_clips)} sound effects to video")
        else:
            print("[WARNING] Video has no audio, cannot add SFX")
            video_clip._sfx_audio_clips = []
        
        return video_clip
    
    def create_sfx_preview(self, sfx_timeline, duration):
        """
        Create an audio-only preview of the SFX timeline
        Useful for testing timing
        
        Args:
            sfx_timeline: List of SFX events
            duration: Total duration in seconds
        
        Returns:
            Path to preview audio file
        """
        print("[SFX] Creating SFX preview...")
        
        sfx_clips = []
        
        for event in sfx_timeline:
            sfx_type = event['sfx_type']
            timestamp = event['timestamp']
            volume = event['volume']
            
            sfx_path = self.sfx_library.get(sfx_type)
            
            if sfx_path and os.path.exists(sfx_path):
                try:
                    sfx_clip = AudioFileClip(sfx_path)
                    sfx_clip = sfx_clip.volumex(volume)
                    sfx_clip = sfx_clip.set_start(timestamp)
                    sfx_clips.append(sfx_clip)
                except:
                    pass
        
        if sfx_clips:
            composite = CompositeAudioClip(sfx_clips)
            composite = composite.set_duration(duration)
            output_path = "data/temp/sfx_preview.mp3"
            try:
                composite.write_audiofile(output_path, verbose=False, logger=None)
                print(f"[SFX] Preview saved: {output_path}")
                return output_path
            finally:
                for clip in sfx_clips:
                    try:
                        clip.close()
                    except Exception:
                        pass
                try:
                    composite.close()
                except Exception:
                    pass
        
        return None
    
    def validate_sfx_library(self):
        """Check which SFX files exist"""
        print("[SFX] Validating sound effects library...")
        
        missing = []
        found = []
        
        for sfx_type, path in self.sfx_library.items():
            if os.path.exists(path):
                found.append(sfx_type)
            else:
                missing.append(f"{sfx_type} ({path})")
        
        print(f"[SFX] Found: {', '.join(found)}")
        if missing:
            print(f"[SFX] Missing: {', '.join(missing)}")
            print("[SFX] Tip: Create data/sfx/ directory and add your MP3 files")
        
        return len(missing) == 0


if __name__ == "__main__":
    # Test the SFX engine
    print("=" * 60)
    print("Testing SFX Engine")
    print("=" * 60)
    
    engine = SFXEngine()
    
    # Validate library
    engine.validate_sfx_library()
    
    # Test with mock timeline
    test_timeline = {
        'scenes': [
            {
                'scene_number': 1,
                'start_time': 0,
                'end_time': 5,
                'elements': [
                    {'type': 'icon', 'timestamp': 1.0, 'animation': 'scale_in'},
                    {'type': 'icon', 'timestamp': 1.5, 'animation': 'scale_in'}
                ]
            },
            {
                'scene_number': 2,
                'start_time': 5,
                'end_time': 10,
                'elements': [
                    {'type': 'graph', 'timestamp': 5.5, 'animation': 'fade_in'}
                ]
            }
        ],
        'transitions': [
            {'from_scene': 1, 'to_scene': 2, 'timestamp': 5.0, 'type': 'crossfade'}
        ]
    }
    
    print("\nMapping SFX to timeline...")
    sfx_timeline = engine.map_sfx_to_events(test_timeline)
    
    print("\nSFX Events:")
    for event in sfx_timeline:
        print(f"  {event['timestamp']:.1f}s: {event['sfx_type']} ({event['element_type']}) vol={event['volume']}")
