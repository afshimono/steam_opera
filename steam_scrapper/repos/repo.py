from typing import List, Optional, Dict, Union

from abc import ABC, abstractmethod

from models import SteamProfile, SteamFriendList, SteamGameinfo, GameplayList, GameplayMonthDeltaList


class Repo(ABC):
    # Friend List
    @abstractmethod
    def get_existing_friend_list_ids(
        self, 
        player_id_list: List[str], 
        created_year: Optional[int]=None, 
        created_month: Optional[int]=None)->List[str]:
        pass

    @abstractmethod
    def get_friend_list_by_id(
        self, 
        player_id: str, 
        created_year: Optional[int]=None, 
        created_month: Optional[int]=None)->List[SteamFriendList]:
        pass

    @abstractmethod
    def save_friend_list(self, player_friend_list: SteamFriendList):
        pass

    # Player Info
    @abstractmethod
    def get_player_info_by_id_list(self, player_id_list: List[str])->List[SteamProfile]:
        pass

    @abstractmethod
    def save_player_info_list(self, player_info_list: List[SteamProfile]):
        pass

    @abstractmethod
    def delete_player_info_list(self, player_id_list: List[str]):
        pass

    # Gameplay Info
    @abstractmethod
    def get_existing_gameplay_info_ids(
        self, 
        player_id_list: List[str], 
        created_year: Optional[int]=None, 
        created_month: Optional[int]=None)->List[str]:
        pass

    @abstractmethod
    def get_gameplay_info_by_id(
        self, 
        player_id: str, 
        created_year: Optional[int]=None, 
        created_month: Optional[int]=None)->List[GameplayList]:
        pass

    @abstractmethod
    def get_gameplay_info_by_id_list(
        self,
        player_id_list: List[str] = None,
        created_year: Optional[int] = None,
        created_month: Optional[int] = None,
        sort_query: Optional[bool] = False,
    ) -> List[GameplayList]:
        pass

    @abstractmethod
    def save_gameplay_info(self, gameplay_info: GameplayList):
        pass

    @abstractmethod
    def delete_gameplay_info(
        self, player_id: Optional[str] = None, created_year: Optional[int] = None, created_month: Optional[int] = None
    ):
        pass

    @abstractmethod
    def delete_gameplay_info_by_id_list(
        self, player_id_list: List[str], created_year: Optional[int] = None, created_month: Optional[int] = None
    ):
        pass

    # Gameplay Delta
    @abstractmethod
    def get_existing_gameplay_delta_info_id_list(
        self, 
        steam_id_list:List[str],
        created_year: Optional[int] = None, 
        created_month: Optional[int] = None
        )-> Union[None, List[str]]:
        pass

    @abstractmethod
    def get_existing_gameplay_delta_info_list(
        self, 
        steam_id_list:List[str],
        created_year: Optional[int] = None, 
        created_month: Optional[int] = None
        )-> Union[None, List[GameplayMonthDeltaList]]:
        pass

    @abstractmethod
    def save_gameplay_delta_info_list(self, gameplay_delta_info_list: List[GameplayMonthDeltaList]):
        pass


    # Game Info
    @abstractmethod
    def get_game_info_by_game_id_list(self, game_id_list: List[str]):
        pass

    @abstractmethod
    def save_game_info_list(self, game_info_list: List[SteamGameinfo]):
        pass

