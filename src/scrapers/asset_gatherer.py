import os
import requests
from PIL import Image
import io
import time
import json
import yaml
from duckduckgo_search import DDGS
from urllib.parse import urlparse

class AssetGatherer:
    """
    Find and prepare visual assets (icons, images) for video production
    """
    
    def __init__(self, assets_dir="data/assets"):
        self.assets_dir = assets_dir
        self.icons_dir = os.path.join(assets_dir, "icons")
        self.manual_icons_dir = os.path.join(assets_dir, "manual_icons")
        os.makedirs(self.icons_dir, exist_ok=True)
        os.makedirs(self.manual_icons_dir, exist_ok=True)
        
        # Load global search context and rate limiting settings from config
        self.global_context = ""
        self.download_delay = 0.8  # Default: 0.8s between keyword downloads
        self.retry_delay = 2.0     # Default: 2.0s before retrying failures
        self.max_retries = 3       # Default: 3 retries per query
        self.last_download_time = 0  # Track when we last downloaded to enforce delay
        
        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
                pipeline_config = config.get('pipeline', {})
                self.global_context = pipeline_config.get('search_context', '')
                self.download_delay = pipeline_config.get('icon_download_delay', 0.8)
                self.retry_delay = pipeline_config.get('icon_retry_delay', 2.0)
                self.max_retries = pipeline_config.get('icon_max_retries', 3)
                
                if self.global_context:
                    print(f"[ASSETS] Global search context: '{self.global_context}'")
                print(f"[ASSETS] Rate limiting: {self.download_delay}s delay between downloads, {self.retry_delay}s retry delay")
        except Exception as e:
            print(f"[ASSETS] Could not load config: {e}")
    
    def find_icon(self, keyword, context="", sentence_context="", force_redownload=False):
        """
        Find an icon for a keyword
        Searches manual overrides first, then local assets, then downloads from web
        
        Args:
            keyword: The word/concept to find an icon for
            context: Main subject context (e.g., "Brawl Stars", "Clash Royale")
            sentence_context: The full sentence where this keyword appears
            force_redownload: If True, skip local cache and download fresh (but NOT manual overrides)
        
        Returns:
            Path to icon file
        """
        # Merge local context with global context if not already present
        search_context = context
        if self.global_context and self.global_context.lower() not in search_context.lower():
            if search_context:
                search_context = f"{self.global_context} {search_context}"
            else:
                search_context = self.global_context

        print(f"[ASSETS] Looking for icon: {keyword} (Context: {search_context})")
        
        # 0. HIGHEST PRIORITY: Check manual_icons directory for hand-picked overrides
        # Manual overrides are NEVER skipped, even with force_redownload
        manual_path = self._check_manual_override(keyword)
        if manual_path:
            print(f"[ASSETS] ✓ Using MANUAL override: {manual_path}")
            return manual_path
        
        # 1. Check if we already have this icon locally (unless force redownload)
        if not force_redownload:
            local_path = self._find_local_icon(keyword)
            if local_path and os.path.getsize(local_path) > 10000:  # Skip tiny placeholders
                print(f"[ASSETS] Found local icon: {local_path}")
                return local_path
        else:
            print(f"[ASSETS] Force redownload enabled - skipping local cache")
        
        # 2. Check in main assets directory (for character images)
        character_path = os.path.join(self.assets_dir, f"{keyword}.png")
        if os.path.exists(character_path):
            print(f"[ASSETS] Found character asset: {character_path}")
            return character_path
        
        # 3. Search and download from web with FULL context
        print(f"[ASSETS] Downloading icon from web: {keyword}")
        if sentence_context:
            print(f"[ASSETS] Sentence: {sentence_context[:80]}...")
        downloaded_path = self._search_and_download_icon(keyword, context=search_context, sentence_context=sentence_context)
        if downloaded_path:
            print(f"[ASSETS] Downloaded icon: {downloaded_path}")
            return downloaded_path
        
        # 4. Last resort: create placeholder
        print(f"[ASSETS] Creating placeholder for: {keyword}")
        return self._create_placeholder(keyword)
    
    def _check_manual_override(self, keyword):
        """
        Check manual_icons directory for hand-picked, high-quality icons
        This has HIGHEST priority - if a manual icon exists, it's ALWAYS used
        
        Args:
            keyword: The keyword to search for
            
        Returns:
            Path to manual icon file if found, None otherwise
        """
        # Normalize keyword for filename matching
        # Replace spaces with underscores, lowercase
        keyword_normalized = keyword.lower().replace(" ", "_").replace("-", "_")
        
        # Try exact match with common extensions
        for ext in ['.png', '.jpg', '.jpeg', '.webp']:
            manual_path = os.path.join(self.manual_icons_dir, f"{keyword_normalized}{ext}")
            if os.path.exists(manual_path):
                return manual_path
        
        # Also try the original keyword without normalization (in case user named it differently)
        for ext in ['.png', '.jpg', '.jpeg', '.webp']:
            manual_path = os.path.join(self.manual_icons_dir, f"{keyword.lower()}{ext}")
            if os.path.exists(manual_path):
                return manual_path
        
        return None
    
    def _find_local_icon(self, keyword):
        """Search local icons directory"""
        keyword_lower = keyword.lower()
        
        # Try exact match
        for ext in ['.png', '.jpg', '.jpeg']:
            path = os.path.join(self.icons_dir, f"{keyword_lower}{ext}")
            if os.path.exists(path):
                return path
        
        # Try partial match
        if os.path.exists(self.icons_dir):
            for filename in os.listdir(self.icons_dir):
                if keyword_lower in filename.lower():
                    return os.path.join(self.icons_dir, filename)
        
        return None
    
    def _create_placeholder(self, keyword):
        """Create a simple placeholder icon"""
        output_path = os.path.join(self.icons_dir, f"placeholder_{keyword.lower().replace(' ', '_')}.png")
        
        # Create a simple colored square with text
        img = Image.new('RGBA', (200, 200), color=(100, 100, 200, 255))
        img.save(output_path)
        
        print(f"[ASSETS] Created placeholder: {output_path}")
        return output_path
    
    def _generate_icon_search_query(self, keyword, context="", sentence_context=""):
        """
        Use Claude to intelligently generate the best icon search query
        
        Args:
            keyword: The keyword to search for
            context: Main subject/game (e.g., "Brawl Stars")
            sentence_context: The full sentence where keyword appears
        
        Returns:
            Optimized search query string
        """
        from utils.claude_client import ClaudeClient
        
        try:
            claude = ClaudeClient()
            
            # Build context string for Claude
            context_info = f"\nMain topic: {context}" if context else ""
            sentence_info = f"\nFull sentence: \"{sentence_context}\"" if sentence_context else ""
            
            prompt = f"""Generate an image search query to find the RIGHT icon for this keyword.

KEYWORD: "{keyword}"{context_info}{sentence_info}

CRITICAL CONTEXT RULES:
=======================
🎯 ONLY add game context (like "Clash Royale" or "Brawl Stars") for game-specific terms.
🚫 DO NOT add game context for universal emotions, concepts, or general vocabulary.

When to ADD game context:
✅ In-game items/currency: "Power Points", "Coins", "Gems", "Elite Wild Cards", "Pass Royale"
✅ Game characters: "Shelly", "Edgar", "Colt", "Mortis", "Mega Knight"
✅ Game features: "Hypercharge", "Star Power", "Gadget", "Evolution", "Mastery"
✅ Game levels: "Level 15", "maxed", "King Tower"
✅ Game modes/locations: "Ranked", "Trophy Road", "Brawl Ball"

When to SKIP game context (use generic search):
❌ Universal emotions: "angry", "furious", "excited", "frustrated", "thrilled", "devastated"
❌ Abstract concepts: "nightmare", "crisis", "peak", "record", "death spiral", "trap"
❌ General actions: "revolted", "collapsed", "resurrected", "dominated", "dying", "decline"
❌ Question words: "why", "question", "confusion", "problem", "doubt"
❌ Common objects: "fire", "trophy", "money", "dollar", "math"
❌ Social terms: "subreddit", "community", "creators", "players"

CATEGORY DETECTION:

A) YOUTUBER/STREAMER/CONTENT CREATOR:
   Names like: B-Rad, Jynxzi, KairosTime, MrBeast, xQc, Ninja, Shroud
   → "[EXACT name] YouTuber face" or "[EXACT name] streamer"
   Examples:
   - "B-Rad" → "B-Rad Clash Royale YouTuber"
   - "Jynxzi" → "Jynxzi streamer face"
   - "KairosTime" → "KairosTime Brawl Stars YouTuber"

B) GAME NAME/TITLE:
   → "[EXACT game name] logo official"
   - "Clash Royale" → "Clash Royale logo official"
   - "Brawl Stars" → "Brawl Stars logo official"

C) IN-GAME ITEM/CURRENCY/FEATURE (REQUIRES game context):
   → "[GAME NAME] [EXACT item name] icon"
   Examples:
   - "Elite Wild Cards" → "Clash Royale Elite Wild Card item icon"
   - "Pass Royale" → "Clash Royale Pass Royale season pass icon"
   - "Power Points" → "Brawl Stars Power Points currency icon"
   - "Hypercharge" → "Brawl Stars Hypercharge icon"

D) GAME LEVEL/RANK/NUMBER (REQUIRES game context):
   → "[GAME NAME] level [number]"
   Examples:
   - "level 15" → "Clash Royale king tower level 15"
   - "maxed" → "Brawl Stars max level power 11"

E) GAME CHARACTER/TROOP/CARD (REQUIRES game context):
   → "[GAME NAME] [character name] official art"
   - "Mega Knight" → "Clash Royale Mega Knight card"
   - "Shelly" → "Brawl Stars Shelly brawler"
   - "Edgar" → "Brawl Stars Edgar brawler"

F) UNIVERSAL EMOTIONS (NO game context):
   → "[emotion] face icon" or "[emotion] emoji simple"
   - "angry" → "angry face icon red"
   - "furious" → "furious angry icon"
   - "frustrated" → "frustrated icon simple"
   - "excited" → "excited happy icon"

G) ABSTRACT CONCEPTS (NO game context):
   → "[concept] icon simple" or relevant symbol
   - "nightmare" → "nightmare icon scary"
   - "crisis" → "crisis warning icon red"
   - "trap" → "trap icon danger"
   - "death spiral" → "downward spiral icon red"

H) DECLINE/NEGATIVE WORDS (NO game context):
   → Use universal decline symbols
   - "dying" → "downward trend red arrow icon"
   - "decline" → "graph declining red icon"
   - "revolted" → "protest fist icon angry"
   - "collapsed" → "collapse broken icon"

I) POSITIVE/SUCCESS WORDS (NO game context):
   - "record" → "trophy gold icon"
   - "peak" → "mountain peak icon"
   - "resurrected" → "resurrection phoenix icon"

J) QUESTION/CONFUSION (NO game context):
   - "why" → "question mark icon"
   - "question" → "question mark icon blue"
   - "confusion" → "confused question mark icon"

K) OTHER - Generic search: "[keyword] icon simple"

EXAMPLE OUTPUTS:
- "Power Points" + Brawl Stars → "Brawl Stars Power Points currency icon" (game-specific item)
- "angry" + Brawl Stars → "angry face icon red" (universal emotion, NO game context)
- "Shelly" + Brawl Stars → "Brawl Stars Shelly brawler" (game character)
- "nightmare" + Clash Royale → "nightmare icon scary" (universal concept, NO game context)
- "revolted" + Clash Royale → "protest revolt fist icon" (universal action, NO game context)

Return ONLY the search query, nothing else."""

            result = claude.ask(prompt, temperature=0.2)  # Lower temp for more consistent results
            search_query = result.strip().strip('"').strip("'")
            
            # Validation
            if len(search_query) < 3:
                print(f"[ASSETS] Claude returned too short: '{search_query}', using fallback")
                search_query = f"{keyword} icon"
            elif len(search_query) > 120:
                print(f"[ASSETS] Claude returned too long, truncating")
                search_query = search_query[:120]
            
            print(f"[ASSETS] Search query: '{search_query}'")
            return search_query
            
        except Exception as e:
            print(f"[ASSETS] Claude search query generation failed: {e}")
            # Intelligent fallback based on keyword
            if context and (context.lower() in keyword.lower()):
                return f"{keyword} game logo"
            else:
                return f"{keyword} icon"
    
    def prepare_character_images(self, character_names):
        """
        Ensure character images are ready and processed
        
        Args:
            character_names: List of character names to prepare
        
        Returns:
            Dictionary mapping character name to asset path
        """
        character_assets = {}
        
        for name in character_names:
            path = os.path.join(self.assets_dir, f"{name}.png")
            if os.path.exists(path):
                character_assets[name] = path
                print(f"[ASSETS] Character ready: {name}")
            else:
                print(f"[ASSETS] Missing character: {name}")
                # Could implement download logic here
        
        return character_assets
    
    def _search_serper_images(self, query, max_results=8):
        """
        Search using Serper API for images (Google backend with no rate limits)
        
        Args:
            query: Search query string
            max_results: Number of results to return
        
        Returns:
            List of image result dicts with 'image' URL, or None if disabled/failed
        """
        try:
            # Load API credentials from config
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            serper_config = config.get('serper_api', {})
            if not serper_config.get('enabled', False):
                return None
            
            api_key = serper_config.get('api_key')
            if not api_key:
                print("[ASSETS] Serper API key missing")
                return None
            
            print(f"[ASSETS] Using Serper API for: {query}")
            
            # Make API request to Serper
            url = "https://google.serper.dev/images"
            
            payload = json.dumps({
                "q": query,
                "num": max_results,
                "gl": "us",  # Country: United States
                "hl": "en",  # Language: English
                "safe": "active",  # SafeSearch enabled
                "tbs": "itp:clipart,ift:png"  # Filter: clipart type, PNG format
            })
            
            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, headers=headers, data=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to DuckDuckGo-like format for compatibility with existing download code
            images = data.get('images', [])
            formatted_results = []
            
            for img in images[:max_results]:
                image_url = img.get('imageUrl')
                if image_url:
                    formatted_results.append({
                        'image': image_url,
                        'title': img.get('title', ''),
                        'thumbnail': img.get('thumbnailUrl', ''),
                        'source': img.get('source', '')
                    })
            
            print(f"[ASSETS] Serper returned {len(formatted_results)} results")
            return formatted_results
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"[ASSETS] Serper API authentication failed - check your API key")
            elif e.response.status_code == 403:
                print(f"[ASSETS] Serper API quota exceeded")
            else:
                print(f"[ASSETS] Serper API HTTP error: {e}")
            return None
        except Exception as e:
            print(f"[ASSETS] Serper API error: {e}")
            return None
    
    def _search_and_download_icon(self, keyword, context="", sentence_context=""):
        """
        Search for icon using Serper API (primary) or DuckDuckGo (fallback)
        Uses multiple query attempts with fallbacks for better results
        
        Args:
            keyword: Search term
            context: Main topic/game context
            sentence_context: Full sentence where keyword appears
        
        Returns:
            Path to downloaded icon or None
        """
        # Rate limiting: Enforce delay between keyword downloads
        time_since_last = time.time() - self.last_download_time
        if time_since_last < self.download_delay:
            wait_time = self.download_delay - time_since_last
            print(f"[ASSETS] Rate limiting: waiting {wait_time:.1f}s before next download...")
            time.sleep(wait_time)
        
        self.last_download_time = time.time()
        
        # Generate multiple search queries to try
        # 1. Claude-generated (optimized for context)
        # 2. Context + keyword explicitly  
        # 3. Simpler variations
        search_queries = []
        
        # Primary: Claude-generated query (don't add extra terms, Claude's query is optimized)
        search_query = self._generate_icon_search_query(keyword, context, sentence_context)
        search_queries.append(search_query)
        
        # Fallback 1: Same query with "icon png" suffix
        search_queries.append(f"{search_query} icon png")
        
        # Fallback 2: Context + keyword explicitly (if context available)
        if context:
            search_queries.append(f"{context} {keyword} official icon")
            search_queries.append(f"{context} {keyword}")
        
        # Fallback 3: Simple keyword search (last resort)
        search_queries.append(f"{keyword} icon")
        
        # Try each query until we get a good result
        for query_idx, enhanced_query in enumerate(search_queries):
            print(f"[ASSETS] Search attempt {query_idx + 1}/{len(search_queries)}: {enhanced_query[:60]}...")
            
            # TRY SERPER FIRST (fast, no rate limits, better quality)
            results = self._search_serper_images(enhanced_query, max_results=8)
            
            # FALLBACK TO DUCKDUCKGO if Serper unavailable or failed
            if results is None:
                print("[ASSETS] Serper unavailable, using DuckDuckGo fallback")
                
                try:
                    # Use configured retry delay
                    time.sleep(self.retry_delay)
                    
                    with DDGS() as ddgs:
                        results = list(ddgs.images(
                            keywords=enhanced_query,
                            max_results=8,
                            size="Medium"
                        ))
                except Exception as e:
                    print(f"[ASSETS] DuckDuckGo error: {e}")
                    results = []
            
            # If no results, try next query
            if not results:
                print(f"[ASSETS] No results for query {query_idx + 1}, trying next...")
                continue
            
            # Try downloading from results, skipping watermarked sources
            attempts = 0
            for i, result in enumerate(results):
                if attempts >= self.max_retries:  # Use configured max retries
                    break
                    
                try:
                    image_url = result.get('image')
                    if not image_url:
                        continue
                    
                    # Skip known stock photo sites that add watermarks
                    skip_domains = ['shutterstock', 'gettyimages', 'istockphoto', 'adobe', 'depositphotos']
                    if any(domain in image_url.lower() for domain in skip_domains):
                        print(f"[ASSETS] Skipping watermarked source: {image_url[:50]}...")
                        continue
                    
                    attempts += 1
                    print(f"[ASSETS] Trying download {attempts}/{self.max_retries}: {image_url[:50]}...")
                    
                    # Exponential backoff between download attempts
                    if attempts > 1:
                        backoff_delay = min(self.retry_delay * (2 ** (attempts - 2)), 10.0)  # Max 10s
                        print(f"[ASSETS] Waiting {backoff_delay:.1f}s before retry...")
                        time.sleep(backoff_delay)
                    
                    # Download with headers to avoid blocks
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(image_url, timeout=10, headers=headers)
                    response.raise_for_status()
                    
                    # Verify it's an image
                    img = Image.open(io.BytesIO(response.content))
                    
                    # Convert to RGBA
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    # Resize to standard size
                    img = self._resize_maintain_aspect(img, max_size=400)
                    
                    # Save
                    output_path = os.path.join(self.icons_dir, f"{keyword.lower().replace(' ', '_')}.png")
                    img.save(output_path)
                    
                    print(f"[ASSETS] Successfully downloaded: {output_path}")
                    return output_path
                    
                except Exception as e:
                    print(f"[ASSETS] Download {i+1} failed: {e}")
                    continue
            
            # If we tried 3 downloads and all failed, try next query
            print(f"[ASSETS] Downloads failed for query {query_idx + 1}, trying next query...")
        
        # All queries exhausted
        print(f"[ASSETS] ⚠️  All search queries failed for '{keyword}'")
        print(f"[ASSETS] This keyword will display as text instead of an icon")
        print(f"[ASSETS] If you're seeing many failures, try:")
        print(f"[ASSETS]   1. Increase 'icon_download_delay' in config.yaml (current: {self.download_delay}s)")
        print(f"[ASSETS]   2. Check your internet connection")
        print(f"[ASSETS]   3. Verify Serper API key is valid (if enabled)")
        return None
    
    def download_and_process(self, url, keyword):
        """
        Download an image and process it for use as an icon
        
        Args:
            url: URL to download from
            keyword: Keyword for naming
        
        Returns:
            Path to processed image
        """
        try:
            print(f"[ASSETS] Downloading icon for {keyword}...")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # Load image
            img = Image.open(io.BytesIO(response.content))
            
            # Convert to RGBA if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Resize to standard size
            img = self._resize_maintain_aspect(img, max_size=400)
            
            # Save
            output_path = os.path.join(self.icons_dir, f"{keyword.lower().replace(' ', '_')}.png")
            img.save(output_path)
            
            print(f"[ASSETS] Downloaded and processed: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"[ERROR] Failed to download icon: {e}")
            return None
    
    def _resize_maintain_aspect(self, img, max_size=400):
        """Resize image while maintaining aspect ratio"""
        width, height = img.size
        
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def make_transparent_bg(self, image_path):
        """
        Attempt to make background transparent (simple version)
        Works best with solid color backgrounds
        
        Args:
            image_path: Path to image
        
        Returns:
            Path to processed image
        """
        try:
            img = Image.open(image_path).convert('RGBA')
            datas = img.getdata()
            
            new_data = []
            # Simple approach: make white/near-white pixels transparent
            for item in datas:
                # If pixel is mostly white, make transparent
                if item[0] > 240 and item[1] > 240 and item[2] > 240:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
            img.save(image_path)
            print(f"[ASSETS] Made background transparent: {image_path}")
            return image_path
            
        except Exception as e:
            print(f"[WARNING] Could not process transparency: {e}")
            return image_path
    
    def batch_prepare(self, keywords, context="", force_redownload=False):
        """
        Prepare multiple icons at once
        
        Args:
            keywords: List of keyword strings OR keyword dicts with 'word' and 'sentence' fields
            context: Context from the script (e.g., main subject)
            force_redownload: If True, skip local cache and download fresh
        
        Returns:
            Dictionary mapping keyword to icon path
        """
        assets = {}
        
        for idx, keyword in enumerate(keywords):
            # Handle both dict and string formats
            if isinstance(keyword, dict):
                kw_word = keyword.get('word', str(keyword))
                kw_sentence = keyword.get('sentence', '')
            else:
                kw_word = str(keyword)
                kw_sentence = ''
            
            path = self.find_icon(kw_word, context=context, sentence_context=kw_sentence, force_redownload=force_redownload)
            if path:
                assets[kw_word] = path
            
            # Longer delay between keywords to avoid rate limits (except for last one)
            if idx < len(keywords) - 1:
                delay = 4 if force_redownload else 2  # 4s for new downloads, 2s for cached
                print(f"[ASSETS] Pausing {delay}s to avoid rate limits...")
                time.sleep(delay)
        
        success_count = len(assets)
        failed_count = len(keywords) - success_count
        print(f"[ASSETS] Prepared {success_count}/{len(keywords)} assets")
        if failed_count > 0:
            print(f"[ASSETS] WARNING: {failed_count} icons failed (possibly rate limited)")
        return assets


if __name__ == "__main__":
    # Test the asset gatherer
    print("=" * 60)
    print("Testing Asset Gatherer")
    print("=" * 60)
    
    gatherer = AssetGatherer()
    
    # Test finding existing assets
    test_keywords = ["skull_emoji", "trash_can", "Edgar", "Fang", "TestKeyword"]
    
    for keyword in test_keywords:
        icon_path = gatherer.find_icon(keyword)
        print(f"  {keyword} -> {icon_path}")
    
    # Test batch prepare
    print("\nBatch prepare:")
    assets = gatherer.batch_prepare(["skull_emoji", "Edgar", "Fang"])
    for name, path in assets.items():
        print(f"  {name}: {path}")
