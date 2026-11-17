from price_tracker.scrapers.base import BaseScraper
from price_tracker.scrapers.cosibella import CosibellaScraper
from price_tracker.scrapers.oliveyoung import OliveYoungScraper

SCRAPERS: dict[str, type[BaseScraper]] = {
    "cosibella": CosibellaScraper,
    "oliveyoung": OliveYoungScraper,
}
