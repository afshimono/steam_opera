from typing import List

import requests

from config import config
from models import SteamProfile


def fetch_player_info(player_ids, steam_key=None) -> List[SteamProfile]:
    """
    Fetches the player details for the informed player ids.
    :param steam_key: the key to access the Steam API
    :type steam_key: str
    :param player_ids: comma separated steam ids of users
    "type player_ids: str
    """
    steam_key = steam_key or config.steam_key
    player_url = (
        f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={steam_key}&steamids={player_ids}"
    )
    r = requests.get(player_url)
    player_list = r.json()["response"]["players"]
    result = []
    for player in player_list:
        result.append(
            SteamProfile(
                steamid=player.get("steamid"),
                persona_name=player.get("personaname"),
                profile_url=player.get("profileurl"),
                avatar=player.get("avatar"),
                avatar_full=player.get("avatarfull"),
                avatar_medium=player.get("avatarmedium"),
                last_logoff=player.get("lastlogoff"),
                time_created=player.get("timecreated"),
                real_name=player.get("realname"),
                loc_country=player.get("loccountrycode"),
                loc_state=player.get("locstatecode"),
            )
        )
    return result
