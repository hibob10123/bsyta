import os
import sys
import time
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

class YouTubeIntelligence:
    """
    Integration for YouTube content and evidence in videos
    """
    
    def __init__(self):
        pass
    
    def generate_youtube_graphic(self, video_data, output_path=None):
        """
        Generate a YouTube video evidence card (thumbnail + title + channel)
        """
        if output_path is None:
            timestamp = int(time.time())
            output_path = f"data/assets/youtube_{timestamp}.png"
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        url = video_data.get('url', '')
        title = video_data.get('title', 'YouTube Video')
        channel = video_data.get('channel', 'YouTube Channel')
        views = video_data.get('views', 'Evidence')
        
        print(f"[YOUTUBE] Generating graphic for: {title} by {channel}")
        
        # YouTube Dark Mode style
        bg_color = (15, 15, 15)  # Very dark gray
        text_color = (255, 255, 255)
        secondary_text_color = (170, 170, 170)
        
        # Create image
        width, height = 1200, 400
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        try:
            # Try to load fonts
            font_path = "C:/Windows/Fonts/arialbd.ttf"
            font_reg_path = "C:/Windows/Fonts/arial.ttf"
            
            if not os.path.exists(font_path):
                font_path = "arial.ttf"
                
            title_font = ImageFont.truetype(font_path, 36)
            channel_font = ImageFont.truetype(font_reg_path, 28)
            meta_font = ImageFont.truetype(font_reg_path, 24)
            
            # 1. Draw Thumbnail (Left side)
            thumb_w, thumb_h = 480, 270
            thumb_x, thumb_y = 40, 65
            
            # Try to fetch actual thumbnail
            thumbnail_loaded = False
            video_id = self._extract_video_id(url)
            
            if video_id:
                # Try different qualities (maxres down to mq)
                thumb_urls = [
                    f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                    f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                    f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                ]
                
                for thumb_url in thumb_urls:
                    try:
                        resp = requests.get(thumb_url, timeout=5)
                        if resp.status_code == 200:
                            thumb_img = Image.open(BytesIO(resp.content)).convert('RGB')
                            # Resize to fit
                            thumb_img = thumb_img.resize((thumb_w, thumb_h), Image.LANCZOS)
                            img.paste(thumb_img, (thumb_x, thumb_y))
                            thumbnail_loaded = True
                            print(f"[YOUTUBE] Successfully loaded thumbnail from {thumb_url}")
                            break
                    except:
                        continue
            
            if not thumbnail_loaded:
                # Fallback to placeholder if no video_id or fetch failed
                draw.rectangle([thumb_x, thumb_y, thumb_x + thumb_w, thumb_y + thumb_h], fill=(40, 40, 40), outline=(60, 60, 60))
                # Add "Play" icon symbol
                play_size = 60
                center_x, center_y = thumb_x + thumb_w//2, thumb_y + thumb_h//2
                draw.polygon([
                    (center_x - play_size//2, center_y - play_size//2),
                    (center_x - play_size//2, center_y + play_size//2),
                    (center_x + play_size//2, center_y)
                ], fill=(255, 255, 255, 200))
            
            # 2. Draw Text (Right side)
            text_x = 560
            
            # Wrap title if too long
            title_lines = self._wrap_text(title, 35)
            y_pos = 65
            for line in title_lines[:2]: # Max 2 lines
                draw.text((text_x, y_pos), line, font=title_font, fill=text_color)
                y_pos += 45
                
            # Channel and Meta
            y_pos = 200
            draw.text((text_x, y_pos), channel, font=channel_font, fill=secondary_text_color)
            draw.text((text_x, y_pos + 45), views, font=meta_font, fill=secondary_text_color)
            
            # Add YouTube Logo (Red rectangle + White triangle)
            logo_x, logo_y = width - 100, 40
            draw.rectangle([logo_x, logo_y, logo_x + 60, logo_y + 40], fill=(255, 0, 0))
            draw.polygon([
                (logo_x + 20, logo_y + 10),
                (logo_x + 20, logo_y + 30),
                (logo_x + 45, logo_y + 20)
            ], fill=(255, 255, 255))
            
        except Exception as e:
            print(f"[YOUTUBE] Font/Graphics error: {e}, using basic text")
            draw.text((40, 40), title, fill=text_color)
            draw.text((40, 100), channel, fill=secondary_text_color)
        
        img.save(output_path)
        print(f"[YOUTUBE] Generated graphic saved: {output_path}")
        return output_path

    def _extract_video_id(self, url):
        """Extract video ID from various YouTube URL formats"""
        if not url:
            return None
            
        import re
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:be\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11}).*',
            r'^([0-9A-Za-z_-]{11})$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

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

if __name__ == "__main__":
    yt = YouTubeIntelligence()
    yt.generate_youtube_graphic({
        'title': 'The Brawl Stars Update That Changed Everything',
        'channel': 'KairosTime Gaming',
        'views': '1.2M views'
    }, "test_youtube_card.png")
