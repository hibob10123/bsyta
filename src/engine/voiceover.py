import os
from gtts import gTTS

def generate_voiceover(text, filename):
    """
    Generates an MP3 voiceover from text.
    Returns the path to the saved file.
    """
    save_path = f"data/temp/{filename}.mp3"
    
    # Create the audio object (lang='en', slow=False)
    tts = gTTS(text=text, lang='en', tld='com')
    
    try:
        tts.save(save_path)
        print(f"   [VOICE] Voice generated: {save_path}")
        return save_path
    except Exception as e:
        print(f"[ERROR] Error generating voice: {e}")
        return None

if __name__ == "__main__":
    # Test it out
    generate_voiceover("Is Fang actually broken? Let's look at the data.", "test_voice")