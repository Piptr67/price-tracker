from price_tracker.scrapers.base import BaseScraper
from price_tracker.scrapers.cosibella import CosibellaScraper

SCRAPERS: dict[str, type[BaseScraper]] = {"cosibella": CosibellaScraper}
