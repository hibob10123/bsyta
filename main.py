import os
import sys
import json
import warnings

# Suppress DeprecationWarnings from moviepy/imageio
warnings.filterwarnings("ignore", category=DeprecationWarning)
# Specifically target the imageio imread warning if needed, but the above is safer for overall cleanup
warnings.filterwarnings("ignore", message=".*Starting with ImageIO v3.*")

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, 'src'))
sys.path.append(os.path.join(current_dir, 'src', 'engine'))
sys.path.append(os.path.join(current_dir, 'src', 'scrapers'))
sys.path.append(os.path.join(current_dir, 'src', 'analysis'))
sys.path.append(os.path.join(current_dir, 'src', 'utils'))
# ------------------

from analysis.script_analyzer import ScriptAnalyzer
from analysis.research_assistant import ResearchAssistant
from scrapers.reddit_intelligence import RedditIntelligence
from scrapers.youtube_intelligence import YouTubeIntelligence
from scrapers.asset_gatherer import AssetGatherer
from scrapers.broll_gatherer import BRollGatherer
from engine.graph_generator import GraphGenerator
from engine.scene_planner import ScenePlanner
from engine.director_v3 import DirectorV3
from engine.voiceover import generate_voiceover
from utils.config_loader import load_config


class VideoAutomationPipeline:
    """
    Complete LLM-powered video automation pipeline
    Transforms scripts into polished videos with AI assistance
    """
    
    def __init__(self, config_path="config.yaml"):
        print("=" * 70)
        print("LLM-POWERED VIDEO AUTOMATION PIPELINE")
        print("=" * 70)
        
        # Load configuration
        self.config = load_config(config_path)
        self.config.ensure_directories()
        
        # Initialize all modules
        print("\n[INIT] Initializing modules...")
        self.analyzer = ScriptAnalyzer()
        self.reddit = RedditIntelligence()
        self.youtube = YouTubeIntelligence()
        self.assets = AssetGatherer()
        self.broll = BRollGatherer()
        self.graph_gen = GraphGenerator()
        self.planner = ScenePlanner()
        self.director = DirectorV3()
        
        # Optional research assistant
        if self.config.get('pipeline.do_research_assist'):
            self.research = ResearchAssistant()
        else:
            self.research = None
        
        print("[INIT] All modules ready!")
    
    def run_full_pipeline(self, script_text, reddit_posts=None, youtube_videos=None, output_name="final_video"):
        """
        Run the complete pipeline from script to video
        
        Args:
            script_text: The video script
            reddit_posts: Optional list of Reddit post dicts with 'url' and 'description'
            youtube_videos: Optional list of YouTube video dicts
                Example: [{"url": "...", "title": "...", "channel": "...", "note": "..."}]
            output_name: Name for output files
        
        Returns:
            Path to final video
        """
        print("\n" + "=" * 70)
        print("STARTING FULL PIPELINE")
        print("=" * 70)
        
        # Strip section markers so they aren't spoken
        script_text = self.analyzer.strip_section_markers(script_text)

        # STEP 1: Analyze Script with Claude
        print("\n" + "="*70)
        print("[STEP 1/8] Analyzing script with Claude...")
        print("="*70)
        analysis = self.analyzer.analyze_script(script_text)
        self.analyzer.save_analysis(analysis, output_name)
        
        print(f"   -> Found {len(analysis['keywords'])} keywords")
        print(f"   -> Found {len(analysis['claims'])} claims")
        print(f"   -> Found {len(analysis['statistics'])} statistics")
        print(f"   -> Main subject: {analysis['main_subject']}")
        
        # STEP 2: Gather Reddit Evidence (with smart matching)
        print("\n" + "="*70)
        print("[STEP 2/8] Gathering Reddit evidence...")
        print("="*70)
        reddit_posts_raw = []
        
        # Handle user-provided posts (can be URLs or dicts with descriptions)
        if reddit_posts:
            for post in reddit_posts:
                if isinstance(post, str):
                    # Old format: just URL
                    reddit_posts_raw.append({
                        'url': post,
                        'description': 'User provided (no description)',
                        'title': 'User provided',
                        'score': 0
                    })
                elif isinstance(post, dict):
                    # New format: URL + description
                    reddit_posts_raw.append({
                        'url': post.get('url', ''),
                        'description': post.get('description', 'User provided'),
                        'title': post.get('description', 'User provided')[:100],
                        'score': post.get('score', 0)
                    })
            print(f"   -> Added {len(reddit_posts)} user-provided posts")
        
        # Optional: Auto-search for additional posts (usually disabled when using Gemini)
        if self.config.get('pipeline.do_reddit_search') and analysis['claims'] and not reddit_posts:
            print("   -> No user posts provided, searching Reddit...")
            for claim in analysis['claims'][:3]:  # Top 3 claims
                found_posts = self.reddit.search_for_claim(
                    claim['claim'],
                    max_results=self.config.get('pipeline.reddit_max_posts', 5),
                    main_subject=analysis.get('main_subject')
                )
                if found_posts:
                    ranked_posts = self.reddit.rank_relevance(found_posts, claim['claim'])
                    for p in ranked_posts[:2]:
                        reddit_posts_raw.append({
                            'url': p.get('url', ''),
                            'description': p.get('title', ''),
                            'title': p.get('title', ''),
                            'score': p.get('score', 0)
                        })
        
        print(f"   -> Total Reddit posts: {len(reddit_posts_raw)}")
        
        # STEP 2.5: Gather YouTube Video Evidence
        print("\n" + "="*70)
        print("[STEP 2.5/8] Gathering YouTube evidence...")
        print("="*70)
        youtube_cards = []
        if youtube_videos:
            for i, video in enumerate(youtube_videos):
                if isinstance(video, str):
                    # Just URL provided - will use yt-dlp to get info
                    print(f"   -> Processing YouTube URL {i+1}...")
                    card_path = self.youtube.generate_youtube_graphic(
                        {'url': video},
                        output_path=f"data/assets/youtube_{output_name}_{i}.png"
                    )
                    if card_path:
                        youtube_cards.append({
                            'path': card_path,
                            'url': video,
                            'note': ''
                        })
                elif isinstance(video, dict):
                    # Full data provided
                    print(f"   -> Processing YouTube video {i+1}: {video.get('title', 'Unknown')[:40]}...")
                    card_path = self.youtube.generate_youtube_graphic(
                        video,
                        output_path=f"data/assets/youtube_{output_name}_{i}.png"
                    )
                    if card_path:
                        youtube_cards.append({
                            'path': card_path,
                            'url': video.get('url', ''),
                            'title': video.get('title', ''),
                            'channel': video.get('channel', ''),
                            'note': video.get('note', '')  # Description for Claude matching
                        })
            print(f"   -> Prepared {len(youtube_cards)} YouTube evidence cards")
        
        # Use RedditMatcher to intelligently place posts in script
        if reddit_posts_raw:
            from analysis.reddit_matcher import RedditMatcher
            matcher = RedditMatcher()
            
            # Match posts to script segments
            matched_posts = matcher.match_posts_to_script(
                analysis['segments'],
                reddit_posts_raw
            )
            
            print(f"   -> Matched {len(matched_posts)} posts to script segments")
        else:
            matched_posts = []
        
        # Screenshot Reddit posts (only high-relevance matched posts)
        reddit_screenshots = []
        posts_to_screenshot = [p for p in matched_posts if p.get('relevance_score', 0) >= 6][:5]  # Top 5 with score >= 6
        
        for i, post in enumerate(posts_to_screenshot):
            if 'url' in post and post['url']:
                print(f"   -> Screenshotting post {i+1} (relevance: {post.get('relevance_score', 0)}/10)...")
                screenshot_path = self.reddit.screenshot_with_highlight(
                    post['url'],
                    output_path=f"data/assets/reddit_{output_name}_{i}.png"
                )
                if screenshot_path:
                    reddit_screenshots.append({
                        'path': screenshot_path,
                        'url': post['url'],
                        'description': post.get('description', ''),
                        'matched_segment': post.get('matched_segment', 1),
                        'relevance_score': post.get('relevance_score', 0)
                    })
        
        # STEP 3: Generate Graphs (with metadata for intelligent placement)
        print("\n" + "="*70)
        print("[STEP 3/8] Generating data visualizations...")
        print("="*70)
        graphs = []  # List of dicts: {path, metric, description, labels, segment_hint}
        
        if self.config.get('pipeline.do_graph_generation') and analysis['statistics']:
            print(f"[GRAPH] Found {len(analysis['statistics'])} statistics in analysis")
            # Group statistics by metric to create combined charts
            from collections import defaultdict
            import re
            metric_groups = defaultdict(list)
            
            for stat in analysis['statistics']:
                metric = stat.get('metric', 'value')
                metric_groups[metric].append(stat)
            
            # Create one graph per metric group (need at least 2 data points)
            for metric, stats in metric_groups.items():
                print(f"[GRAPH] Metric '{metric}': {len(stats)} data point(s)")
                if len(stats) >= 2:
                    # Check if this is a time series (has years) or a comparison (has names)
                    has_years = any(re.search(r'(19|20)\d{2}', stat['stat_text']) for stat in stats)
                    
                    if has_years:
                        # Time series -> Line chart
                        print(f"   -> Creating line chart for {metric}...")
                        
                        x_vals = []
                        y_vals = []
                        
                        for stat in stats:
                            year_match = re.search(r'(19|20)\d{2}', stat['stat_text'])
                            if year_match:
                                x_vals.append(int(year_match.group()))
                            else:
                                x_vals.append(len(x_vals))
                            
                            y_vals.append(stat['value'])
                        
                        data = {
                            'x': x_vals, 
                            'y': y_vals,
                            'x_label': 'Year',
                            'y_label': metric.replace('_', ' ').title()
                        }
                        graph_name = f"{output_name}_graph_{len(graphs)}"
                        graph_path = self.graph_gen.create_dynamic_scene('line', data, graph_name)
                        
                        if graph_path:
                            # Create description for Claude
                            year_range = f"{min(x_vals)}-{max(x_vals)}"
                            value_range = f"{min(y_vals)}-{max(y_vals)}"
                            description = f"Line graph showing {metric.replace('_', ' ')} over time ({year_range}), values: {value_range}"
                            
                            # Find which segment mentions these years
                            segment_hint = self._find_segment_for_stats(analysis['segments'], stats)
                            
                            graphs.append({
                                'path': graph_path,
                                'metric': metric,
                                'description': description,
                                'labels': [str(x) for x in x_vals],
                                'segment_hint': segment_hint,
                                'stat_texts': [s['stat_text'] for s in stats]
                            })
                    else:
                        # Comparison (e.g., Edgar vs Mortis, or Clash Royale vs Brawl Stars) -> Bar chart
                        print(f"   -> Creating bar chart for {metric}...")
                        
                        # Extract names and values, preferring context field
                        labels = []
                        values = []
                        
                        for stat in stats:
                            # First try to use 'context' field if available
                            if 'context' in stat and stat['context']:
                                name = stat['context']
                            else:
                                # Try to extract name from stat_text (first word, or capitalized word)
                                text = stat['stat_text']
                                words = text.split()
                                
                                # Find capitalized word (likely the name)
                                name = None
                                for word in words:
                                    if word[0].isupper() and word.lower() not in ['is', 'the', 'a', 'an', 'in', 'july']:
                                        name = word
                                        break
                                
                                if not name:
                                    name = words[0] if words else f"Item {len(labels)+1}"
                            
                            labels.append(name)
                            values.append(stat['value'])
                        
                        # Determine appropriate x_label using Claude
                        x_label = self._determine_x_axis_label(labels, metric)
                        
                        # Format y_label nicely
                        y_label = metric.replace('_', ' ').replace('revenue millions', 'Revenue ($M)').title()
                        
                        # Create bar chart data
                        data = {
                            'labels': labels,
                            'values': values,
                            'x_label': x_label,
                            'y_label': y_label
                        }
                        graph_name = f"{output_name}_graph_{len(graphs)}"
                        graph_path = self.graph_gen.create_dynamic_scene('bar', data, graph_name)
                        
                        if graph_path:
                            # Create description for Claude
                            labels_str = ", ".join(labels)
                            description = f"Bar chart comparing {metric.replace('_', ' ')} for: {labels_str}"
                            
                            # Find which segment mentions these labels
                            segment_hint = self._find_segment_for_stats(analysis['segments'], stats)
                            
                            graphs.append({
                                'path': graph_path,
                                'metric': metric,
                                'description': description,
                                'labels': labels,
                                'segment_hint': segment_hint,
                                'stat_texts': [s['stat_text'] for s in stats]
                            })
                else:
                    # Single stat -> Skip creating graph (can't visualize single data point meaningfully)
                    print(f"   -> Skipping graph for '{metric}' (only 1 data point)")
                    print(f"   ->     Statistic: {stats[0]['stat_text']}")
                    print(f"   ->     TIP: Add comparisons to your script for graphs")
                    print(f"   ->     Example: 'X had 60%, while Y had 45%'")
        
        print(f"   -> Generated {len(graphs)} graphs")
        for i, g in enumerate(graphs):
            print(f"      Graph {i}: {g['description'][:60]}... (segment hint: {g.get('segment_hint', 'none')})")
        
        if len(graphs) == 0 and self.config.get('pipeline.do_graph_generation'):
            if not analysis['statistics']:
                print("\n[GRAPH] No statistics found in script")
                print("[GRAPH] To generate graphs, include comparisons like:")
                print("[GRAPH]   - 'Edgar has 60% win rate, Mortis has 45%'")
                print("[GRAPH]   - 'Revenue grew from $50M in 2020 to $84M in 2024'")
                print("[GRAPH]   - See SCRIPT_FORMATTING_GUIDE.md for more tips")
        
        # STEP 4: Gather Icon Assets (only for icon-type keywords)
        print("\n" + "="*70)
        print("[STEP 4/8] Gathering icon assets...")
        print("="*70)
        icon_assets = {}
        
        if self.config.get('pipeline.do_asset_gathering'):
            # DYNAMIC keyword limit based on estimated video length
            # Rule: ~20 icons per minute of video (aim for 1 icon every 3 seconds) - INCREASED
            estimated_duration = sum(seg.get('duration_estimate', 5) for seg in analysis['segments'])
            estimated_minutes = max(1, estimated_duration / 60)
            
            # Calculate dynamic limit: 20 icons per minute, minimum 20, maximum 150
            # More icons = less blank space in the video
            keyword_limit = int(min(150, max(20, estimated_minutes * 20)))
            
            print(f"   -> Video estimated at {estimated_duration:.0f}s ({estimated_minutes:.1f} min)")
            print(f"   -> Using {keyword_limit} keywords (dynamically calculated)")
            
            # Filter: Only prepare icons for keywords with display_type='icon'
            # Text-type keywords (dates, numbers) don't need image downloads
            all_keywords = analysis['keywords'][:keyword_limit]
            icon_keywords = [kw for kw in all_keywords if kw.get('display_type', 'icon') == 'icon']
            text_keywords = [kw for kw in all_keywords if kw.get('display_type', 'icon') == 'text']
            
            print(f"   -> {len(icon_keywords)} icon elements (need image download)")
            print(f"   -> {len(text_keywords)} text elements (will show as text overlay)")
            
            # Use script's main subject as context for better icon search
            context = analysis.get('main_subject', '')
            icon_assets = self.assets.batch_prepare(icon_keywords, context=context)
        
        print(f"   -> Prepared {len(icon_assets)} icon assets")
        
        # STEP 4.5: Gather B-Roll Assets (optional, based on script content)
        print("\n[STEP 4.5/8] Gathering b-roll assets...")
        broll_assets = {}
        
        if self.config.get('pipeline.do_asset_gathering'):
            # Generate b-roll queries based on main subject and key themes
            main_subject = analysis.get('main_subject', '')
            
            broll_queries = []
            if main_subject:
                broll_queries.append(f"{main_subject} gameplay")
            
            # Add queries for major keywords (up to 2)
            for kw in analysis['keywords'][:2]:
                if isinstance(kw, dict):
                    word = kw.get('word', '')
                    if word and len(word.split()) > 1:  # Multi-word terms make good b-roll
                        broll_queries.append(f"{main_subject} {word}")
            
            # Download b-roll (1-2 images per query)
            for query in broll_queries[:2]:  # Limit to 2 queries max
                images = self.broll.find_broll_images(query, count=2)
                if images:
                    broll_assets[query] = images
            
            print(f"   -> Prepared {sum(len(imgs) for imgs in broll_assets.values())} b-roll images")
        else:
            print(f"   -> B-roll gathering disabled in config")
        
        # STEP 5: Create Scene Timeline (with matched Reddit placements and b-roll)
        print("\n" + "="*70)
        print("[STEP 5/8] Creating video timeline with Claude...")
        print("="*70)
        timeline = self.planner.create_timeline(
            script_segments=analysis['segments'],
            keywords=analysis['keywords'],
            reddit_posts=matched_posts,  # Use matched posts with segment info
            reddit_screenshots=reddit_screenshots,  # Pass screenshots with metadata
            graphs=graphs,
            broll_assets=broll_assets,  # Pass b-roll images
            youtube_cards=youtube_cards  # Pass YouTube evidence cards
        )
        self.planner.save_timeline(timeline, output_name)
        
        # STEP 6: Generate Voiceover (SENTENCE-BY-SENTENCE for precise timing)
        print("\n" + "="*70)
        print("[STEP 6/8] Generating voiceover with ElevenLabs (sentence-level)...")
        print("="*70)
        
        from engine.voiceover import generate_voiceover_by_sentence
        voiceover_data = generate_voiceover_by_sentence(script_text, f"{output_name}_voiceover")
        
        if not voiceover_data:
            print("[ERROR] Voiceover generation failed!")
            return None
        
        voiceover_path = voiceover_data['combined_audio_path']
        actual_duration = voiceover_data['total_duration']
        sentence_timings = voiceover_data['sentences']
        
        print(f"\n[VOICE] ✓ Generated {len(sentence_timings)} sentence audio files")
        print(f"[VOICE] ✓ Total duration: {actual_duration:.2f}s")
        
        # Adjust timeline to match actual voiceover WITH sentence-level precision
        timeline = self.planner.assign_timing_with_sentences(
            timeline, 
            actual_duration,
            sentence_timings
        )
        
        # STEP 7: Map Sound Effects
        print("\n" + "="*70)
        print("[STEP 7/8] Mapping sound effects...")
        print("="*70)
        # SFX mapping happens inside director
        
        # STEP 8: Render Final Video
        print("\n" + "="*70)
        print("[STEP 8/8] Rendering final video...")
        print("="*70)
        output_path = os.path.join(
            self.config.get('paths.output_dir', 'data/output'),
            f"{output_name}.mp4"
        )
        
        final_video = self.director.render_video(
            timeline=timeline,
            voiceover_path=voiceover_path,
            output_path=output_path,
            sentence_timings=sentence_timings,  # Add sentence timings for subtitles
            reddit_screenshots=reddit_screenshots,  # Add Reddit metadata for proper matching
            graph_metadata=graphs,  # Add graph metadata for proper matching
            youtube_cards=youtube_cards  # Add YouTube evidence cards
        )
        
        if final_video:
            print("\n" + "=" * 70)
            print("PIPELINE COMPLETE!")
            print("=" * 70)
            print(f"\nFinal video: {final_video}")
            return final_video
        else:
            print("\n[ERROR] Video rendering failed!")
            return None
    
    def run_multipart_pipeline(self, script_text, reddit_posts=None, youtube_videos=None, output_name="final_video"):
        """
        Run the pipeline with automatic section detection.
        Each section is processed separately for better reliability on long videos.
        
        Args:
            script_text: The video script (can contain section markers)
            reddit_posts: Optional list of Reddit post dicts
            youtube_videos: Optional list of YouTube video dicts
            output_name: Name for output files
        
        Returns:
            Path to final video
        """
        print("\n" + "=" * 70)
        print("MULTI-PART VIDEO PIPELINE")
        print("=" * 70)
        
        # Step 1: Detect sections in the script
        sections = self.analyzer.detect_sections(script_text)
        
        if len(sections) <= 1:
            print("[MULTIPART] Only one section detected - using standard pipeline")
            return self.run_full_pipeline(script_text, reddit_posts, youtube_videos, output_name)
        
        print(f"\n[MULTIPART] Processing {len(sections)} sections separately...")
        
        # Get available gameplay files
        gameplay_files = self._get_gameplay_files()
        print(f"[MULTIPART] Found {len(gameplay_files)} gameplay file(s) for variety")
        
        # Get available music files
        music_files = self._get_music_files()
        print(f"[MULTIPART] Found {len(music_files)} music file(s) for variety")
        
        # Process each section
        part_videos = []
        part_timings = []  # For tracking cumulative timing
        cumulative_duration = 0.0
        
        for i, section in enumerate(sections):
            print(f"\n" + "=" * 70)
            print(f"PROCESSING SECTION {section['number']}/{len(sections)}: {section['title']}")
            print(f"=" * 70)
            print(f"Word count: {section['word_count']}")
            
            # Select gameplay file for this section (rotate through available files)
            gameplay_idx = i % len(gameplay_files)
            section_gameplay = gameplay_files[gameplay_idx]
            
            # Select music file for this section (rotate through available files)
            music_idx = i % len(music_files) if music_files else 0
            section_music = music_files[music_idx] if music_files else None
            
            print(f"[MULTIPART] Using gameplay: {os.path.basename(section_gameplay)}")
            if section_music:
                print(f"[MULTIPART] Using music: {os.path.basename(section_music)}")
            
            # Generate part video
            part_output = f"data/temp/part_{i+1}_{output_name}.mp4"
            
            try:
                # Create a temporary director with this section's gameplay and music
                from engine.director_v3 import DirectorV3
                section_director = DirectorV3(gameplay_path=section_gameplay, music_path=section_music)
                
                # Distribute Reddit posts and YouTube videos across sections
                # Each section gets a portion of the evidence based on content matching
                section_reddit = None
                section_youtube = None
                
                if reddit_posts:
                    # Give each section ~1/3 of posts (min 2 per section if available)
                    posts_per_section = max(2, len(reddit_posts) // len(sections))
                    start_idx = i * posts_per_section
                    end_idx = start_idx + posts_per_section
                    section_reddit = reddit_posts[start_idx:end_idx] if start_idx < len(reddit_posts) else None
                
                if youtube_videos:
                    # Give each section ~1/3 of videos (min 1 per section if available)
                    videos_per_section = max(1, len(youtube_videos) // len(sections))
                    start_idx = i * videos_per_section
                    end_idx = start_idx + videos_per_section
                    section_youtube = youtube_videos[start_idx:end_idx] if start_idx < len(youtube_videos) else None
                
                # Process this section
                part_video = self._process_section(
                    section=section,
                    section_number=i + 1,
                    total_sections=len(sections),
                    director=section_director,
                    reddit_posts=section_reddit,
                    youtube_videos=section_youtube,
                    output_path=part_output
                )
                
                if part_video and os.path.exists(part_video):
                    part_videos.append(part_video)
                    
                    # Get duration of this part
                    from moviepy.editor import VideoFileClip
                    with VideoFileClip(part_video) as clip:
                        part_duration = clip.duration
                    
                    part_timings.append({
                        'part': i + 1,
                        'title': section['title'],
                        'start': cumulative_duration,
                        'duration': part_duration,
                        'end': cumulative_duration + part_duration
                    })
                    cumulative_duration += part_duration
                    
                    print(f"[MULTIPART] Part {i+1} complete: {part_duration:.1f}s")
                else:
                    print(f"[MULTIPART] WARNING: Part {i+1} failed to generate")
                    
            except Exception as e:
                print(f"[MULTIPART] ERROR processing section {i+1}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if not part_videos:
            print("[MULTIPART] ERROR: No parts were generated!")
            return None
        
        # Step 2: Concatenate all parts with transitions
        print(f"\n" + "=" * 70)
        print(f"CONCATENATING {len(part_videos)} PARTS")
        print("=" * 70)
        
        final_output = os.path.join(
            self.config.get('paths.output_dir', 'data/output'),
            f"{output_name}.mp4"
        )
        
        final_video = self._concatenate_parts(part_videos, part_timings, final_output)
        
        # Cleanup temp files
        print("[MULTIPART] Cleaning up temporary files...")
        for part_file in part_videos:
            try:
                if os.path.exists(part_file):
                    os.remove(part_file)
            except:
                pass
        
        if final_video:
            print("\n" + "=" * 70)
            print("MULTI-PART PIPELINE COMPLETE!")
            print("=" * 70)
            print(f"\nFinal video: {final_video}")
            print(f"Total duration: {cumulative_duration:.1f}s ({cumulative_duration/60:.1f} minutes)")
            print(f"Sections: {len(sections)}")
            return final_video
        else:
            print("\n[ERROR] Video concatenation failed!")
            return None
    
    def _get_gameplay_files(self):
        """Get list of available gameplay video files"""
        gameplay_dir = "data/assets"
        gameplay_files = []
        
        # Check for main gameplay file
        main_gameplay = self.config.get('paths.gameplay_video', 'data/assets/gameplay.mp4')
        if os.path.exists(main_gameplay):
            gameplay_files.append(main_gameplay)
        
        # Look for additional gameplay files (gameplay_2.mp4, gameplay_3.mp4, etc.)
        for i in range(2, 10):
            alt_gameplay = os.path.join(gameplay_dir, f"gameplay_{i}.mp4")
            if os.path.exists(alt_gameplay):
                gameplay_files.append(alt_gameplay)
        
        # Also check config for gameplay_files list
        config_files = self.config.get('paths.gameplay_files', [])
        for cf in config_files:
            if os.path.exists(cf) and cf not in gameplay_files:
                gameplay_files.append(cf)
        
        # Fallback to just the main file
        if not gameplay_files:
            gameplay_files = [main_gameplay]
        
        return gameplay_files
    
    def _get_music_files(self):
        """Get list of available background music files for multi-part videos"""
        sfx_dir = self.config.get('paths.sfx_dir', 'data/sfx')
        music_files = []
        
        # Check config for music_files list first
        bg_music_config = self.config.get('background_music', {})
        config_files = bg_music_config.get('music_files', [])
        
        for mf in config_files:
            if os.path.exists(mf):
                music_files.append(mf)
        
        # If no music files in config, look for SONG files in sfx dir
        if not music_files:
            for i in range(1, 10):
                song_path = os.path.join(sfx_dir, f"(SONG{i}).mp3")
                if os.path.exists(song_path):
                    music_files.append(song_path)
        
        # Fallback to default path
        if not music_files:
            default_path = bg_music_config.get('path', 'data/sfx/(SONG1).mp3')
            if os.path.exists(default_path):
                music_files.append(default_path)
        
        return music_files
    
    def _process_section(self, section, section_number, total_sections, director, reddit_posts=None, youtube_videos=None, output_path=None):
        """
        Process a single section of the script.
        Similar to run_full_pipeline but for one section only.
        """
        # Strip section markers so they aren't spoken
        section_text = self.analyzer.strip_section_markers(section['text'])
        section_title = section['title']
        
        print(f"\n[SECTION {section_number}] Analyzing...")
        
        # Analyze this section
        analysis = self.analyzer.analyze_script(section_text)
        
        print(f"[SECTION {section_number}] Found {len(analysis['keywords'])} keywords")
        
        # Generate voiceover for this section
        print(f"[SECTION {section_number}] Generating voiceover...")
        from engine.voiceover import generate_voiceover_by_sentence
        
        voiceover_data = generate_voiceover_by_sentence(
            section_text, 
            f"section_{section_number}"
        )
        
        if not voiceover_data:
            print(f"[SECTION {section_number}] Voiceover generation failed!")
            return None
        
        voiceover_path = voiceover_data['combined_audio_path']
        actual_duration = voiceover_data['total_duration']
        sentence_timings = voiceover_data['sentences']
        
        print(f"[SECTION {section_number}] Voiceover: {actual_duration:.1f}s")
        
        # Gather icons for this section
        print(f"[SECTION {section_number}] Gathering icons...")
        
        # Dynamic keyword limit for this section - INCREASED for denser coverage
        # More icons = less blank space
        estimated_minutes = max(0.5, actual_duration / 60)
        keyword_limit = int(min(80, max(15, estimated_minutes * 20)))  # Increased from 12 to 20 per minute
        
        icon_keywords = [kw for kw in analysis['keywords'][:keyword_limit] 
                        if kw.get('display_type', 'icon') == 'icon']
        
        context = analysis.get('main_subject', '')
        icon_assets = self.assets.batch_prepare(icon_keywords, context=context)
        
        print(f"[SECTION {section_number}] Prepared {len(icon_assets)} icons")
        
        # Generate graphs for statistics in this section
        graphs = []
        if self.config.get('pipeline.do_graph_generation') and analysis['statistics']:
            print(f"[SECTION {section_number}] Generating graphs for {len(analysis['statistics'])} statistics...")
            from collections import defaultdict
            import re
            
            metric_groups = defaultdict(list)
            for stat in analysis['statistics']:
                metric = stat.get('metric', 'value')
                metric_groups[metric].append(stat)
            
            for metric, stats in metric_groups.items():
                if len(stats) >= 2:
                    has_years = any(re.search(r'(19|20)\d{2}', stat['stat_text']) for stat in stats)
                    
                    if has_years:
                        # Line chart for time series
                        x_vals = []
                        y_vals = []
                        for stat in stats:
                            year_match = re.search(r'(19|20)\d{2}', stat['stat_text'])
                            if year_match:
                                x_vals.append(int(year_match.group()))
                            else:
                                x_vals.append(len(x_vals))
                            y_vals.append(stat['value'])
                        
                        data = {
                            'x': x_vals, 
                            'y': y_vals,
                            'x_label': 'Year',
                            'y_label': metric.replace('_', ' ').title()
                        }
                        graph_name = f"section_{section_number}_graph_{len(graphs)}"
                        graph_path = self.graph_gen.create_dynamic_scene('line', data, graph_name)
                        
                        if graph_path:
                            # Find which segment mentions these statistics
                            segment_hint = self._find_segment_for_stats(analysis['segments'], stats)
                            
                            graphs.append({
                                'path': graph_path,
                                'metric': metric,
                                'description': f"Line graph: {metric}",
                                'segment_hint': segment_hint,
                                'stat_texts': [s['stat_text'] for s in stats]
                            })
                    else:
                        # Bar chart for comparisons
                        labels = [stat.get('context', f"Item {i}") for i, stat in enumerate(stats)]
                        values = [stat['value'] for stat in stats]
                        
                        data = {
                            'labels': labels,
                            'values': values,
                            'x_label': 'Category',
                            'y_label': metric.replace('_', ' ').title()
                        }
                        graph_name = f"section_{section_number}_graph_{len(graphs)}"
                        graph_path = self.graph_gen.create_dynamic_scene('bar', data, graph_name)
                        
                        if graph_path:
                            # Find which segment mentions these labels
                            segment_hint = self._find_segment_for_stats(analysis['segments'], stats)
                            
                            graphs.append({
                                'path': graph_path,
                                'metric': metric,
                                'description': f"Bar chart: {metric}",
                                'segment_hint': segment_hint,
                                'stat_texts': [s['stat_text'] for s in stats]
                            })
            
            print(f"[SECTION {section_number}] Generated {len(graphs)} graph(s)")
        
        # Process Reddit posts if provided for this section
        reddit_screenshots = []
        if reddit_posts:
            print(f"[SECTION {section_number}] Processing {len(reddit_posts)} Reddit posts...")
            try:
                # Match posts to this section's content
                from analysis.reddit_matcher import RedditMatcher
                matcher = RedditMatcher()
                matched_posts = matcher.match_posts_to_script(analysis['segments'], reddit_posts)
                
                # Screenshot the matched posts
                for i, post in enumerate(matched_posts[:3]):  # Max 3 posts per section
                    url = post.get('url', '')
                    if url:
                        screenshot_path = self.reddit.screenshot_with_highlight(
                            url, 
                            output_path=f"data/assets/section_{section_number}_reddit_{i}.png"
                        )
                        if screenshot_path:
                            reddit_screenshots.append({
                                'path': screenshot_path,
                                'url': url,
                                'description': post.get('description', ''),
                                'matched_segment': post.get('matched_segment', 1),
                                'relevance_score': post.get('relevance_score', 0)
                            })
                print(f"[SECTION {section_number}] Captured {len(reddit_screenshots)} Reddit screenshots")
            except Exception as e:
                print(f"[SECTION {section_number}] Reddit processing error: {e}")
                import traceback
                traceback.print_exc()
        
        # Process YouTube videos if provided for this section
        youtube_cards = []
        if youtube_videos:
            print(f"[SECTION {section_number}] Processing {len(youtube_videos)} YouTube videos...")
            try:
                for i, video in enumerate(youtube_videos[:2]):  # Max 2 videos per section
                    url = video.get('url', '')
                    if url:
                        card_path = self.youtube.generate_youtube_graphic(
                            video, 
                            output_path=f"data/assets/section_{section_number}_youtube_{i}.png"
                        )
                        if card_path:
                            youtube_cards.append({
                                'path': card_path,
                                'url': url,
                                'title': video.get('title', ''),
                                'channel': video.get('channel', ''),
                                'note': video.get('note', '')
                            })
                print(f"[SECTION {section_number}] Created {len(youtube_cards)} YouTube cards")
            except Exception as e:
                print(f"[SECTION {section_number}] YouTube processing error: {e}")
                import traceback
                traceback.print_exc()
        
        # Create timeline for this section
        print(f"[SECTION {section_number}] Creating timeline...")
        timeline = self.planner.create_timeline(
            script_segments=analysis['segments'],
            keywords=analysis['keywords'][:keyword_limit],
            reddit_posts=reddit_posts or [],
            reddit_screenshots=reddit_screenshots,
            graphs=graphs,
            broll_assets={},
            youtube_cards=youtube_cards
        )
        
        # Adjust timeline with actual voiceover timing
        timeline = self.planner.assign_timing_with_sentences(
            timeline,
            actual_duration,
            sentence_timings,
            section_number=section_number
        )
        
        # Render this section
        print(f"[SECTION {section_number}] Rendering video...")
        
        part_video = director.render_video(
            timeline=timeline,
            voiceover_path=voiceover_path,
            output_path=output_path,
            sentence_timings=sentence_timings,
            reddit_screenshots=reddit_screenshots,
            graph_metadata=graphs,  # Pass generated graphs
            youtube_cards=youtube_cards
        )
        
        return part_video
    
    def _concatenate_parts(self, part_videos, part_timings, output_path):
        """
        Concatenate video parts with smooth transitions and section title cards.
        """
        from moviepy.editor import (
            VideoFileClip, TextClip, CompositeVideoClip, 
            ColorClip, concatenate_videoclips
        )
        
        print(f"[CONCAT] Loading {len(part_videos)} video parts...")
        
        clips = []
        transition_duration = 0.5  # Fade duration between parts
        
        for i, (part_path, timing) in enumerate(zip(part_videos, part_timings)):
            try:
                # Load part video
                part_clip = VideoFileClip(part_path)
                
                # Add section title card for parts after the first
                if i > 0:
                    # Create title card (2 seconds)
                    title_duration = 2.0
                    
                    # Black background
                    bg = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=title_duration)
                    
                    # Section title text
                    try:
                        title_text = TextClip(
                            timing['title'],
                            fontsize=80,
                            color='white',
                            font='Arial-Bold',
                            stroke_color='gray',
                            stroke_width=2,
                            method='caption',
                            size=(1600, None)
                        ).set_duration(title_duration).set_position('center')
                        
                        title_card = CompositeVideoClip([bg, title_text], size=(1920, 1080))
                        title_card = title_card.crossfadein(0.3).crossfadeout(0.3)
                        
                        clips.append(title_card)
                        print(f"[CONCAT] Added title card for: {timing['title']}")
                    except Exception as e:
                        print(f"[CONCAT] Warning: Could not create title card: {e}")
                
                # Add crossfade to part
                if i > 0:
                    part_clip = part_clip.crossfadein(transition_duration)
                if i < len(part_videos) - 1:
                    part_clip = part_clip.crossfadeout(transition_duration)
                
                clips.append(part_clip)
                print(f"[CONCAT] Added part {i+1}: {part_clip.duration:.1f}s")
                
            except Exception as e:
                print(f"[CONCAT] Error loading part {i+1}: {e}")
                continue
        
        if not clips:
            print("[CONCAT] No clips to concatenate!")
            return None
        
        # Concatenate all clips
        print("[CONCAT] Concatenating clips...")
        final = concatenate_videoclips(clips, method="compose")
        
        # Write final video
        print(f"[CONCAT] Writing final video to {output_path}...")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            verbose=True,
            logger='bar'
        )
        
        # Cleanup
        for clip in clips:
            try:
                clip.close()
            except:
                pass
        final.close()
        
        return output_path
    
    def _find_segment_for_stats(self, segments, stats):
        """
        Find which script segment mentions the statistics
        Returns segment number or None
        """
        # Collect all text from stats to search for
        search_terms = []
        for stat in stats:
            search_terms.append(stat.get('stat_text', '').lower())
            if 'context' in stat:
                search_terms.append(stat['context'].lower())
        
        # Search through segments
        for segment in segments:
            segment_text = segment.get('text', '').lower()
            for term in search_terms:
                if term and len(term) > 3 and term in segment_text:
                    return segment.get('segment_number', 1)
        
        return None

    def _determine_x_axis_label(self, labels, metric):
        """
        Use Claude to determine the best x-axis label for a graph
        
        Args:
            labels: List of category labels (e.g., ["Clash Royale", "Brawl Stars"])
            metric: The metric being measured (e.g., "revenue_millions")
        
        Returns:
            Appropriate x-axis label string
        """
        from utils.claude_client import ClaudeClient
        
        try:
            claude = ClaudeClient()
            
            labels_str = ", ".join(labels)
            prompt = f"""Given these graph categories: {labels_str}
Metric: {metric}

What is the best generic x-axis label? Choose the most appropriate from these options:
- If they are game titles → "Game"
- If they are character/player names → "Character"  
- If they are company/brand names → "Company"
- If they are country/location names → "Location"
- If they are time periods → "Period"
- Otherwise → "Category"

Return ONLY ONE WORD - the label itself."""

            result = claude.ask(prompt, temperature=0.2)
            x_label = result.strip().strip('"').strip("'")
            
            # Validation
            valid_labels = ['Game', 'Character', 'Company', 'Location', 'Period', 'Category', 'Player', 'Team']
            if x_label not in valid_labels:
                x_label = 'Category'
            
            return x_label
            
        except Exception as e:
            print(f"[WARNING] Claude x-axis label generation failed: {e}")
            return 'Category'
    
    def quick_video(self, script_text, output_name="quick_video"):
        """
        Quick video generation with minimal Reddit/graph generation
        Good for testing
        """
        print("\n[QUICK MODE] Generating video with minimal processing...")
        
        # Analyze script
        analysis = self.analyzer.analyze_script(script_text)
        
        # Simple timeline (no Reddit, minimal graphs)
        timeline = self.planner.create_timeline(
            script_segments=analysis['segments'],
            keywords=analysis['keywords'][:5],
            reddit_posts=[],
            graphs=[]
        )
        
        # Generate voiceover
        voiceover_path = generate_voiceover(script_text, output_name)
        
        if not voiceover_path:
            return None
        
        # Render
        output_path = os.path.join(
            self.config.get('paths.output_dir'),
            f"{output_name}.mp4"
        )
        
        return self.director.render_video(timeline, voiceover_path, output_path)


def main():
    """Main entry point"""
    
    # Initialize pipeline
    pipeline = VideoAutomationPipeline()
    
    # Example script (replace with your own)
    user_script = """
    Is Edgar completely broken right now? This character has dominated the meta for weeks.
    He has a win rate of over 60 percent in Showdown and it is ruining the game for everyone.
    Players are frustrated because Edgar requires zero skill to use effectively.
    Reddit users are constantly sharing clips of him jumping on enemies with his super.
    The community has been begging for a nerf, but Supercell hasn't responded yet.
    Compare this to characters like Spike who sit at 49% win rate - perfectly balanced.
    Will Edgar finally get the nerf he deserves? Only time will tell.
    """
    
    # Optional: Provide specific Reddit URLs
    reddit_urls = [
        # "https://www.reddit.com/r/BrawlStars/comments/...",
    ]
    
    # Optional: Provide specific Tweets
    tweets = [
        # "https://twitter.com/Supercell/status/...",
        # {"text": "This update is insane!", "user": "ProPlayer", "handle": "@pro_player"}
    ]
    
    # Run the full pipeline
    pipeline.run_full_pipeline(
        script_text=user_script,
        reddit_posts=None, # Can pass dicts with 'url' and 'description'
        tweets=tweets if tweets else None,
        output_name="edgar_video"
    )


if __name__ == "__main__":
    main()
