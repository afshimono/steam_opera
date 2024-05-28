from typing import List
import datetime as dt

import requests
import backoff

from config import config
from models import SteamProfile, SteamFriendItem, GameplayItem, SteamGameinfo

@backoff.on_exception(backoff.expo,(requests.exceptions.Timeout,
                       requests.exceptions.ConnectionError),max_tries=5)
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
    current_time = dt.datetime.now()
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
                created_at=current_time,
                updated_at=current_time
            )
        )
    return result

@backoff.on_exception(backoff.expo,(requests.exceptions.Timeout,
                       requests.exceptions.ConnectionError),max_tries=5)
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

@backoff.on_exception(backoff.expo,(requests.exceptions.Timeout,
                       requests.exceptions.ConnectionError),max_tries=5)
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

@backoff.on_exception(backoff.expo,(requests.exceptions.Timeout,
                       requests.exceptions.ConnectionError),max_tries=5)
def fetch_game_details(app_id:str, steam_key:str=None)->SteamGameinfo:
    """
    Fetches the game details for a given app id.
    :param steam_key: the key to access the Steam API
    :type steam_key: str
    :param app_id: app id in steam
    "type player_ids: str
    """
    steam_key = steam_key or config.steam_key
    gameinfo_url = (
        f"http://store.steampowered.com/api/appdetails?appids={app_id}"
    )
    r = requests.get(gameinfo_url)
    gameinfo_details = r.json()[str(app_id)]["data"]
    release_date_str = gameinfo_details["release_date"].get("date") if not gameinfo_details["release_date"]["coming_soon"] else None
    if release_date_str:
        try:
            release_date = dt.datetime.strptime(release_date_str,"%d %b, %Y")
        except ValueError:
            try:
                release_date = dt.datetime.strptime(release_date_str,"%b %d, %Y")
            except ValueError:
                try:
                    release_date = dt.datetime.strptime(release_date_str,"%d %b %Y")
                except ValueError:
                    release_date = None
    genre_item = gameinfo_details.get("genres")
    genre_list = [item["description"] for item in genre_item] if genre_item else []
    categories_item = gameinfo_details.get("categories")
    categories_list = [item["description"] for item in categories_item] if categories_item else []
    metacritic_item = gameinfo_details.get("metacritic")
    result = SteamGameinfo(
        appid=gameinfo_details.get("steam_appid"),
        name=gameinfo_details.get("name"),
        min_age=int(gameinfo_details.get("required_age")),
        description=gameinfo_details.get("detailed_description"),
        about=gameinfo_details.get("about_the_game"),
        release_date=release_date,
        is_free=gameinfo_details.get("is_free"),
        type=gameinfo_details.get("type"),
        developers=gameinfo_details.get("developers"),
        publishers=gameinfo_details.get("publishers"),
        metacritic_score=metacritic_item.get("score") if metacritic_item else None,
        genres=genre_list,
        categories=categories_list
    )
    return result