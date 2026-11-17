from price_tracker.scrapers.base import BaseScraper
from price_tracker.scrapers.cosibella import CosibellaScraper
from price_tracker.scrapers.oliveyoung import OliveYoungScraper
from price_tracker.scrapers.skinseoul import SkinSeoulScraper

SCRAPERS: dict[str, type[BaseScraper]] = {
    "cosibella": CosibellaScraper,
    "skinseoul": SkinSeoulScraper,
    "oliveyoung": OliveYoungScraper,
}
