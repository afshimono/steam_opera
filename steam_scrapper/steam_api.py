from typing import List, Union
import datetime as dt

import requests
import backoff

from config import config
from models import SteamProfile, SteamFriendItem, GameplayItem, SteamGameinfo
from errors import SteamResourceNotAvailable

MAX_RETRIES = 10

@backoff.on_exception(backoff.expo,(
        requests.exceptions.ConnectTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        SteamResourceNotAvailable),max_tries=MAX_RETRIES)
def fetch_player_info(
    player_ids:str, 
    steam_key:str=None,
    current_time:dt.datetime = dt.datetime.now()) -> List[SteamProfile]:
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
    if r.status_code in [429]:
        raise SteamResourceNotAvailable("Status code not acceptable.")
    if r.status_code >= 400:
        return []
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
                created_at=current_time,
                updated_at=current_time
            )
        )
    return result

@backoff.on_exception(backoff.expo,(
        requests.exceptions.ConnectTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        SteamResourceNotAvailable
        ),max_tries=MAX_RETRIES)
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
    if r.status_code in [429]:
        raise SteamResourceNotAvailable("Status code not acceptable.")
    if r.status_code >= 400:
        return []
    friend_list = r.json()["friendslist"]["friends"]
    result = []
    for friend in friend_list:
        result.append(SteamFriendItem(
            steamid=friend.get("steamid"),
            friend_since=dt.datetime.fromtimestamp(friend.get("friend_since"))
        ))
    return result

@backoff.on_exception(backoff.expo,(
        requests.exceptions.ConnectTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        SteamResourceNotAvailable),max_tries=MAX_RETRIES)
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
    if r.status_code in [429]:
        raise SteamResourceNotAvailable("Status code not acceptable.")
    if r.status_code >= 400:
        return []
    gameplay_list = r.json()["response"].get("games")
    if gameplay_list is None:
        return []
    result = []
    for gameplay in gameplay_list:
        last_time_played = gameplay.get("rtime_last_played",0)
        result.append(GameplayItem(
            appid=str(gameplay.get("appid")),
            last_time_played=dt.datetime.fromtimestamp(last_time_played) if last_time_played != 0 else None,
            playtime=gameplay.get("playtime_forever"))
        )
    return result

@backoff.on_exception(backoff.expo,(
        requests.exceptions.ConnectTimeout,
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        SteamResourceNotAvailable),max_tries=MAX_RETRIES)
def fetch_game_details(
    app_id:str, 
    steam_key:str=None,
    current_time:dt.datetime = dt.datetime.now())->Union[SteamGameinfo,None]:
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
    if r.status_code in [429]:
        raise SteamResourceNotAvailable("Status code not acceptable.")
    if r.status_code >= 400:
        return None
    gameinfo_result = r.json()[str(app_id)]
    if not gameinfo_result["success"]:
        return None
    gameinfo_details = gameinfo_result["data"]
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
    else:
        release_date = None
    genre_item = gameinfo_details.get("genres")
    genre_list = [item["description"] for item in genre_item] if genre_item else []
    categories_item = gameinfo_details.get("categories")
    categories_list = [item["description"] for item in categories_item] if categories_item else []
    metacritic_item = gameinfo_details.get("metacritic")
    result = SteamGameinfo(
        appid=str(gameinfo_details.get("steam_appid")),
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
        categories=categories_list,
        created_at=current_time,
        updated_at=current_time
    )
    return result