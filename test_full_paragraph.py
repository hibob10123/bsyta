"""Full paragraph test - Use this for testing with your actual script content"""
import sys
import os
import warnings

# Suppress DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Starting with ImageIO v3.*")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import VideoAutomationPipeline

script = """
Part I.
In 2024, Clash Royale was dying. It wasn’t just a feeling; the game was in a genuine death spiral. If you were around in 2023, you remember the "Update for Losers." You remember the introduction of Level 15. The community didn’t just dislike these updates; they revolted.

Supercell told us Level 15 would cost no gold, but then they locked it behind 50,000 Elite Wild Cards. The subreddit was on fire. Players calculated the math and realized their maxed-out accounts had basically been devalued overnight. The vibe was awful. The Pass Royale got more expensive while giving less value. Creators like B-rad were making videos titled "Clash Royale Has Failed Its Players," which racked up 1.4 million views. It was a PR nightmare.

And the financial data backed it up. In 2023, revenue dropped by nearly 10 percent. By November 2024, the monthly active user count had fallen from 17.8 million to a low of just 4.1 million players. The casual players evaporated, leaving only the hardcore whales. Search volume for the game hit multi-year lows. The game needed a miracle. It didn't need an update. It needed a savior.

Part 2: Enter The Mid-Ladder Menace
Enter Nicholas "Jynxzi" Stewart. He wasn’t a strategy pro. He was a Rainbow Six Siege streamer known for screaming and raging. And when he switched to Clash Royale, he broke every rule in the book. First off, he played a mobile game on a PC while holding a PlayStation controller. It was absurd. But it was also perfect content. He brought a chaotic energy that the game had been missing for years.

He didn't play optimal decks. He became the "Mid-Ladder Menace." He used the cards everyone hated—Mega Knight, Witch, Wizard—and he raged just like the rest of us. Then there was the Fan Mail. He turned his stream into a physical show. People sent him Clash Royale plushies, cosplay crowns, and troll items. If he lost a match, he’d throw the plushie across the room.

This created a viral loop. Clippers flooded TikTok and YouTube Shorts with his "Good Luck" screams and rage moments. Suddenly, millions of people who hadn't thought about Clash Royale since middle school were seeing it on their "For You" page every single day. He made the game look fun again by making it look chaotic.

Part 3: The Jynxzi Effect
So, did the screaming actually work? The data from 2025 is honestly shocking. In April 2025, the game’s revenue was sitting at a baseline of around 17.1 million dollars. But as Jynxzi hit viral mass in May, that number jumped to 27.7 million dollars.

But that was just the warm-up. By July 2025, revenue exploded from that 17 million dollar baseline to an incredible 82.7 million dollars in a single month. That was the game's best financial month since 2017. It made more money than Brawl Stars and Clash of Clans combined that month.

The player count tells the same story. Daily active users jumped from 17.8 million in April to 32.3 million in August. But here is the crazy part: data suggests most of these weren't new players. They were reactivations. 30 million dormant accounts logged back in. The "Jynxzi Kids"—mostly guys aged 18 to 23—came back to the game.

He even out-performed the official esports scene. His 20,000 dollar invitational tournament pulled more viewers than official competitive streams. Jynxzi didn't fix the economy. He didn't fix Level 15. The game was mechanically the same broken product from 2023. But he proved that in 2025, hype is more important than polish. He didn't just play the game; he saved it.


"""

# NEW FORMAT: Reddit posts with descriptions (from Gemini Deep Research)
# System will automatically match each post to the right part of the script
reddit_posts = [
    {
        "url": "https://www.reddit.com/r/ClashRoyale/comments/1jxi8es/the_game_is_dead/",
        "description": "PART 1 (INTRO). Overlay immediately after title card. Matches the opening hook: 'By the end of 2024, everyone knew the truth: Clash Royale was dying.'"
    },
    {
        "url": "https://www.reddit.com/r/ClashRoyale/comments/1c8mmr5/level_15_is_the_worst_thing/",
        "description": "PART 1 (THE REVOLT). Flash on screen when the script says: 'You remember the introduction of Level 15.' Visual proof of the backlash."
    },
    {
        "url": "https://www.reddit.com/r/ClashRoyale/comments/1p5i8t5/why_did_they_did_my_level_15_cards_to_level_14/",
        "description": "PART 1 (THE MATH). Overlay when the script says: 'Players calculated the math and realized their maxed-out accounts had basically been devalued.' Shows the specific complaint."
    },
    {
        "url": "https://www.reddit.com/r/ClashRoyale/comments/1oumg8j/jynxzi_kept_his_word_and_got_the_r9_haircut_after/",
        "description": "PART 2 (THE MENACE). Use this image for the line: 'It was absurd. But it was also perfect content.' The haircut visualizes the absurdity described."
    },
    {
        "url": "https://www.reddit.com/r/ClashRoyale/comments/1p451a9/the_fate_of_this_game_is_in_the_hands_of_this_guy/",
        "description": "PART 3 (OUTRO). Use for the final line: 'He didn't just play the game; he saved it.' Reinforces the savior narrative."
    }
]

# NEW: YouTube videos (evidence from content creators)
# System will download thumbnail and generate a clean card
youtube_videos = [
    {
        "url": "https://www.youtube.com/watch?v=D0EBpQyynrw",
        "title": "Clash Royale Has Failed Its Players",
        "channel": "B-rad",
        "views": "1.4M views",
        "note": "PART 1 (CREATORS). Mandatory match. Display the thumbnail/title when the script quotes it directly: 'Creators like B-rad were making videos titled...'"
    },
    {
        "url": "https://www.youtube.com/watch?v=UCtKbQP5KVw",
        "title": "Jynxzi Rages & Loses All His Trophies on Clash Royale",
        "channel": "Jynxzi Live",
        "views": "1.1M views",
        "note": "PART 2 (CHAOS). Use clips of him screaming/raging here. Matches: 'He was a Rainbow Six Siege streamer known for screaming and raging.'"
    },
    {
        "url": "https://www.youtube.com/watch?v=XpLa9-wMEm8",
        "title": "CLASH ROYALE FAN MAIL",
        "channel": "Jynxzi",
        "views": "2.1M views",
        "note": "PART 2 (FAN MAIL). Sync specifically with the line: 'Then there was the Fan Mail... If he lost a match, he’d throw the plushie across the room.'"
    },
    {
        "url": "https://www.youtube.com/watch?v=ZXBcVWQ1K4g",
        "title": "Can $1,000 Save a Dead Clash Royale Account? *JYNXZI REACTS*",
        "channel": "Jynxzi Live",
        "views": "721K views",
        "note": "PART 3 (REVENUE). Use footage of him buying gems/offers. Matches the section on financial data: 'Revenue exploded from that 17 million dollar baseline...'"
    },
    {
        "url": "https://www.youtube.com/watch?v=-MJkw_OjPh0",
        "title": "I won Jynxzi's tournament",
        "channel": "Orange Juice Gaming",
        "views": "2.2M views",
        "note": "PART 3 (ESPORTS). Overlay tournament bracket/gameplay when the script reads: 'His 20,000 dollar invitational tournament pulled more viewers than official competitive streams.'"
    }
]

output_name = "jynxzi_revival_test"

print("="*70)
print("FULL PARAGRAPH TEST")
print("="*70)
print(f"\nScript ({len(script.split())} words):")
print(script)
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
use_multipart = len(sections) > 1

print(f"\n{'='*70}")
print(f"PIPELINE MODE: {'MULTI-PART' if use_multipart else 'STANDARD'}")
print(f"{'='*70}")

try:
    if use_multipart:
        # Use multi-part pipeline for scripts with multiple sections
        # This processes each section separately for better reliability
        print("Using MULTI-PART pipeline (each section processed separately)")
        video_path = pipeline.run_multipart_pipeline(
            script_text=script,
            output_name=output_name,
            reddit_posts=reddit_posts if reddit_posts else None,
            youtube_videos=youtube_videos if youtube_videos else None
        )
    else:
        # Use standard pipeline for single-section scripts
        print("Using STANDARD pipeline")
        video_path = pipeline.run_full_pipeline(
            script_text=script,
            output_name=output_name,
            reddit_posts=reddit_posts if reddit_posts else None,
            youtube_videos=youtube_videos if youtube_videos else None
        )
    
    print("\n" + "="*70)
    print("SUCCESS!")
    print("="*70)
    print(f"Video saved: {video_path}")
    print("\nCheck the video - it should have:")
    print("  - Gameplay background (dimmed for evidence scenes)")
    print("  - Icons appearing for key terms (Edgar, nerf, etc.)")
    print("  - Graph showing win rate statistics")
    print("  - Reddit post(s) with community reactions")
    print("  - Background music playing throughout")
    print("  - Sound effects for transitions and icons")
    
except Exception as e:
    print(f"\n[ERROR] Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
