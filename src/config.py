from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data/raw/ridership_headline.csv"
OUTPUT_DIR = ROOT / "data/processed"
SOURCE_URL = "https://data.gov.my/data-catalogue/ridership_headline"

# Names follow the publisher's service labels; mode groups are analytical choices.
SERVICES = {
    "bus_rkl": ("Rapid Bus KL", "Bus"),
    "bus_rkn": ("Rapid Bus Kuantan", "Bus"),
    "bus_rpn": ("Rapid Bus Penang", "Bus"),
    "rail_lrt_ampang": ("LRT Ampang", "LRT"),
    "rail_mrt_kajang": ("MRT Kajang", "MRT"),
    "rail_lrt_kj": ("LRT Kelana Jaya", "LRT"),
    "rail_monorail": ("KL Monorail", "Monorail"),
    "rail_mrt_pjy": ("MRT Putrajaya", "MRT"),
    "rail_lrt_shah_alam": ("LRT Shah Alam", "LRT"),
    "rail_ets": ("KTMB ETS", "ETS"),
    "rail_intercity": ("KTM Intercity", "Intercity Rail"),
    "rail_komuter_utara": ("KTM Komuter Utara", "KTM Komuter"),
    "rail_tebrau": ("KTM Shuttle Tebrau", "Shuttle Rail"),
    "rail_komuter": ("KTM Komuter", "KTM Komuter"),
}
CORE_SERVICES = ["rail_lrt_ampang", "rail_mrt_kajang", "rail_lrt_kj", "rail_monorail"]
