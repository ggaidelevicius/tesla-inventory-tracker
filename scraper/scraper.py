import math
import json
import urllib.parse
from selenium import webdriver
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


def scrape_website_data(db: Database) -> None:
    active_cars = set(get_active_cars(db))
    found_cars = set()
    offset = 0
    query_parameters = {
        "query": {
            "model": "m3",
            "condition": ["used", "new"],
            "arrangeby": "Price",
            "order": "asc",
            "market": "AU",
            "language": "en",
            "super_region": "asia pacific",
            "lng": 151.21,
            "lat": -33.868,
            "zip": "2000",
            "range": 9999,
        },
        "offset": offset,
        "count": 50,
        "outsideOffset": 0,
        "outsideSearch": False,
    }
    encoded_query = urllib.parse.urlencode({"query": json.dumps(query_parameters)})
    url = f"https://www.tesla.com/inventory/api/v4/inventory-results?{encoded_query}"
    try:
        driver = webdriver.Chrome()
        driver.get(url)
        page_source = driver.find_element("tag name", "pre").text
        data = json.loads(page_source)
        scraped_pages = 1
        total_pages_to_scrape = math.ceil(int(data["total_matches_found"]) / 50)

        for entry in data["results"]:
            car_id = entry["VIN"]
            car_type = entry["TRIM"][0]
            car_colour = entry["PAINT"][0]
            car_wheels = entry["WHEELS"][0]
            car_interior = entry["INTERIOR"][0]
            car_price = entry["TotalPrice"]
            car_state = entry["StateProvince"]
            print(car_id, car_type, car_colour, car_wheels, car_interior, car_price, car_state)
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
            insert_car_location(db, car_id, car_state)
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
