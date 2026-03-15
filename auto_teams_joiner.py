import time
import re
from playwright.sync_api import sync_playwright

# ---------------- CONFIG ----------------
print('Welcome to ALiBot , this automation created by Ali Fathan')
GROUP_NAME = input("Enter WhatsApp group name exactly the same please : ")
YOUR_NAME = input("Enter the name you want in the meeting: ")
SCAN_MESSAGES = 100
CHECK_INTERVAL = 10
# ----------------------------------------

teams_pattern = r"https://teams\.(?:microsoft|live)\.com/[^\s]+"

seen_links = set()


def extract_teams_link(text):
    match = re.search(teams_pattern, text)

    if match:
        link = match.group(0)

        if "webjoin=true" not in link:
            if "?" in link:
                link += "&webjoin=true"
            else:
                link += "?webjoin=true"

        return link

    return None


def join_teams(browser, link):

    print("\nOpening Teams meeting:")
    print(link)

    page = browser.new_page()

    def block(route, request):
        if request.url.startswith("msteams://"):
            route.abort()
        else:
            route.continue_()

    page.route("**/*", block)

    page.goto(link)

    try:
        page.locator("text=Continue on this browser").click(timeout=15000)
        print("Clicked browser join.")
    except:
        pass

    try:
        name_input = page.locator("input").first
        name_input.wait_for(timeout=45000)
        name_input.fill(YOUR_NAME)
        print("Typed name.")
    except:
        print("Name input skipped (possibly logged account).")

    try:
        page.locator('[data-tid="toggle-mute"]').click()
        print("Mic disabled.")
    except:
        pass

    try:
        page.locator('[data-tid="toggle-video"]').click()
        print("Camera disabled.")
    except:
        pass

    try:
        page.locator('button:has-text("Join")').first.click()
        print("Joined meeting.")
    except:
        print("Join button not found (maybe lobby).")


def find_latest_teams_link(messages):

    latest_link = None

    for msg in reversed(messages[-SCAN_MESSAGES:]):
        try:
            text = msg.inner_text()
            link = extract_teams_link(text)

            if link:
                latest_link = link
                break

        except:
            pass

    return latest_link


def monitor_whatsapp(page, browser):

    print("\nMonitoring WhatsApp for Teams links...")

    while True:

        try:
            messages = page.query_selector_all(
                "div.message-in, div.message-out"
            )

            link = find_latest_teams_link(messages)

            if link and link not in seen_links:

                seen_links.add(link)

                print("\nTeams link detected:")
                print(link)

                join_teams(browser, link)

                return

        except:
            pass

        time.sleep(CHECK_INTERVAL)


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch_persistent_context(
            user_data_dir="./chrome_data",
            headless=False,
            permissions=["camera", "microphone"],
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--disable-notifications",
                "--start-maximized"
            ],
            no_viewport=True
        )

        page = browser.new_page()

        page.goto("https://web.whatsapp.com")

        print("Waiting for WhatsApp login...")
        page.wait_for_selector("#pane-side", timeout=300000)

        print("WhatsApp loaded.")

        try:
            page.locator(f'span[title="{GROUP_NAME}"]').click()
        except:
            print("Open the group manually:", GROUP_NAME)
            page.wait_for_selector(
                f'header span[title="{GROUP_NAME}"]'
            )

        print("Group opened.")

        monitor_whatsapp(page, browser)

        print("\nScript will stay running while you are in meeting.")

        while True:
            time.sleep(100)


if __name__ == "__main__":
    main()
