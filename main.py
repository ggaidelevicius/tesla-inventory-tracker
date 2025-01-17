import psycopg
from psycopg import sql
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from time import sleep
from datetime import datetime
import re

SERVICE = Service()
STATES = [
    {"name": "NSW", "previous_stock": 0},
    {"name": "VIC", "previous_stock": 0},
    {"name": "QLD", "previous_stock": 0},
    {"name": "SA", "previous_stock": 0},
    {"name": "WA", "previous_stock": 0},
    {"name": "TAS", "previous_stock": 0},
    {"name": "NT", "previous_stock": 0},
    {"name": "ACT", "previous_stock": 0},
]

def get_connection():
    return psycopg.connect(
        dbname="postgres",
        user="postgres",
        password="postgres",
        host="localhost",
        port=5432,
    )


# Create the main 'cars' table (using native Postgres types)
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cars (
                id TEXT PRIMARY KEY,
                first_seen_time TIMESTAMP,
                available_in_nsw BOOLEAN,
                available_in_vic BOOLEAN,
                available_in_qld BOOLEAN,
                available_in_sa BOOLEAN,
                available_in_wa BOOLEAN,
                available_in_tas BOOLEAN,
                available_in_nt BOOLEAN,
                available_in_act BOOLEAN,
                matches_preferences BOOLEAN
            )
            """
        )

# Create each state's inventory table and fetch the most recent stock
for state in STATES:
    with get_connection() as conn:
        with conn.cursor() as cur:
            table_name = f"tesla_inventory_{state['name'].lower()}"
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP,
                        stock INTEGER
                    )
                    """
                ).format(table_name=sql.Identifier(table_name))
            )

            cur.execute(
                sql.SQL(
                    """
                    SELECT stock 
                    FROM {table_name}
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ).format(table_name=sql.Identifier(table_name))
            )
            result = cur.fetchone()
            if result:
                state["previous_stock"] = result[0]

while True:
    ALL_STOCK_UNCHANGED = True
    current_hour = datetime.now().hour
    # Simple AM/PM representation
    if current_hour == 0:
        label = "12AM"
    elif current_hour < 12:
        label = f"{current_hour}AM"
    elif current_hour == 12:
        label = "12PM"
    else:
        label = f"{current_hour % 12}PM"
    print(f"==================== {label} ====================")

    for state in STATES:
        url = f"https://www.tesla.com/en_AU/inventory/new/m3?TRIM=LRAWD&arrangeby=relevance&zip=6154&range=0&RegistrationProvince={state['name']}"
        driver = webdriver.Chrome(service=SERVICE)
        driver.get(url)
        sleep(5)

        confirm_button = driver.find_element(By.XPATH, "//button[text()='Confirm']")
        confirm_button.click()
        sleep(5)

        articles = driver.find_elements(By.CSS_SELECTOR, "article.result.card")
        current_stock = len(articles)
        if state["previous_stock"] != current_stock:
            print(
                f"STOCK CHANGE IN {state['name']}: {state['previous_stock']} -> {current_stock}"
            )
            ALL_STOCK_UNCHANGED = False
        state["previous_stock"] = current_stock

        with get_connection() as conn:
            with conn.cursor() as cur:
                for article in articles:
                    data_id = article.get_attribute("data-id")
                    article_html = article.get_attribute("innerHTML")

                    # Check user preferences
                    matches_preferences = (
                        bool(re.search(r"Pearl White Paint", article_html))
                        and bool(re.search(r"Photon Wheels", article_html))
                        and bool(re.search(r"Black Premium Interior", article_html))
                    )

                    # Check if car already exists
                    cur.execute("SELECT 1 FROM cars WHERE id = %s", (data_id,))
                    exists = cur.fetchone() is not None

                    # If not in DB, insert new record
                    if not exists:
                        cur.execute(
                            """
                            INSERT INTO cars (
                                id,
                                first_seen_time,
                                available_in_nsw,
                                available_in_vic,
                                available_in_qld,
                                available_in_sa,
                                available_in_wa,
                                available_in_tas,
                                available_in_nt,
                                available_in_act,
                                matches_preferences
                            )
                            VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            """,
                            (
                                data_id,
                                datetime.now(),
                                state["name"] == "NSW",
                                state["name"] == "VIC",
                                state["name"] == "QLD",
                                state["name"] == "SA",
                                state["name"] == "WA",
                                state["name"] == "TAS",
                                state["name"] == "NT",
                                state["name"] == "ACT",
                                matches_preferences,
                            ),
                        )
                    else:
                        # Update existing record for the current state
                        cur.execute(
                            sql.SQL(
                                """
                                UPDATE cars
                                SET {} = %s
                                WHERE id = %s
                                """
                            ).format(sql.Identifier(f"available_in_{state['name'].lower()}")),
                            (True, data_id),
                        )

                    # Insert stock level into the state's inventory table
                table_name = f"tesla_inventory_{state['name'].lower()}"
                cur.execute(
                    sql.SQL(
                        """
                        INSERT INTO {table_name} (timestamp, stock)
                        VALUES (%s, %s)
                        """
                    ).format(table_name=sql.Identifier(table_name)),
                    (datetime.now(), current_stock),
                )

        driver.quit()

    if ALL_STOCK_UNCHANGED:
        print("stock unchanged")

    print("\n")
    sleep(3600)
