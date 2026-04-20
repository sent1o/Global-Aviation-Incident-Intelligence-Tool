import json
import requests
import asyncio
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import random
import os


def main():
    url = "https://aviation-safety.net"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    }
    year = 1919
    filename = "avia_crashes.json"
    all_data = []

    if os.path.exists(filename):
        print(f"📌 Знайшов готовий файл {filename}. Пропускаю парсинг сайту...")
        with open(filename, "r", encoding="utf-8") as f:
            all_data = json.load(f)
    else:
        print("🔍 Файлу не знайдено. Починаю повний збір даних з Aviation Safety...")
        while year < 2027:
            print(f"--- Processing YEAR: {year} ---")
            first_page = f"/database/year/{year}/1"
            page_of_year = f"{url}{first_page}"
            response = requests.get(page_of_year, headers=headers)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")
                links = find_crashes(soup, url)
                paginator = soup.find("div", class_="pagenumbers")
                if paginator:
                    pages = paginator.find_all("a")
                    links += change_page(pages, url, headers)

                print(f"Total crashes found for {year}: {len(links)}")

                year += 1

            for link in links:
                data = get_data(link, headers)

                if data:
                    all_data.append(data)
                    writer(all_data)

                time.sleep(random.uniform(0.5, 1.5))

    add_photo(all_data)
    print("All photos founded. Let`s write it!")
    writer(all_data)
    print("File is created. Job done!!!")


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


def writer(dict):
    with open("avia_crashes.json", "w", encoding="utf-8") as f:
        json.dump(dict, f, ensure_ascii=False, indent=4)


def find_crashes(s, url):
    crash_links = []
    crashes = s.find_all("td", string="w/o")

    for crash in crashes:
        try:
            parent = crash.find_parent()
            href = parent.find("span").find("a").get("href")
            link = f"{url}{href}"
            crash_links.append(link)

        except AttributeError:
            continue

    return crash_links


def change_page(pages, url, headers):
    additional_links = []
    seen_pages = set()

    for page in pages:

        next_page = page.get("href")
        if next_page in seen_pages:
            continue

        seen_pages.add(next_page)
        link_next = f"{url}{next_page}"
        try:
            load_page = requests.get(link_next, headers=headers)
            s = BeautifulSoup(load_page.text, "lxml")
            additional_links += find_crashes(s, url)
        except Exception as e:
            print(f"Error paging {link_next}: {e}")

    return additional_links


def get_data(link, headers):
    try:
        response = requests.get(link, headers=headers)
        soup = BeautifulSoup(response.text, "lxml")
    except:
        print(f"Failed to fetch {link}")
        return None

    def safe_find(label):
        tag = soup.find("td", string=re.compile(rf"^{label}", re.I))
        if tag and tag.find_next_sibling("td"):
            result = tag.find_next_sibling("td").text.strip()
            return result if result else "N/A"
        return "N/A"

    # Safe names
    location = "N/A"
    find_airport_arr = "N/A"
    fatalities = "N/A"
    occupants = "N/A"
    survivors = "N/A"
    flight_number = "N/A"
    aircraft_age_years = "N/A"
    country = "N/A"

    # if "Military" in safe_find("Nature"):
    #     return None

    # All types of victims
    try:
        all_fatalities_str = safe_find("Fatalities")  # Наприклад "12 / 15"
        if "/" in all_fatalities_str:
            parts = all_fatalities_str.split("/")
            fatalities = re.sub(r"\D", "", parts[0])
            occupants = re.sub(r"\D", "", parts[1])
            if fatalities and occupants:
                survivors = int(occupants) - int(fatalities)

    except Exception:
        pass

    # Age of plane
    date = safe_find("Date")
    year_mnf = safe_find("Year of manufacture")
    year_end = re.search(r"(\d{4})", str(date))
    if year_end and year_mnf.isdigit():
        try:
            aircraft_age_years = int(year_end.group()) - int(year_mnf)
        except:
            pass

    # # Trying get flight number
    try:
        narrative = soup.find("span", lang="en-US")
        if narrative:
            try:
                summary = narrative.text
                match = re.search(r"Flight\s+(\w+)", summary, re.IGNORECASE)

                if match:
                    probably = match.group(1)
                    flight_number = re.sub(r"\D", "", probably)

                    if not flight_number.isdigit():
                        flight_number = "N/A"
            except:
                pass
        else:
            summary = "N/A"
    except:
        summary = "N/A"

    # Find country
    location_string = safe_find("Location")
    if location_string != "N/A":
        if "-" in location_string:
            location_parts = location_string.split("-")
            location = "-".join(location_parts[:-1]).strip()
            temp_country = location_parts[-1].strip()
            country = re.sub(r"^[^a-zA-Z0-9]+", "", temp_country).strip()
        else:
            location = location_string
            country = location_string

    # Пошук міст та аеропортів і їх розділення
    find_airport_dep = safe_find("Departure airport")
    if find_airport_dep == "N/A":
        dep_airport = "N/A"
        dep_city = "N/A"
    try:
        split_departure = find_airport_dep.split("(")
        dep_airport_raw = split_departure[-1][:-1]
        dep_airport = dep_airport_raw.split("/")[0]
        if len(dep_airport) > 4:
            dep_airport = "N/A"
        dep_city = split_departure[0].strip()
    except:
        dep_airport = find_airport_dep
        dep_city = "N/A"

    airport_arr_cont = soup.find(
        "nobr", string=re.compile(rf"^Destination airport", re.I)
    )
    if airport_arr_cont:
        parent = airport_arr_cont.find_parent("td")
        find_airport_arr = parent.find_next_sibling("td").text.strip()

    try:
        split_arrival = find_airport_arr.split("(")
        arr_airport_raw = split_arrival[-1][:-1]
        arr_airport = arr_airport_raw.split("/")[0]
        if len(arr_airport) > 4:
            arr_airport = "N/A"
        arr_city = split_arrival[0].strip()
    except:
        arr_airport = find_airport_arr
        arr_city = "N/A"

    # Searching media links
    cont_media = soup.find(
        "div", class_="captionhr", string=re.compile(rf"^Media", re.I)
    )
    media_links = []
    if cont_media:
        for sibling in cont_media.find_next_siblings():

            if sibling.name == "div" and sibling.get("class") == ["captionhr"]:
                break

            if sibling.name == "iframe":
                media_links.append(sibling.get("src"))

            elif sibling.name == "div":
                iframe = sibling.find("iframe")
                if iframe:
                    media_links.append(iframe.get("src"))

        if not media_links:
            media_links = "N/A"
    else:
        media_links = "N/A"

    res = {
        "msn": safe_find("MSN"),
        "date": date,
        "latitude": "N/A",
        "longitude": "N/A",
        "flight_number": flight_number,
        "registration": safe_find("Registration"),
        "airline_name": safe_find("Owner/operator"),
        "model": safe_find("Type"),
        "location_description": location,
        "departure_airport": dep_airport,
        "arrival_airport": arr_airport,
        "departure_city": dep_city,
        "arrival_sity": arr_city,
        "fatalities": fatalities,
        "survivors": survivors,
        "occupants": occupants,
        "ground_fatalities": safe_find("Other fatalities"),
        "phase": safe_find("Phase"),
        "cause": safe_find("Category"),
        "cause_category": "N/A",
        "flight_type": safe_find("Nature"),
        "country": country,
        "aircraft_age_years": aircraft_age_years,
        "video_urls": media_links,
        "summary": summary,
    }

    # Геолокація (теж з перевіркою)
    map_tag = soup.find(
        lambda tag: tag.name == "iframe"
        and tag.has_attr("src")
        and "kml_map" in tag["src"]
    )
    if map_tag:
        try:
            # src="...&ll=36.72,-4.42&z=..."
            coords_part = map_tag["src"].split("ll=")[-1].split("&")[0]
            if "," in coords_part:
                lat, lon = coords_part.split(",")
                res["latitude"] = lat
                res["longitude"] = lon
        except:
            pass

    return res


if __name__ == "__main__":
    main()
