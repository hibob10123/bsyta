import os
import requests
from duckduckgo_search import DDGS

def download_icon(keyword, filename_override=None):
    """
    Searches for an icon/PNG and downloads it to data/assets/icons/
    """
    # 1. Setup paths
    save_dir = "data/assets/icons"
    os.makedirs(save_dir, exist_ok=True)
    
    # Clean filename
    clean_name = filename_override if filename_override else keyword.replace(" ", "_")
    save_path = os.path.join(save_dir, f"{clean_name}.png")

    # If we already have it, skip downloading (Cache)
    if os.path.exists(save_path):
        print(f"   ✅ Icon found in cache: {clean_name}")
        return save_path

    print(f"   ⬇️ Searching for icon: '{keyword}'...")

    # 2. Search DuckDuckGo
    # We add "transparent png icon" to ensure we get good assets
    search_query = f"{keyword} icon transparent background png"
    
    try:
        with DDGS() as ddgs:
            # Get 1 result
            results = list(ddgs.images(
                search_query, 
                max_results=1, 
                type_image="transparent", # Try to filter for transparent
            ))
            
            if not results:
                print(f"   ❌ No images found for {keyword}")
                return None
                
            image_url = results[0]['image']

            # 3. Download
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ Downloaded: {save_path}")
                return save_path
            else:
                print("   ❌ Download failed (Bad Status)")
                return None

    except Exception as e:
        print(f"   ❌ Error searching for icon: {e}")
        return None

if __name__ == "__main__":
    # Test it
    download_icon("trash can")
    download_icon("skull emoji")