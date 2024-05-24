from typing import List
import datetime as dt

import requests

from config import config
from models import SteamProfile, SteamFriendItem, GameplayItem


def fetch_player_info(player_ids:str, steam_key:str=None) -> List[SteamProfile]:
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

def fetch_player_friend_list(player_id:str, steam_key:str=None)->List[SteamFriendItem]:
    """
    Fetches the friend list for a given player id.
    :param steam_key: the key to access the Steam API
    :type steam_key: str
    :param player_id: player id in steam
    "type player_ids: str
    """
    steam_key = steam_key or config.steam_key
    friends_url = (
        f"http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={steam_key}&steamid={player_id}&relationship=friend"
    )
    r = requests.get(friends_url)
    friend_list = r.json()["friendslist"]["friends"]
    result = []
    for friend in friend_list:
        result.append(SteamFriendItem(
            steamid=friend.get("steamid"),
            friend_since=dt.datetime.fromtimestamp(friend.get("friend_since"))
        ))
    return result

def fetch_player_gameplay_list(player_id:str, steam_key:str=None)->List[GameplayItem]:
    """
    Fetches the gameplay list for a given player id.
    :param steam_key: the key to access the Steam API
    :type steam_key: str
    :param player_id: player id in steam
    "type player_ids: str
    """
    steam_key = steam_key or config.steam_key
    gameplay_url = (
        f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={steam_key}&steamid={player_id}&format=json"
    )
    r = requests.get(gameplay_url)
    gameplay_list = r.json()["response"]["games"]
    result = []
    for gameplay in gameplay_list:
        result.append(GameplayItem(
            appid=gameplay.get("appid"),
            last_time_played=dt.datetime.fromtimestamp(gameplay.get("rtime_last_played")),
            playtime=gameplay.get("playtime_forever"))
        )
    return result
