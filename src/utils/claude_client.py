import os
import json
import time
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ClaudeClient:
    """Wrapper for Claude API with consistent configuration"""
    
    def __init__(self, model="claude-sonnet-4-5-20250929", max_tokens=16000, temperature=0.7):
        api_key = os.getenv("CLAUDE_API_KEY")
        if not api_key:
            raise ValueError("[ERROR] No CLAUDE_API_KEY found! Make sure it's in your .env file.")
        
        self.client = Anthropic(api_key=api_key, timeout=300.0)  # 5 minute timeout for very long scripts
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
    
    def ask(self, prompt, system_prompt=None, temperature=None, max_retries=3):
        """
        Simple ask method for general queries with automatic retry on timeout
        
        Args:
            prompt: User message
            system_prompt: Optional system context
            temperature: Override default temperature
            max_retries: Number of times to retry on timeout (default: 3)
        
        Returns:
            String response from Claude
        """
        messages = [{"role": "user", "content": prompt}]
        
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
            "messages": messages
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        for attempt in range(max_retries):
            try:
                print(f"[CLAUDE] Sending request (attempt {attempt + 1}/{max_retries})...")
                response = self.client.messages.create(**kwargs)
                return response.content[0].text
                
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Claude API Error on attempt {attempt + 1}: {e}")
                
                # Check if it's a timeout or rate limit error
                if "timeout" in error_msg.lower() or "rate" in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 30  # 30s, 60s, 90s
                        print(f"[RETRY] Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"[ERROR] Max retries ({max_retries}) exceeded")
                        import traceback
                        traceback.print_exc()
                        return None
                else:
                    # Non-retryable error
                    import traceback
                    traceback.print_exc()
                    return None
        
        return None
    
    def ask_json(self, prompt, system_prompt=None, temperature=None):
        """
        Ask Claude and expect a JSON response
        
        Args:
            prompt: User message
            system_prompt: Optional system context
            temperature: Override default temperature
        
        Returns:
            Parsed JSON dict or None on error
        """
        result = self.ask(prompt, system_prompt, temperature)
        
        if result:
            try:
                # Try to find JSON in the response (handle markdown code blocks)
                if "```json" in result:
                    json_str = result.split("```json")[1].split("```")[0].strip()
                elif "```" in result:
                    json_str = result.split("```")[1].split("```")[0].strip()
                else:
                    json_str = result.strip()
                
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse JSON response: {e}")
                print(f"Response was: {result[:200]}...")
                return None
        
        return None
    
    def test_connection(self):
        """Test if Claude API is working"""
        try:
            response = self.ask("Reply with just the word 'working' if you can read this.")
            if response and "working" in response.lower():
                print("[SUCCESS] Claude API connection successful!")
                return True
            else:
                print("[WARNING] Claude responded but unexpectedly")
                return False
        except Exception as e:
            print(f"[ERROR] Claude API test failed: {e}")
            return False


if __name__ == "__main__":
    # Test the client
    print("Testing Claude API Client...")
    client = ClaudeClient()
    client.test_connection()
    
    # Test JSON parsing
    print("\nTesting JSON response parsing...")
    result = client.ask_json(
        "Return a JSON object with keys 'name' and 'status', where name is 'test' and status is 'success'",
        system_prompt="You are a helpful assistant that returns valid JSON."
    )
    
    if result:
        print(f"Success - JSON parsing successful: {result}")
    else:
        print("Error - JSON parsing failed")
