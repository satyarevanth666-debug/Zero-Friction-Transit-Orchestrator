"""Import script for baseline cities, stations, aliases, and geographic nodes."""

from app.db.seed import seed_database

if __name__ == "__main__":
    seed_database()
