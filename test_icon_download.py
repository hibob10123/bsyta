"""
Test icon downloading functionality
"""
import os
import sys

sys.path.append('src')
sys.path.append('src/scrapers')

from scrapers.asset_gatherer import AssetGatherer

print("=" * 70)
print("TESTING ICON DOWNLOADER")
print("=" * 70)

gatherer = AssetGatherer()

# Test keywords from your script
test_keywords = [
    "Edgar",
    "trash",
    "showdown",
    "meta",
    "nerf",
    "skull",
]

print("\nDownloading icons...\n")

for keyword in test_keywords:
    print(f"[{keyword}]")
    icon_path = gatherer.find_icon(keyword)
    
    if icon_path and os.path.exists(icon_path):
        size = os.path.getsize(icon_path)
        if size > 10000:
            print(f"  [SUCCESS] {icon_path} ({size} bytes)")
        else:
            print(f"  [PLACEHOLDER] {icon_path} ({size} bytes)")
    else:
        print(f"  [FAILED]")
    print("")

print("=" * 70)
print("Check data/assets/icons/ for downloaded files")
print("=" * 70)
