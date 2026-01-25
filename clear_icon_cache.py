"""Clear cached icons to force fresh downloads"""
import os
import shutil

icons_dir = "data/assets/icons"

print("="*70)
print("CLEAR ICON CACHE")
print("="*70)

if os.path.exists(icons_dir):
    # Count files
    files = [f for f in os.listdir(icons_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    count = len(files)
    
    if count == 0:
        print(f"\nNo icons found in {icons_dir}")
    else:
        print(f"\nFound {count} cached icons in {icons_dir}")
        print("\nIcons to be deleted:")
        for f in files[:10]:  # Show first 10
            print(f"  - {f}")
        if count > 10:
            print(f"  ... and {count - 10} more")
        
        response = input(f"\nDelete all {count} icons? (y/n): ").lower().strip()
        
        if response == 'y':
            for f in files:
                try:
                    os.remove(os.path.join(icons_dir, f))
                except Exception as e:
                    print(f"Failed to delete {f}: {e}")
            
            print(f"\n✓ Deleted {count} icons!")
            print("Next icon search will download fresh icons with improved queries.")
        else:
            print("\nCancelled. No icons were deleted.")
else:
    print(f"\n{icons_dir} doesn't exist yet.")

print("\n" + "="*70)
