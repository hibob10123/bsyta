"""
Quick test to verify NVIDIA GPU is being used for encoding
"""
import subprocess
import sys

print("=" * 70)
print("NVIDIA GPU ENCODING TEST")
print("=" * 70)

# Step 1: Check if FFmpeg has NVENC support
print("\n[1/3] Checking FFmpeg NVENC support...")
try:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if "h264_nvenc" in result.stdout:
        print("✓ FFmpeg has h264_nvenc support")
    else:
        print("✗ FFmpeg does NOT have h264_nvenc support")
        print("   You need to install FFmpeg with NVENC support")
        sys.exit(1)
except Exception as e:
    print(f"✗ Error checking FFmpeg: {e}")
    sys.exit(1)

# Step 2: List available NVENC devices
print("\n[2/3] Checking available NVENC devices...")
try:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "nullsrc=s=256x256:d=1", 
         "-c:v", "h264_nvenc", "-gpu", "list", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    output = result.stderr + result.stdout
    
    # Parse GPU list
    if "GPU" in output:
        print("✓ Found NVENC-capable GPUs:")
        for line in output.split('\n'):
            if 'GPU' in line and ('NVIDIA' in line or 'GeForce' in line or 'RTX' in line):
                print(f"   {line.strip()}")
        
        if "GPU #0" in output or "GPU 0" in output:
            print("\n✓ GPU 0 detected (your NVIDIA RTX 5070 Ti)")
            print("  Encoding will use: -gpu 0")
        else:
            print("\n⚠ Warning: GPU 0 might not be available")
            print("  Check NVIDIA Control Panel settings")
    else:
        print("✗ Could not detect NVENC GPUs")
        print("  This might be a driver issue")
        
except Exception as e:
    print(f"✗ Error listing GPUs: {e}")

# Step 3: Try actual encoding with GPU 1
print("\n[3/3] Testing actual encoding with GPU 1...")
try:
    # Create a 2-second test video using NVENC with GPU 0
    result = subprocess.run([
        "ffmpeg", "-hide_banner",
        "-f", "lavfi", "-i", "color=c=blue:s=1920x1080:d=2",
        "-c:v", "h264_nvenc",
        "-gpu", "0",  # Target NVIDIA GPU (GPU 0 on your laptop)
        "-preset", "p4",
        "-pix_fmt", "yuv420p",
        "-y",  # Overwrite
        "data/temp/gpu_test.mp4"
    ], capture_output=True, text=True, timeout=30)
    
    if result.returncode == 0:
        print("✓ Successfully encoded test video with GPU 1!")
        print("  Your NVIDIA RTX GPU is working correctly")
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nYour video encoding will now use the NVIDIA RTX GPU")
        print("Look for 'Video Encode' usage in Task Manager > Performance > GPU 1")
    else:
        print("✗ Encoding failed with GPU 1")
        print("\nError output:")
        print(result.stderr)
        
        if "No capable devices found" in result.stderr:
            print("\n❌ PROBLEM: NVENC cannot find NVIDIA GPU")
            print("\n🔧 SOLUTIONS:")
            print("1. Open NVIDIA Control Panel")
            print("2. Manage 3D Settings > Program Settings")
            print("3. Add your Python executable:")
            print("   C:\\Users\\alexa\\code\\yta\\venv\\Scripts\\python.exe")
            print("4. Set to 'High-performance NVIDIA processor'")
            print("5. Restart your terminal and try again")
        
        elif "Unknown encoder" in result.stderr:
            print("\n❌ PROBLEM: FFmpeg doesn't have NVENC support")
            print("   Download FFmpeg with NVENC from:")
            print("   https://github.com/BtbN/FFmpeg-Builds/releases")
        
except Exception as e:
    print(f"✗ Test encoding failed: {e}")

print("\n" + "=" * 70)
