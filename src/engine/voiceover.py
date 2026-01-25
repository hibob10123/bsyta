import os
import yaml
import re
import time
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from dotenv import load_dotenv
try:
    from moviepy import AudioFileClip, concatenate_audioclips
except ImportError:
    from moviepy.editor import AudioFileClip, concatenate_audioclips

# --- CONFIGURATION ---
load_dotenv()
API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not API_KEY:
    raise ValueError("[ERROR] No API Key found! Make sure you created the .env file.")

# Load voice settings from config
def load_voice_config():
    try:
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
            return config.get('voice', {})
    except:
        return {}

voice_config = load_voice_config()
VOICE_ID = voice_config.get('voice_id', "B8gJV1IhpuegLxdpXFOE")
MODEL_ID = voice_config.get('model_id', "eleven_multilingual_v2")

def split_into_sentences(text):
    """
    Split text into sentences intelligently.
    Handles abbreviations and common cases.
    """
    # Use regex to split on sentence boundaries
    # Keep the punctuation with the sentence
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    # Filter out empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences

def generate_voiceover(text, filename):
    """
    Generates high-quality audio using ElevenLabs API.
    Legacy function - generates single audio file.
    """
    save_path = f"data/temp/{filename}.mp3"
    
    # Initialize the client
    client = ElevenLabs(api_key=API_KEY)
    
    try:
        print(f"   [VOICE] ElevenLabs: Generating audio for '{filename}'...")
        
        # 1. Generate the audio stream
        audio_stream = client.text_to_speech.convert(
            text=text,
            voice_id=VOICE_ID,
            model_id=MODEL_ID,
            output_format="mp3_44100_128"
        )
        
        # 2. Save to file (Consumes the generator)
        # We manually write the bytes to ensure compatibility
        with open(save_path, "wb") as f:
            for chunk in audio_stream:
                if chunk:
                    f.write(chunk)
                    
        print(f"   [VOICE] Saved to: {save_path}")
        return save_path
        
    except Exception as e:
        print(f"   [ERROR] ElevenLabs Error: {e}")
        return None

def generate_voiceover_by_sentence(text, base_filename):
    """
    NEW: Generates audio sentence-by-sentence for precise timing.
    
    Args:
        text: Full script text
        base_filename: Base name for output files
    
    Returns:
        dict with:
        - 'sentences': List of sentence dicts with text, audio_path, duration, start_time, end_time
        - 'total_duration': Total duration of all sentences
        - 'combined_audio_path': Path to concatenated audio file
    """
    print(f"\n[VOICE] Generating sentence-level audio for precise timing...")
    
    # Split into sentences
    sentences = split_into_sentences(text)
    print(f"[VOICE] Split script into {len(sentences)} sentences")
    
    # Initialize client
    client = ElevenLabs(api_key=API_KEY)
    
    # Generate audio for each sentence
    sentence_data = []
    cumulative_time = 0.0
    
    os.makedirs("data/temp", exist_ok=True)
    
    for i, sentence_text in enumerate(sentences):
        print(f"\n[VOICE] Sentence {i+1}/{len(sentences)}: \"{sentence_text[:50]}...\"")
        
        # Generate audio for this sentence
        sentence_filename = f"{base_filename}_sentence_{i+1}"
        audio_path = f"data/temp/{sentence_filename}.mp3"
        
        # Retry logic with exponential backoff
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                # Add delay between requests to avoid rate limiting (after first sentence)
                if i > 0:
                    time.sleep(1.5)  # 1.5 second delay between sentences
                
                # Generate audio
                audio_stream = client.text_to_speech.convert(
                    text=sentence_text,
                    voice_id=VOICE_ID,
                    model_id=MODEL_ID,
                    output_format="mp3_44100_128"
                )
                
                # Save to file
                with open(audio_path, "wb") as f:
                    for chunk in audio_stream:
                        if chunk:
                            f.write(chunk)
                
                # Get actual duration
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration
                audio_clip.close()
                
                # Track timing
                start_time = cumulative_time
                end_time = cumulative_time + duration
                
                sentence_data.append({
                    'sentence_number': i + 1,
                    'text': sentence_text,
                    'audio_path': audio_path,
                    'duration': duration,
                    'start_time': start_time,
                    'end_time': end_time,
                    'word_count': len(sentence_text.split())
                })
                
                print(f"   Generated: {duration:.2f}s ({start_time:.2f}s - {end_time:.2f}s)")
                
                cumulative_time = end_time
                break  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    print(f"   WARNING: Attempt {attempt+1} failed: {error_msg}")
                    print(f"   ↻ Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print(f"   ERROR generating sentence {i+1} after {max_retries} attempts: {error_msg}")
                    print(f"   ℹ This is usually due to ElevenLabs rate limiting or network issues.")
                    print(f"   ℹ Consider: 1) Waiting a few minutes, 2) Using shorter scripts, 3) Checking API quota")
                    return None
    
    # Concatenate all sentence audio files
    print(f"\n[VOICE] Concatenating {len(sentence_data)} sentences...")
    combined_path = f"data/temp/{base_filename}_combined.mp3"
    
    try:
        # Load all audio clips
        clips = [AudioFileClip(s['audio_path']) for s in sentence_data]
        
        # Concatenate
        combined = concatenate_audioclips(clips)
        combined.write_audiofile(combined_path, logger=None)
        
        # Clean up
        for clip in clips:
            clip.close()
        combined.close()
        
        print(f"[VOICE] Combined audio saved: {combined_path}")
        print(f"[VOICE] Total duration: {cumulative_time:.2f}s")
        
    except Exception as e:
        print(f"[VOICE] ERROR concatenating audio: {e}")
        return None
    
    return {
        'sentences': sentence_data,
        'total_duration': cumulative_time,
        'combined_audio_path': combined_path
    }

if __name__ == "__main__":
    # Test it (Costs ~100 characters of credit)
    generate_voiceover("Within Supercell, there is a paradox. A tale of two sister games, on two completely different paths. On one hand, you have Clash Royale. A game long criticized for predatory monetization and stale metas, which, in the last year, has seen an explosive, unprecedented resurrection", "test_11labs")