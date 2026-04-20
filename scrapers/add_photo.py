import json
import time
import random
from playwright.sync_api import sync_playwright


def main():
    with open("avia_crashes.json", "r") as file:
        all_data = json.load(file)

    add_photo(all_data)
    print(all_data)


def add_photo(items):
    total = len(items)
    count = 1
    print(f"🚀 Починаємо роботу з фото. Всього до обробки: {total} бортів.")
    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False, args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page.goto("https://www.jetphotos.com/")
        page.wait_for_load_state("networkidle")
        try:
            page.click("#didomi-notice-disagree-button")
        except:
            pass

        for item in items:
            if item.get("image_urls") and item["image_urls"] != "N/A":
                print(f"⏩ {item.get('registration')} вже має фото, скіпаємо.")
                count += 1
                continue

            search_queries = [
                (item["registration"], "Registration"),
                (item["msn"], "Serial No."),
                (item["model"], "Aircraft"),
            ]
            try:
                for query, filter in search_queries:
                    images = searching(page, filter, query)
                    if images:
                        item["image_urls"] = images
                        print(
                            f"Found photo for {count} plane by {filter}. Still {total - count} planes"
                        )
                        break

                if not images:
                    item["image_urls"] = "N/A"
                    print(
                        f"For board number: {count} didn`t founded photo. Still {total - count} planes"
                    )

                if "msn" in item:
                    del item["msn"]

                writer(items)
                count += 1

            except Exception as e:
                print(f"❌ Помилка на борту {item.get('registration')}: {e}")
                time.sleep(5)
                continue


def searching(page, filter_box, search_by):

    if search_by == "N/A":
        return

    input_bar = page.locator("#quicksearch")
    try:
        input_bar.wait_for(state="visible", timeout=5000)
    except:
        print("🔄 Пошук не з'явився, пробую рефреш сторінки...")
        page.reload()
        input_bar.wait_for(state="visible", timeout=5000)

    input_bar.click()
    page.locator("ul#ui-id-1 a:has-text('Advanced search')").click()
    filter = page.locator(
        "div.col-6_sm-12",
        has=page.locator("label.form__label", has_text="Keywords"),
    )
    filter.locator("#search_advanced_keywords_chosen").click()
    filter.locator("ul.chosen-results li", has_text=filter_box).click()
    filter.get_by_placeholder("Keyword").fill(search_by)
    page.get_by_placeholder("Keyword").press("Enter")
    time.sleep(random.uniform(2, 4))
    try:
        page.wait_for_load_state("domcontentloaded")
        if page.locator("h1", has_text="No results").count() > 0:
            return

        big_href = page.locator("a.result__photoLink").first.get_attribute("href")
        alt_cont = page.locator("a.result__photoLink").first
        alt_src = alt_cont.locator("img.result__photo").get_attribute("src")
    except:
        return

    big_link = f"https://www.jetphotos.com{big_href}"
    alt_link = f"https:{alt_src}"

    image_links = [big_link, alt_link]

    return image_links


main()
