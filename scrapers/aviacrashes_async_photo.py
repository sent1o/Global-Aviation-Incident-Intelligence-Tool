import json
import asyncio
from playwright.async_api import async_playwright
import random
import os

FILENAME = "part_test.json"


async def main():
    if not os.path.exists(FILENAME):
        print(f"❌ Файл {FILENAME} не знайдено! Перевір назву.")
        return

    print(f"📌 Підвантажую базу з {FILENAME}...")
    with open(FILENAME, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    await add_photo(all_data)

    print("✅ Робота завершена. Файл повністю оновлено!")


async def is_frozen(page):
    try:
        title = (await page.title()).lower()
        if any(
            x in title
            for x in [
                "cloudflare",
                "too many requests",
                "access denied",
                "just a moment",
            ]
        ):
            return True

        content = (await page.content()).lower()
        if "rate limit exceeded" in content:
            return True

        return False
    except:
        return False


async def wait_out_cloudflare(page):
    print("⏳ Заморозка. Буду рефрешити сторінку автоматично...")
    for i in range(15):
        await asyncio.sleep(20)
        try:
            print(f"🔄 Спроба рефрешу {i+1}/15...")
            await page.reload(timeout=30000)
            await page.wait_for_load_state("domcontentloaded")

            if not await is_frozen(page):
                print("🔥 Розморозилось! Повертаємось до роботи.")
                return True
        except:
            print("⚠️ Не вдалося рефрешнути, спробую ще раз...")

    return False


async def add_photo(items):
    total = len(items)

    # Очищення MSN з усієї бази одразу перед стартом
    for item in items:
        if "msn" in item:
            del item["msn"]

    # Рахуємо ТІЛЬКИ тих, у кого вже є фотки (image_urls - це список)
    items_with_photos = sum(
        1 for item in items if isinstance(item.get("image_urls"), list)
    )

    print(f"🚀 Всього в базі: {total} бортів. (MSN видалено)")
    print(f"📊 Бортів із вже знайденими фото для перепровірки: {items_with_photos}")

    if items_with_photos == 0:
        print("🎉 Немає записів з фото для перевірки! Робити нічого.")
        return

    recovered_count = 0
    new_na_count = 0

    async with async_playwright() as p:
        proxy_settings = {
            "server": "http://209.101.151.61:50100",
            "username": "yra3908",
            "password": "wLk3BwBg5s",
        }

        browser = await p.chromium.launch(
            headless=False, args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            viewport={"width": 1920, "height": 1080},
            proxy=proxy_settings,
        )
        page = await context.new_page()

        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        try:
            await page.goto("https://www.jetphotos.com/", timeout=60000)
            await page.wait_for_load_state("networkidle")
            try:
                await page.locator("#didomi-notice-disagree-button").click(timeout=3000)
            except:
                pass
        except Exception as e:
            print(f"⚠️ Проблема з завантаженням головної: {e}")

        current_index = 0
        requests_made = 0

        for item in items:
            urls = item.get("image_urls")

            # Пропускаємо все, де немає фоток (N/A або порожньо)
            if not isinstance(urls, list):
                continue

            current_index += 1
            reg_number = item.get("registration", "N/A")
            model = item.get("model", "")

            # Підстраховка від крашу: якщо моделі нема, просто робимо пусту стрічку
            check_model = model.lower().split(maxsplit=1)[0] if model else ""

            # Якщо реєстрації або моделі в принципі немає - затираємо старе фото
            if reg_number == "N/A" or not reg_number or not check_model:
                item["image_urls"] = "N/A"
                print(f"🗑️ Затерто (немає інфи для звірки) [{reg_number}]")
                new_na_count += 1
                writer(items)
                continue

            requests_made += 1

            if requests_made % 10 == 0:
                print("☕️ Перерва 15 сек...")
                await asyncio.sleep(15)

            try:
                # Шукаємо ТІЛЬКИ по Registration
                images, status = await searching(page, reg_number, check_model)

                if status == "frozen":
                    print(
                        f"🧊 {reg_number} -> ПРОПУСК (заморозка). Спробую наступного разу."
                    )
                    continue

                if images:
                    item["image_urls"] = images
                    print(
                        f"✅ Підтверджено! ({current_index}/{items_with_photos}) [{reg_number} + {check_model}]"
                    )
                    recovered_count += 1
                else:
                    item["image_urls"] = "N/A"
                    print(
                        f"🗑️ Затерто ліве фото ({current_index}/{items_with_photos}). [{reg_number} не співпав з {check_model}]"
                    )
                    new_na_count += 1

                writer(items)

            except Exception as e:
                print(f"❌ Error {reg_number}: {e}")
                await asyncio.sleep(5)
                continue

    print(f"\n✅ Перепрогін існуючих фото по реєстрації завершено!")
    print(f"📈 Залишено правильних фоток: {recovered_count}")
    print(f"📉 Змінено на N/A (видалено помилкових): {new_na_count}")


async def searching(page, search_by, model):
    if await is_frozen(page):
        print("🧊 Реальний бан. Чекаю...")
        if not await wait_out_cloudflare(page):
            return None, "frozen"

        await page.reload()
        await page.wait_for_load_state("networkidle")
        if "jetphotos.com" not in page.url:
            await page.goto("https://www.jetphotos.com/")

    input_bar = page.locator("#quicksearch")

    try:
        await input_bar.wait_for(state="visible", timeout=10000)
    except:
        if await is_frozen(page):
            return None, "frozen"
        await page.goto("https://www.jetphotos.com/")
        try:
            await input_bar.wait_for(state="visible", timeout=10000)
        except:
            return None, "ok"

    try:
        await input_bar.click()
        await page.locator("ul#ui-id-1 a:has-text('Advanced search')").click(
            timeout=2000
        )

        filter_loc = page.locator(
            "div.col-6_sm-12",
            has=page.locator("label.form__label", has_text="Keywords"),
        )
        dropdown = filter_loc.locator("#search_advanced_keywords_chosen")
        await dropdown.locator("a.chosen-single").click()
        await asyncio.sleep(0.5)  # Чекаємо поки випаде список
        await dropdown.locator(
            ".chosen-drop ul.chosen-results li", has_text="All fields"
        ).click()

        await asyncio.sleep(1)  # Твоя пауза

        # 2. Знову відкриваємо меню і клікаємо "Registration"
        await dropdown.locator("a.chosen-single").click()
        await asyncio.sleep(0.5)
        await dropdown.locator(
            ".chosen-drop ul.chosen-results li", has_text="Registration"
        ).click()

        # Далі вводимо текст
        await filter_loc.get_by_placeholder("Keyword").fill(search_by)
        await asyncio.sleep(1)
        async with page.expect_navigation():
            await page.get_by_placeholder("Keyword").press("Enter")

    except Exception as e:
        print(f"Error: {e}")
        return None, "ok"

    # РОЗУМНЕ ОЧІКУВАННЯ (замість жорсткого сліпу)
    # Чекаємо до 20 секунд поки не з'явиться або картинка, або текст "No results"
    try:
        await page.wait_for_selector(
            ".result__photoLink, .result__noResults, h1:has-text('No results')",
            timeout=20000,
        )
    except:
        # Якщо за 20 секунд нічого не підгрузилось
        if await is_frozen(page):
            return None, "frozen"
        pass

    if await is_frozen(page):
        print("🧊 Бан після запиту! Чекаю...")
        if not await wait_out_cloudflare(page):
            return None, "frozen"
        print("🔥 Розморозилось! Дивимось результат...")

    try:
        await page.wait_for_load_state("domcontentloaded")

        if (
            await page.locator("h1", has_text="No results").count() > 0
            or await page.locator(".result__noResults").count() > 0
        ):
            return None, "ok"

        if model:
            found_photos = []  # Сюди будемо збирати до 4 фоток
            try:
                # 1. Знаходимо всі КАРТОЧКИ результатів (контейнери div.result)
                # які містять потрібну нам модель в блоці Aircraft
                cards = await page.locator(
                    "div.result",
                    has=page.locator(
                        "span.result__infoListText:has-text('Aircraft:')",
                        has_text=model,
                    ),
                ).all()

                # 2. Проходимося по знайдених карточках
                for card in cards:
                    if len(found_photos) >= 4:  # Якщо вже зібрали 4 - гальмуємо
                        break

                    # Витягуємо лінки тільки з поточної карточки
                    big_href = await card.locator(
                        "a.result__photoLink"
                    ).first.get_attribute("href", timeout=2000)
                    alt_src = await card.locator(
                        "img.result__photo"
                    ).first.get_attribute("src", timeout=2000)

                    if big_href and alt_src:
                        big_link = f"https://www.jetphotos.com{big_href}"
                        alt_link = f"https:{alt_src}"

                        # Додаємо пару лінків у наш масив
                        found_photos.append([big_link, alt_link])

                # Якщо щось знайшли - повертаємо список фоток
                if found_photos:
                    return found_photos, "ok"
                else:
                    return None, "ok"

            except Exception as e:
                print(f"⚠️ Помилка збору фоток: {e}")
                pass
        else:
            return None, "ok"  # Якщо моделі нема, просто йдемо далі

    except:
        pass

    return None, "ok"


def writer(data_dict):
    temp_file = FILENAME + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=4)
        os.replace(temp_file, FILENAME)
    except Exception as e:
        print(f"⚠️ Помилка запису файлу: {e}")


if __name__ == "__main__":
    asyncio.run(main())
