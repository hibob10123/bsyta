"""
Reddit Post Matcher - Intelligently matches Reddit posts to script segments
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.claude_client import ClaudeClient

class RedditMatcher:
    """
    Uses LLM to match Reddit posts (with descriptions) to appropriate
    locations in the video script
    """
    
    def __init__(self):
        self.claude = ClaudeClient()
    
    def match_posts_to_script(self, script_segments, reddit_posts_with_desc):
        """
        Match Reddit posts to script segments based on relevance
        
        Args:
            script_segments: List of segment dicts from script analyzer
            reddit_posts_with_desc: List of dicts with 'url' and 'description'
                Example: [
                    {
                        "url": "https://reddit.com/...",
                        "description": "Community discussing player count growth"
                    }
                ]
        
        Returns:
            List of dicts with matched posts and their ideal placement:
            [
                {
                    "url": "...",
                    "description": "...",
                    "matched_segment": 2,
                    "relevance_score": 9,
                    "reason": "Post discusses player growth mentioned in segment 2"
                }
            ]
        """
        if not reddit_posts_with_desc or not script_segments:
            return []
        
        print(f"[REDDIT_MATCHER] Matching {len(reddit_posts_with_desc)} Reddit posts to {len(script_segments)} script segments...")
        
        # Prepare script summary
        script_summary = "\n".join([
            f"Segment {s['segment_number']}: \"{s['text'][:100]}...\" (type: {s['type']})"
            for s in script_segments
        ])
        
        # Prepare Reddit posts summary
        posts_summary = "\n".join([
            f"Post {i+1}: {p.get('description', 'No description')}\n   URL: {p.get('url', '')}"
            for i, p in enumerate(reddit_posts_with_desc)
        ])
        
        prompt = f"""You are matching Reddit posts to video script segments for a documentary-style gaming video.

SCRIPT SEGMENTS:
{script_summary}

REDDIT POSTS TO PLACE:
{posts_summary}

For each Reddit post, determine:
1. Which script segment it's most relevant to.
2. A relevance score (0-10, where 10 is perfect match).
3. Brief reason for the match.

CRITICAL RULES FOR MATCHING:
1. **RESPECT "PART X" HINTS**: If a post description starts with "PART 1", "PART 2", etc., you MUST match it to a segment that belongs to that part of the story.
2. **SEMANTIC MATCHING**: Match based on specific topics, names, or events.
3. **DO NOT FORCE MATCH**: If a post is for "PART 2" but the script segments provided only cover "PART 1", assign `matched_segment: -1` and `relevance_score: 0`.
4. **CHRONOLOGICAL ORDER**: Reddit posts should generally appear in the order they are listed if they match sequential segments.

Return a JSON array:
[
  {{
    "post_number": 1,
    "matched_segment": 2,
    "relevance_score": 9,
    "reason": "Post matches 'PART 1' and discusses Level 15 mentioned in segment 2"
  }},
  ...
]

Return ONLY the JSON array."""

        matches = self.claude.ask_json(prompt, temperature=0.3)
        
        if not matches:
            print("[REDDIT_MATCHER] Claude matching failed, using fallback")
            return self._fallback_matching(script_segments, reddit_posts_with_desc)
        
        # Combine matches with original post data
        matched_posts = []
        for match in matches:
            post_idx = match.get('post_number', 1) - 1
            if 0 <= post_idx < len(reddit_posts_with_desc):
                post_data = reddit_posts_with_desc[post_idx].copy()
                post_data.update({
                    'matched_segment': match.get('matched_segment', 1),
                    'relevance_score': match.get('relevance_score', 5),
                    'reason': match.get('reason', 'Auto-matched')
                })
                matched_posts.append(post_data)
        
        # Sort by relevance score (highest first)
        matched_posts.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        print(f"[REDDIT_MATCHER] Matched {len(matched_posts)} posts to script segments")
        print("")
        for i, post in enumerate(matched_posts):
            # Find the segment to show timing info and text
            seg = next((s for s in script_segments if s['segment_number'] == post['matched_segment']), None)
            
            if seg:
                # Calculate approximate time range
                time_start = sum(s.get('duration_estimate', 5) for s in script_segments if s['segment_number'] < post['matched_segment'])
                time_end = sum(s.get('duration_estimate', 5) for s in script_segments if s['segment_number'] <= post['matched_segment'])
                seg_info = f"(~{time_start:.0f}s-{time_end:.0f}s)"
                
                # Show segment text preview
                seg_text = seg.get('text', '')[:80]
                
                print(f"   Post {i} -> Segment {post['matched_segment']} {seg_info}")
                print(f"      Description: {post.get('description', '')[:70]}...")
                print(f"      Relevance: {post['relevance_score']}/10")
                print(f"      Reason: {post['reason'][:80]}...")
                print(f"      Segment text: \"{seg_text}...\"")
                print("")
            else:
                print(f"   Post {i} -> Segment {post['matched_segment']} (WARNING: segment not found!)")
                print(f"      Description: {post.get('description', '')[:70]}...")
                print("")
        
        return matched_posts
    
    def _fallback_matching(self, script_segments, reddit_posts):
        """Simple fallback if Claude matching fails"""
        matched_posts = []
        
        # Assign posts round-robin to segments
        for i, post in enumerate(reddit_posts):
            segment_idx = i % len(script_segments)
            post_data = post.copy()
            post_data.update({
                'matched_segment': script_segments[segment_idx]['segment_number'],
                'relevance_score': 5,
                'reason': 'Auto-assigned (fallback)'
            })
            matched_posts.append(post_data)
        
        return matched_posts
    
    def create_reddit_timeline_entries(self, matched_posts, script_segments):
        """
        Create timeline entries for Reddit posts based on matched segments
        
        Args:
            matched_posts: Output from match_posts_to_script()
            script_segments: Script segments with timing info
        
        Returns:
            List of timeline-ready Reddit elements with timestamps
        """
        reddit_entries = []
        
        for post in matched_posts:
            segment_num = post.get('matched_segment', 1)
            
            # Find the corresponding segment
            segment = next((s for s in script_segments if s['segment_number'] == segment_num), None)
            
            if segment:
                # Calculate timing for this Reddit post
                segment_duration = segment.get('duration_estimate', 5)
                segment_type = segment.get('type', 'gameplay')
                
                # Calculate when this segment starts (sum of previous segments)
                segment_start = sum(
                    s.get('duration_estimate', 5) 
                    for s in script_segments 
                    if s['segment_number'] < segment_num
                )
                
                # Smart placement based on segment type
                if segment_type == 'evidence':
                    # Evidence segments: Show Reddit early (after brief intro)
                    placement = segment_start + min(1.0, segment_duration * 0.2)
                elif segment_type == 'data':
                    # Data segments: Show Reddit after the data (as supporting evidence)
                    placement = segment_start + (segment_duration * 0.7)
                else:
                    # Hook/gameplay segments: Show Reddit in middle-to-late part
                    placement = segment_start + (segment_duration * 0.5)
                
                reddit_entries.append({
                    'url': post.get('url', ''),
                    'description': post.get('description', ''),
                    'segment_number': segment_num,
                    'segment_start': segment_start,
                    'segment_end': segment_start + segment_duration,
                    'estimated_timestamp': placement,
                    'relevance_score': post.get('relevance_score', 5),
                    'reason': post.get('reason', '')
                })
                
                print(f"[REDDIT_MATCHER] Post will appear at {placement:.1f}s (segment {segment_num}: {segment_start:.1f}s-{segment_start + segment_duration:.1f}s)")
        
        return reddit_entries


if __name__ == "__main__":
    # Test the matcher
    print("="*70)
    print("Testing Reddit Matcher")
    print("="*70)
    
    test_segments = [
        {
            'segment_number': 1,
            'text': 'In December 2024, Brawl Stars exploded to 84 million players—up from 65 million in 2022 and 50 million back in 2020.',
            'type': 'hook',
            'duration_estimate': 8
        },
        {
            'segment_number': 2,
            'text': 'This massive growth was fueled by the Toy Story collaboration.',
            'type': 'data',
            'duration_estimate': 5
        }
    ]
    
    test_posts = [
        {
            'url': 'https://reddit.com/r/BrawlStars/post1',
            'description': 'Community celebrating hitting 84 million players milestone'
        },
        {
            'url': 'https://reddit.com/r/BrawlStars/post2',
            'description': 'Discussion about Toy Story collab impact on player count'
        }
    ]
    
    matcher = RedditMatcher()
    matched = matcher.match_posts_to_script(test_segments, test_posts)
    
    print("\n" + "="*70)
    print("MATCHED POSTS:")
    print("="*70)
    for post in matched:
        print(f"\nPost: {post['description'][:60]}...")
        print(f"  Matched to: Segment {post['matched_segment']}")
        print(f"  Relevance: {post['relevance_score']}/10")
        print(f"  Reason: {post['reason']}")
    
    print("\n" + "="*70)
    print("TIMELINE ENTRIES:")
    print("="*70)
    timeline = matcher.create_reddit_timeline_entries(matched, test_segments)
    for entry in timeline:
        print(f"\n{entry['description'][:60]}...")
        print(f"  Timestamp: ~{entry['estimated_timestamp']:.1f}s")
        print(f"  Segment: {entry['segment_number']}")
