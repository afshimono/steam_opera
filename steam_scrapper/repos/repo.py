from abc import ABC, abstractmethod


class Repo(ABC):
    @abstractmethod
    def get_player_info_by_id(player_id: str):
        pass
