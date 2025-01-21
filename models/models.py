from peewee import (
    Model,
    CharField,
    DateTimeField,
    IntegerField,
    ForeignKeyField,
    PostgresqlDatabase,
)
from datetime import datetime

db = PostgresqlDatabase(
    "postgres",
    user="postgres",
    password="postgres",
    host="localhost",
    port=5432,
)


class BaseModel(Model):
    class Meta:
        database = db


class Car(BaseModel):
    id = CharField(primary_key=True)
    added_at = DateTimeField(default=datetime.now)
    removed_at = DateTimeField(null=True)


class Location(BaseModel):
    name = CharField(unique=True)


class CarMetadata(BaseModel):
    car = ForeignKeyField(Car, backref="metadata", unique=True)
    type = CharField()
    colour = CharField()
    wheels = CharField()
    interior = CharField()
    price = IntegerField()


class CarLocation(BaseModel):
    car = ForeignKeyField(Car, backref="locations")
    location = ForeignKeyField(Location, backref="cars")

    class Meta:
        primary_key = False  # We don't need a primary key for this table, as the combination of car and location is unique
        indexes = (
            (("car", "location"), True),  # This is a unique index
        )
