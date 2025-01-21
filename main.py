import signal
import sys
from scraper import scrape_website_data
from models import db, Car, Location, CarMetadata, CarLocation
from peewee import PostgresqlDatabase


def signal_handler(db: PostgresqlDatabase, _sig, _frame):
    print("Exiting and closing database connection")
    if not db.is_closed():
        db.close()
    sys.exit(0)


if __name__ == "__main__":
    db.connect()
    db.create_tables([Car, Location, CarMetadata, CarLocation])
    db.close()
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(db, sig, frame))
    try:
        while True:
            scrape_website_data(db)
    except KeyboardInterrupt:
        signal_handler(db, None, None)
