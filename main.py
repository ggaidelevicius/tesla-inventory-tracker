# TODO: investigate if can use requests rather than selenium

import psycopg
import signal
import sys
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
from datetime import datetime


class Database:
    def __init__(self, dbname: str, user: str, password: str, host: str, port: int):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.connection = None

    def connect(self):
        if not self.connection or self.connection.closed:
            self.connection = psycopg.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
            )
        return self.connection

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def execute(self, query, params=None):
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()

    def fetch_one(self, query, params=None):
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            conn.commit()
            return row

    def fetch_all(self, query, params=None):
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            conn.commit()
            return rows


def signal_handler(_sig: None, _frame: None) -> None:
    print("Exiting and closing database connection")
    db.close()
    sys.exit(0)


def create_enums(db: Database) -> None:
    # Create the enumerated type for car types
    db.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'car_type') THEN
                CREATE TYPE car_type AS ENUM ('RWD', 'AWD', 'UNKNOWN');
            END IF;
        END
        $$;
        """
    )

    # Create the enumerated type for car colours
    db.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'car_colour') THEN
                CREATE TYPE car_colour AS ENUM ('Pearl White', 'Solid Black', 'Deep Blue Metallic', 'Stealth Grey', 'Quicksilver', 'Ultra Red', 'UNKNOWN');
            END IF;
        END
        $$;
        """
    )

    # Create the enumerated type for car wheels
    db.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'car_wheels') THEN
                CREATE TYPE car_wheels AS ENUM ('18" Photon Wheels', '19" Nova Wheels', 'UNKNOWN');
            END IF;
        END
        $$;
        """
    )

    # Create the enumerated type for car interiors
    db.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'car_interior') THEN
                CREATE TYPE car_interior AS ENUM ('Black', 'White', 'UNKNOWN');
            END IF;
        END
        $$;
        """
    )


def create_tables(db: Database) -> None:
    # Create the cars table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS cars (
            id TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            removed_at TIMESTAMP DEFAULT NULL
        )
        """
    )

    # Create the car metadata table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS car_metadata (
            id SERIAL PRIMARY KEY,
            car_id TEXT UNIQUE REFERENCES cars(id) NOT NULL,
            type car_type NOT NULL,
            colour car_colour NOT NULL,
            wheels car_wheels NOT NULL,
            interior car_interior NOT NULL
        )
        """
    )

    # Create the locations table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        )
        """
    )

    # Create the car_locations junction table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS car_locations (
            car_id TEXT REFERENCES cars(id) NOT NULL,
            location_id INTEGER REFERENCES locations(id) NOT NULL,
            PRIMARY KEY (car_id, location_id)
        )
        """
    )

    # Create a view to compute availability
    db.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_views WHERE viewname = 'car_availability') THEN
                CREATE VIEW car_availability AS
                SELECT
                    c.id AS car_id,
                    l.name AS location,
                    EXISTS (
                        SELECT 1
                        FROM car_locations cl
                        WHERE cl.car_id = c.id AND cl.location_id = l.id
                    ) AS available
                FROM
                    cars c
                CROSS JOIN
                    locations l;
            END IF;
        END
        $$;
        """
    )


def seed_tables(db: Database) -> None:
    # Seed the locations table
    for state in ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]:
        db.execute(
            """
            INSERT INTO locations (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
            """,
            (state,),
        )


def get_location_id(db: Database, location_name: str) -> int:
    location_row = db.fetch_one(
        "SELECT id FROM locations WHERE name = %s", (location_name,)
    )
    if location_row is None:
        raise ValueError(f"Location '{location_name}' not found")
    return location_row[0]


def insert_car(db: Database, car_id: str) -> None:
    db.execute(
        """
        INSERT INTO cars (id)
        VALUES (%s)
        ON CONFLICT (id) DO NOTHING
        """,
        (car_id,),
    )


def insert_car_metadata(
    db: Database,
    car_id: str,
    car_type: str,
    car_colour: str,
    car_wheels: str,
    car_interior: str,
) -> None:
    db.execute(
        """
        INSERT INTO car_metadata (car_id, type, colour, wheels, interior)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (car_id) DO NOTHING
        """,
        (car_id, car_type, car_colour, car_wheels, car_interior),
    )


def insert_car_location(db: Database, car_id: str, location_name: str) -> None:
    location_id = get_location_id(db, location_name)
    db.execute(
        """
        INSERT INTO car_locations (car_id, location_id)
        VALUES (%s, %s)
        ON CONFLICT (car_id, location_id) DO NOTHING
        """,
        (car_id, location_id),
    )


def get_active_cars(db: Database) -> list[str]:
    rows = db.fetch_all("SELECT id FROM cars WHERE removed_at IS NULL")
    car_ids = [row[0] for row in rows]
    return car_ids


def mark_car_as_removed(db: Database, car_id: str) -> None:
    db.execute(
        "UPDATE cars SET removed_at = CURRENT_TIMESTAMP WHERE id = %s", (car_id,)
    )


def determine_car_colour(car_html: str) -> str:
    if re.search(r"Pearl White", car_html):
        return "Pearl White"
    elif re.search(r"Solid Black", car_html):
        return "Solid Black"
    elif re.search(r"Deep Blue Metallic", car_html):
        return "Deep Blue Metallic"
    elif re.search(r"Stealth Grey", car_html):
        return "Stealth Grey"
    elif re.search(r"Quicksilver", car_html):
        return "Quicksilver"
    elif re.search(r"Ultra Red", car_html):
        return "Ultra Red"
    return "UNKNOWN"


def scrape_website_data(db: Database) -> None:
    active_cars = set(get_active_cars(db))
    found_cars = set()
    try:
        for state in ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]:
            url = f"https://www.tesla.com/en_AU/inventory/new/m3?RegistrationProvince={state}"
            driver = webdriver.Chrome()
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

                insert_car(db, car_id)
                insert_car_metadata(
                    db, car_id, car_type, car_colour, car_wheels, car_interior
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


if __name__ == "__main__":
    db = Database(
        dbname="postgres",
        user="postgres",
        password="postgres",
        host="localhost",
        port=5432,
    )
    create_enums(db)
    create_tables(db)
    seed_tables(db)

    # Register the signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    try:
        while True:
            scrape_website_data(db)
    except KeyboardInterrupt:
        signal_handler(None, None)
