import os
from dataclasses import dataclass


@dataclass
class SteamApiConfig:
    """
    Class that contains all the required configurations for the Steam API connector.
    """

    steam_api_url: str
    steam_store_url: str
    steam_key: str
    player_id: str

    def __init__(self, steam_key=None, player_id=None):
        self.steam_api_url = "https://api.steampowered.com"
        self.steam_api_url = "http://store.steampowered.com"
        self.steam_key = steam_key or os.getenv("STEAM_KEY")
        self.player_id = player_id or os.getenv("PLAYER_ID")


config = SteamApiConfig()
