"""Full paragraph test - Use this for testing with your actual script content"""
import sys
import os
import warnings

# Suppress DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Starting with ImageIO v3.*")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import VideoAutomationPipeline

# ============================================================================
# CONFIGURATION: Which part to generate?
# ============================================================================
# Options:
#   None       = Generate ENTIRE script (auto-detects multipart)
#   "Part 1"   = Only generate Part 1 (single video)
#   "Part 2"   = Only generate Part 2 (single video)
#   "Part 3"   = Only generate Part 3 (single video)
#   etc.
#
# Why use this?
#   - Test individual parts quickly without waiting for full multipart video
#   - Fix timing/icons for one part at a time
#   - Avoid long processing times during development
#   - Bypass max_tokens issues with very long scripts
#
# NOTE: When generating a single part, reddit_posts and youtube_videos will
#       automatically filter to only use items tagged for that part.
# ============================================================================


PART_TO_GENERATE = "Part 4"  # Change to "Part 1", "Part 2", etc. or leave as None for full script

script = """
Your brain sees the drop almost split, or split once, and interprets it as "I almost won big." This creates an addiction loop that masks the actual quality of the rewards, which are often small amounts of Bling or experience points, not the Power Points you desperately need to afford Buffies.
Chaos Drops are the candy used to lure players into the van of the Buffie economy. They keep you engaged with the system despite the mathematical impossibility of free-to-play progression. Supercell buried the 475 dollar paywall under shiny animations and Ultra Legendary drops so the community would argue about drop rates instead of economic inflation.

"""
output_name = "buffies_p4_2"

# ============================================================================
# REDDIT POSTS & YOUTUBE VIDEOS
# ============================================================================
# Tag each item with (PART X) in the description/note so they can be filtered
# when generating individual parts using PART_TO_GENERATE above.
#
# When PART_TO_GENERATE is set (e.g., "Part 2"), only posts/videos with
# "(PART 2)" in their description will be included.
#
# When PART_TO_GENERATE is None, ALL posts/videos are used (multipart mode).
# ============================================================================

reddit_posts = [
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1p7mb3e/buffies_are_arguably_worse_than_power_lvl_12/",
        "description": "(PART 1) A thread literally titled 'Buffies are arguably worse than power lvl 12', which serves as the perfect evidence for your script's claim that Buffies are just Power Level 12 in disguise."
    },
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1qebl5v/there_is_no_economy/",
        "description": "(PART 1) A highly upvoted discussion arguing that the game is 'committing economic warfare' and that the economy is destroyed, aligning with your opening hook."
    },
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1q4j1r9/everyone_agrees_that_buffies_arent_good_for_the/",
        "description": "(PART 2) A highly relevant community thread discussing how 'Buffies' are detrimental to the game, aligning with the script's argument about the update being a 'trap' rather than content."
    },
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1po01ku/this_legitimately_might_be_one_of_the_worst/",
        "description": "(PART 3) A critical discussion specifically targeting the 'Buffies' update, useful for backing up the segment about the mechanical betrayal and negative player sentiment."
    },
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1q22tve/chaos_drops_are_garbage_and_this_game_is/",
        "description": "(PART 4) A thread calling Chaos Drops 'garbage' and a 'distraction', perfect for the section arguing that the flashy drops are just a lure to mask the poor economy."
    },
    {
        "url": "https://www.reddit.com/r/ClashRoyale/comments/14b3wsh/in_protest_of_level_15_do_not_upgrade_your_cards/",
        "description": "(PART 5) The historical Reddit thread from the Clash Royale Level 15 controversy, proving the 'subreddit was on fire' claim regarding the devaluation of maxed accounts."
    },
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1p7wyde/i_feel_like_this_will_be_the_biggest_nerf_to/",
        "description": "(PART 2) A thread titled 'I feel like this will be the biggest nerf to economy,' directly supporting the script's argument about the hidden costs of the update."
    },
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1prl1jn/things_i_like_and_dont_like_about_recent_updates/",
        "description": "(PART 2) Discussion specifically mentioning the 'Buffies claw machine' and calling the gem cost a crime, matching the 'Scam' narrative."
    },
    {
        "url": "https://www.reddit.com/r/BrawlStarsCompetitive/comments/1plxjsm/buffies_are_completely_broken/",
        "description": "(PART 3) A competitive subreddit analysis breaking down why 'Buffies are completely broken,' perfect for the segment on mechanical imbalances."
    },
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1pyui7b/buffies_are_a_problem_for_all_players_not_just_f2p/",
        "description": "(PART 3) A post arguing that Buffies hurt the game's integrity, mirroring the script's points about the 'Pay-to-Win Mechanics'."
    },
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1q22tve/chaos_drops_are_garbage_and_this_game_is/",
        "description": "(PART 4) A thread explicitly calling 'Chaos Drops garbage' and a 'distraction', aligning perfectly with the 'Chaos Drop Distraction' section."
    },
    {
        "url": "https://www.reddit.com/r/Brawlstars/comments/1ppxdx8/for_anyone_wondering_how_does_opening_chaos_drop/",
        "description": "(PART 4) A post showing the opening animation of Chaos Drops. Use this to illustrate the 'flashy animations' and 'splitting mechanic' discussed in the script."
    },
    {
        "url": "https://www.reddit.com/r/ClashRoyale/comments/11csee2/level_15_and_supercells_approach_to_monetization/",
        "description": "(PART 5) Historical thread from the Clash Royale Level 15 controversy, proving the 'subreddit was on fire' claim regarding monetization cycles."
    },
    {
        "url": "https://www.reddit.com/r/ClashRoyale/comments/1ou198v/level_16_will_cost_more_than_you_think/",
        "description": "(PART 5) A thread discussing future level costs (Level 16), reinforcing the 'Pattern' argument that Supercell constantly moves the goalposts."
    }
]

youtube_videos = [
    {
        "url": "https://www.youtube.com/shorts/2CgxTrEoFms",
        "title": "Did Brawl Stars Scam Us?",
        "channel": "Kashewz",
        "views": "451K views",
        "note": "(PART 1) A short, punchy clip asking if Supercell scammed players. Use this as a fast-paced hook to accompany the line about 'forensic analysis of the numbers'."
    },
    {
        "url": "https://www.youtube.com/watch?v=QbKuSWBQ2lY",
        "title": "The Hidden Cost of Buffies",
        "channel": "Bedlam",
        "views": "94K views",
        "note": "(PART 2) A breakdown video analyzing the economic impact of Buffies. Use this to visually support the 'forensic analysis' and cost breakdown of the $475 scam."
    },
    {
        "url": "https://www.youtube.com/watch?v=Q2PUp57M_gE",
        "title": "Buffies Update :: Brawl Stars",
        "channel": "Daneo Playz",
        "views": "N/A",
        "note": "(PART 3) Gameplay footage showing the unlocking and equipping of Buffies. Use this to demonstrate the 'Pay-to-Win Mechanics' and the actual in-game UI."
    },
    {
        "url": "https://www.youtube.com/watch?v=KQDDykeCqPE",
        "title": "Insane Chaos Drop Glitch",
        "channel": "Nubbz3 / SuperLab",
        "views": "367K views",
        "note": "(PART 4) Use the visual of opening these drops to illustrate the 'flashy animations' and 'splitting mechanic' designed to trigger dopamine responses."
    },
    {
        "url": "https://www.youtube.com/watch?v=daEOA_8_LOg&pp=ygUmaSB3aWxsIG5ldmVyIHVwZ3JhZGUgdG8gbGV2ZWwgMTUgYi1yYWQ%3D",
        "title": "The Disgusting Monetization of Clash Royale",
        "channel": "B-rad",
        "views": "1.5M views",
        "note": "(PART 5) The B-rad video protesting Level 15. Use this when the title is directly quoted. this is the core video documenting his refusal to upgrade, perfectly matching the 'I Will Never Upgrade' reference."
    },
    {
        "url": "https://www.youtube.com/watch?v=JVTkIxmSJ1c",
        "title": "I Bought EVERY Buffie! It cost me...",
        "channel": "KairosTime Gaming",
        "views": "260K views",
        "note": "(PART 2) KairosTime's spending spree video. Use the section where he calculates the total cost to visually back up the '$475' claim."
    },
    {
        "url": "https://www.youtube.com/watch?v=JvVLoyYSRiA",
        "title": "20 Balance Changes! | Brawl News!",
        "channel": "KairosTime Gaming",
        "views": "250K views",
        "note": "(PART 2) Use for general B-roll of the Update 65 changes and to show the 'previous' state of the game before the Buffie economy took over."
    },
    {
        "url": "https://www.youtube.com/watch?v=yFLNt9cvOhk",
        "title": "*BROKEN* 99% WIN RATE COMP WITH KIT",
        "channel": "SpenLC - Brawl Stars",
        "views": "39K views",
        "note": "(PART 3) Gameplay showing a 'broken' win rate. While featuring Kit, this visually demonstrates the 'unfair advantage' and lack of counterplay described."
    },
    {
        "url": "https://www.youtube.com/watch?v=hPhUVPET_XE",
        "title": "KIT IS FINALLY GETTING NERFED!!!!",
        "channel": "SpenLC - Brawl Stars",
        "views": "24K views",
        "note": "(PART 3) Use this to illustrate the cycle of 'release broken brawler -> nerf later', supporting the argument that mechanics are intentionally broken at launch."
    },
    {
        "url": "https://www.youtube.com/watch?v=w5Q1fQ5a1_A",
        "title": "I opened 1000 ULTRA LEGENDARY Chaos Drops",
        "channel": "BenTimm1",
        "views": "194K views",
        "note": "(PART 4) A massive opening video. Use the footage of the 'Ultra Legendary' drops and the splitting animations to demonstrate the 'gambling psychology' loop."
    },
    {
        "url": "https://www.youtube.com/shorts/K5WXTKA1BZ8",
        "title": "CHAOS DROP OPENING!",
        "channel": "RaxoR",
        "views": "6.4K views",
        "note": "(PART 4) A short clip showing the 'splitting' animation in action, perfect for a quick visual reference of the mechanic."
    },
    {
        "url": "https://www.youtube.com/watch?v=qwZY2HTd86Q",
        "title": "I reached Ultimate Champion without upgrading cards",
        "channel": "B-rad",
        "views": "1.3M views",
        "note": "(PART5) The specific B-rad video referenced in the script. Use the title card and his commentary to prove the 'I Will Never Upgrade' point."
    }
]






print("="*70)
print("FULL PARAGRAPH TEST")
print("="*70)

# ============================================================================
# EXTRACT SPECIFIC PART (if specified)
# ============================================================================
original_script = script
original_reddit = reddit_posts
original_youtube = youtube_videos

if PART_TO_GENERATE is not None:
    print(f"\n🎯 MODE: Generating ONLY {PART_TO_GENERATE}")
    print("="*70)
    
    pipeline = VideoAutomationPipeline()
    sections = pipeline.analyzer.detect_sections(script)
    
    # Find the specified part
    target_section = None
    for section in sections:
        section_title = section.get('title', '').lower()
        target_lower = PART_TO_GENERATE.lower()
        
        if target_lower in section_title or section_title.startswith(target_lower):
            target_section = section
            break
    
    if target_section:
        # Extract just this part's text
        script = target_section['text']
        print(f"✓ Extracted: {target_section['title']}")
        print(f"✓ Length: {target_section.get('word_count', len(script.split()))} words")
        
        # Filter reddit posts for this part only
        if reddit_posts:
            original_count = len(reddit_posts)
            filtered_reddit = []
            for post in reddit_posts:
                desc = post.get('description', '')
                # Check if description mentions this part
                if PART_TO_GENERATE.lower() in desc.lower() or f"(part {PART_TO_GENERATE[-1]})" in desc.lower():
                    filtered_reddit.append(post)
            reddit_posts = filtered_reddit
            print(f"✓ Filtered Reddit: {original_count} posts → {len(reddit_posts)} for {PART_TO_GENERATE}")
        
        # Filter YouTube videos for this part only
        if youtube_videos:
            original_count = len(youtube_videos)
            filtered_youtube = []
            for video in youtube_videos:
                note = video.get('note', '')
                # Check if note mentions this part
                if PART_TO_GENERATE.lower() in note.lower() or f"(part {PART_TO_GENERATE[-1]})" in note.lower():
                    filtered_youtube.append(video)
            youtube_videos = filtered_youtube
            print(f"✓ Filtered YouTube: {original_count} videos → {len(youtube_videos)} for {PART_TO_GENERATE}")
        
        # Update output name to include part
        part_suffix = PART_TO_GENERATE.lower().replace(" ", "_")
        output_name = f"{output_name}_{part_suffix}"
        
        print()
    else:
        print(f"⚠ WARNING: Could not find '{PART_TO_GENERATE}' in script")
        print(f"Available sections: {[s.get('title') for s in sections]}")
        print(f"Generating entire script instead...\n")
else:
    print(f"\n🎯 MODE: Generating ENTIRE SCRIPT (all parts)")
    print("="*70)

print(f"\nScript ({len(script.split())} words):")
print(script[:200] + "..." if len(script) > 200 else script)
print(f"\nReddit Posts: {len(reddit_posts) if reddit_posts else 'None (or AUTO SEARCH)'}")
if reddit_posts:
    for i, post in enumerate(reddit_posts[:3]):
        desc = post.get('description', post) if isinstance(post, dict) else 'URL only'
        print(f"  {i+1}. {desc[:60]}...")
print(f"\nOutput: data/output/{output_name}.mp4")
print("\nGenerating...\n")

pipeline = VideoAutomationPipeline()

# Detect sections first to decide which pipeline to use
sections = pipeline.analyzer.detect_sections(script)
use_multipart = len(sections) > 1 and PART_TO_GENERATE is None  # Only use multipart if not targeting specific part

print(f"\n{'='*70}")
if PART_TO_GENERATE:
    print(f"PIPELINE MODE: SINGLE PART ({PART_TO_GENERATE})")
else:
    print(f"PIPELINE MODE: {'MULTI-PART' if use_multipart else 'STANDARD'}")
print(f"{'='*70}")

# Filter reddit posts and youtube videos based on PART_TO_GENERATE
filtered_reddit_posts = reddit_posts
filtered_youtube_videos = youtube_videos

if PART_TO_GENERATE and reddit_posts:
    # Extract part number from PART_TO_GENERATE (e.g., "Part 5" -> "5")
    import re
    part_num_match = re.search(r'(\d+)', PART_TO_GENERATE)
    if part_num_match:
        part_num = part_num_match.group(1)
        part_tag = f"(PART {part_num})"  # e.g., "(PART 5)"
        
        filtered_reddit_posts = []
        excluded_posts = []
        
        for post in reddit_posts:
            desc = post.get('description', '').upper()
            # Match specifically for (PART X) pattern
            if re.search(rf'\(PART\s*{part_num}\)', desc, re.IGNORECASE):
                filtered_reddit_posts.append(post)
            else:
                excluded_posts.append(post)
        
        print(f"\n[FILTERING] Reddit posts for {PART_TO_GENERATE}:")
        print(f"  Total: {len(reddit_posts)}")
        print(f"  Included: {len(filtered_reddit_posts)}")
        print(f"  Excluded: {len(excluded_posts)}")
        
        if filtered_reddit_posts:
            print(f"\n  ✅ INCLUDED {len(filtered_reddit_posts)} posts:")
            for post in filtered_reddit_posts:
                print(f"     • {post.get('description', '')[:80]}")
        else:
            print(f"\n  ⚠ WARNING: No Reddit posts found tagged with {part_tag}")
            
        if excluded_posts:
            print(f"\n  ❌ EXCLUDED {len(excluded_posts)} posts (wrong part tags):")
            for post in excluded_posts[:3]:  # Show first 3 excluded
                desc_preview = post.get('description', '')[:60]
                print(f"     • {desc_preview}...")
    else:
        print(f"\n[FILTERING] WARNING: Could not parse part number from '{PART_TO_GENERATE}'")

if PART_TO_GENERATE and youtube_videos:
    import re
    part_num_match = re.search(r'(\d+)', PART_TO_GENERATE)
    if part_num_match:
        part_num = part_num_match.group(1)
        part_tag = f"(PART {part_num})"
        
        filtered_youtube_videos = []
        excluded_videos = []
        
        for video in youtube_videos:
            note = video.get('note', '').upper()
            # Match specifically for (PART X) pattern
            if re.search(rf'\(PART\s*{part_num}\)', note, re.IGNORECASE):
                filtered_youtube_videos.append(video)
            else:
                excluded_videos.append(video)
        
        print(f"\n[FILTERING] YouTube videos for {PART_TO_GENERATE}:")
        print(f"  Total: {len(youtube_videos)}")
        print(f"  Included: {len(filtered_youtube_videos)}")
        print(f"  Excluded: {len(excluded_videos)}")
        
        if filtered_youtube_videos:
            print(f"\n  ✅ INCLUDED {len(filtered_youtube_videos)} videos:")
            for video in filtered_youtube_videos:
                title = video.get('title', 'Unknown')
                print(f"     • {title} - {video.get('note', '')[:60]}")
        else:
            print(f"\n  ⚠ WARNING: No YouTube videos found tagged with {part_tag}")
            
        if excluded_videos:
            print(f"\n  ❌ EXCLUDED {len(excluded_videos)} videos (wrong part tags):")
            for video in excluded_videos[:3]:  # Show first 3 excluded
                title = video.get('title', 'Unknown')[:40]
                print(f"     • {title}...")
    else:
        print(f"\n[FILTERING] WARNING: Could not parse part number from '{PART_TO_GENERATE}'")

try:
    if use_multipart:
        # Use multi-part pipeline for scripts with multiple sections
        # This processes each section separately for better reliability
        print("Using MULTI-PART pipeline (each section processed separately)")
        video_path = pipeline.run_multipart_pipeline(
            script_text=script,
            output_name=output_name,
            reddit_posts=filtered_reddit_posts if filtered_reddit_posts else None,
            youtube_videos=filtered_youtube_videos if filtered_youtube_videos else None
        )
    else:
        # Use standard pipeline for single-section scripts
        if PART_TO_GENERATE:
            print(f"Using STANDARD pipeline for {PART_TO_GENERATE} only")
        else:
            print("Using STANDARD pipeline")
        video_path = pipeline.run_full_pipeline(
            script_text=script,
            output_name=output_name,
            reddit_posts=filtered_reddit_posts if filtered_reddit_posts else None,
            youtube_videos=filtered_youtube_videos if filtered_youtube_videos else None
        )
    
    print("\n" + "="*70)
    if PART_TO_GENERATE:
        print(f"SUCCESS! Generated {PART_TO_GENERATE} video")
    else:
        print("SUCCESS!")
    print("="*70)
    print(f"Video saved: {video_path}")
    if PART_TO_GENERATE:
        print(f"\nGenerated: {PART_TO_GENERATE} only ({len(script.split())} words)")
        print("\nTo generate other parts:")
        print(f"  1. Change PART_TO_GENERATE at line 42")
        print(f"  2. Run again: python test_full_paragraph.py")
    print("\nCheck the video - it should have:")
    print("  - Gameplay background (dimmed for evidence scenes)")
    print("  - Icons appearing for key terms")
    print("  - Evidence scenes (Reddit/YouTube/Graphs)")
    print("  - Background music playing throughout")
    print("  - Sound effects for transitions and icons")
    
except Exception as e:
    print(f"\n[ERROR] Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
