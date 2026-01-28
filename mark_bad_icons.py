#!/usr/bin/env python3
"""
Bad Icon Marker - Interactive Tool

After running preview_and_download_icons.py, use this to mark which icons are wrong.
It generates a shopping list of icons you need to manually download.

Usage:
    python mark_bad_icons.py
"""

import os
import json
from datetime import datetime

def normalize_filename(keyword):
    """Convert keyword to the correct manual_icons filename"""
    return keyword.lower().replace(" ", "_").replace("-", "_") + ".png"

def main():
    print("=" * 70)
    print("  BAD ICON MARKER")
    print("=" * 70)
    print()
    
    # Load the download report
    report_path = "data/icon_download_report.json"
    if not os.path.exists(report_path):
        print("❌ No report found!")
        print("Please run: python preview_and_download_icons.py first")
        return
    
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    downloads = report.get('downloads', [])
    
    # Filter to only web downloads (newly downloaded, most likely to be wrong)
    web_downloads = [d for d in downloads if d['source'] == 'WEB_DOWNLOAD']
    
    if not web_downloads:
        print("✓ No new downloads to review!")
        print("All icons are either manual overrides or cached.")
        return
    
    print(f"Found {len(web_downloads)} newly downloaded icons to review.\n")
    print("For each icon, I'll show you:")
    print("  - The keyword that triggered it")
    print("  - The sentence context")
    print("  - The downloaded file path")
    print()
    print("Mark icons as 'bad' if they're incorrect, and I'll generate a shopping list.\n")
    print("=" * 70)
    
    bad_icons = []
    
    for i, download in enumerate(web_downloads, 1):
        keyword = download['keyword']
        sentence = download['sentence']
        icon_path = download['icon_path']
        
        print(f"\n[{i}/{len(web_downloads)}]")
        print(f"Keyword:  \"{keyword}\"")
        print(f"Context:  {sentence}")
        print(f"File:     {os.path.basename(icon_path)}")
        print(f"Location: {icon_path}")
        
        # Ask user
        while True:
            response = input("\nIs this icon CORRECT? (y/n/skip): ").lower().strip()
            if response in ['y', 'yes']:
                print("  ✓ Marked as good")
                break
            elif response in ['n', 'no']:
                # Get reason
                reason = input("  What's wrong? (e.g. 'wrong person', 'generic icon', 'not the game item'): ").strip()
                if not reason:
                    reason = "incorrect"
                
                bad_icons.append({
                    'keyword': keyword,
                    'sentence': sentence,
                    'current_path': icon_path,
                    'reason': reason,
                    'needed_filename': normalize_filename(keyword)
                })
                print(f"  ✗ Marked as bad: {reason}")
                break
            elif response in ['s', 'skip']:
                print("  ⊘ Skipped")
                break
            else:
                print("  Please enter y (yes), n (no), or s (skip)")
    
    # Generate shopping list
    if not bad_icons:
        print("\n" + "=" * 70)
        print("✓ ALL ICONS ARE GOOD!")
        print("=" * 70)
        print("\nNo bad icons found. You're ready to generate videos!")
        return
    
    print("\n" + "=" * 70)
    print("❌ BAD ICONS SHOPPING LIST")
    print("=" * 70)
    print(f"\nFound {len(bad_icons)} incorrect icons that need manual overrides.\n")
    
    # Save shopping list
    shopping_list_path = "data/manual_icons_needed.txt"
    with open(shopping_list_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("  ICONS TO DOWNLOAD MANUALLY\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Total icons needed: {len(bad_icons)}\n")
        f.write("\n" + "=" * 70 + "\n\n")
        
        for i, bad in enumerate(bad_icons, 1):
            f.write(f"{i}. {bad['keyword']}\n")
            f.write(f"   Problem: {bad['reason']}\n")
            f.write(f"   Context: {bad['sentence']}\n")
            f.write(f"   Current: {bad['current_path']}\n")
            f.write(f"   \n")
            f.write(f"   TO FIX:\n")
            f.write(f"   1. Find correct image for \"{bad['keyword']}\"\n")
            f.write(f"   2. Save as: data/assets/manual_icons/{bad['needed_filename']}\n")
            f.write(f"   3. Recommended: 512x512px PNG with transparency\n")
            f.write("\n" + "-" * 70 + "\n\n")
    
    print(f"✓ Shopping list saved to: {shopping_list_path}\n")
    
    # Print summary to console
    print("Quick reference:")
    print()
    for i, bad in enumerate(bad_icons, 1):
        print(f"{i}. \"{bad['keyword']}\" → {bad['needed_filename']}")
        print(f"   Issue: {bad['reason']}")
        print()
    
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print(f"1. Open: {shopping_list_path}")
    print(f"2. For each icon, download the correct image")
    print(f"3. Save to: data/assets/manual_icons/[filename]")
    print(f"4. Re-run: python preview_and_download_icons.py")
    print(f"5. Verify manual overrides work correctly")
    print()
    print("Tips for finding correct images:")
    print("  - YouTubers/Streamers: Use their profile pictures")
    print("  - Game items: Check game wikis or official press kits")
    print("  - Logos: Search '[brand name] official logo png'")
    print("  - Characters: Search '[game name] [character] official art'")
    print()
    print("=" * 70)
    
    # Save JSON report
    bad_icons_report = {
        'timestamp': datetime.now().isoformat(),
        'total_bad_icons': len(bad_icons),
        'bad_icons': bad_icons
    }
    
    report_json_path = "data/bad_icons_report.json"
    with open(report_json_path, 'w', encoding='utf-8') as f:
        json.dump(bad_icons_report, f, indent=2, ensure_ascii=False)
    
    print(f"✓ JSON report saved to: {report_json_path}\n")

if __name__ == "__main__":
    main()
