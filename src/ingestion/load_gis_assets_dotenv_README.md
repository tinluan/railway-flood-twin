# How to use the .env version of the GIS loader

## 1. Save the loader script to:
`src/ingestion/load_gis_assets.py`

## 2. Create a file named `.env` in the project root:
`railway-flood-twin/.env`

## 3. Add this line to `.env`:
`DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres`

## 4. Install python-dotenv if needed:
`pip install python-dotenv`

## 5. Run from the project root:
`python src/ingestion/load_gis_assets_dotenv.py`
