import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
from datetime import datetime
from database import Database
from models import (
    insert_car,
    insert_car_metadata,
    insert_car_location,
    get_active_cars,
    mark_car_as_removed,
)
from .helpers import determine_car_colour


def scrape_website_data(db: Database) -> None:
    active_cars = set(get_active_cars(db))
    found_cars = set()
    try:
        driver = webdriver.Chrome()
        for state in ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]:
            url = f"https://www.tesla.com/en_AU/inventory/new/m3?RegistrationProvince={state}"
            driver.get(url)
            sleep(5)

            confirm_button = driver.find_element(By.XPATH, "//button[text()='Confirm']")
            confirm_button.click()
            sleep(5)

            articles = driver.find_elements(By.CSS_SELECTOR, "article.result.card")
            for article in articles:
                article_html = article.get_attribute("innerHTML")
                car_id = article.get_attribute("data-id")
                car_type = "AWD" if re.search(r"All-Wheel", article_html) else "RWD"
                car_colour = determine_car_colour(article_html)
                car_wheels = (
                    '18" Photon Wheels'
                    if re.search(r"Photon Wheels", article_html)
                    else '19" Nova Wheels'
                )
                car_interior = (
                    "Black"
                    if re.search(r"Black Premium Interior", article_html)
                    else "White"
                )
                car_price = int(
                    re.sub(
                        r"\D",
                        "",
                        article.find_element(
                            By.CSS_SELECTOR, "span.result-purchase-price"
                        ).text,
                    )
                )

                insert_car(db, car_id)
                insert_car_metadata(
                    db,
                    car_id,
                    car_type,
                    car_colour,
                    car_wheels,
                    car_interior,
                    car_price,
                )
                insert_car_location(db, car_id, state)
                found_cars.add(car_id)

        driver.quit()
        removed_cars = active_cars - found_cars
        for car_id in removed_cars:
            mark_car_as_removed(db, car_id)

        print(f"✅ Scraped data at {datetime.now()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        sleep(3600)
