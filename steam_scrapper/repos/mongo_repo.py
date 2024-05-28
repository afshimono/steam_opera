from typing import Optional, List
import os
from dataclasses import asdict, fields

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from repos.repo import Repo
from models import SteamProfile

class SteamMongo(Repo):
    def __init__(self, mongo_url:Optional[str]=None):
        mongo_url = mongo_url or os.getenv("MONGO_DB_URL")
        self.client = MongoClient(mongo_url, server_api=ServerApi('1'))
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)
        self.steam_db = self.client.SteamOperaDB
        self.steam_profiles = self.steam_db.steam_profiles


    def get_player_info_by_id_list(self, player_id_list: List[str])->List[SteamProfile]:
        result_query = self.steam_profiles.find({"steamid": {"$in":player_id_list}})
        field_names = set(f.name for f in fields(SteamProfile))
        final_result = [SteamProfile(
            **{k:v for k,v in profile.items() if k in field_names}) 
            for profile in list(result_query)]
        return final_result

    def save_player_info_list(self, player_info_list: List[SteamProfile]):
        transformed_list = [asdict(profile) for profile in player_info_list]
        result = self.steam_profiles.insert_many(transformed_list)

    def delete_player_info_list(self, player_id_list: List[str]):
        result = self.steam_profiles.delete_many({"steamid": {"$in":player_id_list}})

    def get_gameplay_info_by_id_list(self, player_id_list: List[str]):
        pass

    def get_friend_list_by_id(self, player_id: str):
        pass

    def get_game_info_by_game_id_list(self, game_id_list: List[str]):
        pass


