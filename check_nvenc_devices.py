"""
Quick check to see what NVENC devices FFmpeg can find
"""
import subprocess

print("Checking what hardware encoders FFmpeg can see...\n")

# Check NVENC devices
print("="*70)
print("NVENC DEVICE CHECK")
print("="*70)

try:
    result = subprocess.run(
        ['ffmpeg', '-hide_banner', '-f', 'lavfi', '-i', 'nullsrc=s=256x256:d=1', 
         '-c:v', 'h264_nvenc', '-gpu', 'list', '-f', 'null', '-'],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*70)
print("CHECKING ALL AVAILABLE HARDWARE ENCODERS")
print("="*70)

try:
    result = subprocess.run(
        ['ffmpeg', '-hide_banner', '-encoders'],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    print("\nHardware encoders found:")
    for line in result.stdout.split('\n'):
        if 'nvenc' in line.lower() or 'qsv' in line.lower() or 'amf' in line.lower():
            print(f"  {line.strip()}")
            
except Exception as e:
    print(f"Error: {e}")

input("\nPress Enter to exit...")
