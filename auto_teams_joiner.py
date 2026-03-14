import time
import re
from playwright.sync_api import sync_playwright

GROUP_NAME = "Ali Fathan"
YOUR_NAME = "ali fathn"

teams_pattern = r"https://teams\.(?:microsoft|live)\.com/[^\s]+"

seen_links = set()


def extract_teams_link(text):
    match = re.search(teams_pattern, text)
    if match:
        link = match.group(0)

        # force browser join
        if "webjoin=true" not in link:
            if "?" in link:
                link += "&webjoin=true"
            else:
                link += "?webjoin=true"

        return link
    return None


def join_teams(browser, link):

    print("Opening Teams meeting:", link)

    page = browser.new_page()

    # block desktop protocol
    def block(route, request):
        if request.url.startswith("msteams://"):
            route.abort()
        else:
            route.continue_()

    page.route("**/*", block)

    page.goto(link)

    # click join on browser
    try:
        page.locator("text=Continue on this browser").click(timeout=15000)
    except:
        pass

    # wait for lobby
    name_input = page.locator("input").first
    name_input.wait_for(timeout=30000)

    name_input.fill(YOUR_NAME)

    # disable mic
    try:
        page.locator('[data-tid="toggle-mute"]').click()
    except:
        pass

    # disable camera
    try:
        page.locator('[data-tid="toggle-video"]').click()
    except:
        pass

    # join meeting
    page.locator('button:has-text("Join")').click()

    print("Joined meeting as:", YOUR_NAME)


def monitor_whatsapp(page, browser):

    print("Monitoring WhatsApp group for Teams links...")

    while True:

        messages = page.query_selector_all("div.message-in, div.message-out")

        for msg in reversed(messages[-5:]):
            try:
                text = msg.inner_text()

                link = extract_teams_link(text)

                if link and link not in seen_links:
                    seen_links.add(link)

                    print("Teams link detected:")
                    print(link)

                    join_teams(browser, link)

                    return

            except:
                pass

        time.sleep(10)


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch_persistent_context(
            user_data_dir="./chrome_data",
            headless=False
        )

        page = browser.new_page()

        page.goto("https://web.whatsapp.com")

        print("Scan QR code if needed...")

        page.wait_for_selector("#pane-side", timeout=300000)

        print("WhatsApp loaded")

        try:
            page.locator(f'span[title="{GROUP_NAME}"]').click()
        except:
            print("Open the group manually:", GROUP_NAME)
            page.wait_for_selector(f'header span[title="{GROUP_NAME}"]')

        print("Group opened")

        monitor_whatsapp(page, browser)

        while True:
            time.sleep(100)


if __name__ == "__main__":
    main()
