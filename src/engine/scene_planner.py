import os
import sys
import json

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.claude_client import ClaudeClient
from utils.timing_utils import parse_timestamp, calculate_stagger_times, estimate_speech_duration

class ScenePlanner:
    """
    Uses Claude to create a precise timeline of when each visual element appears
    Orchestrates the entire video structure based on script analysis
    """
    
    def __init__(self):
        self.claude = ClaudeClient()
        self.available_memes = self._load_available_memes()
        self.available_keywords = []  # Store keywords for gap-filling
        self.keyword_time_map = {}
        self.number_time_map = {}
    
    def create_timeline(self, script_segments, keywords, reddit_posts, graphs, voiceover_duration=None, reddit_screenshots=None, broll_assets=None, youtube_cards=None):
        """
        Create a complete timeline for video production
        
        Args:
            script_segments: List of segment dicts from script analyzer
            keywords: List of keyword dicts with icons
            reddit_posts: List of Reddit post dicts
            graphs: List of graph video paths OR list of graph metadata dicts
            voiceover_duration: Total duration of voiceover (estimated if None)
            reddit_screenshots: List of Reddit screenshots with metadata
            broll_assets: Dictionary of b-roll image paths
            youtube_cards: List of YouTube video evidence cards with metadata
        
        Returns:
            Complete timeline dictionary with precise timestamps
        """
        print("[PLANNER] Creating video timeline...")
        
        # Estimate duration if not provided
        if voiceover_duration is None:
            full_script = ' '.join([seg['text'] for seg in script_segments])
            voiceover_duration = estimate_speech_duration(full_script)
        
        print(f"[PLANNER] Total estimated duration: {voiceover_duration:.1f}s")
        
        # Count available assets for validation
        num_graphs = len(graphs) if graphs else 0
        num_reddit = len(reddit_screenshots) if reddit_screenshots else (len(reddit_posts) if reddit_posts else 0)
        num_youtube = len(youtube_cards) if youtube_cards else 0
        print(f"[PLANNER] Available assets: {num_graphs} graphs, {num_reddit} Reddit posts, {num_youtube} YouTube videos")
        
        # Store keywords for later gap-filling
        self.available_keywords = keywords
        
        # Use Claude to intelligently plan the timeline
        timeline = self._plan_with_claude(
            script_segments,
            keywords,
            reddit_posts,
            graphs,
            voiceover_duration,
            reddit_screenshots,
            broll_assets,
            youtube_cards
        )
        
        # Store asset counts for validation
        timeline['_metadata'] = {
            'num_graphs': num_graphs,
            'num_reddit': num_reddit,
            'num_youtube': num_youtube,
            'voiceover_duration': voiceover_duration
        }

        # Store assets + segments for later timing alignment
        timeline['_segments'] = script_segments
        timeline['_assets'] = {
            'reddit_screenshots': reddit_screenshots or [],
            'youtube_cards': youtube_cards or [],
            'graphs': graphs or []
        }
        
        # Validate and enrich timeline (this fixes duplicate indices, long scenes, etc.)
        timeline = self._validate_timeline(timeline, voiceover_duration)
        
        # CRITICAL: Fill any empty or sparse scenes with elements
        timeline = self._fill_empty_scenes(timeline, voiceover_duration)
        
        # Print timeline summary
        self._print_timeline_summary(timeline)
        
        print(f"[PLANNER] Created timeline with {len(timeline['scenes'])} scenes")
        
        return timeline
    
    def _print_timeline_summary(self, timeline):
        """Print a clear summary of the timeline for debugging"""
        print("\n" + "=" * 60)
        print("TIMELINE SUMMARY")
        print("=" * 60)
        
        scene_type_counts = {}
        graph_uses = []
        reddit_uses = []
        
        for scene in timeline.get('scenes', []):
            scene_type = scene.get('type', 'unknown')
            scene_type_counts[scene_type] = scene_type_counts.get(scene_type, 0) + 1
            
            duration = scene['end_time'] - scene['start_time']
            elements_str = ""
            
            for elem in scene.get('elements', []):
                if elem.get('type') == 'graph':
                    graph_uses.append(elem.get('index', 0))
                elif elem.get('type') == 'reddit':
                    reddit_uses.append(elem.get('post_index', 0))
            
            elem_count = len(scene.get('elements', []))
            print(f"  Scene {scene['scene_number']:2d}: {scene_type:18s} | {scene['start_time']:5.1f}s - {scene['end_time']:5.1f}s ({duration:4.1f}s) | {elem_count} elements")
        
        print("-" * 60)
        print("Scene type distribution:")
        for stype, count in sorted(scene_type_counts.items()):
            print(f"  {stype}: {count}")
        
        if graph_uses:
            print(f"\nGraph indices used: {sorted(graph_uses)} (should be unique!)")
            if len(graph_uses) != len(set(graph_uses)):
                print("  WARNING: Duplicate graph indices detected!")
        
        if reddit_uses:
            print(f"Reddit indices used: {sorted(reddit_uses)} (should be unique!)")
            if len(reddit_uses) != len(set(reddit_uses)):
                print("  WARNING: Duplicate Reddit indices detected!")
        
        print("=" * 60 + "\n")
    
    def _load_available_memes(self):
        """
        Load available meme files and their descriptions (if provided)
        
        Returns:
            List of meme dicts with file, description, and keywords
        """
        meme_dir = "data/assets/memes"
        memes_config_path = os.path.join(meme_dir, "memes.json")
        
        # If no meme directory, return empty
        if not os.path.exists(meme_dir):
            return []
        
        # Try to load memes.json for descriptions
        if os.path.exists(memes_config_path):
            try:
                with open(memes_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    memes = config.get('memes', [])
                    print(f"[PLANNER] Loaded {len(memes)} memes with descriptions")
                    return memes
            except Exception as e:
                print(f"[PLANNER] Warning: Could not load memes.json: {e}")
        
        # Fallback: Just scan directory for video files
        meme_files = []
        try:
            for file in os.listdir(meme_dir):
                if file.lower().endswith(('.mp4', '.webm', '.mov', '.avi')):
                    # Extract name without extension as keyword
                    name = os.path.splitext(file)[0]
                    meme_files.append({
                        'file': file,
                        'description': f"Meme video: {name}",
                        'keywords': [name.lower()]
                    })
            
            if meme_files:
                print(f"[PLANNER] Found {len(meme_files)} meme files (no descriptions)")
            return meme_files
        except Exception as e:
            print(f"[PLANNER] Warning: Could not scan meme directory: {e}")
            return []
    
    def _format_memes_for_prompt(self):
        """Format available memes for Claude prompt"""
        if not self.available_memes:
            return "(No meme files found - add .mp4 files to data/assets/memes/ for humor!)"
        
        meme_lines = []
        for i, meme in enumerate(self.available_memes[:10], 1):  # Limit to 10 to keep prompt manageable
            file = meme.get('file', 'unknown')
            desc = meme.get('description', '')
            keywords = meme.get('keywords', [])
            
            if desc:
                meme_lines.append(f"{i}. {file}: {desc}")
            else:
                meme_lines.append(f"{i}. {file}")
            
            if keywords:
                meme_lines.append(f"   Keywords: {', '.join(keywords)}")
        
        if len(self.available_memes) > 10:
            meme_lines.append(f"... and {len(self.available_memes) - 10} more memes")
        
        return "\n".join(meme_lines) if meme_lines else "(No memes available)"
    
    def _format_graphs_for_prompt(self, graphs):
        """
        Format graph metadata for Claude prompt
        Graphs can be list of paths (old format) or list of dicts with metadata (new format)
        """
        if not graphs:
            return "(No graphs available)"
        
        # Handle old format (just paths)
        if graphs and isinstance(graphs[0], str):
            return f"{len(graphs)} graph(s) available (use index 0 to {len(graphs)-1})"
        
        # New format with metadata
        graph_lines = []
        for i, graph in enumerate(graphs):
            desc = graph.get('description', f'Graph {i}')
            segment_hint = graph.get('segment_hint')
            labels = graph.get('labels', [])
            stat_texts = graph.get('stat_texts', [])
            
            line = f"Graph {i}: {desc}"
            if segment_hint:
                line += f" [BEST FIT: segment {segment_hint}]"
            if stat_texts:
                line += f"\n   Shows: {'; '.join(stat_texts[:3])}"
            
            graph_lines.append(line)
        
        result = "\n".join(graph_lines)
        result += f"\n\nCRITICAL: You have {len(graphs)} graph(s). Each graph can ONLY be used ONCE!"
        result += "\n- Graph 0 can appear in ONE scene only"
        if len(graphs) > 1:
            result += f"\n- Graph 1 can appear in ONE scene only"
        if len(graphs) > 2:
            result += f"\n- ... and so on for all {len(graphs)} graphs"
        
        return result
    
    def _plan_with_claude(self, segments, keywords, reddit_posts, graphs, duration, reddit_screenshots=None, broll_assets=None, youtube_cards=None):
        """Use Claude to intelligently plan scene timing"""
        
        # Build FULL script text with word-level timing hints
        full_script = ""
        cumulative_time = 0.0
        for s in segments:
            seg_text = s['text']
            seg_dur = s.get('duration_estimate', 5)
            full_script += f"\n[{cumulative_time:.1f}s-{cumulative_time + seg_dur:.1f}s] {seg_text}"
            cumulative_time += seg_dur
        
        # Enrich keywords with their exact position in script
        keywords_with_context = []
        full_text = ' '.join([s['text'] for s in segments])
        for kw in keywords:
            kw_text = kw.get('word', kw) if isinstance(kw, dict) else kw
            kw_display_type = kw.get('display_type', 'icon') if isinstance(kw, dict) else 'icon'
            # Find where this keyword appears in the script
            script_lower = full_text.lower()
            kw_lower = kw_text.lower()
            if kw_lower in script_lower:
                pos_idx = script_lower.find(kw_lower)
                # Estimate timing based on position
                # CRITICAL: Must match the duration estimate rate (150 WPM = 0.4s per word)
                words_before = full_text[:pos_idx].split()
                base_time = len(words_before) * 0.4  # Match estimate_speech_duration (150 WPM)
                
                # No buffer here - let the sync_offset in config.yaml handle timing adjustments
                # User can tune sync_offset for their preference (negative = earlier, positive = later)
                estimated_time = base_time
                
                context_start = max(0, pos_idx - 30)
                context_end = min(len(full_text), pos_idx + len(kw_text) + 30)
                context = full_text[context_start:context_end]
                keywords_with_context.append({
                    'keyword': kw_text,
                    'estimated_time': estimated_time,
                    'context': f"...{context}...",
                    'display_type': kw_display_type
                })
            else:
                keywords_with_context.append({
                    'keyword': kw_text,
                    'estimated_time': None,
                    'context': 'Not found in script',
                    'display_type': kw_display_type
                })
        
        # Use reddit_screenshots if available (has segment matching info), otherwise reddit_posts
        if reddit_screenshots:
            reddit_summary = [
                f"Post {i+1}: '{p.get('description', '')[:80]}...' (MUST show in segment {p.get('matched_segment', '?')}, relevance: {p.get('relevance_score', 0)}/10)"
                for i, p in enumerate(reddit_screenshots[:5])
            ]
            print(f"[PLANNER] Reddit posts with segment matching:")
            for i, p in enumerate(reddit_screenshots[:5]):
                print(f"   Post {i}: Segment {p.get('matched_segment', '?')} - {p.get('description', '')[:60]}...")
        else:
            reddit_summary = [
                f"Post: '{p.get('title', '')[:50]}...' (score: {p.get('score', 0)})"
                for p in reddit_posts[:5]
            ]
            
        # Add YouTube video summary
        youtube_summary = []
        if youtube_cards:
            for i, video in enumerate(youtube_cards):
                title = video.get('title', 'Video')[:60]
                channel = video.get('channel', 'Unknown Channel')
                note = video.get('note', '')
                if note:
                    youtube_summary.append(f"YouTube {i}: '{title}' (by {channel}) - NOTE: {note}")
                else:
                    youtube_summary.append(f"YouTube {i}: '{title}' (by {channel})")
        else:
            youtube_summary = ["(none available)"]
        
        system_prompt = """You are an expert video director. Create precise timelines for documentary-style gaming videos.
Your job is to decide exactly when each visual element (icon, Reddit post, graph, YouTube video) should appear based on the script.

SCENE TYPES:
1. gameplay_icons: High-energy gameplay with multiple icons, text overlays, or memes.
2. data_graph: Full-screen graph visualization. Use when citing statistics.
3. reddit_evidence: Full-screen Reddit post. Use for community opinions.
4. youtube_evidence: Full-screen YouTube video card (thumbnail + title). Use for creator/pro-player video evidence.
5. mixed_evidence: Dimmed gameplay with a combination of graphs, Reddit posts, or YouTube cards.
6. text_statement: Bold text revealed word-by-word on a black background. Use for dramatic emphasis.
7. scrolling_comments: A feed of community reactions scrolling up.
8. split_comparison: Screen split in half (A vs B) with vertical divider. PERFECT for "Old vs New", "Buff vs Nerf", or comparing two brawlers.
   - Use 'elements' with 'position': 'left' and 'position': 'right'.
9. spotlight: Darkened background with a single center focus on an icon or character. Use for dramatic reveals.
10. broll: Cinematic image with Ken Burns panning effect. Use for visual variety.

CRITICAL: Icons must appear at the EXACT moment their word/concept is spoken in the voiceover."""

        user_prompt = f"""Create a video timeline with these elements:

FULL SCRIPT WITH TIMING:
{full_script}

AVAILABLE KEYWORDS (with context and display type):
{chr(10).join([f"- '{kw['keyword']}' ({kw['display_type']}) at ~{kw['estimated_time']:.1f}s: {kw['context']}" if kw['estimated_time'] else f"- '{kw['keyword']}' ({kw['display_type']}) (not in script)" for kw in keywords_with_context[:80]])}
... ({len(keywords_with_context)} keywords total - USE ALL OF THEM FOR A RICH VIDEO!)

REDDIT POSTS AVAILABLE (with smart segment matching):
{chr(10).join(reddit_summary) if reddit_summary else '(none)'}

YOUTUBE VIDEOS AVAILABLE (creator/pro evidence):
{chr(10).join(youtube_summary)}

⚠️  MANDATORY: You MUST use EVERY Reddit post and EVERY YouTube video provided!
    - Each Reddit post index (0 to {len(reddit_screenshots)-1 if reddit_screenshots else 0}) MUST appear in at least one scene.
    - Each YouTube video index (0 to {len(youtube_cards)-1 if youtube_cards else 0}) MUST appear in at least one scene.
    - If you ignore these, the video will lack the required evidence.

⚠️  CRITICAL: Each Reddit post has been intelligently matched to a SPECIFIC script segment!
    - Post index N MUST appear in/near its matched segment
    - The matched segment number tells you EXACTLY where this post should appear
    - DO NOT randomly place Reddit posts - respect the segment matching!
    - Example: "Post 0 matched to segment 3" → create reddit_evidence scene during segment 3

GRAPHS AVAILABLE (with descriptions - USE THESE to place graphs correctly!):
{self._format_graphs_for_prompt(graphs)}

B-ROLL IMAGES AVAILABLE:
{sum(len(imgs) for imgs in (broll_assets or {}).values())} b-roll image(s) for cinematic variety

MEME VIDEOS AVAILABLE (short clips for humor/emphasis):
{self._format_memes_for_prompt()}

TOTAL DURATION: {duration:.1f} seconds

Create a JSON timeline with this structure:
{{
    "scenes": [
        {{
            "scene_number": 1,
            "start_time": 0.0,
            "end_time": 6.5,
            "type": "gameplay_icons",
            "script_text": "opening text",
            "elements": [
                {{"type": "text", "text": "December 2024", "timestamp": 0.8, "animation": "fade_in"}},
                {{"type": "icon", "keyword": "Brawl Stars", "timestamp": 1.5, "animation": "scale_in"}},
                {{"type": "text", "text": "84 million", "timestamp": 3.5, "animation": "zoom_in"}}
            ]
        }},
        {{
            "scene_number": 2,
            "start_time": 6.5,
            "end_time": 9.0,
            "type": "text_statement",
            "script_text": "dramatic statement text",
            "statement_text": "A Record-Breaking Milestone",
            "background_color": "black"
        }},
        {{
            "scene_number": 3,
            "start_time": 9.0,
            "end_time": 15.0,
            "type": "data_graph",
            "script_text": "statistics text",
            "elements": [
                {{"type": "graph", "index": 0, "timestamp": 9.5, "animation": "fade_in"}}
            ]
        }},
        {{
            "scene_number": 4,
            "start_time": 15.0,
            "end_time": 20.0,
            "type": "broll",
            "script_text": "visual context",
            "broll_query": "Brawl Stars gameplay celebration"
        }},
        {{
            "scene_number": 5,
            "start_time": 20.0,
            "end_time": 26.0,
            "type": "reddit_evidence",
            "script_text": "evidence text",
            "elements": [
                {{"type": "reddit", "post_index": 0, "timestamp": 20.5, "animation": "slide_up"}}
            ]
        }},
        {{
            "scene_number": 6,
            "start_time": 26.0,
            "end_time": 32.0,
            "type": "youtube_evidence",
            "script_text": "creator opinion",
            "elements": [
                {{"type": "youtube", "youtube_index": 0, "timestamp": 26.5, "animation": "pop"}}
            ]
        }},
        {{
            "scene_number": 7,
            "start_time": 32.0,
            "end_time": 38.0,
            "type": "split_comparison",
            "script_text": "comparing two brawlers",
            "elements": [
                {{"type": "icon", "keyword": "Edgar", "timestamp": 32.5, "position": "left"}},
                {{"type": "icon", "keyword": "Fang", "timestamp": 32.5, "position": "right"}}
            ]
        }}
    ],
    "transitions": [
        {{"from_scene": 1, "to_scene": 2, "timestamp": 5.0, "type": "crossfade"}}
    ]
}}

AVAILABLE SCENE TYPES:
1. **gameplay_icons**: Gameplay with icons/text overlays (narrative segments)
2. **data_graph**: BLACK background with animated graph (pure data visualization)
3. **reddit_evidence**: WHITE background with Reddit post screenshot (community evidence)
4. **youtube_evidence**: DARK background with YouTube video card (thumbnail + title). Use for creator/pro evidence.
5. **text_statement**: Colored background with bold text (dramatic statements, chapter breaks)
   - Use for: Dramatic quotes, key statements, chapter dividers
6. **scrolling_comments**: Scrolling Reddit comments feed (multiple community reactions)
   - Use for: Showing many community reactions at once
7. **split_comparison**: Screen split in half (A vs B) with vertical divider.
   - Use for: Comparing stats, "Old vs New", "Buff vs Nerf", or comparing two different brawlers.
   - Elements inside MUST have "position": "left" or "position": "right".
8. **spotlight**: Darkened background with a single center focus.
   - Use for: Dramatic reveals, focusing on one specific character or item.
9. **broll**: Cinematic image with slow pan/zoom (visual variety, establishing shots)
   - Use for: Establishing context, visual breaks, related imagery

CRITICAL TIMING RULES:
1. **SYNC VISUALS TO EXACT WORDS**: Look at the keyword's estimated_time and context. Elements MUST appear at that exact moment.
   - Example: If "Brawl Stars" appears at 2.3s in script, element timestamp should be ~2.3s
   - Example: If "December 2024" appears at 0.8s, text timestamp should be ~0.8s
   - DO NOT just evenly space elements - match them to when those words are actually spoken!

2. **ELEMENT TYPES - Use the display_type from keywords**:
   - **"text" elements**: For dates, numbers, statistics (e.g., "December 2024", "84 million", "60%")
     * JSON: {{"type": "text", "text": "December 2024", "timestamp": 0.8, "animation": "fade_in"}}
     * Animations: "fade_in", "zoom_in", "slide_up"
   - **"icon" elements**: For names, concepts, objects (e.g., "Brawl Stars", "record", "peak")
     * JSON: {{"type": "icon", "keyword": "Brawl Stars", "timestamp": 2.3, "animation": "pop"}}
     * Animations: "pop", "bounce", "scale_in", "fade_scale"
   - **"quote" elements**: For ANY text in quotation marks in the script - displays as LARGE ANIMATED TEXT in center
     * JSON: {{"type": "quote", "text": "a sugar high", "timestamp": 5.2, "animation": "zoom_in"}}
     * CRITICAL: Detect ALL quoted phrases in the script and create quote elements for them!
     * Examples: "hollow peak", "sugar high", "caught in 4k", "skill issue"
     * Appears in CENTER of screen with icon-like animations (zoom, breathing effect)
     * Animations: "zoom_in", "pop", "bounce"
     * Use this for ANY quotation marks, slang, or emphasized phrases in quotes
   - **"meme" elements**: SHORT video meme clips for humor/emphasis (1-2s max, appears in corner)
     * JSON: {{"type": "meme", "keyword": "bruh", "timestamp": 15.2, "animation": "pop"}}
     * Use sparingly (1-3 per video) for comedic moments, reactions, or emphasis
     * USE KEYWORDS FROM THE "MEME VIDEOS AVAILABLE" SECTION ABOVE - pick memes that match the moment!
     * Check meme descriptions to understand when each meme is appropriate
     * Appears in screen corner, doesn't block main content
     * If no appropriate meme available, use "random" or skip

3. **SCENE STRUCTURE & WHEN TO USE EACH**:
   - **gameplay_icons**: For narrative/story segments. 3-6 icons/text elements timed to specific words. (Most common, 50-60% of scenes)
   - **data_graph**: PURE graph (BLACK bg, NO other elements, 6-12s). Use ONLY when statistics are discussed. (5-15% of scenes)
     * CRITICAL: Each graph index can ONLY be used ONCE in the entire video!
     * Graph 0 -> ONE scene. Graph 1 -> ONE different scene. etc.
     * Check the graph descriptions above to match the RIGHT graph to the RIGHT statistics
   - **reddit_evidence**: PURE Reddit post (WHITE bg, NO other elements, 6-12s). Use for single important community post.
     * CRITICAL: Each post_index can ONLY be used ONCE in the entire video!
     * post_index 0 -> ONE scene. post_index 1 -> ONE different scene. etc.
     * MUST place in the matched segment! Check "matched to segment X" in the post list above
   - **youtube_evidence**: YouTube video card (DARK bg, NO other elements, 4-10s). Use for creator/pro video evidence.
     * CRITICAL: Each youtube_index can ONLY be used ONCE in the entire video!
     * youtube_index 0 -> ONE scene. youtube_index 1 -> ONE different scene. etc.
     * Shows thumbnail + title + channel name
     * (10-15% of scenes)
   - **text_statement**: Bold text on colored bg (3-6s). Use for dramatic moments, quotes, chapter breaks. (5-10% of scenes)
   - **scrolling_comments**: Scrolling comment feed (5-8s). Use when showing many community reactions at once. (5-10% of scenes)
   - **broll**: Cinematic image with pan (4-8s). Use for visual variety, establishing shots, transitions. (5-10% of scenes)
   
   **SCENE DURATION LIMITS (HARD LIMITS):**
   - gameplay_icons: MAX 30 seconds per scene (split longer narrative into multiple scenes!)
   - data_graph: MAX 12 seconds (graphs don't need long viewing time)
   - reddit_evidence: MAX 15 seconds (enough to read)
   - text_statement: MAX 6 seconds (impactful, brief)
   - broll: MAX 10 seconds (visual variety)
   
   **FOR LONGER VIDEOS (3+ minutes):** Create MORE scenes (15-30+), not longer scenes!
   
   🚨 **CRITICAL: DISTRIBUTE SPECIAL SCENES THROUGHOUT THE ENTIRE VIDEO!** 🚨
   - DO NOT cluster all Reddit/YouTube/graph/text_statement scenes in the first 30 seconds!
   - For a 6-minute video: Place evidence scenes in the FIRST, MIDDLE, and FINAL thirds
   - Example distribution for 6-minute video with 2 Reddit posts, 1 YouTube, 2 graphs:
     * 0:00-2:00 (first third): 1 graph scene
     * 2:00-4:00 (middle third): 1 Reddit post, 1 YouTube evidence
     * 4:00-6:00 (final third): 1 graph scene, 1 Reddit post
   - The video should feel varied and interesting ALL THE WAY THROUGH, not front-loaded!
   - NEVER have more than 60 seconds of just gameplay_icons without a special scene

4. **SCENE TIMING**:
   - Create scenes based on the script segment timing provided above
   - If script says "[0.0s-5.0s] Opening text", that scene should be 0.0-5.0s
   - Don't arbitrarily extend or shorten - match the voiceover!

5. **ELEMENT PLACEMENT WITHIN SCENES**:
   - Read each keyword's context to see the EXACT sentence it appears in
   - Check the display_type: use "text" for dates/numbers, "icon" for names/concepts
   - Set the element's timestamp to match when that word is spoken
   - Examples:
     * "December 2024" (text) at 0.8s → {{"type": "text", "text": "December 2024", "timestamp": 0.8}}
     * "Brawl Stars" (icon) at 1.2s → {{"type": "icon", "keyword": "Brawl Stars", "timestamp": 1.2}}
     * "84 million" (text) at 3.5s → {{"type": "text", "text": "84 million", "timestamp": 3.5}}
     * "record" (icon) at 3.2s → {{"type": "icon", "keyword": "record", "timestamp": 3.2}}

6. **GRAPH/REDDIT SCENES - CRITICAL TIMING**:
   - **data_graph**: Place EXACTLY when the numbers are spoken in the script
     * Look for sentences with "from X to Y", "X in 2022, Y in 2023", "X%, Y%, Z%"
     * The graph should START right as the narrator begins saying the numbers
     * Duration: 4-6s (long enough to show the data but not drag)
   - **reddit_evidence**: Place in the MATCHED SEGMENT! (see "matched to segment X" above)
     * ⚠️ DO NOT IGNORE THE SEGMENT MATCHING! It was intelligently calculated based on post content
     * Post description tells you what claim it supports
     * Should appear DURING or shortly AFTER the narrator mentions the related topic
     * Example: Post about "Mastery removal" matched to segment 5 → place reddit_evidence scene in segment 5's time range
     * Duration: 5-8s (enough time to read the post)
   - These should be SEPARATE scenes from gameplay_icons
   - **If statistics appear early (first 10s), PRIORITIZE data_graph as scene 2 or 3**

7. **QUANTITY - ABSOLUTELY CRITICAL - THIS IS THE #1 PRIORITY**:
   - 🚨 YOU MUST USE AT LEAST 95% OF KEYWORDS! That means use {max(15, int(len(keywords_with_context) * 0.95))}+ out of {len(keywords_with_context)} available!
   - 🚨 Aim for 7-13 elements (icons + text) per gameplay_icons scene - BE GENEROUS WITH VISUALS!
   - Every major concept, action, and entity mentioned in the script MUST have a visual element
   - Mix text and icons naturally based on display_type
   - DON'T leave keywords unused - the user specifically extracted these for visual representation!
   - Example: A 30-second script with 15 keywords should use 14-15 of them, not just 5-6
   - 🚨 IF YOU USE LESS THAN 85% OF KEYWORDS, THE VIDEO WILL BE REJECTED!
   - Rich visual elements = engaging video. Sparse visuals = boring video.
   - MORE ICONS = BETTER! Users want constant visual stimulation!

8. **KEYWORD DISTRIBUTION - PREVENT EMPTY GAPS**:
   - 🚨 CRITICAL: Keywords MUST be distributed EVENLY across the ENTIRE video duration!
   - Do NOT front-load all icons in the first 30 seconds - this is WRONG!
   - For a {duration:.0f}s video, you should have icons appearing throughout:
     * First third (0-{duration/3:.0f}s): Use ~33% of keywords
     * Middle third ({duration/3:.0f}s-{2*duration/3:.0f}s): Use ~33% of keywords  
     * Final third ({2*duration/3:.0f}s-{duration:.0f}s): Use ~33% of keywords
   - NEVER have more than 10 seconds without at least one visual element!
   - If keywords have estimated_time values, USE THEM to place elements at the right moment!
   - Icons should appear continuously from start to finish - no "dead zones" in the middle!

EXAMPLES:

Example 1 - Basic elements:
Script: "[0.0s-6.5s] In December 2024, Brawl Stars was on top of the world."
Keywords: 
  - "December 2024" (text) at ~0.8s (context: "In December 2024, Brawl Stars")
  - "Brawl Stars" (icon) at ~1.8s (context: "December 2024, Brawl Stars was")
  - "top" (icon) at ~4.2s (context: "was on top of")

Timeline should be:
{{
  "scene_number": 1,
  "start_time": 0.0,
  "end_time": 6.5,
  "type": "gameplay_icons",
  "script_text": "In December 2024, Brawl Stars was on top of the world.",
  "elements": [
    {{"type": "text", "text": "December 2024", "timestamp": 0.8, "animation": "fade_in"}},
    {{"type": "icon", "keyword": "Brawl Stars", "timestamp": 1.8, "animation": "pop"}},
    {{"type": "icon", "keyword": "top", "timestamp": 4.2, "animation": "bounce"}}
  ]
}}

Example 2 - Quotes (CRITICAL - ALWAYS detect quoted text!):
Script: "[6.5s-12.0s] But it was a 'hollow peak'. A 'sugar high'."
Keywords:
  - "hollow peak" (text) at ~9.0s (context: "was a 'hollow peak'. A")
  - "sugar high" (text) at ~10.5s (context: "peak'. A 'sugar high'.")

Timeline should be:
{{
  "scene_number": 2,
  "start_time": 6.5,
  "end_time": 12.0,
  "type": "gameplay_icons",
  "script_text": "But it was a 'hollow peak'. A 'sugar high'.",
  "elements": [
    {{"type": "quote", "text": "hollow peak", "timestamp": 9.0, "animation": "zoom_in"}},
    {{"type": "quote", "text": "sugar high", "timestamp": 10.5, "animation": "pop"}}
  ]
}}

🚨 CRITICAL QUOTE RULE: Any text in quotation marks (single or double quotes) in the script MUST be a "quote" element!
This includes slang, emphasized phrases, and actual quotes. They will appear as large animated text in the center.

Return ONLY the JSON timeline.

🚨 FINAL REMINDER: The user will reject this timeline if you use less than 70% of the keywords!
Rich, frequent visual elements are ESSENTIAL for an engaging video. Be generous with icons and text!"""

        # Use higher temperature to encourage abundant icon usage (more creative, less conservative)
        timeline = self.claude.ask_json(user_prompt, system_prompt, temperature=0.65)
        
        if not timeline:
            print("[WARNING] Claude timeline failed, using fallback")
            return self._create_fallback_timeline(segments, keywords, reddit_posts, graphs, duration)
        
        # CRITICAL: Check if timeline was truncated (common for longer videos)
        # This happens when max_tokens is hit mid-JSON
        if 'scenes' in timeline and timeline['scenes']:
            last_scene = timeline['scenes'][-1]
            last_scene_end = last_scene.get('end_time', 0)
            
            # If timeline ends MUCH earlier than expected, it was likely truncated
            coverage_ratio = last_scene_end / duration if duration > 0 else 1.0
            
            if coverage_ratio < 0.7:
                print(f"\n[WARNING] Timeline only covers {coverage_ratio*100:.0f}% of video ({last_scene_end:.1f}s of {duration:.1f}s)")
                print("[WARNING] Claude response may have been truncated - generating filler scenes...")
                
                # Generate filler scenes for the remaining duration
                filler_scenes = self._generate_filler_scenes(
                    timeline['scenes'],
                    last_scene_end,
                    duration,
                    keywords_with_context,
                    segments
                )
                timeline['scenes'].extend(filler_scenes)
                print(f"[PLANNER] Added {len(filler_scenes)} filler scenes to cover remaining duration")
            
            # NEW: Check for INTERNAL gaps (scenes without enough elements in the middle)
            # This catches when Claude creates scenes but doesn't populate them with elements
            print("\n[PLANNER] Checking for internal gaps in element distribution...")
            
            # Sort scenes by time
            sorted_scenes = sorted(timeline['scenes'], key=lambda s: s['start_time'])
            
            # Analyze element distribution across video duration
            # Divide video into 30-second chunks and check element density
            chunk_size = 30  # seconds
            num_chunks = max(1, int(duration / chunk_size))
            
            chunk_elements = [0] * num_chunks
            chunk_has_scene = [False] * num_chunks
            
            for scene in sorted_scenes:
                scene_start = scene['start_time']
                scene_end = scene['end_time']
                num_elements = len(scene.get('elements', []))
                
                # Which chunks does this scene cover?
                start_chunk = min(int(scene_start / chunk_size), num_chunks - 1)
                end_chunk = min(int(scene_end / chunk_size), num_chunks - 1)
                
                for chunk_idx in range(start_chunk, end_chunk + 1):
                    chunk_has_scene[chunk_idx] = True
                    # Distribute elements across covered chunks
                    if end_chunk >= start_chunk:
                        elements_per_chunk = num_elements / (end_chunk - start_chunk + 1)
                        chunk_elements[chunk_idx] += elements_per_chunk
            
            # Find chunks with very few elements (potential gaps)
            sparse_chunks = []
            for i, (has_scene, elem_count) in enumerate(zip(chunk_has_scene, chunk_elements)):
                chunk_start = i * chunk_size
                chunk_end = min((i + 1) * chunk_size, duration)
                
                if elem_count < 2:  # Less than 2 elements in 30 seconds is sparse
                    sparse_chunks.append({
                        'chunk': i,
                        'start': chunk_start,
                        'end': chunk_end,
                        'elements': elem_count,
                        'has_scene': has_scene
                    })
            
            if sparse_chunks and len(sparse_chunks) > 0:
                print(f"[PLANNER] WARNING: Found {len(sparse_chunks)} sparse chunk(s) with few elements:")
                for sc in sparse_chunks[:5]:  # Show first 5
                    print(f"[PLANNER]   {sc['start']:.0f}s - {sc['end']:.0f}s: ~{sc['elements']:.1f} elements")
                
                # For each sparse chunk, try to add filler scenes
                for sc in sparse_chunks:
                    if sc['elements'] < 1:  # Very sparse - generate filler
                        filler_scenes = self._generate_filler_scenes(
                            timeline['scenes'],
                            sc['start'],
                            sc['end'],
                            keywords_with_context,
                            segments
                        )
                        if filler_scenes:
                            timeline['scenes'].extend(filler_scenes)
                            print(f"[PLANNER] Added {len(filler_scenes)} filler scene(s) for chunk {sc['start']:.0f}s-{sc['end']:.0f}s")
            else:
                print("[PLANNER] Element distribution looks good - no major gaps detected")
        
        # Validate asset usage
        if reddit_screenshots:
            self._validate_reddit_usage(timeline, reddit_screenshots)
        if youtube_cards:
            self._validate_youtube_usage(timeline, youtube_cards)
        
        return timeline
    
    def _validate_youtube_usage(self, timeline, youtube_cards):
        """
        Validate that YouTube evidence cards are being used correctly
        """
        print("\n[PLANNER] Validating YouTube usage...")
        
        youtube_scenes = []
        for scene in timeline.get('scenes', []):
            if scene.get('type') in ['youtube_evidence', 'mixed_evidence']:
                for element in scene.get('elements', []):
                    if element.get('type') == 'youtube':
                        youtube_scenes.append(scene)
                        idx = element.get('youtube_index', -1)
                        print(f"   Scene {scene.get('scene_number')} uses YouTube card {idx}")
                        break
        
        if len(youtube_cards) > 0 and len(youtube_scenes) == 0:
            print(f"   WARNING: {len(youtube_cards)} YouTube card(s) available but NONE used in timeline!")
            print(f"      Claude may have ignored the YouTube evidence. This is a missed opportunity.")
        elif len(youtube_scenes) < len(youtube_cards):
            print(f"   INFO: Using {len(youtube_scenes)}/{len(youtube_cards)} YouTube cards")
        else:
            print(f"   All {len(youtube_cards)} YouTube cards are being used")
    
    def _create_fallback_timeline(self, segments, keywords, reddit_posts, graphs, duration):
        """Create a basic timeline if Claude fails"""
        timeline = {
            'scenes': [],
            'transitions': []
        }
        
        current_time = 0.0
        
        for i, segment in enumerate(segments):
            seg_duration = segment.get('duration_estimate', 5)
            scene_type = self._determine_scene_type(segment['type'], graphs, reddit_posts)
            
            scene = {
                'scene_number': i + 1,
                'start_time': current_time,
                'end_time': current_time + seg_duration,
                'type': scene_type,
                'script_text': segment['text'],
                'elements': []
            }
            
            # Add appropriate elements based on scene type
            if scene_type == 'gameplay_icons' and keywords:
                # Add 2-3 icons
                icon_keywords = keywords[:3]
                stagger_times = calculate_stagger_times(current_time + 0.5, len(icon_keywords), 0.4)
                for kw, timestamp in zip(icon_keywords, stagger_times):
                    kw_text = kw.get('word', kw) if isinstance(kw, dict) else kw
                    scene['elements'].append({
                        'type': 'icon',
                        'keyword': kw_text,
                        'timestamp': timestamp,
                        'animation': 'scale_in'
                    })
            
            elif scene_type == 'data_graph' and graphs:
                # Pure graph scene - no icons, just the graph
                scene['elements'].append({
                    'type': 'graph',
                    'index': 0,
                    'timestamp': current_time + 0.5,
                    'animation': 'fade_in'
                })
                # Don't add icons to graph scenes
            
            elif scene_type == 'reddit_evidence' and reddit_posts:
                scene['elements'].append({
                    'type': 'reddit',
                    'post_index': 0,
                    'timestamp': current_time + 0.7,
                    'animation': 'slide_up'
                })
            
            elif scene_type == 'mixed_evidence':
                # Add both graph and reddit to gameplay background
                if graphs:
                    scene['elements'].append({
                        'type': 'graph',
                        'index': 0,
                        'timestamp': current_time + 0.5,
                        'animation': 'fade_in'
                    })
                if reddit_posts:
                    scene['elements'].append({
                        'type': 'reddit',
                        'post_index': 0,
                        'timestamp': current_time + 1.5,  # Stagger after graph
                        'animation': 'slide_up'
                    })
                # Can also add icons if available
                if keywords:
                    icon_keywords = keywords[:2]  # Just 1-2 icons for mixed scenes
                    stagger_times = calculate_stagger_times(current_time + 0.3, len(icon_keywords), 0.4)
                    for kw, timestamp in zip(icon_keywords, stagger_times):
                        kw_text = kw.get('word', kw) if isinstance(kw, dict) else kw
                        scene['elements'].append({
                            'type': 'icon',
                            'keyword': kw_text,
                            'timestamp': timestamp,
                            'animation': 'scale_in'
                        })
            
            timeline['scenes'].append(scene)
            
            # Add transition
            if i < len(segments) - 1:
                timeline['transitions'].append({
                    'from_scene': i + 1,
                    'to_scene': i + 2,
                    'timestamp': current_time + seg_duration,
                    'type': 'crossfade'
                })
            
            current_time += seg_duration
        
        return timeline
    
    def _determine_scene_type(self, segment_type, graphs, reddit_posts):
        """Determine appropriate scene type based on segment and available assets"""
        # Don't force mixed_evidence - let scenes play naturally one after another
        if segment_type == 'data' and graphs:
            return 'data_graph'
        elif segment_type == 'evidence' and reddit_posts:
            return 'reddit_evidence'
        elif segment_type == 'hook':
            return 'gameplay_icons'
        else:
            return 'gameplay_icons'
    
    def _generate_filler_scenes(self, existing_scenes, start_time, end_time, keywords_with_context, segments):
        """
        Generate filler scenes for gaps in the timeline.
        Used when Claude's response was truncated due to max_tokens limit.
        
        Args:
            existing_scenes: Scenes already in the timeline
            start_time: Where to start filling
            end_time: Where to end (total duration)
            keywords_with_context: Available keywords with timing info
            segments: Script segments for context
        
        Returns:
            List of filler scenes
        """
        filler_scenes = []
        current_time = start_time
        scene_number = len(existing_scenes) + 1
        
        # Find keywords that haven't been used yet
        used_keywords = set()
        for scene in existing_scenes:
            for elem in scene.get('elements', []):
                kw = elem.get('keyword', elem.get('text', ''))
                if kw:
                    used_keywords.add(kw.lower())
        
        # Filter to unused keywords and sort by estimated time
        unused_keywords = [
            kw for kw in keywords_with_context
            if kw['keyword'].lower() not in used_keywords
        ]
        # Sort by estimated time (for sequential usage)
        unused_keywords.sort(key=lambda kw: kw.get('estimated_time', float('inf')) or float('inf'))
        
        # Also filter to keywords that appear AFTER start_time
        late_keywords = [
            kw for kw in unused_keywords
            if kw.get('estimated_time') and kw['estimated_time'] >= start_time
        ]
        
        # Use late keywords first, then fall back to any unused
        keywords_to_use = late_keywords if late_keywords else unused_keywords
        keyword_idx = 0
        
        print(f"[FILLER] Generating scenes from {start_time:.1f}s to {end_time:.1f}s")
        print(f"[FILLER] {len(keywords_to_use)} unused keywords available")
        
        # Track scenes since last special scene (for variety)
        scenes_since_special = 3  # Start higher so we might add one early
        
        # Generate scenes in chunks of ~15-20 seconds (typical scene length)
        while current_time < end_time - 1:
            # Calculate scene duration (aim for 15-20s, but don't exceed remaining time)
            remaining = end_time - current_time
            scene_duration = min(18, max(8, remaining))  # 8-18s scenes
            
            scene_end = min(current_time + scene_duration, end_time)
            
            # Every 3-4 gameplay scenes, add a text_statement for variety
            # This keeps the video visually interesting even in filler sections
            if scenes_since_special >= 3 and keyword_idx < len(keywords_to_use) and remaining > 20:
                # Create a text_statement scene for dramatic impact
                kw = keywords_to_use[keyword_idx]
                keyword_idx += 1
                
                # Use shorter duration for text statements
                text_scene_duration = min(4, remaining)
                text_scene_end = current_time + text_scene_duration
                
                text_scene = {
                    'scene_number': scene_number,
                    'start_time': current_time,
                    'end_time': text_scene_end,
                    'type': 'text_statement',
                    'script_text': '(auto-generated emphasis)',
                    'statement_text': kw['keyword'].upper(),
                    'background_color': 'black'
                }
                filler_scenes.append(text_scene)
                print(f"[FILLER] Scene {scene_number}: {current_time:.1f}s - {text_scene_end:.1f}s (text_statement: '{kw['keyword']}')")
                
                current_time = text_scene_end
                scene_number += 1
                scenes_since_special = 0
                continue
            
            # Create gameplay_icons scene with available keywords
            scene = {
                'scene_number': scene_number,
                'start_time': current_time,
                'end_time': scene_end,
                'type': 'gameplay_icons',
                'script_text': '(auto-generated filler scene)',
                'elements': []
            }
            
            # Add 4-6 elements (icons/text) to this scene
            elements_to_add = min(6, len(keywords_to_use) - keyword_idx)
            element_times = calculate_stagger_times(current_time + 0.5, elements_to_add, scene_duration / (elements_to_add + 1))
            
            for i, timestamp in enumerate(element_times):
                if keyword_idx >= len(keywords_to_use):
                    break
                    
                kw = keywords_to_use[keyword_idx]
                keyword_idx += 1
                
                display_type = kw.get('display_type', 'icon')
                element = {
                    'type': 'text' if display_type == 'text' else 'icon',
                    'timestamp': timestamp,
                    'animation': 'zoom_in' if display_type == 'text' else 'scale_in'
                }
                
                # Set correct key based on element type
                if display_type == 'text':
                    element['text'] = kw['keyword']
                else:
                    element['keyword'] = kw['keyword']
                
                scene['elements'].append(element)
            
            if scene['elements']:  # Only add if we have elements
                filler_scenes.append(scene)
                print(f"[FILLER] Scene {scene_number}: {current_time:.1f}s - {scene_end:.1f}s with {len(scene['elements'])} elements")
            else:
                # No more keywords - create empty gameplay scene (will show just gameplay)
                scene['elements'] = []
                filler_scenes.append(scene)
                print(f"[FILLER] Scene {scene_number}: {current_time:.1f}s - {scene_end:.1f}s (gameplay only, no keywords left)")
            
            current_time = scene_end
            scene_number += 1
            scenes_since_special += 1
        
        return filler_scenes
    
    def _validate_timeline(self, timeline, total_duration):
        """
        Comprehensive timeline validation and correction
        Fixes common issues from Claude's generation
        """
        
        if 'scenes' not in timeline:
            timeline['scenes'] = []
        
        if 'transitions' not in timeline:
            timeline['transitions'] = []
        
        print("\n[PLANNER] Validating timeline...")
        
        # === FIX 0: Enforce Title Card for Scene 1 ===
        if timeline['scenes']:
            first_scene = timeline['scenes'][0]
            if first_scene.get('type') != 'text_statement':
                print(f"[PLANNER] Enforcing title card for Scene 1 (was {first_scene.get('type')})")
                first_scene['type'] = 'text_statement'
                
                # Extract first sentence for the title card
                if not first_scene.get('statement_text'):
                    script_text = first_scene.get('script_text', '')
                    if not script_text and 'elements' in first_scene:
                        # Fallback to first element text if available
                        for elem in first_scene['elements']:
                            if elem.get('text'):
                                script_text = elem['text']
                                break
                    
                    if script_text:
                        # Take first sentence or first 8 words
                        first_sentence = script_text.split('.')[0].strip()
                        words = first_sentence.split()
                        if len(words) > 8:
                            first_sentence = ' '.join(words[:8])
                        first_scene['statement_text'] = first_sentence
                
                # Ensure it has a black background
                first_scene['background_color'] = 'black'
                
                # Clear other elements to keep it clean, but keep them in metadata if needed
                # Actually, we just added support for icons in text statements, so we can keep them!

        # === FIX 0.1: Only the FIRST scene should be a text_statement ===
        # The user wants gameplay + icons after the title card
        for scene in timeline['scenes'][1:]:
            if scene.get('type') == 'text_statement':
                print(f"[PLANNER] Converting text_statement scene {scene.get('scene_number')} to gameplay_icons")
                scene['type'] = 'gameplay_icons'

        # === FIX 0.2: Mixed evidence scenes are not allowed ===
        # Convert mixed_evidence into a pure evidence scene if possible, otherwise gameplay
        for scene in timeline['scenes']:
            if scene.get('type') == 'mixed_evidence':
                element_types = {e.get('type') for e in scene.get('elements', [])}
                if 'reddit' in element_types:
                    print(f"[PLANNER] Converting mixed_evidence scene {scene.get('scene_number')} -> reddit_evidence")
                    scene['type'] = 'reddit_evidence'
                elif 'youtube' in element_types:
                    print(f"[PLANNER] Converting mixed_evidence scene {scene.get('scene_number')} -> youtube_evidence")
                    scene['type'] = 'youtube_evidence'
                elif 'graph' in element_types:
                    print(f"[PLANNER] Converting mixed_evidence scene {scene.get('scene_number')} -> data_graph")
                    scene['type'] = 'data_graph'
                else:
                    print(f"[PLANNER] Converting mixed_evidence scene {scene.get('scene_number')} -> gameplay_icons")
                    scene['type'] = 'gameplay_icons'
        
        # === FIX 0.5: Remove scenes that extend past the voiceover duration ===
        # This prevents empty scenes from appearing after the narration ends
        voiceover_end = total_duration
        scenes_to_remove = []
        for i, scene in enumerate(timeline['scenes']):
            if scene['start_time'] >= voiceover_end:
                print(f"[PLANNER] FIX: Removing scene {scene.get('scene_number')} - starts after voiceover ({scene['start_time']:.1f}s > {voiceover_end:.1f}s)")
                scenes_to_remove.append(i)
            elif scene['end_time'] > voiceover_end + 1:
                # Cap scenes that extend past voiceover
                scene['end_time'] = voiceover_end
                print(f"[PLANNER] FIX: Capped scene {scene.get('scene_number')} end_time to {voiceover_end:.1f}s")
        
        # Remove scenes in reverse order to maintain indices
        for i in reversed(scenes_to_remove):
            timeline['scenes'].pop(i)
        
        # === FIX 0.6: Evidence scenes should ONLY contain their primary element ===
        # Preserve Claude's indices (post_index/youtube_index/index) when valid.
        # Remove all icons/text/memes from evidence scenes.
        print("[PLANNER] FIX: Cleaning evidence scenes (keeping only reddit/youtube/graph elements)")

        metadata = timeline.get('_metadata', {})
        num_reddit = metadata.get('num_reddit', 0)
        num_youtube = metadata.get('num_youtube', 0)
        num_graphs = metadata.get('num_graphs', 0)

        used_reddit_indices = set()
        used_youtube_indices = set()
        used_graph_indices = set()

        for scene in timeline['scenes']:
            scene_type = scene.get('type', '')

            if scene_type == 'reddit_evidence':
                if num_reddit <= 0:
                    print(f"[PLANNER] No Reddit posts available - converting scene {scene.get('scene_number')} to gameplay_icons")
                    scene['type'] = 'gameplay_icons'
                    scene['elements'] = []
                    continue

                existing_idx = None
                for element in scene.get('elements', []):
                    if element.get('type') == 'reddit':
                        existing_idx = element.get('post_index')
                        break

                idx = None
                if isinstance(existing_idx, int) and 0 <= existing_idx < num_reddit and existing_idx not in used_reddit_indices:
                    idx = existing_idx
                    used_reddit_indices.add(idx)
                else:
                    for candidate in range(num_reddit):
                        if candidate not in used_reddit_indices:
                            idx = candidate
                            used_reddit_indices.add(idx)
                            break

                if idx is None:
                    print(f"[PLANNER] No unused Reddit indices left - converting scene {scene.get('scene_number')} to gameplay_icons")
                    scene['type'] = 'gameplay_icons'
                    scene['elements'] = []
                    continue

                scene_duration = scene['end_time'] - scene['start_time']
                if scene_duration <= 0.6:
                    elem_time = scene['start_time'] + max(0.05, scene_duration / 2)
                else:
                    elem_time = min(scene['start_time'] + 0.3, scene['end_time'] - 0.3)
                scene['elements'] = [{
                    'type': 'reddit',
                    'post_index': idx,
                    'timestamp': elem_time,
                    'animation': 'slide_up'
                }]
                print(f"[PLANNER]   Scene {scene.get('scene_number')}: reddit_evidence -> reddit element only (post_index {idx})")

            elif scene_type == 'youtube_evidence':
                if num_youtube <= 0:
                    print(f"[PLANNER] No YouTube cards available - converting scene {scene.get('scene_number')} to gameplay_icons")
                    scene['type'] = 'gameplay_icons'
                    scene['elements'] = []
                    continue

                existing_idx = None
                for element in scene.get('elements', []):
                    if element.get('type') == 'youtube':
                        existing_idx = element.get('youtube_index', element.get('index'))
                        break

                idx = None
                if isinstance(existing_idx, int) and 0 <= existing_idx < num_youtube and existing_idx not in used_youtube_indices:
                    idx = existing_idx
                    used_youtube_indices.add(idx)
                else:
                    for candidate in range(num_youtube):
                        if candidate not in used_youtube_indices:
                            idx = candidate
                            used_youtube_indices.add(idx)
                            break

                if idx is None:
                    print(f"[PLANNER] No unused YouTube indices left - converting scene {scene.get('scene_number')} to gameplay_icons")
                    scene['type'] = 'gameplay_icons'
                    scene['elements'] = []
                    continue

                scene_duration = scene['end_time'] - scene['start_time']
                if scene_duration <= 0.6:
                    elem_time = scene['start_time'] + max(0.05, scene_duration / 2)
                else:
                    elem_time = min(scene['start_time'] + 0.3, scene['end_time'] - 0.3)
                scene['elements'] = [{
                    'type': 'youtube',
                    'youtube_index': idx,
                    'timestamp': elem_time,
                    'animation': 'pop'
                }]
                print(f"[PLANNER]   Scene {scene.get('scene_number')}: youtube_evidence -> youtube element only (index {idx})")

            elif scene_type in ['data_graph', 'graph_visualization']:
                if num_graphs <= 0:
                    print(f"[PLANNER] No graphs available - converting scene {scene.get('scene_number')} to gameplay_icons")
                    scene['type'] = 'gameplay_icons'
                    scene['elements'] = []
                    continue

                existing_idx = None
                for element in scene.get('elements', []):
                    if element.get('type') == 'graph':
                        existing_idx = element.get('index')
                        break

                idx = None
                if isinstance(existing_idx, int) and 0 <= existing_idx < num_graphs and existing_idx not in used_graph_indices:
                    idx = existing_idx
                    used_graph_indices.add(idx)
                else:
                    for candidate in range(num_graphs):
                        if candidate not in used_graph_indices:
                            idx = candidate
                            used_graph_indices.add(idx)
                            break

                if idx is None:
                    print(f"[PLANNER] No unused graph indices left - converting scene {scene.get('scene_number')} to gameplay_icons")
                    scene['type'] = 'gameplay_icons'
                    scene['elements'] = []
                    continue

                scene_duration = scene['end_time'] - scene['start_time']
                if scene_duration <= 0.6:
                    elem_time = scene['start_time'] + max(0.05, scene_duration / 2)
                else:
                    elem_time = min(scene['start_time'] + 0.3, scene['end_time'] - 0.3)
                scene['elements'] = [{
                    'type': 'graph',
                    'index': idx,
                    'timestamp': elem_time,
                    'animation': 'fade_in'
                }]
                print(f"[PLANNER]   Scene {scene.get('scene_number')}: data_graph -> graph element only (index {idx})")
        
        # === FIX 1: Ensure no repeated graph indices ===
        used_graph_indices = set()
        for scene in timeline['scenes']:
            if scene.get('type') == 'data_graph':
                for element in scene.get('elements', []):
                    if element.get('type') == 'graph':
                        idx = element.get('index', 0)
                        if idx in used_graph_indices:
                            print(f"[PLANNER] WARNING: Graph index {idx} used multiple times! Removing duplicate from scene {scene.get('scene_number')}")
                            # Remove duplicate graph element
                            scene['elements'] = [e for e in scene['elements'] if e.get('type') != 'graph' or e.get('index') != idx]
                            # If scene has no elements left, convert to gameplay_icons
                            if not scene['elements']:
                                print(f"[PLANNER]   -> Converting empty graph scene to gameplay_icons")
                                scene['type'] = 'gameplay_icons'
                        else:
                            used_graph_indices.add(idx)
        
        # === FIX 2: Ensure no repeated Reddit post indices ===
        used_reddit_indices = set()
        for scene in timeline['scenes']:
            if scene.get('type') == 'reddit_evidence':
                for element in scene.get('elements', []):
                    if element.get('type') == 'reddit':
                        idx = element.get('post_index', 0)
                        if idx in used_reddit_indices:
                            print(f"[PLANNER] WARNING: Reddit post index {idx} used multiple times! Removing duplicate from scene {scene.get('scene_number')}")
                            scene['elements'] = [e for e in scene['elements'] if e.get('type') != 'reddit' or e.get('post_index') != idx]
                            if not scene['elements']:
                                print(f"[PLANNER]   -> Converting empty reddit scene to gameplay_icons")
                                scene['type'] = 'gameplay_icons'
                        else:
                            used_reddit_indices.add(idx)
        
        # === FIX 3: Enforce maximum scene duration (30s for most, 45s for gameplay_icons) ===
        MAX_DURATION = {
            'gameplay_icons': 45,
            'data_graph': 15,
            'reddit_evidence': 20,
            'youtube_evidence': 15,
            'text_statement': 10,
            'scrolling_comments': 15,
            'split_comparison': 15,
            'spotlight': 10,
            'broll': 12,
            'mixed_evidence': 20
        }
        
        # === FIX 3.5: Ensure no repeated YouTube indices ===
        used_youtube_indices = set()
        for scene in timeline['scenes']:
            if scene.get('type') == 'youtube_evidence':
                for element in scene.get('elements', []):
                    if element.get('type') == 'youtube':
                        idx = element.get('youtube_index', 0)
                        if idx in used_youtube_indices:
                            print(f"[PLANNER] WARNING: YouTube index {idx} used multiple times! Removing duplicate from scene {scene.get('scene_number')}")
                            scene['elements'] = [e for e in scene['elements'] if e.get('type') != 'youtube' or e.get('youtube_index') != idx]
                            if not scene['elements']:
                                print(f"[PLANNER]   -> Converting empty YouTube scene to gameplay_icons")
                                scene['type'] = 'gameplay_icons'
                        else:
                            used_youtube_indices.add(idx)
        
        scenes_to_split = []
        for i, scene in enumerate(timeline['scenes']):
            scene_type = scene.get('type', 'gameplay_icons')
            max_dur = MAX_DURATION.get(scene_type, 30)
            actual_dur = scene['end_time'] - scene['start_time']
            
            if actual_dur > max_dur:
                print(f"[PLANNER] WARNING: Scene {scene.get('scene_number')} is {actual_dur:.1f}s ({scene_type}) - exceeds max {max_dur}s")
                
                # For evidence/data scenes, just cap the duration
                if scene_type in ['data_graph', 'reddit_evidence', 'youtube_evidence', 'split_comparison', 'spotlight']:
                    scene['end_time'] = scene['start_time'] + max_dur
                    print(f"[PLANNER]   -> Capped to {max_dur}s")
                else:
                    # For gameplay scenes, note for splitting
                    scenes_to_split.append((i, actual_dur, max_dur))
        
        # Split overly long gameplay scenes
        if scenes_to_split:
            print(f"[PLANNER] Splitting {len(scenes_to_split)} overly long scenes...")
            # Process in reverse to maintain indices
            for i, actual_dur, max_dur in reversed(scenes_to_split):
                scene = timeline['scenes'][i]
                num_splits = int(actual_dur / max_dur) + 1
                split_dur = actual_dur / num_splits
                
                print(f"[PLANNER]   Scene {scene.get('scene_number')}: splitting {actual_dur:.1f}s into {num_splits} parts of {split_dur:.1f}s")
                
                # Create split scenes
                new_scenes = []
                original_start = scene['start_time']
                original_elements = scene.get('elements', [])
                
                for j in range(num_splits):
                    new_start = original_start + (j * split_dur)
                    new_end = new_start + split_dur
                    
                    # Filter elements to this time range
                    scene_elements = [
                        e for e in original_elements
                        if new_start <= e.get('timestamp', 0) < new_end
                    ]
                    
                    new_scene = {
                        'scene_number': scene['scene_number'] + j * 0.1,  # Fractional for sorting
                        'start_time': new_start,
                        'end_time': new_end,
                        'type': scene.get('type', 'gameplay_icons'),
                        'script_text': scene.get('script_text', ''),
                        'elements': scene_elements
                    }
                    new_scenes.append(new_scene)
                
                # Replace original with splits
                timeline['scenes'] = timeline['scenes'][:i] + new_scenes + timeline['scenes'][i+1:]
        
        # Re-number scenes sequentially
        for i, scene in enumerate(timeline['scenes']):
            scene['scene_number'] = i + 1
        
        # === FIX 3.5: Fix scenes with negative duration (start_time > end_time) ===
        # This is a critical bug that causes all elements in a scene to be skipped
        scenes_to_remove = []
        for i, scene in enumerate(timeline['scenes']):
            start_time = scene.get('start_time', 0)
            end_time = scene.get('end_time', 0)
            duration = end_time - start_time
            
            if duration <= 0:
                print(f"[PLANNER] CRITICAL: Scene {scene.get('scene_number')} has invalid duration: {duration:.2f}s ({start_time:.2f}s - {end_time:.2f}s)")
                
                # Try to fix by swapping if it's just inverted
                if start_time > end_time:
                    # Check if there are elements that can help determine correct timing
                    elements = scene.get('elements', [])
                    if elements:
                        element_times = [e.get('timestamp', 0) for e in elements if e.get('timestamp')]
                        if element_times:
                            min_time = min(element_times)
                            max_time = max(element_times)
                            # Use element times to determine actual scene boundaries
                            scene['start_time'] = max(0, min_time - 0.5)
                            scene['end_time'] = max_time + 2.0  # Give some buffer after last element
                            print(f"[PLANNER]   -> Fixed using element timestamps: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s")
                        else:
                            # Just swap start and end
                            scene['start_time'], scene['end_time'] = end_time, start_time
                            print(f"[PLANNER]   -> Swapped start/end: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s")
                    else:
                        # No elements, swap times
                        scene['start_time'], scene['end_time'] = end_time, start_time
                        print(f"[PLANNER]   -> Swapped start/end: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s")
                elif duration == 0:
                    # Zero duration - give it a minimum of 2 seconds
                    scene['end_time'] = start_time + 2.0
                    print(f"[PLANNER]   -> Extended zero-duration scene to 2.0s")
                
                # Verify fix worked
                new_duration = scene['end_time'] - scene['start_time']
                if new_duration <= 0:
                    print(f"[PLANNER]   -> Could not fix scene, marking for removal")
                    scenes_to_remove.append(i)
        
        # Remove unfixable scenes (in reverse order to maintain indices)
        for i in reversed(scenes_to_remove):
            removed = timeline['scenes'].pop(i)
            print(f"[PLANNER] Removed unfixable scene {removed.get('scene_number')}")
        
        # Re-number scenes again after potential removals
        for i, scene in enumerate(timeline['scenes']):
            scene['scene_number'] = i + 1
        
        # === FIX 4: Ensure scenes cover full duration without gaps ===
        if timeline['scenes']:
            # Sort by start time
            timeline['scenes'].sort(key=lambda s: s['start_time'])
            
            # Fix ALL gaps and overlaps (even small ones can cause black frames)
            for i in range(len(timeline['scenes']) - 1):
                current = timeline['scenes'][i]
                next_scene = timeline['scenes'][i + 1]
                
                gap = next_scene['start_time'] - current['end_time']
                if gap > 0.05:  # Any gap > 50ms - tightened from 0.5s
                    if gap > 0.5:
                        print(f"[PLANNER] FIXING: {gap:.2f}s gap between scene {current['scene_number']} and {next_scene['scene_number']}")
                    # Extend current scene to fill gap (seamless transition)
                    current['end_time'] = next_scene['start_time']
                elif gap < -0.05:  # Any overlap > 50ms
                    if gap < -0.5:
                        print(f"[PLANNER] FIXING: {-gap:.2f}s overlap between scene {current['scene_number']} and {next_scene['scene_number']}")
                    # Trim current scene to remove overlap
                    current['end_time'] = next_scene['start_time']
            
            # Ensure first scene starts at EXACTLY 0.0s (critical to avoid black screen!)
            first_scene = timeline['scenes'][0]
            if first_scene['start_time'] > 0.01:  # Any non-zero start
                old_start = first_scene['start_time']
                print(f"[PLANNER] FIXING: First scene started at {old_start:.2f}s - adjusting to 0.0s")
                
                # Calculate offset needed
                offset = old_start
                
                # Adjust all elements in first scene to match the new start time
                if 'elements' in first_scene:
                    for element in first_scene['elements']:
                        # Shift element timestamps by the same offset
                        element['timestamp'] = max(0.0, element['timestamp'] - offset)
                
                first_scene['start_time'] = 0.0
                print(f"[PLANNER]   -> First scene now starts at 0.0s, elements adjusted by -{offset:.2f}s")
            
            # Ensure last scene covers remaining duration
            last_scene = timeline['scenes'][-1]
            if last_scene['end_time'] < total_duration - 0.5:
                print(f"[PLANNER] Extending last scene to cover full duration ({last_scene['end_time']:.1f}s -> {total_duration:.1f}s)")
                last_scene['end_time'] = total_duration
        
        # === FIX 5: Scale if timeline exceeds total duration ===
        if timeline['scenes']:
            last_scene = timeline['scenes'][-1]
            if last_scene['end_time'] > total_duration * 1.1:  # More than 10% over
                scale_factor = total_duration / last_scene['end_time']
                print(f"[PLANNER] Scaling timeline by {scale_factor:.2f}x to fit duration")
                for scene in timeline['scenes']:
                    scene['start_time'] *= scale_factor
                    scene['end_time'] *= scale_factor
                    if 'elements' in scene:
                        for element in scene['elements']:
                            element['timestamp'] *= scale_factor
        
        # === FIX 6: Ensure gameplay_icons scenes have enough elements ===
        # For longer videos, empty gameplay scenes are boring
        element_deficit = 0
        for scene in timeline['scenes']:
            if scene.get('type') == 'gameplay_icons':
                num_elements = len(scene.get('elements', []))
                scene_duration = scene['end_time'] - scene['start_time']
                # Expect at least 1 element per 4 seconds
                expected_elements = max(2, int(scene_duration / 4))
                
                if num_elements < expected_elements:
                    deficit = expected_elements - num_elements
                    element_deficit += deficit
                    print(f"[PLANNER] WARNING: Scene {scene['scene_number']} ({scene_duration:.1f}s) has only {num_elements} elements (expected {expected_elements})")
        
        if element_deficit > 5:
            print(f"[PLANNER] WARNING: Timeline has significant element deficit ({element_deficit} missing elements)")
            print(f"[PLANNER] This may result in boring sections with just gameplay - consider adding more keywords to script")
        
        # === FIX 7: Check for very long empty gaps ===
        # Any gameplay_icons scene longer than 20s with 0 elements is problematic
        for scene in timeline['scenes']:
            if scene.get('type') == 'gameplay_icons':
                duration = scene['end_time'] - scene['start_time']
                num_elements = len(scene.get('elements', []))
                if duration > 15 and num_elements == 0:
                    print(f"[PLANNER] CRITICAL: Scene {scene['scene_number']} is {duration:.1f}s with NO elements!")
                    print(f"[PLANNER]   This will be boring gameplay footage with no visual interest")
        
        # === FIX 8: Check if special scenes are clustered at the beginning ===
        # This detects when Claude front-loaded all the interesting scenes
        special_scene_types = ['data_graph', 'reddit_evidence', 'youtube_evidence', 'text_statement', 'split_comparison', 'broll']
        special_scenes = [s for s in timeline['scenes'] if s.get('type') in special_scene_types]
        
        if special_scenes and total_duration > 120:  # Only check for videos > 2 minutes
            last_special_time = max(s['end_time'] for s in special_scenes)
            first_third = total_duration / 3
            
            # Check if ALL special scenes are in the first third
            all_in_first_third = all(s['end_time'] <= first_third * 1.2 for s in special_scenes)
            
            if all_in_first_third:
                print(f"\n[PLANNER] WARNING: ALL {len(special_scenes)} special scenes end by {last_special_time:.1f}s!")
                print(f"[PLANNER] This is only {(last_special_time/total_duration)*100:.0f}% through the {total_duration:.0f}s video!")
                print(f"[PLANNER] The remaining {total_duration - last_special_time:.0f}s will be gameplay_icons only.")
                print(f"[PLANNER] -> Consider adding more Reddit/YouTube evidence or manually distributing scenes\n")
            
            # Also check for long stretches without any special scenes
            scenes_sorted = sorted(timeline['scenes'], key=lambda s: s['start_time'])
            prev_special_end = 0
            long_gaps = []
            
            for scene in scenes_sorted:
                if scene.get('type') in special_scene_types:
                    gap = scene['start_time'] - prev_special_end
                    if gap > 60:  # More than 60 seconds without a special scene
                        long_gaps.append((prev_special_end, scene['start_time'], gap))
                    prev_special_end = scene['end_time']
            
            # Check gap at the end
            final_gap = total_duration - prev_special_end
            if final_gap > 60:
                long_gaps.append((prev_special_end, total_duration, final_gap))
            
            if long_gaps:
                print(f"[PLANNER] WARNING: Found {len(long_gaps)} long stretch(es) without special scenes:")
                for start, end, gap in long_gaps:
                    print(f"[PLANNER]   {start:.0f}s - {end:.0f}s ({gap:.0f}s gap)")
        
        print(f"[PLANNER] Validation complete: {len(timeline['scenes'])} scenes")
        
        return timeline
    
    def _fill_empty_scenes(self, timeline, total_duration, use_timing=False):
        """
        CRITICAL FIX: Fill any gameplay_icons scenes that have no/few elements
        This prevents boring stretches in the middle of the video where nothing happens.
        
        Args:
            timeline: Validated timeline
            total_duration: Total video duration
            use_timing: If True, prefer keywords whose source sentence falls in the scene
        
        Returns:
            Timeline with empty scenes populated with elements
        """
        print("\n[PLANNER] === Checking for empty scenes to fill ===")
        
        if not self.available_keywords:
            print("[PLANNER] No keywords available for filling empty scenes")
            return timeline
        
        # First, find all keywords already used in the timeline
        used_keywords = set()
        for scene in timeline.get('scenes', []):
            for elem in scene.get('elements', []):
                kw = elem.get('keyword', elem.get('text', ''))
                if kw:
                    used_keywords.add(kw.lower())
        
        print(f"[PLANNER] {len(used_keywords)} keywords already used in timeline")
        
        # Find unused keywords
        unused_keywords = []
        for kw in self.available_keywords:
            kw_text = kw.get('word', kw) if isinstance(kw, dict) else kw
            if kw_text.lower() not in used_keywords:
                unused_keywords.append(kw)
        
        print(f"[PLANNER] {len(unused_keywords)} unused keywords available for filling")
        
        if not unused_keywords:
            print("[PLANNER] All keywords used - no more available for filling")
            return timeline
        
        # Find scenes that need filling - MORE AGGRESSIVE to prevent boring gaps
        # ANY gameplay scene with < 1 element per 2.5 seconds should be filled
        scenes_to_fill = []
        for scene in timeline.get('scenes', []):
            if scene.get('type') in ['gameplay_icons', 'gameplay_only']:
                duration = scene['end_time'] - scene['start_time']
                num_elements = len(scene.get('elements', []))
                
                # Calculate expected elements - MORE AGGRESSIVE: 1 per 2.5 seconds (was 4)
                expected_elements = max(2, int(duration / 2.5))
                # Intro boost: more elements in the first 10 seconds for stronger hook
                if scene.get('start_time', 0) < 10.0:
                    expected_elements = max(expected_elements, int(duration / 1.5))
                
                # Fill ANY scene with gaps, not just long ones (lowered from 8s to 4s)
                if duration > 4 and num_elements < expected_elements:
                    deficit = expected_elements - num_elements
                    scenes_to_fill.append({
                        'scene': scene,
                        'duration': duration,
                        'current_elements': num_elements,
                        'expected_elements': expected_elements,
                        'deficit': deficit
                    })
        
        if not scenes_to_fill:
            print("[PLANNER] All scenes have sufficient elements!")
        else:
            print(f"[PLANNER] Found {len(scenes_to_fill)} scenes needing more elements:")
            for info in scenes_to_fill:
                scene = info['scene']
                print(f"[PLANNER]   Scene {scene['scene_number']}: {info['duration']:.1f}s, has {info['current_elements']}/{info['expected_elements']} elements (need {info['deficit']} more)")
        
        # Distribute unused keywords across empty scenes
        total_elements_added = 0

        import re

        def _normalize_kw(text):
            return re.sub(r'[^a-z0-9 ]+', '', (text or '').lower()).strip()

        def _get_kw_time(kw):
            if not use_timing or not self.keyword_time_map:
                return None
            kw_text = kw.get('word', kw) if isinstance(kw, dict) else kw
            key = _normalize_kw(kw_text)
            times = self.keyword_time_map.get(key)
            if times:
                return min(times)
            return None

        def _pop_keyword_for_window(start, end):
            # Prefer keywords whose source sentence falls inside this window
            if use_timing and self.keyword_time_map:
                timed_candidates = []
                for idx, kw in enumerate(unused_keywords):
                    kw_time = _get_kw_time(kw)
                    if kw_time is not None and start <= kw_time <= end:
                        timed_candidates.append((idx, kw_time))
                if timed_candidates:
                    timed_candidates.sort(key=lambda t: t[1])
                    idx = timed_candidates[0][0]
                    return unused_keywords.pop(idx)

            # Fallback: only use ICONS if we don't know timing
            for idx, kw in enumerate(unused_keywords):
                display_type = kw.get('display_type', 'icon') if isinstance(kw, dict) else 'icon'
                if display_type != 'text':
                    return unused_keywords.pop(idx)

            return None
        
        for info in scenes_to_fill:
            scene = info['scene']
            deficit = info['deficit']
            scene_start = scene['start_time']
            scene_duration = info['duration']
            
            # Initialize elements list if not exists
            if 'elements' not in scene:
                scene['elements'] = []
            
            # Calculate timing for new elements
            # Distribute evenly across scene, avoiding existing element timestamps
            existing_times = [e.get('timestamp', 0) for e in scene['elements']]
            
            # Add elements to fill the deficit
            elements_added = 0
            time_step = scene_duration / (deficit + 1)
            
            for i in range(deficit):
                if not unused_keywords:
                    break
                
                # Calculate timestamp for new element
                new_timestamp = scene_start + (i + 1) * time_step
                
                # Avoid placing too close to existing elements
                too_close = any(abs(new_timestamp - et) < 1.5 for et in existing_times)
                if too_close:
                    # Shift slightly
                    new_timestamp += 0.8
                
                # Make sure timestamp is within scene bounds
                if new_timestamp >= scene['end_time'] - 0.5:
                    continue
                
                kw = _pop_keyword_for_window(scene_start, scene['end_time'])
                if not kw:
                    break
                
                # Get keyword info
                kw_text = kw.get('word', kw) if isinstance(kw, dict) else kw
                display_type = kw.get('display_type', 'icon') if isinstance(kw, dict) else 'icon'
                
                # Create element
                element = {
                    'type': 'text' if display_type == 'text' else 'icon',
                    'timestamp': new_timestamp,
                    'animation': 'zoom_in' if display_type == 'text' else 'scale_in'
                }
                
                if display_type == 'text':
                    element['text'] = kw_text
                else:
                    element['keyword'] = kw_text
                
                scene['elements'].append(element)
                existing_times.append(new_timestamp)
                elements_added += 1
                total_elements_added += 1
            
            if elements_added > 0:
                # Sort elements by timestamp
                scene['elements'].sort(key=lambda e: e.get('timestamp', 0))
                print(f"[PLANNER]   -> Added {elements_added} elements to scene {scene['scene_number']}")

        # NEW: Fill large internal gaps inside gameplay scenes (not just count-based deficits)
        for scene in timeline.get('scenes', []):
            if scene.get('type') not in ['gameplay_icons', 'gameplay_only']:
                continue
            if not unused_keywords:
                break
            if 'elements' not in scene or len(scene['elements']) < 1:
                continue
            gap_threshold = 2.0 if scene.get('start_time', 0) < 10.0 else 3.0  # seconds without icons = gap

            scene_start = scene['start_time']
            scene_end = scene['end_time']
            times = sorted([e.get('timestamp', 0) for e in scene['elements'] if e.get('timestamp') is not None])
            if not times:
                continue

            gaps = []
            if times[0] - scene_start > gap_threshold:
                gaps.append((scene_start, times[0]))
            for a, b in zip(times, times[1:]):
                if b - a > gap_threshold:
                    gaps.append((a, b))
            if scene_end - times[-1] > gap_threshold:
                gaps.append((times[-1], scene_end))

            if not gaps:
                continue

            existing_times = list(times)
            for gap_start, gap_end in gaps:
                if not unused_keywords:
                    break
                gap_len = gap_end - gap_start
                if gap_len < gap_threshold:
                    continue
                num_to_add = max(1, int(gap_len / 2.5))
                num_to_add = min(num_to_add, len(unused_keywords))
                step = gap_len / (num_to_add + 1)

                for i in range(num_to_add):
                    if not unused_keywords:
                        break
                    new_timestamp = gap_start + (i + 1) * step
                    if new_timestamp >= scene_end - 0.5:
                        continue
                    if any(abs(new_timestamp - et) < 1.2 for et in existing_times):
                        continue

                    kw = _pop_keyword_for_window(gap_start, gap_end)
                    if not kw:
                        break

                    kw_text = kw.get('word', kw) if isinstance(kw, dict) else kw
                    display_type = kw.get('display_type', 'icon') if isinstance(kw, dict) else 'icon'

                    element = {
                        'type': 'text' if display_type == 'text' else 'icon',
                        'timestamp': new_timestamp,
                        'animation': 'zoom_in' if display_type == 'text' else 'scale_in'
                    }
                    if display_type == 'text':
                        element['text'] = kw_text
                    else:
                        element['keyword'] = kw_text

                    scene['elements'].append(element)
                    existing_times.append(new_timestamp)
                    total_elements_added += 1

                scene['elements'].sort(key=lambda e: e.get('timestamp', 0))
        
        print(f"[PLANNER] Total elements added to fill gaps: {total_elements_added}")
        print(f"[PLANNER] Remaining unused keywords: {len(unused_keywords)}")
        
        return timeline
    
    def assign_timing(self, timeline, actual_voiceover_duration):
        """
        Adjust timeline based on actual voiceover duration
        (Call this after voiceover is generated)
        
        Args:
            timeline: Original timeline
            actual_voiceover_duration: Real duration from audio file
        
        Returns:
            Adjusted timeline
        """
        print(f"[PLANNER] Adjusting timeline to {actual_voiceover_duration:.1f}s")
        
        if not timeline['scenes']:
            return timeline
        
        # Calculate scaling factor
        estimated_duration = timeline['scenes'][-1]['end_time']
        scale_factor = actual_voiceover_duration / estimated_duration if estimated_duration > 0 else 1.0
        
        # Scale all times
        for scene in timeline['scenes']:
            scene['start_time'] *= scale_factor
            scene['end_time'] *= scale_factor
            # Only scale elements if the scene has them (some scene types don't)
            if 'elements' in scene:
                for element in scene['elements']:
                    element['timestamp'] *= scale_factor
        
        for transition in timeline['transitions']:
            transition['timestamp'] *= scale_factor
        
        return timeline
    
    def assign_timing_with_sentences(self, timeline, actual_duration, sentence_timings, section_number=None):
        """
        NEW: Adjust timeline using REAL sentence-level timing for maximum precision.
        This dramatically improves accuracy by using actual sentence durations.
        
        Args:
            timeline: Original timeline
            actual_duration: Total voiceover duration
            sentence_timings: List of sentence dicts with start_time, end_time, text, duration
            section_number: Optional section index for filtering assets
        
        Returns:
            Adjusted timeline with precise element timing
        """
        print(f"\n[PLANNER] ⚡ Using sentence-level timing for maximum precision (Section {section_number or 'ALL'})!")
        
        if not timeline['scenes']:
            return timeline
        
        # Build a quick lookup: text -> sentence timing
        sentence_lookup = {}
        for sent in sentence_timings:
            # Store by text (lowercased for matching)
            sentence_lookup[sent['text'].lower().strip()] = sent

        # Detect if the script itself has explicit part markers
        import re
        script_full_text = " ".join([s.get('text', '') for s in sentence_timings])
        script_has_part_markers = bool(re.search(
            r'\bpart\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b',
            script_full_text,
            re.IGNORECASE
        ))

        # Map keywords to their source sentence (from script analyzer) for precise timing
        keyword_sentence_map = {}
        for kw in (self.available_keywords or []):
            if isinstance(kw, dict):
                kw_text = kw.get('word', '').strip()
                kw_sentence = kw.get('sentence', '').strip()
            else:
                kw_text = str(kw).strip()
                kw_sentence = ''
            if kw_text and kw_sentence:
                key = re.sub(r'[^a-z0-9 ]+', '', kw_text.lower()).strip()
                if key:
                    keyword_sentence_map.setdefault(key, []).append(kw_sentence)

        # Build keyword -> time map and numeric -> sentence map for precise text/stat placement
        self.keyword_time_map = {}
        self.number_time_map = {}

        def _norm_text(text):
            return re.sub(r'[^a-z0-9 ]+', '', (text or '').lower()).strip()

        def _find_sentence_timing(sentence_text):
            sent_norm = _norm_text(sentence_text)
            if not sent_norm:
                return None
            for sent in sentence_timings:
                timing_norm = _norm_text(sent.get('text', ''))
                if sent_norm and (sent_norm in timing_norm or timing_norm in sent_norm):
                    return sent
            return None

        for kw in (self.available_keywords or []):
            if not isinstance(kw, dict):
                continue
            kw_text = kw.get('word', '').strip()
            kw_sentence = kw.get('sentence', '').strip()
            if not kw_text or not kw_sentence:
                continue
            sent_timing = _find_sentence_timing(kw_sentence)
            if not sent_timing:
                continue
            kw_key = _norm_text(kw_text)
            if kw_key:
                start_time = sent_timing.get('start_time', 0)
                self.keyword_time_map.setdefault(kw_key, []).append(start_time)
            # Map numeric tokens from the original keyword text (keep decimals)
            for num in re.findall(r'\d+(?:\.\d+)?', kw_text):
                self.number_time_map.setdefault(num, []).append(sent_timing)
        
        # For each scene with elements, update element timestamps using sentence-level precision
        for scene in timeline['scenes']:
            if 'elements' not in scene:
                continue
            
            script_text = scene.get('script_text', '').lower().strip()
            
            # Try to find which sentence(s) this scene covers
            matching_sentences = []
            for sent in sentence_timings:
                sent_text = sent['text'].lower().strip()
                # Remove punctuation for better matching
                import string
                sent_clean = sent_text.translate(str.maketrans('', '', string.punctuation))
                script_clean = script_text.translate(str.maketrans('', '', string.punctuation))
                
                # Check if sentence is in scene or scene text contains substantial part of sentence
                if sent_clean in script_clean or script_clean in sent_clean or (len(sent_clean) > 20 and sent_clean[:20] in script_clean):
                    matching_sentences.append(sent)
            
            # If still no match, try using the scene index to guess the sentence
            if not matching_sentences:
                scene_idx = timeline['scenes'].index(scene)
                # Proportional estimate
                sent_idx = int((scene_idx / len(timeline['scenes'])) * len(sentence_timings))
                if 0 <= sent_idx < len(sentence_timings):
                    matching_sentences = [sentence_timings[sent_idx]]
                    print(f"   [PLANNER] Scene {scene['scene_number']}: Using index-based sentence guess")
            
            if not matching_sentences:
                # Fallback: use time-based scaling (less precise but works)
                print(f"   [PLANNER] Scene {scene['scene_number']}: No exact sentence match, using time scaling")
                estimated_duration = timeline['scenes'][-1]['end_time']
                scale_factor = actual_duration / estimated_duration if estimated_duration > 0 else 1.0
                scene['start_time'] *= scale_factor
                scene['end_time'] *= scale_factor
                for element in scene['elements']:
                    element['timestamp'] *= scale_factor
                continue
            
            # Calculate scene boundaries from matching sentences
            scene_start = matching_sentences[0]['start_time']
            scene_end = matching_sentences[-1]['end_time']
            
            # CRITICAL: If this is Scene 1 (title card), it MUST start at 0
            if scene.get('scene_number') == 1:
                scene_start = 0.0
            
            scene['start_time'] = scene_start
            scene['end_time'] = scene_end
            
            print(f"   [PLANNER] Scene {scene['scene_number']}: {scene_start:.2f}s - {scene_end:.2f}s (matched {len(matching_sentences)} sentences)")
            
            # Now adjust each element's timestamp with sentence-level precision
            # Use the SAME approach as subtitles for perfect timing!
            for element in scene['elements']:
                element_keyword = element.get('keyword', element.get('text', '')).lower().strip()
                original_timestamp = element.get('timestamp', 0)
                
                # Remove punctuation for better matching
                import string
                element_keyword_clean = element_keyword.translate(str.maketrans('', '', string.punctuation))
                
                print(f"\n      [DEBUG] Processing element '{element_keyword}' (original ts: {original_timestamp:.2f}s, scene: {scene_start:.2f}s-{scene_end:.2f}s)")
                
                # Find which sentence contains this keyword - try multiple strategies
                element_sentence = None
                keyword_position_in_sentence = 0

                # CRITICAL FIX: Search ALL sentences, not just matching_sentences
                # This prevents timing errors when elements are assigned to wrong scenes by Claude
                search_sentences = sentence_timings  # Search ALL sentences for best match
                candidates = []

                # If we have a known source sentence for this keyword, prefer that FIRST
                source_sentences = keyword_sentence_map.get(element_keyword_clean, [])
                if source_sentences:
                    print(f"      [DEBUG] Found {len(source_sentences)} source sentence(s) from analyzer")
                    best_candidate = None
                    best_score = 0
                    for src_text in source_sentences:
                        src_norm = re.sub(r'[^a-z0-9 ]+', '', src_text.lower()).strip()
                        if not src_norm:
                            continue
                        for sent in sentence_timings:
                            sent_norm = re.sub(r'[^a-z0-9 ]+', '', sent.get('text', '').lower()).strip()
                            if src_norm and (src_norm in sent_norm or sent_norm in src_norm):
                                score = min(len(src_norm), len(sent_norm))
                                if score > best_score:
                                    best_score = score
                                    best_candidate = sent
                    if best_candidate:
                        element_sentence = best_candidate
                        keyword_position_in_sentence = re.sub(r'[^a-z0-9 ]+', '', best_candidate['text'].lower()).find(element_keyword_clean)
                        print(f"      [DEBUG] Matched via source sentence at {best_candidate['start_time']:.2f}s: \"{best_candidate['text'][:60]}...\"")

                # If keyword contains numbers, match to the sentence that mentions the number
                if not element_sentence and re.search(r'\d', element_keyword):
                    print(f"      [DEBUG] Trying numeric matching for '{element_keyword}'")
                    num_candidates = []
                    num_tokens = re.findall(r'\d+(?:\.\d+)?', element_keyword.replace(',', ''))
                    for sent in sentence_timings:
                        sent_text_raw = sent.get('text', '')
                        sent_norm_nums = re.sub(r',', '', sent_text_raw)
                        for num in num_tokens:
                            if num and num in sent_norm_nums:
                                # Prefer sentences with more token matches and earlier appearance
                                num_candidates.append((len(num), sent, num))
                    if num_candidates:
                        num_candidates.sort(key=lambda c: (-c[0], c[1].get('start_time', 0)))
                        best_sent = num_candidates[0][1]
                        best_num = num_candidates[0][2]
                        element_sentence = best_sent
                        keyword_position_in_sentence = re.sub(r'[^a-z0-9 ]+', '', best_sent['text'].lower()).find(best_num.replace('.', ''))
                        print(f"      [DEBUG] Matched via numeric token '{best_num}' at {best_sent['start_time']:.2f}s: \"{best_sent['text'][:60]}...\"")

                if element_sentence:
                    # Skip broader search if we already matched via source sentence
                    pass
                else:
                    candidates = []
                    keyword_words = element_keyword_clean.split() if element_keyword_clean else []

                    for sent in search_sentences:
                        sent_text = sent['text']
                        sent_lower = sent_text.lower()
                        sent_clean = sent_lower.translate(str.maketrans('', '', string.punctuation))
                        sent_words = sent_clean.split()

                        match_score = 0
                        match_ratio = 0.0
                        match_type = None
                        match_pos = 0

                        if element_keyword_clean and element_keyword_clean in sent_clean:
                            # Strategy 1: Direct substring match (highest confidence)
                            match_score = 3
                            match_ratio = 1.0
                            match_type = "direct"
                            match_pos = sent_clean.find(element_keyword_clean)
                        elif keyword_words:
                            # Strategy 2: Word-by-word consecutive match
                            for i in range(len(sent_words) - len(keyword_words) + 1):
                                match = True
                                for j, kw_word in enumerate(keyword_words):
                                    if i + j >= len(sent_words) or kw_word not in sent_words[i + j]:
                                        match = False
                                        break
                                if match:
                                    match_score = 2
                                    match_ratio = 1.0
                                    match_type = "phrase"
                                    match_pos = len(' '.join(sent_words[:i]))
                                    break

                            # Strategy 3: Partial match
                            if match_score == 0 and len(keyword_words) > 1:
                                words_found = sum(1 for kw_word in keyword_words if kw_word in sent_words)
                                match_ratio = words_found / len(keyword_words)
                                if match_ratio >= 0.6:  # At least 60% of words match
                                    match_score = 1
                                    match_type = "partial"
                                    for kw_word in keyword_words:
                                        if kw_word in sent_clean:
                                            match_pos = sent_clean.find(kw_word)
                                            break

                        if match_score > 0:
                            candidates.append({
                                'sent': sent,
                                'score': match_score,
                                'ratio': match_ratio,
                                'type': match_type,
                                'position': match_pos
                            })

                if candidates:
                    # Prefer strongest textual match, then earliest occurrence
                    candidates.sort(
                        key=lambda c: (-c['score'], -c['ratio'], c['sent'].get('start_time', 0))
                    )

                    best = candidates[0]
                    element_sentence = best['sent']
                    keyword_position_in_sentence = best['position']
                    print(f"      [DEBUG] Matched via fallback ({best['type']}) at {best['sent']['start_time']:.2f}s: \"{best['sent']['text'][:60]}...\"")
                
                if element_sentence:
                    # Calculate precise timing based on character/word position (like subtitles do!)
                    sent_text_clean = element_sentence['text'].translate(str.maketrans('', '', string.punctuation)).lower()
                    
                    if len(sent_text_clean) > 0:
                        # CRITICAL FIX: Clamp position to valid range
                        keyword_position_in_sentence = max(0, min(keyword_position_in_sentence, len(sent_text_clean) - 1))
                        
                        # Calculate position ratio based on characters
                        position_ratio = keyword_position_in_sentence / len(sent_text_clean)
                        position_ratio = max(0.0, min(1.0, position_ratio))  # Clamp to 0-1
                        
                        # Apply to actual sentence duration
                        offset_in_sentence = position_ratio * element_sentence['duration']
                        new_timestamp = element_sentence['start_time'] + offset_in_sentence
                        
                        # CRITICAL: Ensure timestamp is within sentence bounds
                        new_timestamp = max(element_sentence['start_time'], 
                                          min(new_timestamp, element_sentence['end_time'] - 0.1))
                        
                        old_timestamp = element['timestamp']
                        element['timestamp'] = new_timestamp
                        
                        print(f"      [DEBUG] ✓ New timestamp: {new_timestamp:.2f}s (was {old_timestamp:.2f}s, delta: {new_timestamp - old_timestamp:+.2f}s)")
                    else:
                        # Fallback: use sentence start
                        element['timestamp'] = element_sentence['start_time'] + 0.1
                        print(f"      [DEBUG] ✓ Using sentence start: {element_sentence['start_time'] + 0.1:.2f}s")
                else:
                    # Last resort: Keep original timestamp if reasonable, otherwise use estimated position
                    original_ts = element.get('timestamp', 0)
                    if 0 < original_ts < actual_duration:
                        # Original timestamp is valid - keep it
                        print(f"      [DEBUG] ✗ No sentence match - keeping original: {original_ts:.2f}s")
                    else:
                        # Use proportional position based on scene
                        element['timestamp'] = scene_start + 0.3
                        print(f"      [DEBUG] ✗ No sentence match - using scene start: {scene_start + 0.3:.2f}s")
        
        # === NEW: Re-distribute elements to correct scenes based on updated timestamps ===
        # CRITICAL: Only redistribute to gameplay_icons scenes
        # Evidence scenes (reddit, youtube, graph) should NEVER receive icons
        print("[PLANNER] Re-distributing elements to gameplay_icons scenes only...")
        
        # Define which scene types can receive elements (icons, text, memes)
        ICON_ALLOWED_SCENE_TYPES = ['gameplay_icons', 'gameplay_only']
        EVIDENCE_SCENE_TYPES = ['reddit_evidence', 'youtube_evidence', 'data_graph', 'text_statement']
        
        # Collect elements ONLY from gameplay scenes (not from evidence scenes)
        all_elements = []
        for scene in timeline['scenes']:
            scene_type = scene.get('type', 'gameplay_icons')
            if scene_type in ICON_ALLOWED_SCENE_TYPES:
                if 'elements' in scene:
                    for element in scene['elements']:
                        # Only collect icon/text/meme/quote elements
                        if element.get('type') in ['icon', 'text', 'meme', 'quote']:
                            all_elements.append(element)
                    scene['elements'] = []  # Clear for redistribution
            # Evidence scenes: keep their elements intact (reddit/youtube/graph)
        
        print(f"[PLANNER] Collected {len(all_elements)} icon/text/meme elements to redistribute")
        
        # Re-assign each element to the CORRECT gameplay_icons scene
        for element in all_elements:
            ts = element.get('timestamp', 0)
            assigned = False
            
            for scene in timeline['scenes']:
                scene_type = scene.get('type', 'gameplay_icons')
                scene_num = scene.get('scene_number', 1)
                
                # Skip scene 1 (title card)
                if scene_num == 1:
                    continue
                
                # Skip evidence scenes - they should NOT receive icons
                if scene_type in EVIDENCE_SCENE_TYPES:
                    continue
                
                # Check if timestamp falls in this scene
                if scene['start_time'] <= ts < scene['end_time']:
                    if 'elements' not in scene:
                        scene['elements'] = []
                    scene['elements'].append(element)
                    assigned = True
                    break
            
            if not assigned:
                # Find the nearest gameplay_icons scene for this element
                best_scene = None
                best_distance = float('inf')
                
                for scene in timeline['scenes']:
                    scene_type = scene.get('type', 'gameplay_icons')
                    scene_num = scene.get('scene_number', 1)
                    
                    if scene_num == 1 or scene_type in EVIDENCE_SCENE_TYPES:
                        continue
                    
                    # Calculate distance to scene
                    if ts < scene['start_time']:
                        distance = scene['start_time'] - ts
                    elif ts > scene['end_time']:
                        distance = ts - scene['end_time']
                    else:
                        distance = 0
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_scene = scene
                
                if best_scene:
                    if 'elements' not in best_scene:
                        best_scene['elements'] = []
                    best_scene['elements'].append(element)
                else:
                    elem_kw = element.get('keyword', element.get('text', 'element'))
                    print(f"[PLANNER] WARNING: No gameplay scene found for '{elem_kw}' at {ts:.2f}s - element dropped")
        
        # Sort elements in each scene
        for scene in timeline['scenes']:
            if 'elements' in scene:
                scene['elements'].sort(key=lambda e: e.get('timestamp', 0))

        # FIX: Ensure scenes don't overlap - sequential scenes should stay sequential
        # Sort scenes by original scene_number to preserve intended order
        scenes = timeline['scenes']
        scenes.sort(key=lambda s: s['scene_number'])
        
        # Minimum durations for evidence scenes - these need time to be readable!
        MIN_DURATIONS = {
            'youtube_evidence': 4.0,   # At least 4s to show thumbnail + title
            'reddit_evidence': 5.0,    # At least 5s to read the post
            'data_graph': 4.0,         # At least 4s to understand the graph
            'graph_visualization': 4.0,
        }
        
        # CRITICAL: Enforce minimum durations BEFORE overlap fixing
        # This ensures evidence scenes don't get compressed to unreadable lengths
        for scene in scenes:
            scene_type = scene.get('type', 'gameplay_icons')
            min_dur = MIN_DURATIONS.get(scene_type, 0)
            if min_dur > 0:
                actual_dur = scene['end_time'] - scene['start_time']
                if actual_dur < min_dur:
                    print(f"[PLANNER] FIX: {scene_type} scene {scene.get('scene_number')} too short ({actual_dur:.1f}s < {min_dur}s) - extending")
                    scene['end_time'] = scene['start_time'] + min_dur
        
        # Fix overlapping scenes by dividing overlapping time with priority for evidence scenes
        for i in range(1, len(scenes)):
            prev_scene = scenes[i - 1]
            curr_scene = scenes[i]
            
            # Check if current scene starts before or at the same time as previous ends
            if curr_scene['start_time'] < prev_scene['end_time']:
                overlap_start = curr_scene['start_time']
                overlap_end = prev_scene['end_time']
                
                # If they have the SAME start and end (exact overlap), divide the time with priority
                if abs(curr_scene['start_time'] - prev_scene['start_time']) < 0.1:
                    total_duration = prev_scene['end_time'] - prev_scene['start_time']
                    
                    # Check if either scene is an evidence scene that needs minimum duration
                    prev_min = MIN_DURATIONS.get(prev_scene['type'], 0)
                    curr_min = MIN_DURATIONS.get(curr_scene['type'], 0)
                    
                    # Calculate how to split the time
                    if prev_min > 0 and curr_min == 0:
                        # Previous is evidence, current is not - give prev the min (capped at total)
                        prev_duration = min(prev_min, total_duration)
                        prev_scene['end_time'] = prev_scene['start_time'] + prev_duration
                        curr_scene['start_time'] = prev_scene['end_time']
                        print(f"[PLANNER] FIX: Evidence scene {prev_scene['scene_number']} ({prev_scene['type']}) gets priority ({prev_duration:.1f}s)")
                    elif curr_min > 0 and prev_min == 0:
                        # Current is evidence, previous is not - give curr the min (capped at total)
                        curr_duration = min(curr_min, total_duration)
                        prev_duration = total_duration - curr_duration
                        if prev_duration < 0.5:
                            # Not enough room - give at least 0.5s to prev
                            prev_duration = min(0.5, total_duration * 0.3)
                            curr_duration = total_duration - prev_duration
                        prev_scene['end_time'] = prev_scene['start_time'] + prev_duration
                        curr_scene['start_time'] = prev_scene['end_time']
                        print(f"[PLANNER] FIX: Evidence scene {curr_scene['scene_number']} ({curr_scene['type']}) gets priority ({curr_duration:.1f}s)")
                    elif prev_min > 0 and curr_min > 0:
                        # Both are evidence - split proportionally based on min durations
                        total_min = prev_min + curr_min
                        prev_ratio = prev_min / total_min
                        prev_duration = total_duration * prev_ratio
                        prev_scene['end_time'] = prev_scene['start_time'] + prev_duration
                        curr_scene['start_time'] = prev_scene['end_time']
                        print(f"[PLANNER] FIX: Both scenes are evidence - split proportionally")
                    else:
                        # Neither is evidence - split 50/50
                        half_duration = total_duration / 2
                        prev_scene['end_time'] = prev_scene['start_time'] + half_duration
                        curr_scene['start_time'] = prev_scene['end_time']
                        print(f"[PLANNER] FIX: Scenes {prev_scene['scene_number']} and {curr_scene['scene_number']} overlapped - split 50/50")
                    
                    print(f"[PLANNER]      Scene {prev_scene['scene_number']}: {prev_scene['start_time']:.2f}s - {prev_scene['end_time']:.2f}s")
                    print(f"[PLANNER]      Scene {curr_scene['scene_number']}: {curr_scene['start_time']:.2f}s - {curr_scene['end_time']:.2f}s")
                else:
                    # Partial overlap - just adjust current scene to start after previous ends
                    curr_scene['start_time'] = prev_scene['end_time']
                    print(f"[PLANNER] FIX: Scene {curr_scene['scene_number']} start adjusted to {curr_scene['start_time']:.2f}s (after scene {prev_scene['scene_number']})")
                
                # CRITICAL: Ensure scene still has positive duration after adjustment
                if curr_scene['start_time'] >= curr_scene['end_time']:
                    # Scene became invalid - extend end time
                    curr_scene['end_time'] = curr_scene['start_time'] + 2.0
                    print(f"[PLANNER] WARNING: Scene {curr_scene['scene_number']} had negative duration after overlap fix - extended to {curr_scene['end_time']:.2f}s")
                
                # NOTE: Do NOT adjust element timestamps here!
                # The second redistribution pass will correctly place elements based on their
                # sentence-matched timestamps. Adjusting timestamps here corrupts accurate timing
                # and causes the "late icon spam" bug where icons appear 5+ seconds delayed.
                # Elements that no longer fit their scene will be redistributed correctly later.
        
        # FINAL PASS: Ensure ALL scenes have positive duration
        for scene in timeline['scenes']:
            duration = scene['end_time'] - scene['start_time']
            if duration <= 0:
                print(f"[PLANNER] FINAL FIX: Scene {scene.get('scene_number')} still has invalid duration {duration:.2f}s")
                scene['end_time'] = scene['start_time'] + 2.0

        # FINAL PASS: Clamp to actual voiceover duration and remove scenes beyond end
        scenes_clamped = []
        for scene in timeline['scenes']:
            if scene['start_time'] >= actual_duration:
                print(f"[PLANNER] Removing scene {scene.get('scene_number')} beyond voiceover end ({scene['start_time']:.2f}s)")
                continue
            if scene['end_time'] > actual_duration:
                print(f"[PLANNER] Capping scene {scene.get('scene_number')} end_time to {actual_duration:.2f}s")
                scene['end_time'] = actual_duration
            if scene['end_time'] <= scene['start_time']:
                print(f"[PLANNER] Dropping scene {scene.get('scene_number')} (invalid after clamp)")
                continue
            scenes_clamped.append(scene)
        timeline['scenes'] = scenes_clamped

        # NEW: Rebuild evidence scenes using sentence timing + asset metadata
        # This ensures Reddit/YouTube/Graph scenes correlate to the right script sentence/segment
        assets = timeline.get('_assets', {})
        segments = timeline.get('_segments', [])
        reddit_screenshots = assets.get('reddit_screenshots', []) or []
        youtube_cards = assets.get('youtube_cards', []) or []
        graphs = assets.get('graphs', []) or []

        # Collect gameplay elements before we rebuild scenes
        precollected_gameplay_elements = []
        print("\n[PLANNER] === Collecting gameplay elements before evidence rebuild ===")
        for scene in timeline['scenes']:
            for element in scene.get('elements', []):
                if element.get('type') in ['icon', 'text', 'meme', 'quote']:
                    elem_kw = element.get('keyword', element.get('text', 'element'))
                    elem_ts = element.get('timestamp', 0)
                    print(f"[PLANNER]   Collecting '{elem_kw}' @ {elem_ts:.2f}s (from scene {scene.get('scene_number')})")
                    precollected_gameplay_elements.append(element)

        # Helper for matching text
        import re
        def _norm_text(text):
            return re.sub(r'[^a-z0-9 ]+', '', (text or '').lower()).strip()

        # Build segment timing map (use sentence matches if possible, else estimated timing)
        segment_times = {}
        if segments:
            total_est = sum(seg.get('duration_estimate', 5) for seg in segments) or 1
            scale = actual_duration / total_est if total_est > 0 else 1.0
            cumulative = 0.0
            for seg in segments:
                seg_num = seg.get('segment_number', 1)
                seg_dur = seg.get('duration_estimate', 5)
                est_start = cumulative * scale
                cumulative += seg_dur
                est_end = cumulative * scale

                seg_text_norm = _norm_text(seg.get('text', ''))
                matching = []
                for sent in sentence_timings:
                    sent_norm = _norm_text(sent.get('text', ''))
                    if sent_norm and (sent_norm in seg_text_norm or seg_text_norm in sent_norm):
                        matching.append(sent)

                if matching:
                    start = matching[0]['start_time']
                    end = matching[-1]['end_time']
                else:
                    start = est_start
                    end = est_end

                segment_times[seg_num] = (max(0.0, start), min(actual_duration, end))

        # Track title card end (avoid evidence overlapping the title card)
        title_card_end = 0.0
        for scene in timeline['scenes']:
            if scene.get('scene_number') == 1 and scene.get('type') == 'text_statement':
                # CRITICAL: Title card only covers the FIRST sentence
                if sentence_timings:
                    scene['start_time'] = 0.0
                    scene['end_time'] = sentence_timings[0]['end_time']
                title_card_end = scene['end_time']
                break

        evidence_scenes = []

        # Helper: extract quote phrases from descriptions for precise matching
        def _extract_desc_phrases(desc):
            phrases = []
            if not desc:
                return phrases
            # Capture quoted phrases
            for match in re.findall(r'"([^"]+)"|\'([^\']+)\'', desc):
                phrase = match[0] or match[1]
                if phrase and len(phrase.strip()) > 4:
                    phrases.append(phrase.strip())
            # Capture common hint formats (e.g., "script says: ...")
            for token in ['script says:', 'matches:', 'match:', 'line:', 'says:']:
                idx = desc.lower().find(token)
                if idx != -1:
                    tail = desc[idx + len(token):].strip()
                    if tail:
                        phrase = tail.split('.')[0].strip()
                        if len(phrase) > 4:
                            phrases.append(phrase)
            # De-dup while preserving order
            seen = set()
            unique = []
            for p in phrases:
                key = _norm_text(p)
                if key and key not in seen:
                    seen.add(key)
                    unique.append(p)
            return unique

        def _match_phrase_to_sentence(phrase):
            phrase_norm = _norm_text(phrase)
            if not phrase_norm or len(phrase_norm) < 5:
                return None
            best = None
            best_score = 0
            for sent in sentence_timings:
                sent_norm = _norm_text(sent.get('text', ''))
                if phrase_norm and phrase_norm in sent_norm:
                    score = len(phrase_norm)
                    if score > best_score:
                        best = sent
                        best_score = score
            return best

        # Reddit evidence scenes based on matched_segment
        for idx, post in enumerate(reddit_screenshots):
            seg_num = post.get('matched_segment', 1)
            start = None
            end = None

            # Try to match by quoted phrase in description
            desc = post.get('description', '') or ''
            phrases = _extract_desc_phrases(desc)
            for phrase in phrases:
                matched = _match_phrase_to_sentence(phrase)
                if matched:
                    start = matched.get('start_time')
                    end = matched.get('end_time')
                    print(f"[PLANNER] Reddit post {idx} matched quote: \"{phrase[:50]}...\"")
                    break

            # Fallback to segment timing if no phrase match
            if start is None:
                seg_start, seg_end = segment_times.get(seg_num, (0.0, actual_duration))
                start = seg_start
                end = seg_end

            start = max(title_card_end + 0.1, start)
            target_dur = max(5.0, min(8.0, end - start if end else 6.0))
            end = min(start + target_dur, actual_duration)
            if end - start < 1.0:
                continue
            evidence_scenes.append({
                'scene_number': 0,
                'start_time': start,
                'end_time': end,
                'type': 'reddit_evidence',
                'script_text': post.get('description', ''),
                'elements': [{
                    'type': 'reddit',
                    'post_index': idx,
                    'timestamp': min(start + 0.3, end - 0.3),
                    'animation': 'slide_up'
                }]
            })

        # Rebuild evidence scenes based on title/note match to sentence timing
        for idx, card in enumerate(youtube_cards):
            title = card.get('title', '')
            note = card.get('note', '')
            channel = card.get('channel', '')
            phrases = [title, note, channel]
            start = None
            end = None

            # Try to match phrases to sentences first
            for sent in sentence_timings:
                sent_norm = _norm_text(sent.get('text', ''))
                for phrase in phrases:
                    phrase_norm = _norm_text(phrase)
                    if phrase_norm and len(phrase_norm) > 4 and phrase_norm in sent_norm:
                        start = sent.get('start_time')
                        end = sent.get('end_time')
                        print(f"[PLANNER] YouTube card '{title[:30]}' matched sentence: \"{sent['text'][:50]}...\"")
                        break
                if start is not None:
                    break

            # Fallback 1: Match to segment text
            if start is None and segments:
                for seg in segments:
                    seg_text_norm = _norm_text(seg.get('text', ''))
                    for phrase in phrases:
                        phrase_norm = _norm_text(phrase)
                        if phrase_norm and len(phrase_norm) > 4 and phrase_norm in seg_text_norm:
                            seg_num = seg.get('segment_number', 1)
                            seg_start, seg_end = segment_times.get(seg_num, (0.0, actual_duration))
                            start = seg_start
                            end = seg_end
                            print(f"[PLANNER] YouTube card '{title[:30]}' matched segment {seg_num}")
                            break
                    if start is not None:
                        break

            # Fallback 2: Check for "PART X" in the note/title
            if start is None:
                # Look for "PART 1", "PART 2", etc.
                part_match = re.search(r'PART\s*(\d+)', f"{title} {note}", re.IGNORECASE)
                if part_match:
                    part_num = int(part_match.group(1))
                    
                    # CRITICAL: If we are in a specific section, skip videos for OTHER parts
                    if section_number is not None and part_num != section_number:
                        print(f"[PLANNER] YouTube card '{title[:30]}' matches PART {part_num} but we are in SECTION {section_number} - skipping")
                        continue
                    
                    # If the script has no explicit part markers, don't force PART-based placement
                    if section_number is None and not script_has_part_markers:
                        print(f"[PLANNER] YouTube card '{title[:30]}' has PART {part_num} but script has no part markers - skipping")
                        continue
                        
                    # Find first segment in that part (assuming 1-indexed segments roughly map to parts)
                    # suele ser 3 segmentos por parte
                    seg_num = None
                    for seg in segments:
                        if f"PART {part_num}" in seg.get('text', '').upper():
                            seg_num = seg.get('segment_number')
                            break
                    
                    if seg_num is None:
                        # Crude estimate: part 1 = seg 1-3, part 2 = seg 4-6, etc.
                        seg_num = (part_num - 1) * 3 + 1
                    
                    if seg_num not in segment_times:
                        print(f"[PLANNER] YouTube card '{title[:30]}' PART {part_num} has no matching segment in script - skipping")
                        continue
                    
                    seg_start, seg_end = segment_times.get(seg_num, (0.0, actual_duration))
                    start = seg_start
                    end = seg_end
                    print(f"[PLANNER] YouTube card '{title[:30]}' matched via {part_match.group(0)}")

            if start is None:
                # Final Fallback: If it's mandatory or has content, don't skip it, just put it somewhere
                # but only if we really have to. For now, let's keep it skipped if no match found.
                print(f"[PLANNER] WARNING: No script match for YouTube card '{title[:40]}...' - skipping")
                continue

            if start is None:
                # Skip if we can't match - better to omit than show wrong evidence
                print(f"[PLANNER] WARNING: No script match for YouTube card '{title[:40]}...' - skipping")
                continue

            start = max(title_card_end + 0.1, start)
            base_end = end if end is not None else start + 4.0
            target_dur = max(4.0, min(6.0, base_end - start))
            end = min(start + target_dur, actual_duration)
            if end - start < 1.0:
                continue

            evidence_scenes.append({
                'scene_number': 0,
                'start_time': start,
                'end_time': end,
                'type': 'youtube_evidence',
                'script_text': title or note,
                'elements': [{
                    'type': 'youtube',
                    'youtube_index': idx,
                    'timestamp': min(start + 0.3, end - 0.3),
                    'animation': 'pop'
                }]
            })

        # Graph evidence scenes based on segment_hint or stat text
        for idx, graph in enumerate(graphs):
            seg_num = graph.get('segment_hint')
            start = None
            end = None

            # Prefer direct sentence matches to stat text/labels (more accurate)
            stat_texts = graph.get('stat_texts', []) or []
            labels = graph.get('labels', []) or []
            phrases = stat_texts + labels
            best_match = None
            best_score = 0

            for sent in sentence_timings:
                sent_norm = _norm_text(sent.get('text', ''))
                for phrase in phrases:
                    phrase_norm = _norm_text(phrase)
                    if phrase_norm and len(phrase_norm) > 3 and phrase_norm in sent_norm:
                        score = len(phrase_norm)
                        if score > best_score:
                            best_score = score
                            best_match = sent

            if best_match:
                start = best_match.get('start_time')
                end = best_match.get('end_time')
            elif isinstance(seg_num, int) and seg_num in segment_times:
                start, end = segment_times[seg_num]

            if start is None:
                continue

            start = max(title_card_end + 0.1, start)
            base_end = end if end is not None else start + 4.0
            target_dur = max(4.0, min(6.0, base_end - start))
            end = min(start + target_dur, actual_duration)
            if end - start < 1.0:
                continue

            evidence_scenes.append({
                'scene_number': 0,
                'start_time': start,
                'end_time': end,
                'type': 'data_graph',
                'script_text': graph.get('description', ''),
                'elements': [{
                    'type': 'graph',
                    'index': idx,
                    'timestamp': min(start + 0.3, end - 0.3),
                    'animation': 'fade_in'
                }]
            })

        # INTRO PACING: avoid back-to-back evidence in first 10s after title card
        if evidence_scenes:
            intro_window_end = min(actual_duration, title_card_end + 10.0)
            min_gap = 1.0
            max_intro_evidence = 4.0
            max_intro_total = 6.0
            intro_total = 0.0

            evidence_scenes.sort(key=lambda s: s['start_time'])
            last_end = title_card_end

            for scene in evidence_scenes:
                if scene['start_time'] <= intro_window_end:
                    dur = scene['end_time'] - scene['start_time']
                    if dur > max_intro_evidence:
                        scene['end_time'] = scene['start_time'] + max_intro_evidence
                        dur = max_intro_evidence

                    if scene['start_time'] - last_end < min_gap:
                        scene['start_time'] = last_end + min_gap
                        scene['end_time'] = min(scene['start_time'] + dur, actual_duration)

                    if intro_total + dur > max_intro_total:
                        scene['start_time'] = max(scene['start_time'], intro_window_end + 0.1)
                        scene['end_time'] = min(scene['start_time'] + dur, actual_duration)
                    else:
                        intro_total += dur
                        last_end = scene['end_time']

                    # Keep primary element inside new bounds
                    for elem in scene.get('elements', []):
                        elem['timestamp'] = min(scene['start_time'] + 0.3, scene['end_time'] - 0.3)

        # Keep only title card + evidence scenes, then rebuild gameplay coverage
        title_scene = None
        for scene in timeline['scenes']:
            if scene.get('scene_number') == 1 and scene.get('type') == 'text_statement':
                title_scene = scene
                break

        base_scenes = []
        if title_scene:
            base_scenes.append(title_scene)
        base_scenes.extend(evidence_scenes)
        timeline['scenes'] = base_scenes

        # NEW: Fill large gaps with gameplay scenes or extend existing gameplay scenes
        # The base video should always be gameplay with icons between evidence scenes
        if timeline['scenes']:
            scenes_sorted = sorted(timeline['scenes'], key=lambda s: s['start_time'])
            filled_scenes = []

            for i, scene in enumerate(scenes_sorted):
                if not filled_scenes:
                    # Gap at start
                    if scene['start_time'] > 0.1:
                        gap_scene = {
                            'scene_number': 0,
                            'start_time': 0.0,
                            'end_time': scene['start_time'],
                            'type': 'gameplay_icons',
                            'script_text': '(auto-filled gap)',
                            'elements': []
                        }
                        filled_scenes.append(gap_scene)
                    filled_scenes.append(scene)
                    continue

                prev_scene = filled_scenes[-1]
                gap = scene['start_time'] - prev_scene['end_time']

                if gap > 0.1:
                    # If previous scene is gameplay, extend it to fill gap
                    if prev_scene.get('type') == 'gameplay_icons':
                        prev_scene['end_time'] = scene['start_time']
                    else:
                        # Insert a gameplay scene to cover the gap
                        gap_scene = {
                            'scene_number': 0,
                            'start_time': prev_scene['end_time'],
                            'end_time': scene['start_time'],
                            'type': 'gameplay_icons',
                            'script_text': '(auto-filled gap)',
                            'elements': []
                        }
                        filled_scenes.append(gap_scene)

                filled_scenes.append(scene)

            # Gap at end
            last_scene = filled_scenes[-1]
            if last_scene['end_time'] < actual_duration - 0.1:
                if last_scene.get('type') == 'gameplay_icons':
                    last_scene['end_time'] = actual_duration
                else:
                    gap_scene = {
                        'scene_number': 0,
                        'start_time': last_scene['end_time'],
                        'end_time': actual_duration,
                        'type': 'gameplay_icons',
                        'script_text': '(auto-filled gap)',
                        'elements': []
                    }
                    filled_scenes.append(gap_scene)

            # Replace with gap-filled scenes
            timeline['scenes'] = filled_scenes

        # Preserve collected gameplay elements for redistribution after gap fill
        timeline['_precollected_elements'] = precollected_gameplay_elements
        
        # === CRITICAL: Final element redistribution (respecting evidence scenes) ===
        # This MUST happen after ALL scene time adjustments to prevent icon bursting
        # IMPORTANT: Evidence scenes keep their primary elements, gameplay scenes get icons
        print("[PLANNER] Final element redistribution (allowing icons over evidence)...")
        
        # Evidence scenes that should NOT receive icons
        EVIDENCE_BLOCK_TYPES = ['data_graph', 'text_statement']
        # All evidence-related scene types
        EVIDENCE_TYPES = ['reddit_evidence', 'youtube_evidence', 'data_graph', 'text_statement']
        # Scenes that can receive icons (including overlays on reddit/youtube)
        ICON_ALLOWED_SCENE_TYPES = ['gameplay_icons', 'gameplay_only', 'reddit_evidence', 'youtube_evidence']

        # Collect elements from GAMEPLAY scenes only (evidence scenes keep their elements)
        precollected = timeline.pop('_precollected_elements', None)
        if precollected is not None:
            all_gameplay_elements = precollected
            # Ensure gameplay scenes are empty before redistribution
            for scene in timeline['scenes']:
                if scene.get('type') not in EVIDENCE_TYPES:
                    scene['elements'] = []
        else:
            all_gameplay_elements = []
            for scene in timeline['scenes']:
                scene_type = scene.get('type', 'gameplay_icons')
                
                if scene_type in EVIDENCE_TYPES:
                    # Evidence scene - KEEP its elements (reddit/youtube/graph)
                    continue
                else:
                    # Gameplay scene - collect icon/text/meme elements for redistribution
                    for element in scene.get('elements', []):
                        if element.get('type') in ['icon', 'text', 'meme', 'quote']:
                            all_gameplay_elements.append(element)
                    scene['elements'] = []  # Clear gameplay scene elements for redistribution
        
        print(f"[PLANNER] Redistributing {len(all_gameplay_elements)} gameplay elements")
        
        # DEBUG: Print all element timestamps before redistribution
        print("\n[PLANNER] === Element timestamps at final redistribution ===")
        for elem in all_gameplay_elements[:10]:  # First 10
            elem_kw = elem.get('keyword', elem.get('text', 'element'))
            elem_ts = elem.get('timestamp', 0)
            print(f"[PLANNER]   '{elem_kw}' @ {elem_ts:.2f}s")
        if len(all_gameplay_elements) > 10:
            print(f"[PLANNER]   ... and {len(all_gameplay_elements) - 10} more")
        
        # DEBUG: Print scene boundaries
        print("\n[PLANNER] === Scene boundaries at final redistribution ===")
        for scene in timeline['scenes']:
            stype = scene.get('type', 'unknown')
            snum = scene.get('scene_number', '?')
            print(f"[PLANNER]   Scene {snum}: {scene['start_time']:.2f}s - {scene['end_time']:.2f}s ({stype})")
        
        # Sort elements by timestamp for proper ordering
        all_gameplay_elements.sort(key=lambda e: e.get('timestamp', 0))
        
        # Redistribute to correct GAMEPLAY scenes only
        redistribution_log = []
        for element in all_gameplay_elements:
            ts = element.get('timestamp', 0)
            elem_kw = element.get('keyword', element.get('text', 'element'))
            assigned = False
            
            for scene in timeline['scenes']:
                scene_type = scene.get('type', 'gameplay_icons')
                scene_num = scene.get('scene_number', 1)
                
                # Skip blocked scenes (title card, graphs)
                if scene_num == 1 or scene_type in EVIDENCE_BLOCK_TYPES:
                    continue
                
                # Allow landing in evidence scenes (reddit/youtube) or gameplay
                if scene_type not in ICON_ALLOWED_SCENE_TYPES:
                    continue
                
                in_range = scene['start_time'] <= ts < scene['end_time']
                if not in_range and scene_type in ['reddit_evidence', 'youtube_evidence']:
                    # Allow a small buffer so overlays land on evidence scenes even if slightly off
                    buffer = 0.75
                    if scene['start_time'] - buffer <= ts < scene['end_time'] + buffer:
                        in_range = True

                if in_range:
                    if 'elements' not in scene:
                        scene['elements'] = []
                    # Mark overlays for evidence scenes (reddit/youtube)
                    if scene_type in ['reddit_evidence', 'youtube_evidence']:
                        element['overlay'] = 'evidence'
                        element['position'] = 'center'
                    else:
                        element['position'] = 'center'
                    scene['elements'].append(element)
                    assigned = True
                    redistribution_log.append(f"'{elem_kw}' @ {ts:.2f}s -> Scene {scene_num} ({scene['start_time']:.2f}s-{scene['end_time']:.2f}s)")
                    break
            
            if not assigned:
                # Find the NEAREST valid scene
                best_scene = None
                best_distance = float('inf')
                for scene in timeline['scenes']:
                    scene_type = scene.get('type', 'gameplay_icons')
                    scene_num = scene.get('scene_number', 1)
                    
                    if scene_num == 1 or scene_type in EVIDENCE_BLOCK_TYPES:
                        continue
                    if scene_type not in ICON_ALLOWED_SCENE_TYPES:
                        continue
                    
                    mid_point = (scene['start_time'] + scene['end_time']) / 2
                    distance = abs(ts - mid_point)
                    if distance < best_distance:
                        # CRITICAL: Don't jump icons too far (max 3 seconds)
                        # If an icon is mentioned at 1s, it shouldn't show up at 15s
                        if distance < 3.0:
                            best_distance = distance
                            best_scene = scene
                
                if best_scene:
                    if 'elements' not in best_scene:
                        best_scene['elements'] = []
                    
                    # If we are moving it to a scene it doesn't belong in (fallback),
                    # assign it a timestamp at the start or end based on where it came from
                    if ts < best_scene['start_time']:
                        element['timestamp'] = best_scene['start_time'] + 0.2
                    else:
                        element['timestamp'] = best_scene['end_time'] - 0.4
                        
                    if best_scene.get('type') in ['reddit_evidence', 'youtube_evidence']:
                        element['overlay'] = 'evidence'
                        element['position'] = 'center'
                    best_scene['elements'].append(element)
                else:
                    elem_kw = element.get('keyword', element.get('text', 'element'))
                    print(f"[PLANNER] WARNING: Dropping element '{elem_kw}' at {ts:.2f}s - too far from any valid scene")
        
        if redistribution_log:
            print(f"\n[PLANNER] === Element Redistribution Summary ===")
            for log_line in redistribution_log[:15]:  # Show first 15
                print(f"[PLANNER]   {log_line}")
            if len(redistribution_log) > 15:
                print(f"[PLANNER]   ... and {len(redistribution_log) - 15} more")
        
        # === PRESERVE ACCURATE TIMING - Only fix BOUNDARY issues ===
        # We trust the sentence-level timing - only fix elements that are outside scene bounds
        # Let elements appear at their true times, even if close together

        # Fill any sparse gameplay scenes with additional icons AFTER redistribution
        # Avoids long stretches of gameplay without visuals
        timeline = self._fill_empty_scenes(timeline, actual_duration, use_timing=True)
        
        for scene in timeline['scenes']:
            if 'elements' not in scene or len(scene['elements']) < 1:
                continue
            
            scene_start = scene['start_time']
            scene_end = scene['end_time']
            
            # Sort by timestamp
            scene['elements'].sort(key=lambda e: e.get('timestamp', 0))
            
            # STAGGERING PASS: Ensure icons don't burst at once (even if in same sentence)
            scene_num = scene.get('scene_number', 0)
            scene_has_issues = False
            prev_time = scene_start - 1.0  # Initialize to before scene start
            MIN_GAP = 0.7  # Increased from 0.6s to 0.7s for better pacing
            stagger_log = []
            
            for element in scene['elements']:
                if element.get('type') not in ['icon', 'text', 'meme', 'quote']:
                    continue
                    
                elem_time = element.get('timestamp', scene_start)
                elem_kw = element.get('keyword', element.get('text', 'element'))
                original_elem_time = elem_time
                
                # If too close to previous element, push it forward
                if elem_time < prev_time + MIN_GAP:
                    old_time = elem_time
                    elem_time = prev_time + MIN_GAP
                    stagger_log.append(f"'{elem_kw}': {old_time:.2f}s -> {elem_time:.2f}s (staggered +{elem_time - old_time:.2f}s)")
                    scene_has_issues = True
                
                # If pushing it forward made it cross the scene boundary, drop it
                # instead of bunching it up at the very end
                if elem_time >= scene_end - 0.2:
                    element['timestamp'] = -100  # Mark for removal
                    stagger_log.append(f"'{elem_kw}': DROPPED (pushed beyond scene end)")
                    continue
                
                # Only clamp if actually outside bounds
                if elem_time < scene_start:
                    elem_time = scene_start + 0.15
                    stagger_log.append(f"'{elem_kw}': clamped to scene start")
                
                element['timestamp'] = elem_time
                prev_time = elem_time
            
            # Remove dropped elements
            scene['elements'] = [e for e in scene['elements'] if e.get('timestamp', 0) > -1.0]
            
            if stagger_log:  # Always show if there were any adjustments
                print(f"\n[PLANNER] === Staggering in Scene {scene_num} ({scene_start:.2f}s - {scene_end:.2f}s) ===")
                for log_line in stagger_log:
                    print(f"[PLANNER]   {log_line}")
            
            # DEBUG: Print final element timestamps after staggering
            if scene['elements']:
                print(f"[PLANNER] Scene {scene_num} final timestamps:")
                for elem in scene['elements'][:5]:
                    elem_kw = elem.get('keyword', elem.get('text', 'element'))
                    elem_ts = elem.get('timestamp', 0)
                    rel_ts = elem_ts - scene_start
                    print(f"[PLANNER]   '{elem_kw}' @ {elem_ts:.2f}s (relative: {rel_ts:.2f}s)")
        
        # Re-number scenes based on actual start_time ordering
        timeline['scenes'].sort(key=lambda s: s['start_time'])
        for i, scene in enumerate(timeline['scenes']):
            scene['scene_number'] = i + 1

        # Rebuild transitions to match the final scene order
        transitions = []
        for i in range(len(timeline['scenes']) - 1):
            transitions.append({
                'from_scene': i + 1,
                'to_scene': i + 2,
                'timestamp': timeline['scenes'][i]['end_time'],
                'type': 'crossfade'
            })
        timeline['transitions'] = transitions
        
        print(f"[PLANNER] Timeline adjusted with sentence-level precision\n")
        
        return timeline
    
    def plan_transitions(self, timeline):
        """
        Plan smooth transitions between scenes
        
        Args:
            timeline: Timeline dict
        
        Returns:
            Timeline with enhanced transition info
        """
        for i, transition in enumerate(timeline['transitions']):
            from_scene_idx = transition['from_scene'] - 1
            to_scene_idx = transition['to_scene'] - 1
            
            if from_scene_idx < len(timeline['scenes']) and to_scene_idx < len(timeline['scenes']):
                from_type = timeline['scenes'][from_scene_idx]['type']
                to_type = timeline['scenes'][to_scene_idx]['type']
                
                # Choose transition type based on scene types
                if from_type != to_type:
                    transition['type'] = 'crossfade'
                    transition['duration'] = 0.5
                else:
                    transition['type'] = 'cut'
                    transition['duration'] = 0.0
        
        return timeline
    
    def _validate_reddit_usage(self, timeline, reddit_screenshots):
        """
        Validate that Reddit posts are being used correctly in the timeline
        """
        print("\n[PLANNER] Validating Reddit post usage...")
        
        # Count Reddit scenes in timeline
        reddit_scenes = []
        for scene in timeline.get('scenes', []):
            if scene.get('type') in ['reddit_evidence', 'mixed_evidence']:
                # Check if it has elements with post_index
                for element in scene.get('elements', []):
                    if element.get('type') == 'reddit':
                        reddit_scenes.append(scene)
                        post_idx = element.get('post_index', -1)
                        print(f"   Scene {scene.get('scene_number')} uses Reddit post {post_idx}")
                        
                        # Check if this matches the intended segment
                        if post_idx >= 0 and post_idx < len(reddit_screenshots):
                            intended_segment = reddit_screenshots[post_idx].get('matched_segment', '?')
                            scene_time = scene.get('start_time', 0)
                            print(f"     Post was matched to segment {intended_segment}, appearing at {scene_time:.1f}s")
                        break
        
        # Warn if Reddit posts available but not used
        if len(reddit_screenshots) > 0 and len(reddit_scenes) == 0:
            print(f"   WARNING: {len(reddit_screenshots)} Reddit post(s) available but NONE used in timeline!")
            print(f"      Claude may have ignored the Reddit posts. This is a missed opportunity for evidence.")
        elif len(reddit_scenes) < len(reddit_screenshots):
            print(f"   INFO: Using {len(reddit_scenes)}/{len(reddit_screenshots)} Reddit posts (some were filtered)")
        else:
            print(f"   All {len(reddit_screenshots)} Reddit posts are being used")
        
        print("")
    
    def save_timeline(self, timeline, filename):
        """Save timeline to JSON file"""
        output_path = f"data/scripts/{filename}_timeline.json"
        os.makedirs("data/scripts", exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(timeline, f, indent=2)
        
        print(f"[PLANNER] Saved timeline to {output_path}")
        return output_path


if __name__ == "__main__":
    # Test the scene planner
    print("=" * 60)
    print("Testing Scene Planner")
    print("=" * 60)
    
    # Mock data
    test_segments = [
        {'segment_number': 1, 'text': 'Is Edgar broken?', 'type': 'hook', 'duration_estimate': 5},
        {'segment_number': 2, 'text': 'He has 60% win rate', 'type': 'data', 'duration_estimate': 8},
        {'segment_number': 3, 'text': 'Reddit agrees', 'type': 'evidence', 'duration_estimate': 7}
    ]
    
    test_keywords = [
        {'word': 'Edgar', 'importance': 10},
        {'word': 'broken', 'importance': 8},
        {'word': 'meta', 'importance': 6}
    ]
    
    test_reddit = [
        {'title': 'Edgar is overpowered', 'score': 1500}
    ]
    
    test_graphs = ['graph1.mp4']
    
    planner = ScenePlanner()
    timeline = planner.create_timeline(test_segments, test_keywords, test_reddit, test_graphs)
    
    print("\n" + "=" * 60)
    print("TIMELINE:")
    print("=" * 60)
    print(json.dumps(timeline, indent=2))
    
    # Save for inspection
    planner.save_timeline(timeline, "test_timeline")
