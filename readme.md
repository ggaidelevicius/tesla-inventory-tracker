# Tesla inventory tracker

This project scrapes Tesla's new car listings from Tesla's inventory API and updates a PostgreSQL database to reflect new or removed listings. Some pieces of relevant car metadata such as type, colour, wheels, interior, and price are also captured.

## Requirements
- **Python 3.8+**
- **Docker**

## Setup
1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Create a Docker container for PostgreSQL**
   ```bash
   docker-compose up -d
   ```
3. **Run the script**
   ```bash
   python main.py
   ```
