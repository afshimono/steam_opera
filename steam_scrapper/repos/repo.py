from typing import List

from abc import ABC, abstractmethod

from models import SteamProfile

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
    def get_gameplay_info_by_id_list(self, player_id_list: List[str]):
        pass

    @abstractmethod
    def get_friend_list_by_id(self, player_id: str):
        pass

    @abstractmethod
    def get_game_info_by_game_id_list(self, game_id_list: List[str]):
        pass
