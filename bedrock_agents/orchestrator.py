import sys
from .staff.content_director import ContentDirector
from .staff.web_developer import WebDeveloper
from .staff.publishing_manager import PublishingManager
from .staff.photo_designer import PhotoDesigner

def main():
    print("========================================")
    print("🏢 Bedrock Insurance - Daily Cycle Start")
    print("========================================")
    
    # 1. Content Director Plans
    director = ContentDirector()
    try:
        brief = director.create_daily_brief()
        print(f"\n📋 Creative Brief: {brief['title']}")
        print(f"   Theme: {brief['theme']}")
    except Exception as e:
        print(f"❌ Director Failed: {e}")
        return

    # 2. Photo Designer Creates Assets
    designer = PhotoDesigner()
    image_path = None
    try:
        # Extract concept if available, otherwise use title
        concept = brief.get('image_concept', brief['title'])
        image_path = designer.generate_image(brief['theme'], concept)
        print(f"\n📸 Image Generated: {image_path}")
    except Exception as e:
        print(f"⚠️ Photo Designer Failed (Using Placeholder): {e}")

    # 3. Web Developer Builds (with Image)
    web_dev = WebDeveloper()
    try:
        html_content = web_dev.build_page(brief, image_path)
        print(f"\n🏗️  HTML Generated ({len(html_content)} chars)")
    except Exception as e:
        print(f"❌ Web Dev Failed: {e}")
        return

    # 4. Compliance (Placeholder for now)
    print("\n⚖️  Compliance Officer: Auto-Approved (Bypassed)")

    # 4. Publishing Manager Deploys
    publisher = PublishingManager()
    
    # Check for dry run
    if "--dry-run" in sys.argv:
        print("\n🚫 Dry Run: Skipping Deployment.")
        print("--- Generated HTML Preview ---")
        print(html_content[:500] + "...")
    else:
        try:
            publisher.update_website(html_content, brief['theme'])
        except Exception as e:
            print(f"❌ Publisher Failed: {e}")

    print("\n========================================")
    print("✅ Daily Cycle Complete")
    print("========================================")

if __name__ == "__main__":
    main()
