from typing import List, Optional

from abc import ABC, abstractmethod

from models import SteamProfile, SteamFriendList, SteamGameinfo, GameplayList

class Repo(ABC):
    @abstractmethod
    def get_player_info_by_id_list(self, player_id_list: List[str])->List[SteamProfile]:
        pass

    @abstractmethod
    def save_player_info_list(self, player_info_list: List[SteamProfile]):
        pass

    @abstractmethod
    def delete_player_info_list(self, player_id_list: List[str]):
        pass

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
    def save_gameplay_info(self, gameplay_info: GameplayList):
        pass

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

    @abstractmethod
    def get_game_info_by_game_id_list(self, game_id_list: List[str]):
        pass

    @abstractmethod
    def save_game_info_list(self, game_info_list: List[SteamGameinfo]):
        pass