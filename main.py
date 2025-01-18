import psycopg
import signal
import sys
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
        if self.connection is None:
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
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)


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
                CREATE TYPE car_type AS ENUM ('RWD', 'AWD');
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
                CREATE TYPE car_colour AS ENUM ('Pearl White', 'Solid Black', 'Deep Blue Metallic', 'Stealth Grey', 'Quicksilver', 'Ultra Red');
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
                CREATE TYPE car_wheels AS ENUM ('18" Photon Wheels', '19" Nova Wheels');
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
                CREATE TYPE car_interior AS ENUM ('Black', 'White');
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
            metadata_id TEXT REFERENCES car_metadata(id) DEFAULT NULL,
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
            car_id TEXT REFERENCES cars(id) NOT NULL,
            type car_type NOT NULL,
            type car_colour NOT NULL,
            type car_wheels NOT NULL,
            type car_interior NOT NULL
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
            locations l
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
    result = db.execute("SELECT id FROM locations WHERE name = %s", (location_name,))
    location_id = result.fetchone()
    if location_id:
        return location_id[0]
    else:
        raise ValueError(f"Location '{location_name}' not found")


def insert_car(db: Database, car_id: str) -> None:
    db.execute(
        """
        INSERT INTO cars (id)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING
        """,
        (car_id,),
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


def scrape_website_data(db: Database) -> None:
    # TODO: handle checking of all car ids and flagging removed cars when not found via scraping
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
                car_id = article.get_attribute("data-id")
                insert_car(db, car_id)
                # insert_car_metadata(db, car_id, type, colour, wheels, interior)
                insert_car_location(db, car_id, state)

            driver.quit()
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
