"""
Test encoding speed and GPU usage with NVENC vs CPU
"""
import subprocess
import time
import os

print("=" * 70)
print("ENCODING SPEED TEST - NVENC vs CPU")
print("=" * 70)

# Create a 10-second test video
print("\n[SETUP] Creating 10-second test video...")
subprocess.run([
    "ffmpeg", "-hide_banner", "-loglevel", "error",
    "-f", "lavfi", "-i", "testsrc=duration=10:size=1920x1080:rate=30",
    "-f", "lavfi", "-i", "sine=frequency=1000:duration=10",
    "-pix_fmt", "yuv420p",
    "-y",
    "data/temp/test_source.mp4"
], check=True)

print("✓ Test source created")

# Test 1: NVENC GPU Encoding
print("\n" + "=" * 70)
print("TEST 1: NVENC (GPU) ENCODING")
print("=" * 70)
print("\n⚠ WATCH TASK MANAGER NOW:")
print("  → Performance tab → GPU 0 → Video Encode")
print("  → Should show 80-100% usage during encoding")
print("\nStarting in 3 seconds...")
time.sleep(3)

start = time.time()
result = subprocess.run([
    "ffmpeg", "-hide_banner", "-loglevel", "info",
    "-i", "data/temp/test_source.mp4",
    "-c:v", "h264_nvenc",
    "-gpu", "0",  # Your NVIDIA GPU
    "-preset", "p4",
    "-cq:v", "23",
    "-b:v", "5M",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-y",
    "data/temp/test_nvenc.mp4"
], capture_output=True, text=True)

nvenc_time = time.time() - start

if result.returncode == 0:
    print(f"\n✓ NVENC encoding completed in {nvenc_time:.2f} seconds")
    # Check file size
    size_mb = os.path.getsize("data/temp/test_nvenc.mp4") / (1024 * 1024)
    print(f"  File size: {size_mb:.2f} MB")
else:
    print(f"\n✗ NVENC encoding FAILED")
    print(result.stderr)

# Test 2: CPU Encoding (for comparison)
print("\n" + "=" * 70)
print("TEST 2: CPU ENCODING (for comparison)")
print("=" * 70)
print("\n⚠ This will be SLOWER and use CPU instead")
print("Starting in 3 seconds...")
time.sleep(3)

start = time.time()
result = subprocess.run([
    "ffmpeg", "-hide_banner", "-loglevel", "error",
    "-i", "data/temp/test_source.mp4",
    "-c:v", "libx264",  # CPU encoder
    "-preset", "medium",
    "-crf", "23",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-y",
    "data/temp/test_cpu.mp4"
], capture_output=True, text=True)

cpu_time = time.time() - start

if result.returncode == 0:
    print(f"\n✓ CPU encoding completed in {cpu_time:.2f} seconds")
    size_mb = os.path.getsize("data/temp/test_cpu.mp4") / (1024 * 1024)
    print(f"  File size: {size_mb:.2f} MB")
else:
    print(f"\n✗ CPU encoding FAILED")

# Results
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

if result.returncode == 0 and nvenc_time > 0:
    speedup = cpu_time / nvenc_time
    print(f"\nNVENC (GPU): {nvenc_time:.2f}s")
    print(f"CPU:         {cpu_time:.2f}s")
    print(f"\nSpeedup:     {speedup:.2f}x faster with NVENC")
    
    if speedup < 1.5:
        print("\n⚠ WARNING: NVENC is not much faster!")
        print("  This suggests GPU encoding might not be working properly")
        print("  Expected speedup: 2-5x")
        print("\n  Possible issues:")
        print("  1. GPU might not actually be encoding (check Task Manager)")
        print("  2. Test video too short to show benefits")
        print("  3. Disk I/O bottleneck")
    elif speedup < 2.0:
        print("\n✓ GPU encoding is working, but could be faster")
        print("  Check that Task Manager showed high 'Video Encode' usage")
    else:
        print("\n✓✓✓ GPU encoding is working perfectly!")
        print("  Your videos will encode 2-5x faster")

# Cleanup
print("\n[CLEANUP] Removing test files...")
try:
    os.remove("data/temp/test_source.mp4")
    os.remove("data/temp/test_nvenc.mp4")
    os.remove("data/temp/test_cpu.mp4")
    print("✓ Cleanup complete")
except:
    pass

print("\n" + "=" * 70)
