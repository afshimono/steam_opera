from typing import Optional
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
    real_name: Optional[str] = None
    loc_country: Optional[str] = None
    loc_state: Optional[str] = None

@dataclass
class SteamFriendItem:
    steamid: str
    friend_since: dt.datetime

@dataclass
class GameplayItem:
    appid: str
    last_time_played: dt.datetime
    playtime: int