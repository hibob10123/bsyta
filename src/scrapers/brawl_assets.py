import shutil
import os

# This is where we cloned that massive GitHub repo
REPO_PATH = "data/assets_repo"
# This is where we put files for the CURRENT video project
PROJECT_PATH = "data/current_video_assets"

def fetch_local_asset(asset_type, name):
    """
    Instead of downloading, we find it in our local giant repo 
    and copy it to our working folder.
    """
    # 1. Define where these live in the repo (You'll need to explore the repo folder to find paths)
    paths = {
        "brawler": f"{REPO_PATH}/brawlers/Default",
        "icon": f"{REPO_PATH}/avatars",
        "map": f"{REPO_PATH}/maps"
    }
    
    source_dir = paths.get(asset_type)
    if not source_dir:
        print(f"❌ Unknown asset type: {asset_type}")
        return

    # 2. Search for the file (handling capitalizations)
    # The repo might name it "fang.png" or "Fang.png"
    found_file = None
    for filename in os.listdir(source_dir):
        if filename.lower().startswith(name.lower()):
            found_file = filename
            break
            
    if found_file:
        # Copy it to your project folder
        os.makedirs(PROJECT_PATH, exist_ok=True)
        shutil.copy(f"{source_dir}/{found_file}", f"{PROJECT_PATH}/{found_file}")
        print(f"✅ Retrieved {name} from local repo.")
    else:
        print(f"⚠️ Could not find {name} in local repo. Checking API...")
        # Fallback to the API downloader we wrote earlier!