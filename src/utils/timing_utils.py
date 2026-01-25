import re
from typing import List, Tuple

def parse_timestamp(timestamp_str):
    """
    Parse timestamp string to seconds
    Examples: "1.5s", "0:30", "1:30.5"
    """
    if isinstance(timestamp_str, (int, float)):
        return float(timestamp_str)
    
    timestamp_str = str(timestamp_str).strip()
    
    # Format: "1.5s" or "1.5"
    if 's' in timestamp_str or '.' in timestamp_str:
        return float(timestamp_str.replace('s', ''))
    
    # Format: "1:30" or "0:30.5"
    if ':' in timestamp_str:
        parts = timestamp_str.split(':')
        minutes = float(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    
    return float(timestamp_str)

def format_timestamp(seconds):
    """Convert seconds to readable timestamp"""
    if seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}:{secs:05.2f}"

def calculate_stagger_times(base_time, count, stagger_interval=0.3):
    """
    Calculate staggered appearance times for multiple elements
    
    Args:
        base_time: Starting timestamp
        count: Number of elements
        stagger_interval: Time between each element appearance
    
    Returns:
        List of timestamps
    """
    return [base_time + (i * stagger_interval) for i in range(count)]

def split_script_into_segments(script_text, num_segments=3):
    """
    Split script into roughly equal segments based on sentences
    
    Args:
        script_text: Full script
        num_segments: How many segments to create
    
    Returns:
        List of script segments
    """
    # Split by periods, exclamation marks, question marks
    sentences = re.split(r'[.!?]+', script_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    
    if len(sentences) < num_segments:
        # Pad if too few sentences
        while len(sentences) < num_segments:
            sentences.append(sentences[-1])
    
    # Calculate roughly equal chunks
    chunk_size = len(sentences) // num_segments
    segments = []
    
    for i in range(num_segments):
        start_idx = i * chunk_size
        if i == num_segments - 1:
            # Last segment gets remaining sentences
            end_idx = len(sentences)
        else:
            end_idx = start_idx + chunk_size
        
        segment_sentences = sentences[start_idx:end_idx]
        segments.append('. '.join(segment_sentences) + '.')
    
    return segments

def estimate_speech_duration(text, words_per_minute=150):
    """
    Estimate how long it will take to speak text
    
    Args:
        text: Script text
        words_per_minute: Average speaking rate
    
    Returns:
        Duration in seconds
    """
    words = len(text.split())
    minutes = words / words_per_minute
    return minutes * 60

if __name__ == "__main__":
    # Test utilities
    print("🧪 Testing Timing Utilities...\n")
    
    # Test timestamp parsing
    print("Timestamp parsing:")
    print(f"  '1.5s' -> {parse_timestamp('1.5s')}s")
    print(f"  '1:30' -> {parse_timestamp('1:30')}s")
    print(f"  '0:45.5' -> {parse_timestamp('0:45.5')}s")
    
    # Test stagger times
    print("\nStagger times (base=2.0, count=5):")
    times = calculate_stagger_times(2.0, 5, 0.3)
    print(f"  {[format_timestamp(t) for t in times]}")
    
    # Test script splitting
    test_script = "First sentence here. Second sentence now. Third one coming. Fourth is here. Fifth and final."
    segments = split_script_into_segments(test_script, 3)
    print(f"\nScript segments (3):")
    for i, seg in enumerate(segments):
        print(f"  Segment {i+1}: {seg[:50]}...")
    
    # Test duration estimation
    duration = estimate_speech_duration(test_script)
    print(f"\nEstimated duration: {format_timestamp(duration)}")
    
    print("\n✅ Timing utilities working!")
