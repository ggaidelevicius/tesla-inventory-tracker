import sqlite3
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

connection = sqlite3.connect("data.db")
cursor = connection.cursor()
cursor.execute(
    """CREATE TABLE IF NOT EXISTS cars (id TEXT PRIMARY KEY, first_seen_time TEXT, available_in_nsw INTEGER, available_in_vic INTEGER, available_in_qld INTEGER, available_in_sa INTEGER, available_in_wa INTEGER, available_in_tas INTEGER, available_in_nt INTEGER, available_in_act INTEGER, matches_preferences INTEGER)"""
)
connection.commit()
connection.close()

for state in STATES:
    connection = sqlite3.connect("data.db")
    cursor = connection.cursor()
    cursor.execute(
        f"""CREATE TABLE IF NOT EXISTS tesla_inventory_{state["name"].lower()} (id INTEGER PRIMARY KEY, timestamp TEXT, stock INTEGER)"""
    )
    connection.commit()
    cursor.execute(
        f"""SELECT stock FROM tesla_inventory_{state["name"].lower()} ORDER BY id DESC LIMIT 1"""
    )
    result = cursor.fetchone()
    if result:
        state["previous_stock"] = result[0]
    connection.close()

while True:
    ALL_STOCK_UNCHANGED = True
    print(
        f"==================== {datetime.now().hour % 12}PM ===================="
        if datetime.now().hour > 12
        else f"==================== {datetime.now().hour}AM ===================="
    )
    for state in STATES:
        url = f"https://www.tesla.com/en_AU/inventory/new/m3?TRIM=LRAWD&arrangeby=relevance&zip=6154&range=0&RegistrationProvince={state['name']}"
        driver = webdriver.Chrome(service=SERVICE)
        driver.get(url)
        sleep(5)

        confirm_button = driver.find_element(By.XPATH, "//button[text()='Confirm']")
        confirm_button.click()
        sleep(5)

        articles = driver.find_elements(By.CSS_SELECTOR, "article.result.card")
        if state["previous_stock"] != len(articles):
            print(
                f"STOCK CHANGE IN {state['name']}: {state['previous_stock']} -> {len(articles)}"
            )
            ALL_STOCK_UNCHANGED = False
        state["previous_stock"] = len(articles)

        connection = sqlite3.connect("data.db")
        cursor = connection.cursor()

        for article in articles:
            data_id = article.get_attribute("data-id")
            article_html = article.get_attribute("innerHTML")

            matches_preferences = (
                bool(re.search(r"Pearl White Paint", article_html))
                and bool(re.search(r"Photon Wheels", article_html))
                and bool(re.search(r"Black Premium Interior", article_html))
            )

            cursor.execute("SELECT 1 FROM cars WHERE id = ?", (data_id,))
            if cursor.fetchone() is None:
                cursor.execute(
                    "INSERT INTO cars (id, first_seen_time, available_in_nsw, available_in_vic, available_in_qld, available_in_sa, available_in_wa, available_in_tas, available_in_nt, available_in_act, matches_preferences) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        data_id,
                        str(datetime.now()),
                        int(state["name"] == "NSW"),
                        int(state["name"] == "VIC"),
                        int(state["name"] == "QLD"),
                        int(state["name"] == "SA"),
                        int(state["name"] == "WA"),
                        int(state["name"] == "TAS"),
                        int(state["name"] == "NT"),
                        int(state["name"] == "ACT"),
                        int(matches_preferences),
                    ),
                )
            else:
                cursor.execute(
                    f"UPDATE cars SET available_in_{state['name'].lower()} = ? WHERE id = ?",
                    (1, data_id),
                )

        cursor.execute(
            f"""INSERT INTO tesla_inventory_{state["name"].lower()} (timestamp, stock) VALUES (?, ?)""",
            (str(datetime.now()), len(articles)),
        )

        connection.commit()
        connection.close()

        driver.quit()
    if ALL_STOCK_UNCHANGED:
        print("stock unchanged")
    print("\n")
    sleep(3600)
