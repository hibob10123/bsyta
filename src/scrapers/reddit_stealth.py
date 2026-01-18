from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync # to avoid reddit captcha
import time

def find_and_screenshot_post(topic="Fang"):
    with sync_playwright() as p:
        # launch browser
        browser = p.chromium.launch(headless=False) 
        
        # context for stealth
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/Chicago" # Matches your location (Rice U)
        )
        
        page = context.new_page()
        stealth_sync(page)

        print(f"Searching r/BrawlStars for '{topic}'...")
        page.goto(f"https://www.reddit.com/r/BrawlStars/search/?q={topic}&restrict_sr=1&sort=top")
        
        # --- HUMAN INTERVENTION CHECKPOINT ---
        # If you see the CAPTCHA, solve it manually now. 
        # The script waits here until the 'Play' button in the Playwright Inspector is pressed
        # OR until it finds the element below.
        try:
            page.wait_for_selector('a[data-testid="post-title"]', timeout=5000)
        except:
            print("⚠️ CAPTCHA or Login Wall detected! Please solve it manually in the browser window.")
            print("To continue the script, press the 'Resume' (Play) button in the Playwright Inspector window.")
            page.pause() 
        
        # 4. Click the first result
        page.click('a[data-testid="post-title"] >> nth=0')
        page.wait_for_load_state("networkidle") # Wait for comments to load fully

        # 5. Clean up the view (Remove "Open App" & "Login" popups)
        page.evaluate("""
            document.querySelectorAll('button').forEach(b => {
                if(b.innerText.includes('Open') || b.innerText.includes('Log In')) b.remove(); 
            });
            // Try to remove the bottom sticky banner
            const bottomBar = document.querySelector('shreddit-async-loader[bundlename="faceplate_batch"]');
            if(bottomBar) bottomBar.remove();
        """)
        
        # 6. Screenshot
        post_element = page.locator('shreddit-post').first
        if post_element.count() == 0:
             # Fallback for old reddit or different UI
             post_element = page.locator('#siteTable').first

        output_filename = f"data/assets/{topic}_evidence.png"
        post_element.screenshot(path=output_filename)
        print(f"📸 Saved evidence to {output_filename}")

        browser.close()

if __name__ == "__main__":
    find_and_screenshot_post("Fang Buff")