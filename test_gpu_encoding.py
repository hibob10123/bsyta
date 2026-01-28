"""
Test script to verify NVIDIA GPU encoding is working properly.
Run this to diagnose any GPU encoding issues.
"""

import subprocess
import sys
import os

def check_nvidia_gpu():
    """Check if NVIDIA GPU is detected"""
    print("="*70)
    print("1. CHECKING FOR NVIDIA GPU")
    print("="*70)
    
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ NVIDIA GPU detected!")
            print(f"  {result.stdout.strip()}")
            return True
        else:
            print("✗ nvidia-smi failed")
            return False
    except FileNotFoundError:
        print("✗ nvidia-smi not found - NVIDIA drivers may not be installed")
        return False
    except Exception as e:
        print(f"✗ Error checking GPU: {e}")
        return False

def check_ffmpeg_nvenc():
    """Check if FFmpeg has NVENC support"""
    print("\n" + "="*70)
    print("2. CHECKING FFMPEG NVENC SUPPORT")
    print("="*70)
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-hide_banner', '-encoders'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if 'h264_nvenc' in result.stdout:
            print("✓ FFmpeg has h264_nvenc support!")
            # Extract the line with h264_nvenc
            for line in result.stdout.split('\n'):
                if 'h264_nvenc' in line:
                    print(f"  {line.strip()}")
            return True
        else:
            print("✗ FFmpeg does NOT have h264_nvenc support")
            print("  You need to install FFmpeg with NVENC support")
            print("  Download from: https://github.com/BtbN/FFmpeg-Builds/releases")
            return False
    except FileNotFoundError:
        print("✗ FFmpeg not found in PATH")
        return False
    except Exception as e:
        print(f"✗ Error checking FFmpeg: {e}")
        return False

def test_nvenc_encoding():
    """Test actual NVENC encoding with a small sample"""
    print("\n" + "="*70)
    print("3. TESTING NVENC ENCODING")
    print("="*70)
    
    # Create a test pattern video (5 seconds, 1280x720)
    test_input = "data/temp/test_input.mp4"
    test_output = "data/temp/test_nvenc_output.mp4"
    
    os.makedirs("data/temp", exist_ok=True)
    
    print("Creating test input video...")
    try:
        # Generate test input (5 sec of test pattern)
        result = subprocess.run(
            [
                'ffmpeg', '-y', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=1280x720:rate=30',
                '-c:v', 'libx264', '-preset', 'ultrafast', test_input
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            print(f"✗ Failed to create test input: {result.stderr}")
            return False
        
        print("✓ Test input created")
    except Exception as e:
        print(f"✗ Error creating test input: {e}")
        return False
    
    print("\nTesting NVENC encoding (this will take a few seconds)...")
    try:
        # Test NVENC encoding
        result = subprocess.run(
            [
                'ffmpeg', '-y', 
                '-i', test_input,
                '-c:v', 'h264_nvenc',
                '-preset', 'p4',
                '-gpu', '1',  # GPU 1 = NVIDIA (GPU 0 = Intel Arc)
                '-rc:v', 'vbr',
                '-cq:v', '23',
                '-b:v', '5M',
                test_output
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✓ NVENC encoding SUCCESSFUL!")
            print("  Your GPU is working correctly for video encoding")
            
            # Check file size
            if os.path.exists(test_output):
                size_mb = os.path.getsize(test_output) / (1024 * 1024)
                print(f"  Test output: {size_mb:.2f} MB")
            
            # Cleanup
            try:
                os.remove(test_input)
                os.remove(test_output)
                print("  Test files cleaned up")
            except:
                pass
            
            return True
        else:
            print("✗ NVENC encoding FAILED")
            print(f"\nError details:\n{result.stderr}")
            
            # Try to provide helpful error messages
            if "Cannot load nvcuda.dll" in result.stderr or "cuda" in result.stderr.lower():
                print("\n💡 SOLUTION: Update your NVIDIA drivers")
                print("   Download from: https://www.nvidia.com/download/index.aspx")
            elif "No NVENC capable devices found" in result.stderr:
                print("\n💡 SOLUTION: Your GPU might not support NVENC or drivers are old")
                print("   1. Update NVIDIA drivers")
                print("   2. Make sure your laptop is in 'High Performance' power mode")
                print("   3. Ensure NVIDIA GPU is set as the default for Python:")
                print("      - Open NVIDIA Control Panel")
                print("      - Manage 3D Settings > Program Settings")
                print("      - Add python.exe and set to 'High-performance NVIDIA processor'")
            
            return False
    except Exception as e:
        print(f"✗ Error during NVENC test: {e}")
        return False

def check_laptop_power_settings():
    """Check if laptop is in the right power mode for GPU encoding"""
    print("\n" + "="*70)
    print("4. LAPTOP-SPECIFIC CHECKS")
    print("="*70)
    
    print("\n📝 YOUR LAPTOP GPU CONFIGURATION:")
    print("   GPU 0 = Intel Arc (integrated graphics)")
    print("   GPU 1 = NVIDIA RTX 5070 (discrete GPU)")
    print("   The code is configured to use GPU 1 (NVIDIA)")
    print("\n✅ SOLUTION: Force NVIDIA GPU usage")
    print("   1. Right-click Desktop > NVIDIA Control Panel")
    print("   2. Manage 3D Settings > Program Settings tab")
    print("   3. Click 'Add' and browse to:")
    print(f"      {sys.executable}")
    print("   4. Set 'Select the preferred graphics processor' to:")
    print("      'High-performance NVIDIA processor'")
    print("   5. Click Apply")
    print("\n✅ ALSO CHECK: Windows Power Mode")
    print("   - Set to 'Best Performance' or 'Performance' mode")
    print("   - Not 'Battery Saver' or 'Balanced'")
    print("\n✅ ASUS Armoury Crate (if installed):")
    print("   - Set to 'Turbo' or 'Performance' mode")
    print("   - Not 'Silent' or 'Windows' mode")

def main():
    print("\n🔍 NVIDIA GPU ENCODING DIAGNOSTIC TOOL")
    print("   For ASUS Zephyrus RTX 5070")
    print()
    
    has_gpu = check_nvidia_gpu()
    has_nvenc = check_ffmpeg_nvenc()
    
    if has_gpu and has_nvenc:
        encoding_works = test_nvenc_encoding()
    else:
        encoding_works = False
    
    check_laptop_power_settings()
    
    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)
    print(f"NVIDIA GPU detected:     {'✓ YES' if has_gpu else '✗ NO'}")
    print(f"FFmpeg NVENC support:    {'✓ YES' if has_nvenc else '✗ NO'}")
    print(f"NVENC encoding working:  {'✓ YES' if encoding_works else '✗ NO'}")
    
    if has_gpu and has_nvenc and encoding_works:
        print("\n🎉 SUCCESS! Your GPU encoding is set up correctly!")
        print("   Your videos will now encode 2-5x faster using your RTX 5070")
    else:
        print("\n⚠️  GPU encoding is NOT working yet")
        print("   Follow the solutions above to fix the issues")
    
    print("\n" + "="*70)
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
