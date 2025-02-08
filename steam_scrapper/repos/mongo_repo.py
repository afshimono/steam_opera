from typing import Optional, List, Dict, Union
import os
from dataclasses import asdict, fields
import logging
import json

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ASCENDING, DESCENDING, ReplaceOne
import certifi

from repos.repo import Repo
from models import (
    SteamProfile,
    SteamFriendList,
    SteamFriendItem,
    SteamGameinfo,
    GameplayList,
    GameplayItem,
    GameplayMonthDeltaItem,
    GameplayMonthDeltaList,
)
from errors import DatabaseDeletionError, DatabaseUpdateError

class SteamMongo(Repo):
    def __init__(self, mongo_url:str):
        self.client = MongoClient(mongo_url, server_api=ServerApi("1"), tlsCAFile=certifi.where())
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)
        self.steam_db = self.client.SteamOperaDB
        self.steam_profiles = self.steam_db.steam_profiles
        self.friend_lists = self.steam_db.friend_lists
        self.gameplay = self.steam_db.gameplay
        self.game_info = self.steam_db.game_info
        self.gameplay_delta = self.steam_db.gameplay_delta

    # Friend List

    def get_existing_friend_list_ids(
        self, 
        player_id_list: List[str], 
        created_year: Optional[int]=None, 
        created_month: Optional[int]=None)->List[str]:
        query_dict = {"steamid": {"$in":player_id_list}}
        if created_year is not None:
            query_dict.update({"created_year":created_year})
        if created_month is not None:
            query_dict.update({"created_month":created_month})
        result = self.friend_lists.aggregate([
            # Match the documents possible
            { "$match": query_dict },
            # Group the documents and "count" via $sum on the values
            { "$group": {
                "_id": {
                    "steamid": "$steamid"
                },
                "count": { "$sum": 1 }
            }}
        ])
        result_list = [item["_id"]["steamid"] for item in list(result)]
        return result_list

    def get_friend_list_by_id(
            self, 
            player_id: str, 
            created_year: Optional[int]=None, 
            created_month: Optional[int]=None)->List[SteamFriendList]:
        query_dict = {"steamid": player_id}
        if created_year is not None:
            query_dict.update({"created_year":created_year})
        if created_month is not None:
            query_dict.update({"created_month":created_month})
        result_query = self.friend_lists.find(query_dict).sort("updated_at",DESCENDING)
        field_names = set(f.name for f in fields(SteamFriendList))
        final_result = [SteamFriendList(
            **{k:v for k,v in friend_list_item.items() if k in field_names}) for friend_list_item in result_query]
        friend_list_item_field_names = set(f.name for f in fields(SteamFriendItem))
        for friend_list in final_result:
            friend_list.friend_list = [
                SteamFriendItem(
                    **{k:v for k,v in friend_list_item.items() if k in friend_list_item_field_names}) 
                    for friend_list_item in friend_list.friend_list
            ]
        return final_result

    def save_friend_list(self, player_friend_list: SteamFriendList):
        friend_list_dict = asdict(player_friend_list)
        result = self.friend_lists.replace_one({"steamid":player_friend_list.steamid},friend_list_dict,upsert=True)
        logging.debug(result)

    def delete_friend_list(self, created_month: Optional[int] = None, created_year: Optional[int] = None):
        if not any([created_month, created_year]):
            raise DatabaseDeletionError(
                "At least one of the filter created_month or created_year must be specified to avoid deleting the whole Database."
            )
        delete_filter = {}
        if created_month is not None:
            delete_filter["created_month"] = created_month
        if created_year is not None:
            delete_filter["created_year"] = created_year
        self.friend_lists.delete_many(delete_filter)

    # Player Info

    def get_player_info_by_id_list(self, player_id_list: List[str])->List[SteamProfile]:
        result_query = self.steam_profiles.find({"steamid": {"$in":player_id_list}})
        field_names = set(f.name for f in fields(SteamProfile))
        final_result = [SteamProfile(
            **{k:v for k,v in profile.items() if k in field_names}) 
            for profile in list(result_query)]
        return final_result

    def save_player_info_list(self, player_info_list: List[SteamProfile]):
        if len(player_info_list)>0:
            transformed_list = [asdict(profile) for profile in player_info_list]
            bulk_write_list = [ReplaceOne({"steamid":profile["steamid"]},profile, upsert=True) for profile in transformed_list]
            result = self.steam_profiles.bulk_write(bulk_write_list)
            logging.debug(result)

    def delete_player_info_list(self, player_id_list: List[str]):
        result = self.steam_profiles.delete_many({"steamid": {"$in":player_id_list}})

    # Gameplay Info
    def get_existing_gameplay_info_ids(
        self, 
        player_id_list: List[str], 
        created_year: Optional[int]=None, 
        created_month: Optional[int]=None)->List[str]:
        query_dict = {"steamid": {"$in":player_id_list}}
        if created_year is not None:
            query_dict.update({"created_year":created_year})
        if created_month is not None:
            query_dict.update({"created_month":created_month})
        result = self.gameplay.aggregate([
            # Match the documents possible
            { "$match": query_dict },
            # Group the documents and "count" via $sum on the values
            { "$group": {
                "_id": {
                    "steamid": "$steamid"
                },
                "count": { "$sum": 1 }
            }}
        ])
        result_list = [item["_id"]["steamid"] for item in list(result)]
        return result_list

    def get_gameplay_info_by_id(
        self,
        player_id: Optional[str] = None,
        created_year: Optional[int] = None,
        created_month: Optional[int] = None,
        sort_query: Optional[bool] = False,
    ) -> List[GameplayList]:

        query_dict = {}
        if player_id is not None:
            query_dict.update({"steamid": player_id})
            sort_query = True
        if created_year is not None:
            query_dict.update({"created_year": created_year})
        if created_month is not None:
            query_dict.update({"created_month": created_month})
        return self.get_gameplay_from_query(query_dict=query_dict, sort_query=sort_query)

    def get_gameplay_info_by_id_list(
        self,
        player_id_list: List[str] = None,
        created_year: Optional[int] = None,
        created_month: Optional[int] = None,
        sort_query: Optional[bool] = False,
    ) -> List[GameplayList]:

        query_dict = {}

        query_dict.update({"steamid": {"$in": player_id_list}})

        if created_year is not None:
            query_dict.update({"created_year": created_year})
        if created_month is not None:
            query_dict.update({"created_month": created_month})
        return self.get_gameplay_from_query(query_dict=query_dict, sort_query=sort_query)

    def get_gameplay_from_query(self, query_dict: Dict, sort_query: Optional[bool] = False):
        result_query = self.gameplay.find(query_dict)
        if sort_query:
            result_query = result_query.sort("updated_at", DESCENDING)
        field_names = set(f.name for f in fields(GameplayList))
        final_result = [
            GameplayList(**{k: v for k, v in friend_list_item.items() if k in field_names})
            for friend_list_item in result_query
        ]
        gameplay_item_field_names = set(f.name for f in fields(GameplayItem))
        for gameplay_info in final_result:
            gameplay_info.gameplay_list = [
                GameplayItem(**{k: v for k, v in gameplay_item.items() if k in gameplay_item_field_names})
                for gameplay_item in gameplay_info.gameplay_list
            ]
        return final_result

    def save_gameplay_info(self, gameplay_info: GameplayList):
        gameplay_dict = asdict(gameplay_info)
        for gameplay_item in gameplay_dict["gameplay_list"]:
            gameplay_item["appid"] = str(gameplay_item["appid"])
        self.gameplay.insert_one(gameplay_dict)

    def delete_gameplay_info(
        self, player_id: Optional[str] = None, created_year: Optional[int] = None, created_month: Optional[int] = None
    ):
        if not (player_id or (created_month and created_year)):
            raise DatabaseDeletionError(
                "At least one of the filter player_id or (created_month and created_year) must be specified to avoid deleting the whole Database."
            )
        delete_filter = {}
        if player_id:
            delete_filter["steamid"] = player_id
        if created_month is not None:
            delete_filter["created_month"] = created_month
        if created_year is not None:
            delete_filter["created_year"] = created_year
        self.gameplay.delete_many(delete_filter)

    def delete_gameplay_info_by_id_list(
        self, player_id_list: List[str], created_year: Optional[int] = None, created_month: Optional[int] = None
    ):
        if not (player_id_list):
            raise DatabaseDeletionError(
                "At least one of the filter player_id or (created_month and created_year) must be specified to avoid deleting the whole Database."
            )
        delete_filter = {"steamid": {"$in": player_id_list}}
        if created_month is not None:
            delete_filter["created_month"] = created_month
        if created_year is not None:
            delete_filter["created_year"] = created_year
        self.gameplay.delete_many(delete_filter)

    # Gameplay Delta
    def get_existing_gameplay_delta_info_id_list(
        self, 
        steam_id_list:List[str],
        created_year: Optional[int] = None, 
        created_month: Optional[int] = None
        )-> Union[None, List[str]]:
        query_dict = {"steamid": {"$in":steam_id_list}}
        if created_year is not None:
            query_dict.update({"created_year":created_year})
        if created_month is not None:
            query_dict.update({"created_month":created_month})
        result = self.gameplay_delta.aggregate([
            # Match the documents possible
            { "$match": query_dict },
            # Group the documents and "count" via $sum on the values
            { "$group": {
                "_id": {
                    "steamid": "$steamid"
                },
                "count": { "$sum": 1 }
            }}
        ])
        result_list = [item["_id"]["steamid"] for item in list(result)]
        return result_list
    
    def get_existing_gameplay_delta_info_list(
        self, 
        steam_id_list:List[str],
        created_year: Optional[int] = None, 
        created_month: Optional[int] = None
        )-> Union[None, List[GameplayMonthDeltaList]]:
        query_dict = {"steamid": {"$in":steam_id_list}}
        if created_year is not None:
            query_dict.update({"created_year":created_year})
        if created_month is not None:
            query_dict.update({"created_month":created_month})
        result = self.gameplay_delta.find(query_dict)
        field_names = set(f.name for f in fields(GameplayMonthDeltaList))
        final_result = [
            GameplayMonthDeltaList(**{k: v for k, v in gameplay_delta_item.items() if k in field_names})
            for gameplay_delta_item in result
        ]
        gameplay_delta_item_field_names = set(f.name for f in fields(GameplayMonthDeltaItem))
        for gameplay_delta in final_result:
            gameplay_delta.gameplay_list = [
                GameplayMonthDeltaItem(**{k: v for k, v in gameplay_item.items() if k in gameplay_delta_item_field_names})
                for gameplay_item in gameplay_delta.gameplay_list
            ]
        return final_result

    def save_gameplay_delta_info_list(self, gameplay_delta_info_list: List[GameplayMonthDeltaList])->None:
        if not gameplay_delta_info_list:
            return None
        gameplay_delta_dict = [asdict(item) for item in gameplay_delta_info_list]
        for gameplay_delta_list_item in gameplay_delta_dict:
            for gameplay_delta_item in gameplay_delta_list_item["gameplay_delta_list"]:
                gameplay_delta_item["appid"] = str(gameplay_delta_item["appid"])
        bulk_write_list = [
            ReplaceOne(
                {
                    "steamid": gameplay_delta_list_item["steamid"],
                    "created_year": gameplay_delta_list_item["created_year"],
                    "created_month": gameplay_delta_list_item["created_month"],
                },
                gameplay_delta_list_item,
                upsert=True,
            )
            for gameplay_delta_list_item in gameplay_delta_dict
        ]
        if bulk_write_list:
            result = self.gameplay_delta.bulk_write(bulk_write_list)
            logging.debug(result)

    # Game Info

    def get_game_info_by_game_id_list(self, game_id_list: List[str])->List[SteamGameinfo]:
        result_query = self.game_info.find({"appid": {"$in":game_id_list}})
        field_names = set(f.name for f in fields(SteamGameinfo))
        final_result = [SteamGameinfo(
            **{k:v for k,v in gameinfo.items() if k in field_names}) 
            for gameinfo in list(result_query)]

        return final_result

    def save_game_info_list(self, game_info_list: List[SteamGameinfo]):
        if len(game_info_list)>0:
            transformed_list = [asdict(gameinfo) for gameinfo in game_info_list]
            for item in transformed_list:
                item["appid"] = str(item["appid"])
            bulk_write_list = [ReplaceOne({"appid":gameinfo["appid"]},gameinfo, upsert=True) for gameinfo in transformed_list]
            result = self.game_info.bulk_write(bulk_write_list)
            logging.debug(result)

    # Shared
    def batch_update_type(self, doc_type: str, query: Dict, new_value: Dict):
        type_dict = {
            "gameplay_delta": self.gameplay_delta,
            "gameplay_info": self.gameplay,
            "steam_profile": self.steam_profiles,
            "friend_list": self.friend_lists,
            "game_info": self.game_info,
        }
        db_collection = type_dict.get(doc_type)
        if db_collection is None:
            raise DatabaseUpdateError("Invalid Document type.")
        query = json.loads(query)
        new_value = json.loads(new_value)
        update_query = {"$set": new_value}
        db_collection.update_many(query, update_query)
