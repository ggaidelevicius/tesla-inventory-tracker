import psycopg
from psycopg import sql
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from time import sleep
from datetime import datetime

SERVICE = Service()


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


def create_tables(db: Database) -> None:
    # Create the main 'cars' table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS cars (
            id TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP DEFAULT NULL
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
    for state in ["ACT", "NSW", "NT", "QLD", "SA", "TAS", "VIC", "WA"]:
        url = f"https://www.tesla.com/en_AU/inventory/new/m3?TRIM=LRAWD&arrangeby=relevance&zip=6154&range=0&RegistrationProvince={state}"
        driver = webdriver.Chrome(service=SERVICE)
        driver.get(url)
        sleep(5)

        confirm_button = driver.find_element(By.XPATH, "//button[text()='Confirm']")
        confirm_button.click()
        sleep(5)

        articles = driver.find_elements(By.CSS_SELECTOR, "article.result.card")
        for article in articles:
            car_id = article.get_attribute("data-id")
            insert_car(db, car_id)
            insert_car_location(db, car_id, state)

        driver.quit()
    sleep(3600)


if __name__ == "__main__":
    db = Database(
        dbname="postgres",
        user="postgres",
        password="postgres",
        host="localhost",
        port=5432,
    )
    create_tables(db)
    seed_tables(db)
    while True:
        scrape_website_data(db)
