from database import Database


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
    car_price: int,
) -> None:
    db.execute(
        """
        INSERT INTO car_metadata (car_id, type, colour, wheels, interior, price)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (car_id) DO NOTHING
        """,
        (car_id, car_type, car_colour, car_wheels, car_interior, car_price),
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
