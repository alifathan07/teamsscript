import time
import re
import json
import os
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
GROUP_NAME = "Ali Fathan"
YOUR_NAME = "ali fathn"
# ---------------------

def disable_teams_protocol_handler():
    """
    Edits Chrome's Preferences file BEFORE launch to permanently block
    the 'Open Microsoft Teams desktop?' OS-level dialog.
    """
    prefs_path = "./chrome_data/Default/Preferences"
    os.makedirs("./chrome_data/Default", exist_ok=True)

    # Load existing prefs if they exist
    if os.path.exists(prefs_path):
        with open(prefs_path, 'r', encoding='utf-8') as f:
            try:
                prefs = json.load(f)
            except Exception:
                prefs = {}
    else:
        prefs = {}

    # Tell Chrome: NEVER prompt for msteams:// or ms-teams:// — just ignore them
    if "protocol_handler" not in prefs:
        prefs["protocol_handler"] = {}
    if "excluded_schemes" not in prefs["protocol_handler"]:
        prefs["protocol_handler"]["excluded_schemes"] = {}

    prefs["protocol_handler"]["excluded_schemes"]["msteams"] = True
    prefs["protocol_handler"]["excluded_schemes"]["ms-teams"] = True

    with open(prefs_path, 'w', encoding='utf-8') as f:
        json.dump(prefs, f)

    print("✅ Chrome preferences patched — Teams desktop dialog is disabled.")


def main():
    print("======================================================")
    print(f"Starting WhatsApp monitor for group: {GROUP_NAME}")
    print("You can leave this running for hours while you sleep.")
    print("IMPORTANT: Ensure your PC is set to NEVER sleep/hibernate!")
    print("======================================================\n")

    # --- PATCH CHROME PREFS BEFORE LAUNCHING ---
    disable_teams_protocol_handler()

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./chrome_data",
            headless=False,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-notifications",
                "--start-maximized",
                "--disable-features=ExternalProtocolDialog,ProtocolHandler",
                "--disable-external-intent-requests",
                "--no-default-browser-check",
                "--no-service-autorun",
            ],
            no_viewport=True
        )

        page = browser.new_page()
        page.goto("https://web.whatsapp.com/")
        print("\nWaiting for WhatsApp Web to load...")
        print("Note: If you see a QR code, please scan it with your phone now.")

        try:
            page.wait_for_selector('div[id="pane-side"]', timeout=300000)
            print("\n✅ Logged into WhatsApp Web successfully!")
        except Exception:
            print("\n❌ Error: Timed out waiting to log into WhatsApp.")
            return

        print(f"\nAttempting to find group '{GROUP_NAME}'...")

        try:
            group_element = page.locator(f'span[title="{GROUP_NAME}"]').first
            group_element.wait_for(state="visible", timeout=3000)
            group_element.click()
            print(f"Opened chat for '{GROUP_NAME}'.")
        except Exception:
            print(f"\n⚠️ Could not automatically click the group.")
            print(f"👉 PLEASE CLICK ON THE GROUP '{GROUP_NAME}' MANUALLY IN THE BROWSER NOW.")
            try:
                header_title = page.locator(f'header span[title="{GROUP_NAME}"]')
                header_title.wait_for(state="visible", timeout=300000)
                print(f"✅ Great! You opened '{GROUP_NAME}'.")
            except Exception:
                print(f"❌ Timed out waiting for you to open the group.")
                return

        print("\nChecking chat history for the most recent link to test...")
        time.sleep(3)

        teams_link = None
        messages = page.query_selector_all('div.message-in, div.message-out')

        print("\n--- DEBUG: SCANNING LAST 5 MESSAGES ---")
        recent_msgs = list(reversed(messages))[:5]

        for i, msg in enumerate(recent_msgs):
            try:
                text = msg.inner_text()
                print(f"Message {i+1}: {repr(text[:50])}... (length: {len(text)})")
                match = re.search(r'(https://teams\.(?:microsoft|live)\.com/(?:l/meetup-join|meet)/[^\s"\'\\]+)', text)
                if match:
                    teams_link = match.group(1)
                    print("\n" + "="*40)
                    print(f"🚨 FOUND RECENT TEAMS LINK TO TEST! 🚨\n{teams_link}")
                    print("="*40 + "\n")
                    break
            except Exception:
                pass
        print("---------------------------------------\n")

        if not teams_link:
            print("No Teams links found in recent messages. Monitoring for new ones...")

            loop_count = 0
            while not teams_link:
                try:
                    messages = page.query_selector_all('div.message-in, div.message-out')
                    for msg in list(reversed(messages))[:3]:
                        text = msg.inner_text()
                        match = re.search(r'(https://teams\.(?:microsoft|live)\.com/(?:l/meetup-join|meet)/[^\s"\'\\]+)', text)
                        if match:
                            teams_link = match.group(1)
                            print("\n" + "="*40)
                            print(f"🚨 FOUND NEW TEAMS LINK! 🚨\n{teams_link}")
                            print("="*40 + "\n")
                            break
                except Exception:
                    pass

                if teams_link:
                    break

                time.sleep(10)
                loop_count += 1
                if (loop_count * 10) % 600 == 0:
                    minutes_waiting = (loop_count * 10) // 60
                    print(f"Still waiting... {minutes_waiting} minutes elapsed.")

        if teams_link:
            join_teams_meeting(browser, teams_link)

        print("\nAll done! Keeping the browser open so you stay in the meeting.")
        try:
            while True:
                time.sleep(100)
        except KeyboardInterrupt:
            print("Exiting...")


def join_teams_meeting(browser, link):
    print("\nNavigating to Microsoft Teams...")

    teams_page = browser.new_page()

    # Auto-dismiss any dialog that still slips through
    teams_page.on("dialog", lambda dialog: dialog.dismiss())

    # Block any msteams:// protocol redirects at the network level
    def block_teams_protocol(route, request):
        if request.url.startswith("msteams://") or request.url.startswith("ms-teams://"):
            print("🚫 Blocked protocol redirect to Teams desktop app.")
            route.abort()
        else:
            route.continue_()

    teams_page.route("**/*", block_teams_protocol)

    teams_page.goto(link)

    print("Waiting 2 seconds for page to load...")
    time.sleep(2)

    # 1. Click "Continue on this browser"
    print("Looking for 'Continue on this browser' button...")
    try:
        button = teams_page.locator(
            'button[data-tid="joinOnWeb"], a[data-tid="joinOnWeb"], [id="join-web-button"]'
        ).first
        button.wait_for(state="visible", timeout=15000)
        button.click()
        print("✅ Clicked 'Continue on this browser'.")
    except Exception as e:
        print(f"⚠️ Could not find the 'Continue on browser' button: {e}")

    print("Waiting for the meeting lobby to load...")

    # 2. Enter Name
    try:
        input_field = teams_page.locator(
            'input[id="username"], input[id="preJoinNameInput"], input[placeholder*="name"], input[placeholder*="nom"]'
        ).first
        input_field.wait_for(state="visible", timeout=45000)

        input_field.fill("")
        time.sleep(1)
        input_field.fill(YOUR_NAME)
        print(f"✅ Typed in name: {YOUR_NAME}")
        time.sleep(2)

        # 3. Click Join Now
        join_btn = teams_page.locator(
            'button[data-tid="prejoin-join-button"], button[id="prejoin-join-button"], button:has-text("Join now"), button:has-text("Rejoindre maintenant")'
        ).first
        join_btn.click()
        print("✅ Clicked 'Join Now'!")
        print(f"\n🎉 SUCCESSFULLY JOINED THE MEETING AS '{YOUR_NAME}'!")

    except Exception as e:
        print(f"❌ Issue interacting with Teams Lobby page: {e}")


if __name__ == "__main__":
    main()