"""
B-Roll Asset Gatherer - Downloads relevant images/videos for b-roll footage
"""
import os
import requests
from PIL import Image
import io
import time
from duckduckgo_search import DDGS

class BRollGatherer:
    """
    Automatically finds and downloads b-roll images for video production
    """
    
    def __init__(self, assets_dir="data/assets"):
        self.assets_dir = assets_dir
        self.broll_dir = os.path.join(assets_dir, "broll")
        os.makedirs(self.broll_dir, exist_ok=True)
    
    def find_broll_images(self, search_query, count=3):
        """
        Find and download b-roll images for a topic
        
        Args:
            search_query: What to search for (e.g., "Brawl Stars gameplay", "Toy Story characters")
            count: Number of images to download
        
        Returns:
            List of paths to downloaded images
        """
        print(f"[B-ROLL] Searching for: {search_query}")
        
        downloaded = []
        
        try:
            # Small delay to avoid rate limits
            time.sleep(1.5)
            
            with DDGS() as ddgs:
                # Search for high-quality, landscape images
                results = list(ddgs.images(
                    keywords=f"{search_query} high quality wallpaper",
                    max_results=count * 3,  # Get extra options
                    size="Large"  # Request large images
                ))
            
            if not results:
                print(f"[B-ROLL] No images found for: {search_query}")
                return []
            
            # Skip watermarked sources
            skip_domains = ['shutterstock', 'gettyimages', 'istockphoto', 'adobe', 'depositphotos']
            
            attempts = 0
            for i, result in enumerate(results):
                if len(downloaded) >= count:
                    break
                
                try:
                    image_url = result.get('image')
                    if not image_url:
                        continue
                    
                    # Skip watermarked sources
                    if any(domain in image_url.lower() for domain in skip_domains):
                        continue
                    
                    attempts += 1
                    print(f"[B-ROLL] Downloading image {attempts}/{count}...")
                    
                    # Download
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(image_url, timeout=10, headers=headers)
                    response.raise_for_status()
                    
                    # Verify it's an image
                    img = Image.open(io.BytesIO(response.content))
                    
                    # Convert to RGB (remove alpha channel if present)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (0, 0, 0))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize to 1920x1080 maintaining aspect ratio
                    img = self._resize_to_1080p(img)
                    
                    # Save
                    safe_query = "".join(c if c.isalnum() or c in (' ', '-') else '_' for c in search_query)
                    safe_query = safe_query.replace(' ', '_')[:30]
                    output_path = os.path.join(self.broll_dir, f"{safe_query}_{len(downloaded)}.jpg")
                    img.save(output_path, quality=95)
                    
                    downloaded.append(output_path)
                    print(f"[B-ROLL] Downloaded: {output_path}")
                    
                    # Small delay between downloads
                    time.sleep(0.8)
                    
                except Exception as e:
                    print(f"[B-ROLL] Download failed: {e}")
                    continue
            
            print(f"[B-ROLL] Downloaded {len(downloaded)}/{count} images")
            return downloaded
            
        except Exception as e:
            print(f"[B-ROLL] Search failed: {e}")
            return []
    
    def _resize_to_1080p(self, img):
        """Resize image to 1920x1080 (crop to fit)"""
        target_w, target_h = 1920, 1080
        target_ratio = target_w / target_h
        
        img_w, img_h = img.size
        img_ratio = img_w / img_h
        
        if img_ratio > target_ratio:
            # Image is wider - crop width
            new_h = target_h
            new_w = int(new_h * img_ratio)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Center crop
            left = (new_w - target_w) // 2
            img = img.crop((left, 0, left + target_w, target_h))
        else:
            # Image is taller - crop height
            new_w = target_w
            new_h = int(new_w / img_ratio)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            # Center crop
            top = (new_h - target_h) // 2
            img = img.crop((0, top, target_w, top + target_h))
        
        return img
    
    def batch_prepare(self, topics, images_per_topic=3):
        """
        Prepare b-roll for multiple topics
        
        Args:
            topics: List of search queries
            images_per_topic: How many images per topic
        
        Returns:
            Dictionary mapping topic to list of image paths
        """
        broll_assets = {}
        
        for topic in topics:
            images = self.find_broll_images(topic, count=images_per_topic)
            if images:
                broll_assets[topic] = images
        
        print(f"[B-ROLL] Prepared b-roll for {len(broll_assets)} topics")
        return broll_assets


if __name__ == "__main__":
    # Test the b-roll gatherer
    print("="*70)
    print("Testing B-Roll Gatherer")
    print("="*70)
    
    gatherer = BRollGatherer()
    
    test_queries = [
        "Brawl Stars gameplay",
        "Toy Story Buzz Lightyear"
    ]
    
    for query in test_queries:
        print(f"\n{'='*70}")
        print(f"Searching: {query}")
        print('='*70)
        images = gatherer.find_broll_images(query, count=2)
        print(f"\nDownloaded {len(images)} images:")
        for img in images:
            print(f"  - {img}")
