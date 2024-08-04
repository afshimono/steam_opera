from typing import Optional,List
from dataclasses import dataclass
import datetime as dt


@dataclass
class SteamProfile:
    steamid: str
    persona_name: str
    profile_url: str
    avatar: str
    avatar_medium: str
    avatar_full: str
    last_logoff: dt.datetime
    time_created: dt.datetime
    created_at: dt.datetime
    updated_at: dt.datetime
    last_failed_update_attempt: Optional[dt.datetime] = None
    real_name: Optional[str] = None
    loc_country: Optional[str] = None
    loc_state: Optional[str] = None
    missing_in_action: Optional[bool] = False
    killed_in_action: Optional[bool] = False

@dataclass
class SteamFriendItem:
    steamid: str
    friend_since: dt.datetime

@dataclass
class SteamFriendList:
    steamid: str
    friend_list: List[SteamFriendItem]
    created_at: dt.datetime
    updated_at: dt.datetime
    created_year: int
    created_month: int

@dataclass
class GameplayItem:
    appid: str
    playtime: int
    last_time_played: Optional[dt.datetime]=None

@dataclass
class GameplayList:
    steamid: str
    gameplay_list: List[GameplayItem]
    created_at: dt.datetime
    updated_at: dt.datetime
    created_year: int
    created_month: int
    
@dataclass
class SteamGameinfo:
    appid: str
    name: str
    type: str
    min_age: int
    description: str
    developers: List[str]
    publishers:  List[str]
    genres:  List[str]
    categories: List[str]
    about: str
    is_free: bool
    created_at: dt.datetime
    updated_at: dt.datetime
    release_date: Optional[dt.datetime]=None
    metacritic_score: Optional[int]=None
    last_failed_update_attempt: Optional[dt.datetime] = None