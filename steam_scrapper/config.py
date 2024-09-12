import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class SteamApiConfig:
    """
    Class that contains all the required configurations for the Steam API connector.
    """

    steam_api_url: str
    steam_store_url: str
    steam_key: str
    dry_run: bool
    mongodb_url: Optional[str]

    def __init__(self, steam_key:str=None, player_id:str=None, mongodb_url:str=None):
        self.steam_api_url = "https://api.steampowered.com"
        self.steam_store_url = "http://store.steampowered.com"
        self.steam_key = steam_key or os.getenv("STEAM_KEY")
        self.mongodb_url = mongodb_url or os.getenv("MONGO_DB_URL")
        self.dry_run = False


config = SteamApiConfig()
