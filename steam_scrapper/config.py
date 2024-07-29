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
    player_id: str
    mongodb_url: Optional[str]
    sleep_time_in_ms: Optional[int]

    def __init__(self, steam_key:str=None, player_id:str=None, mongodb_url:str=None, sleep_time_in_ms:int=None):
        self.steam_api_url = "https://api.steampowered.com"
        self.steam_api_url = "http://store.steampowered.com"
        self.steam_key = steam_key or os.getenv("STEAM_KEY")
        self.player_id = player_id or os.getenv("PLAYER_ID")
        self.mongodb_url = mongodb_url or os.getenv("MONGO_DB_URL")
        self.sleep_time_in_ms = sleep_time_in_ms or os.getenv("SLEEP_TIME_IN_MS")


config = SteamApiConfig()
