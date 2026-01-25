import os
import sys
import time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw, ImageFont

# Import stealth function
try:
    from playwright_stealth import stealth_sync
except ImportError:
    def stealth_sync(page):
        pass

class TwitterIntelligence:
    """
    Integration for Twitter/X content in videos
    """
    
    def __init__(self):
        pass
    
    def screenshot_tweet(self, tweet_url, output_path=None):
        """
        Attempt to screenshot a tweet URL
        """
        if output_path is None:
            timestamp = int(time.time())
            output_path = f"data/assets/tweet_{timestamp}.png"
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Normalize URL (x.com -> twitter.com often works better with tools)
        tweet_url = tweet_url.replace('x.com', 'twitter.com')
        
        print(f"[TWITTER] Attempting to screenshot: {tweet_url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            
            page = context.new_page()
            stealth_sync(page)
            
            try:
                # Twitter is VERY aggressive with login walls. 
                # We'll try to use a "nitter" instance or similar if it fails, 
                # but for now let's try direct screenshot.
                
                page.goto(tweet_url, timeout=30000, wait_until="networkidle")
                time.sleep(3)  # Wait for rendering
                
                # Try to find the tweet article
                tweet_selector = 'article[data-testid="tweet"]'
                try:
                    page.wait_for_selector(tweet_selector, timeout=5000)
                    tweet_element = page.locator(tweet_selector).first
                    tweet_element.screenshot(path=output_path)
                    print(f"[TWITTER] Screenshot saved: {output_path}")
                    browser.close()
                    return output_path
                except:
                    print("[TWITTER] Could not find tweet element (likely login wall)")
                    browser.close()
                    return None
                    
            except Exception as e:
                print(f"[TWITTER] Error screenshotting: {e}")
                browser.close()
                return None

    def generate_tweet_graphic(self, tweet_data, output_path=None):
        """
        Generate a fake tweet graphic from text/metadata
        Useful as fallback if screenshotting fails or for 'hard-pasted' text
        """
        if output_path is None:
            timestamp = int(time.time())
            output_path = f"data/assets/tweet_gen_{timestamp}.png"
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        text = tweet_data.get('text', 'No content provided')
        user = tweet_data.get('user', 'Twitter User')
        handle = tweet_data.get('handle', '@user')
        date = tweet_data.get('date', 'Jan 1, 2024')
        
        print(f"[TWITTER] Generating graphic for: {user} ({handle})")
        
        # Twitter Dark Mode style
        bg_color = (21, 32, 43)  # Dark blue/black
        text_color = (255, 255, 255)
        secondary_text_color = (136, 153, 166)
        
        # Create image
        width, height = 1000, 400
        # Adjust height based on text length
        lines = self._wrap_text(text, 50)
        height = 150 + (len(lines) * 40) + 100
        
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to load fonts
            font_path = "C:/Windows/Fonts/arialbd.ttf"  # Bold for name
            font_reg_path = "C:/Windows/Fonts/arial.ttf"
            
            if not os.path.exists(font_path):
                font_path = "arial.ttf"
                
            name_font = ImageFont.truetype(font_path, 32)
            handle_font = ImageFont.truetype(font_reg_path, 24)
            text_font = ImageFont.truetype(font_reg_path, 30)
            meta_font = ImageFont.truetype(font_reg_path, 20)
            
            # Draw User Avatar Placeholder
            draw.ellipse([40, 40, 100, 100], fill=(50, 60, 70))
            
            # Draw Name and Handle
            draw.text((120, 40), user, font=name_font, fill=text_color)
            draw.text((120, 80), handle, font=handle_font, fill=secondary_text_color)
            
            # Draw Text
            y_pos = 140
            for line in lines:
                draw.text((40, y_pos), line, font=text_font, fill=text_color)
                y_pos += 45
                
            # Draw Date/Meta
            draw.text((40, y_pos + 20), date, font=meta_font, fill=secondary_text_color)
            
            # Add X Logo (simplified)
            draw.text((width - 80, 40), "X", font=name_font, fill=text_color)
            
        except Exception as e:
            print(f"[TWITTER] Font error: {e}, using default")
            draw.text((40, 40), f"{user} {handle}", fill=text_color)
            draw.text((40, 100), text, fill=text_color)
        
        img.save(output_path)
        print(f"[TWITTER] Generated graphic saved: {output_path}")
        return output_path

    def _wrap_text(self, text, max_chars):
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= max_chars:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
            
        return lines
