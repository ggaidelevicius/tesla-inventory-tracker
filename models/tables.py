from database import Database


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
