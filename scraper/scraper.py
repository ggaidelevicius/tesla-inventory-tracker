import math
import json
import urllib.parse
from datetime import datetime
from time import sleep
from selenium import webdriver
from peewee import PostgresqlDatabase
from models import Car, CarMetadata, Location, CarLocation


def scrape_website_data(db: PostgresqlDatabase) -> None:
    """
    Scrapes Tesla inventory data and updates Car, CarMetadata, Location, and CarLocation tables.
    Marks cars that no longer appear in the listing as removed.
    """
    driver = None
    try:
        db.connect()
        # Track currently active cars in the database
        active_cars = set(car.id for car in Car.select())
        found_cars = set()

        # Prepare query parameters
        query_parameters = {
            "query": {
                "model": "m3",
                "condition": ["new"],
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
            "offset": 0,
            "count": 50,
            "outsideOffset": 0,
            "outsideSearch": False,
        }

        # Create Selenium driver once
        driver = webdriver.Chrome()

        # Fetch the first page of results
        data = fetch_page_data(driver, query_parameters)

        # Determine the total number of pages to scrape
        total_matches = int(data["total_matches_found"])
        total_pages_to_scrape = math.ceil(total_matches / 50)

        # Process the initial page
        process_results(data, found_cars)

        # Fetch subsequent pages
        for _ in range(1, total_pages_to_scrape):
            sleep(5)  # Sleep to avoid rate limiting
            query_parameters["offset"] += 50  # increment offset
            data = fetch_page_data(driver, query_parameters)
            process_results(data, found_cars)

        # Mark missing cars as removed
        removed_cars = active_cars - found_cars
        for car_id in removed_cars:
            car_to_mark_as_removed = Car.select().where(Car.id == car_id).get()
            car_to_mark_as_removed.removed_at = datetime.now()
            car_to_mark_as_removed.save()

        print(f"✅ Scraped data at {datetime.now()}")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        if driver:
            driver.quit()
        db.close()
        sleep(3600)


def fetch_page_data(driver: webdriver.Chrome, query_parameters: dict) -> dict:
    """
    Given a Selenium driver and query parameters dict,
    sends a request to Tesla's inventory API and returns the parsed JSON data.
    """
    encoded_query = urllib.parse.urlencode({"query": json.dumps(query_parameters)})
    url = f"https://www.tesla.com/inventory/api/v4/inventory-results?{encoded_query}"

    driver.get(url)
    page_source = driver.find_element("tag name", "pre").text
    data = json.loads(page_source)
    return data


def process_results(data: dict, found_cars: set) -> None:
    """
    Processes the 'results' from Tesla's inventory data,
    inserting or ignoring database conflicts, and updates found_cars set.
    """
    for entry in data.get("results", []):
        car_id = entry["VIN"]
        car_type = entry["TRIM"][0]
        car_colour = entry["PAINT"][0]
        car_wheels = entry["WHEELS"][0]
        car_interior = entry["INTERIOR"][0]
        car_price = entry["TotalPrice"]
        car_state = entry["StateProvince"]

        # Insert or ignore existing records
        Car.insert(id=car_id).on_conflict_ignore().execute()
        CarMetadata.insert(
            car=car_id,
            type=car_type,
            colour=car_colour,
            wheels=car_wheels,
            interior=car_interior,
            price=car_price,
        ).on_conflict_ignore().execute()

        Location.insert(name=car_state).on_conflict_ignore().execute()
        CarLocation.insert(
            car=car_id,
            location=Location.select().where(Location.name == car_state).get(),
        ).on_conflict_ignore().execute()

        found_cars.add(car_id)
