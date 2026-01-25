import os
import sys
import json
import time
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
# Import stealth function - simple direct import
try:
    from playwright_stealth import stealth_sync
    print("[REDDIT] playwright-stealth loaded successfully")
except ImportError:
    # No stealth available - create no-op
    print("[WARNING] playwright-stealth not available, proceeding without stealth mode")
    def stealth_sync(page):
        pass
from PIL import Image, ImageDraw, ImageFont

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.claude_client import ClaudeClient

class RedditIntelligence:
    """
    Enhanced Reddit integration with LLM-powered search and ranking
    """
    
    def __init__(self, default_subreddit=None):
        self.claude = ClaudeClient()
        self.default_subreddit = default_subreddit or "gaming"  # Use broader default
    
    def search_for_claim(self, claim_text, subreddit=None, max_results=10, main_subject=None):
        """
        Search Reddit for posts that support a claim
        
        Args:
            claim_text: The claim to find evidence for
            subreddit: Which subreddit to search (default: auto-detect from main_subject)
            max_results: Maximum posts to return
            main_subject: Main topic/game from script (e.g., "Brawl Stars", "Clash Royale")
        
        Returns:
            List of post dictionaries with title, url, score, etc.
        """
        # Auto-detect subreddit from main subject if not provided
        if subreddit is None:
            subreddit = self._determine_subreddit(main_subject) if main_subject else self.default_subreddit
        
        print(f"[REDDIT] Searching r/{subreddit} for: {claim_text[:50]}...")
        
        # Use Claude to generate optimal search terms
        search_terms = self._generate_search_terms(claim_text, main_subject)
        print(f"[REDDIT] Search terms: {search_terms}")
        
        posts = []
        
        with sync_playwright() as p:
            # Use headless=False for better stealth (headless is easier to detect)
            browser = p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                viewport={'width': 1920, 'height': 1080},
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                }
            )
            page = context.new_page()
            stealth_sync(page)
            
            # Additional stealth: override navigator properties
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            """)
            
            try:
                # Use old.reddit.com which is MUCH less protected and easier to scrape
                encoded_query = quote_plus(search_terms)
                
                # Build old Reddit search URL
                if subreddit and subreddit != "gaming" and subreddit != "all":
                    # Search within specific subreddit
                    search_url = f"https://old.reddit.com/r/{subreddit}/search/?q={encoded_query}&restrict_sr=on&sort=top&t=year"
                else:
                    # Search all of Reddit
                    search_url = f"https://old.reddit.com/search/?q={encoded_query}&sort=top&t=year"
                
                print(f"[REDDIT] URL: {search_url}")
                print(f"[REDDIT] Using old.reddit.com for better compatibility...")
                
                # First, visit reddit homepage to establish session
                page.goto("https://old.reddit.com", timeout=30000)
                time.sleep(1)  # Let session establish
                
                # Now go to search
                page.goto(search_url, timeout=30000)
                time.sleep(1)  # Wait for page load
                
                # Wait for posts to load - old Reddit uses div.thing
                try:
                    page.wait_for_selector('div.thing[data-type="link"]', timeout=10000)
                    print("[REDDIT] Posts loaded successfully!")
                except:
                    print("[WARNING] Posts didn't load...")
                    
                    # Check if blocked
                    blocked_text = page.locator('text="blocked"').count()
                    if blocked_text > 0:
                        print("[ERROR] Blocked by Reddit. If you see a security check, please complete it.")
                        print("[WAITING] 30 seconds for you to solve any security challenges...")
                        time.sleep(30)
                        
                        # Try again after waiting
                        try:
                            page.wait_for_selector('div.thing[data-type="link"]', timeout=10000)
                            print("[REDDIT] Posts loaded after security check!")
                        except:
                            print("[ERROR] Still blocked or no results found")
                            browser.close()
                            return []
                    else:
                        print("[ERROR] No posts found")
                        # Save screenshot
                        debug_path = "data/assets/reddit_debug_search.png"
                        os.makedirs("data/assets", exist_ok=True)
                        page.screenshot(path=debug_path)
                        print(f"[DEBUG] Saved screenshot to {debug_path}")
                        browser.close()
                        return []
                
                # Debug: Check page
                print(f"[DEBUG] Page title: {page.title()}")
                
                # Extract post information - old Reddit uses div.thing
                post_elements = page.locator('div.thing[data-type="link"]').all()[:max_results]
                print(f"[DEBUG] Found {len(post_elements)} posts on old Reddit")
                
                for element in post_elements:
                    try:
                        # Old Reddit structure: title is in a.title
                        title_link = element.locator('a.title').first
                        title = title_link.inner_text() if title_link.count() > 0 else "No title"
                        
                        # Get post URL from data-permalink attribute
                        permalink = element.get_attribute('data-permalink')
                        url = f"https://old.reddit.com{permalink}" if permalink else ""
                        
                        # Get score from div.score.unvoted
                        score_elem = element.locator('div.score.unvoted').first
                        if score_elem.count() == 0:
                            score_elem = element.locator('div.score').first
                        score_text = score_elem.inner_text() if score_elem.count() > 0 else "0"
                        score = self._parse_score(score_text)
                        
                        posts.append({
                            'title': title,
                            'url': url,
                            'score': score,
                            'subreddit': subreddit
                        })
                        
                        print(f"[DEBUG] Post: {title[:50]}... (score: {score})")
                        
                    except Exception as e:
                        print(f"[WARNING] Failed to extract post: {e}")
                        continue
                
            except Exception as e:
                print(f"[ERROR] Reddit search failed: {e}")
            finally:
                browser.close()
        
        print(f"[REDDIT] Found {len(posts)} posts")
        
        # If no posts found and we used a specific subreddit, try broader search
        if len(posts) == 0:
            if subreddit and subreddit not in ["gaming", "all"]:
                print(f"[REDDIT] No results in r/{subreddit}, trying r/gaming...")
                return self.search_for_claim(claim_text, subreddit="gaming", max_results=max_results, main_subject=None)
            elif subreddit == "gaming":
                print(f"[REDDIT] No results in r/gaming, trying ALL of Reddit...")
                return self.search_for_claim(claim_text, subreddit="all", max_results=max_results, main_subject=None)
        
        return posts
    
    def _determine_subreddit(self, main_subject):
        """
        Determine the best subreddit based on the main subject
        
        Args:
            main_subject: Main topic from script (e.g., "Brawl Stars", "Clash Royale")
        
        Returns:
            Subreddit name (without r/)
        """
        if not main_subject:
            return self.default_subreddit
        
        # Simple mapping for common games
        subject_lower = main_subject.lower()
        
        # Remove spaces for subreddit names
        subreddit_mappings = {
            'brawl stars': 'BrawlStars',
            'clash royale': 'ClashRoyale',
            'clash of clans': 'ClashOfClans',
            'fortnite': 'FortNiteBR',
            'minecraft': 'Minecraft',
            'league of legends': 'leagueoflegends',
            'valorant': 'VALORANT',
            'apex legends': 'apexlegends'
        }
        
        for game, subreddit in subreddit_mappings.items():
            if game in subject_lower:
                print(f"[REDDIT] Auto-detected subreddit: r/{subreddit}")
                return subreddit
        
        # Fallback: try using subject directly (remove spaces)
        fallback_subreddit = main_subject.replace(' ', '')
        print(f"[REDDIT] Using fallback subreddit: r/{fallback_subreddit}")
        return fallback_subreddit
    
    def _generate_search_terms(self, claim_text, main_subject=None):
        """Use Claude to generate optimal Reddit search terms"""
        context = f" (about {main_subject})" if main_subject else ""
        
        prompt = f"""Given this claim from a video script{context}: "{claim_text}"

Generate optimal Reddit search query (2-3 BROAD keywords) that would find related discussions.

CRITICAL RULES:
1. Use BROAD, COMMON keywords that would appear in many post titles
2. Reddit search is VERY LIMITED - simpler is better
3. Avoid specific numbers, dates, or rare phrases
4. Use the most GENERAL terms related to the topic
5. 2-3 words maximum

EXAMPLES:
- Claim: "Edgar has 60% win rate in Showdown" → "Edgar overpowered" (NOT "Edgar win rate showdown")
- Claim: "Brawl Stars hit 84 million players in December 2024" → "Brawl Stars players" (NOT specific numbers)
- Claim: "Buzz Lightyear brawler caused problems" → "Buzz Lightyear" (just the character name)
- Claim: "Game is dying due to bad updates" → "dying game" or just "updates"

Return ONLY 2-3 broad keywords, nothing else."""

        result = self.claude.ask(prompt, temperature=0.3)
        if result:
            # Clean up the result
            terms = result.strip().replace('"', '').replace("'", '').replace('\n', ' ')
            # Limit to first 3 words for simplicity
            words = terms.split()[:3]
            return ' '.join(words)
        else:
            # Fallback: extract key words from claim (BROAD)
            words = claim_text.split()
            # Filter out common filler words AND numbers
            stopwords = {'the', 'a', 'an', 'is', 'was', 'were', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but', 'with', 'by', 'from', 'this', 'that'}
            keywords = [w for w in words if w.lower() not in stopwords and not w.replace(',', '').replace('.', '').isdigit()]
            return ' '.join(keywords[:2])  # Only 2 words for fallback
    
    def _parse_score(self, score_text):
        """Parse Reddit score text like '1.2k' to integer"""
        try:
            score_text = score_text.strip().lower()
            if 'k' in score_text:
                return int(float(score_text.replace('k', '')) * 1000)
            elif 'm' in score_text:
                return int(float(score_text.replace('m', '')) * 1000000)
            else:
                return int(score_text)
        except:
            return 0
    
    def rank_relevance(self, posts, claim_text):
        """
        Use Claude to rank posts by relevance to the claim
        
        Args:
            posts: List of post dictionaries
            claim_text: The original claim
        
        Returns:
            Posts sorted by relevance score (highest first)
        """
        if not posts:
            return []
        
        print(f"[REDDIT] Ranking {len(posts)} posts for relevance...")
        
        # Create prompt for Claude
        posts_text = "\n".join([
            f"{i+1}. [{post['score']} upvotes] {post['title']}"
            for i, post in enumerate(posts)
        ])
        
        prompt = f"""Claim: "{claim_text}"

Reddit posts:
{posts_text}

Rank each post by how well it supports the claim. Return a JSON array with objects containing:
- post_number (1-{len(posts)})
- relevance_score (0-10, where 10 is perfect support)

Return ONLY the JSON array."""

        rankings = self.claude.ask_json(prompt, temperature=0.2)
        
        if rankings:
            # Apply rankings to posts
            for ranking in rankings:
                post_idx = ranking.get('post_number', 0) - 1
                if 0 <= post_idx < len(posts):
                    posts[post_idx]['relevance_score'] = ranking.get('relevance_score', 5)
            
            # Sort by relevance score
            posts.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        else:
            # Fallback: sort by Reddit score
            posts.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return posts
    
    def extract_key_quote(self, post_url):
        """
        Visit post and extract the most important quote using Claude
        
        Args:
            post_url: URL to the Reddit post
        
        Returns:
            Dictionary with 'quote' and 'context'
        """
        print(f"[REDDIT] Extracting key quote from post...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = context.new_page()
            stealth_sync(page)
            
            try:
                page.goto(post_url, timeout=30000)
                page.wait_for_load_state("networkidle")
                
                # Get post title and content
                title_elem = page.locator('[slot="title"]').first
                title = title_elem.inner_text() if title_elem.count() > 0 else ""
                
                # Get post body if exists
                body_elem = page.locator('[slot="text-body"]').first
                body = body_elem.inner_text() if body_elem.count() > 0 else ""
                
                browser.close()
                
                # Use Claude to identify key quote
                if body:
                    full_text = f"Title: {title}\n\nBody: {body}"
                else:
                    full_text = f"Title: {title}"
                
                prompt = f"""From this Reddit post, identify the single most important sentence or quote that would support a video claim.

Post:
{full_text[:500]}

Return a JSON object with:
- "quote": the exact quote (keep it short, max 100 chars)
- "is_title": true if the quote is from the title, false if from body

Return ONLY the JSON."""

                result = self.claude.ask_json(prompt)
                
                if result:
                    return {
                        'quote': result.get('quote', title)[:100],
                        'is_title': result.get('is_title', True)
                    }
                else:
                    return {'quote': title[:100], 'is_title': True}
                    
            except Exception as e:
                print(f"[ERROR] Failed to extract quote: {e}")
                browser.close()
                return {'quote': '', 'is_title': True}
    
    def screenshot_with_highlight(self, post_url, quote_text=None, output_path=None):
        """
        Screenshot a Reddit post and optionally highlight a specific quote
        
        Args:
            post_url: URL to screenshot
            quote_text: Optional text to highlight
            output_path: Where to save (default: data/assets/reddit_{timestamp}.png)
        
        Returns:
            Path to screenshot file
        """
        if output_path is None:
            timestamp = int(time.time())
            output_path = f"data/assets/reddit_{timestamp}.png"
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"[REDDIT] Screenshotting post...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,  # Keep visible for debugging
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',  # Help with image loading
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            
            # Simpler, more reliable context
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            
            # Apply stealth FIRST before any navigation
            stealth_sync(page)
            print("[REDDIT] Stealth mode applied")
            
            try:
                # Convert old.reddit.com URLs to www.reddit.com for better screenshot visuals
                screenshot_url = post_url.replace('old.reddit.com', 'www.reddit.com')
                
                print(f"[REDDIT] Loading page: {screenshot_url}")
                
                # Visit homepage first to establish session
                page.goto("https://www.reddit.com", timeout=30000)
                time.sleep(1.5)
                
                # Now go to post
                page.goto(screenshot_url, timeout=30000)
                
                # Wait for the post to actually load
                print("[REDDIT] Waiting for post to load...")
                is_new_reddit = False
                try:
                    # New Reddit uses shreddit-post
                    page.wait_for_selector('shreddit-post', timeout=10000)
                    is_new_reddit = True
                    print("[REDDIT] New Reddit post loaded!")
                except:
                    print("[REDDIT] Warning: New Reddit post not found")
                
                # Wait for network to be mostly idle
                print("[REDDIT] Waiting for page to load...")
                page.wait_for_load_state("domcontentloaded")
                time.sleep(1.5)
                
                # Scroll to trigger lazy-loaded images
                print("[REDDIT] Scrolling to load images...")
                page.evaluate("""
                    // Scroll through the page to trigger lazy loading
                    const post = document.querySelector('shreddit-post');
                    if (post) {
                        // Scroll to post and beyond
                        post.scrollIntoView({behavior: 'instant', block: 'start'});
                        window.scrollBy(0, 500);  // Scroll down
                        window.scrollBy(0, -500); // Scroll back up
                    }
                """)
                time.sleep(2)  # Let lazy load trigger
                
                # Force eager loading on all images
                print("[REDDIT] Forcing image loads...")
                page.evaluate("""
                    // Force all images to load eagerly
                    const allImages = document.querySelectorAll('img');
                    allImages.forEach(img => {
                        // Change loading attribute
                        img.loading = 'eager';
                        
                        // Force load by accessing src
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                        }
                        
                        // Trigger load event
                        img.scrollIntoView({behavior: 'instant', block: 'center'});
                    });
                """)
                
                # Wait for network idle after forcing loads
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                    print("[REDDIT] Network idle - images should be loaded")
                except:
                    print("[REDDIT] Warning: Network not idle, but continuing...")
                
                time.sleep(2)  # Final buffer for rendering
                
                # Clean up UI elements (minimal - don't break image loading)
                print("[REDDIT] Cleaning up UI...")
                page.evaluate("""
                    // Remove obvious popups/banners ONLY
                    const bannersToRemove = [
                        '[slot="bottom-bar"]',
                        'xpromo-bottom-bar', 
                        '[data-testid="cookie-banner"]',
                        'shreddit-async-loader[bundlename="faceplate_batch"]'
                    ];
                    
                    bannersToRemove.forEach(sel => {
                        const elems = document.querySelectorAll(sel);
                        elems.forEach(elem => {
                            if (elem) elem.remove();
                        });
                    });
                    
                    // Remove blur filters from images (NSFW content)
                    document.querySelectorAll('img, video').forEach(media => {
                        if (media.style.filter && media.style.filter.includes('blur')) {
                            media.style.filter = 'none';
                        }
                        media.classList.remove('blur', 'blurred');
                        
                        // Ensure media is visible
                        media.style.opacity = '1';
                        media.style.visibility = 'visible';
                    });
                    
                    // Scroll to post for screenshot
                    const post = document.querySelector('shreddit-post');
                    if (post) {
                        post.scrollIntoView({behavior: 'instant', block: 'start'});
                    }
                """)
                
                time.sleep(1.5)  # Let cleanup and rendering finish
                
                # Screenshot the post with better capture including upvotes
                print("[REDDIT] Taking screenshot...")
                
                if is_new_reddit:
                    # Scroll to top of post
                    page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(0.5)
                    
                    # Try to find the main content area with upvotes
                    # New Reddit has the post in a container that includes vote buttons
                    post_container = page.locator('shreddit-post').first
                    
                    if post_container.count() > 0:
                        print(f"[REDDIT] Found shreddit-post element")
                        
                        # Get bounding box to check if we got content
                        box = post_container.bounding_box()
                        if box:
                            print(f"[REDDIT] Post element size: {box['width']}x{box['height']}")
                            
                            # Expand the screenshot area to include upvotes/sidebar
                            # Capture a larger area around the post
                            expanded_x = max(0, box['x'] - 100)  # Include left sidebar with upvotes
                            expanded_y = max(0, box['y'] - 20)
                            expanded_width = min(1920, box['width'] + 200)
                            expanded_height = min(1080, box['height'] + 100)
                            
                            page.screenshot(
                                path=output_path,
                                clip={
                                    'x': expanded_x,
                                    'y': expanded_y,
                                    'width': expanded_width,
                                    'height': expanded_height
                                }
                            )
                            print(f"[REDDIT] Captured expanded area: {expanded_width}x{expanded_height}")
                        else:
                            print("[REDDIT] Could not get bounding box, taking element screenshot")
                            post_container.screenshot(path=output_path)
                    else:
                        print("[REDDIT] No post element found, taking full page screenshot")
                        page.screenshot(path=output_path, full_page=False)
                else:
                    print("[REDDIT] Fallback: taking full page screenshot")
                    page.screenshot(path=output_path, full_page=False)
                
                browser.close()
                
                # If quote provided, add highlight
                if quote_text:
                    self._add_highlight_to_image(output_path, quote_text)
                
                print(f"[REDDIT] Screenshot saved: {output_path}")
                return output_path
                
            except Exception as e:
                print(f"[ERROR] Screenshot failed: {e}")
                browser.close()
                return None
    
    def extract_post_parts(self, post_url, claim_text):
        """
        Extract different parts of a Reddit post and identify which support the claim
        Returns a list of parts (title, body sections, key comments) with relevance scores
        """
        print(f"[REDDIT] Analyzing post parts for relevance...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                viewport={'width': 1920, 'height': 1080},
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            page = context.new_page()
            stealth_sync(page)
            
            # Additional stealth
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                window.chrome = {runtime: {}};
            """)
            
            try:
                # Use old Reddit for extraction (more reliable)
                old_reddit_url = post_url.replace('www.reddit.com', 'old.reddit.com')
                
                # Visit homepage first
                page.goto("https://old.reddit.com", timeout=30000)
                time.sleep(1)
                
                # Go to post
                page.goto(old_reddit_url, timeout=30000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # Extract post title (old Reddit uses a.title in div.thing)
                title_elem = page.locator('a.title').first
                title = title_elem.inner_text() if title_elem.count() > 0 else ""
                
                # Extract post body (old Reddit uses div.usertext-body)
                body_elem = page.locator('div.usertext-body form div.md').first
                body = body_elem.inner_text() if body_elem.count() > 0 else ""
                
                # Extract top comments (old Reddit uses div.comment)
                comments = []
                comment_elems = page.locator('div.comment div.usertext-body div.md').all()[:5]  # Top 5 comments
                for i, elem in enumerate(comment_elems):
                    try:
                        comment_text = elem.inner_text()[:200]  # First 200 chars
                        if comment_text:
                            comments.append({
                                'text': comment_text,
                                'index': i
                            })
                    except:
                        continue
                
                browser.close()
                
                # Use Claude to analyze which parts best support the claim
                parts_text = f"""Title: {title}
                
Body: {body[:300]}

Comments:
{chr(10).join([f"{i+1}. {c['text']}" for i, c in enumerate(comments)])}"""
                
                prompt = f"""Claim: "{claim_text}"

Reddit Post Parts:
{parts_text}

Identify which parts of this Reddit post best support the claim. Return a JSON array of objects:
[
  {{"part": "title", "relevance": 8, "reason": "why it supports claim"}},
  {{"part": "body", "relevance": 6, "reason": "why it supports claim"}},
  {{"part": "comment_1", "relevance": 9, "reason": "why it supports claim"}}
]

Only include parts with relevance >= 6. Order by relevance (highest first).
Return ONLY the JSON array."""
                
                parts = self.claude.ask_json(prompt, temperature=0.2)
                
                return {
                    'title': title,
                    'body': body,
                    'comments': comments,
                    'relevant_parts': parts if parts else []
                }
                
            except Exception as e:
                print(f"[ERROR] Failed to extract post parts: {e}")
                browser.close()
                return None
    
    def _add_highlight_to_image(self, image_path, quote_text):
        """Add a subtle highlight box to emphasize text (simplified version)"""
        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img, 'RGBA')
            
            # Add a semi-transparent yellow overlay at the top (where title usually is)
            # This is a simplified approach - full text detection would require OCR
            width, height = img.size
            highlight_box = [(20, 20), (width - 20, 120)]
            draw.rectangle(highlight_box, fill=(255, 255, 0, 30), outline=(255, 200, 0, 150), width=3)
            
            img.save(image_path)
            print("[REDDIT] Added highlight to image")
        except Exception as e:
            print(f"[WARNING] Could not add highlight: {e}")


if __name__ == "__main__":
    # Test the Reddit intelligence
    print("=" * 60)
    print("Testing Reddit Intelligence")
    print("=" * 60)
    
    reddit = RedditIntelligence()
    
    # Test search
    test_claim = "Edgar is overpowered in Showdown"
    posts = reddit.search_for_claim(test_claim, max_results=5)
    
    if posts:
        print(f"\nFound {len(posts)} posts:")
        for i, post in enumerate(posts[:3]):
            print(f"  {i+1}. [{post['score']}] {post['title'][:60]}...")
        
        # Test ranking
        ranked = reddit.rank_relevance(posts, test_claim)
        print(f"\nTop ranked post: {ranked[0]['title'][:60]}...")
    else:
        print("\nNo posts found (may need CAPTCHA solving)")
