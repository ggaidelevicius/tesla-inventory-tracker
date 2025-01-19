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
