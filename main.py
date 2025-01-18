# TODO: investigate if can use requests rather than selenium

import signal
import sys
from database import Database
from models import create_enums, create_tables, seed_tables
from scraper import scrape_website_data


def signal_handler(db: Database, _sig, _frame):
    print("Exiting and closing database connection")
    db.close()
    sys.exit(0)


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

    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(db, sig, frame))
    try:
        while True:
            scrape_website_data(db)
    except KeyboardInterrupt:
        signal_handler(db, None, None)
