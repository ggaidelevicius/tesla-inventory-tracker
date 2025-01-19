from database import Database


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
            interior car_interior NOT NULL,
            price INTEGER NOT NULL
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
    car_price: int
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
