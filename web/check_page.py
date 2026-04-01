from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    
    # Capture console errors
    errors = []
    page.on("console", lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
    
    page.goto('http://localhost:3001', wait_until='networkidle', timeout=15000)
    page.wait_for_timeout(2000)
    
    # Take screenshot
    page.screenshot(path='E:\\ai-project\\study-github\\learn-claude-code\\web\\page_check.png', full_page=True)
    
    # Get page title
    title = page.title()
    print(f"Title: {title}")
    
    # Check for errors
    if errors:
        print("\nConsole Errors:")
        for e in errors:
            print(f"  {e}")
    else:
        print("\nNo console errors detected")
    
    # Check visible text
    content = page.text_content('body')
    print(f"\nPage text (first 500 chars):")
    print(content[:500] if content else "No content")
    
    browser.close()
