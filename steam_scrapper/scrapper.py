import datetime as dt
from typing import List, Optional, Union
import logging
import time

from tqdm import tqdm

from repos.repo import Repo
from repos.mongo_repo import SteamMongo
from models import (
    SteamProfile, 
    SteamFriendList, 
    SteamGameinfo, 
    GameplayList, 
    TimestampedBaseClass
    )
import steam_api

class SteamScrapper:
    def __init__(self, repo:Repo, frequency:str):
        self.repo = repo
        self.steam_api = steam_api
        self.frequency = frequency
        self.current_time = dt.datetime.now()
    
        self.GAME_INFO_BATCH_SIZE = 500


    def scrap_users(self, steam_ids: str)->List[SteamProfile]:
        """
        Populates a list with the required steam_ids.
        If they exist in the DB but are not found in SteamAPI, the status of missing_in_action
        or killed_in_action is populated.

        :param steam_ids: Comma separated list of steam ids to be scrapped.
        :type steam_ids: str
        """
        steam_id_list = steam_ids.split(",")
        db_user_profiles = self.repo.get_player_info_by_id_list(steam_id_list)
        db_user_profile_dict = { user.steamid:user for user in db_user_profiles}
        db_profile_ids = [steam_profile.steamid for steam_profile in db_user_profiles]
        steam_ids_not_in_db_list = [id for id in steam_id_list 
                                    if (id not in db_profile_ids) or
                                    not self.is_model_updated(db_user_profile_dict[id])]
        steam_user_profiles = steam_api.fetch_player_info(",".join(steam_ids_not_in_db_list)) if len(steam_ids_not_in_db_list)>0 else []
        steam_user_profile_ids = [steam_profile.steamid for steam_profile in steam_user_profiles]
        steam_user_profile_dict = { user.steamid:user for user in steam_user_profiles}

        user_to_save_in_db = []
        for idx, steam_id in enumerate(tqdm(steam_id_list, desc="User Info")):
            # profile does not exist both in steam and in db
            if steam_id not in db_profile_ids and steam_id not in steam_user_profile_ids:
                continue
            # new profile
            elif steam_id not in db_profile_ids and steam_id in steam_user_profile_ids:
                user_to_save_in_db.append(steam_user_profile_dict[steam_id])
            # profile not found in steam but existing in db
            elif steam_id in db_profile_ids and steam_id not in steam_user_profile_ids:
                if not self.is_model_updated(db_user_profile_dict[steam_id]):
                    db_user_profile_dict[steam_id].missing_in_action = True
                    user_to_save_in_db.append(db_user_profile_dict[steam_id])
            # profile found and already exists in db
            else:
                if not self.is_model_updated(db_user_profile_dict[steam_id]):
                    steam_user_profile_dict[steam_id].created_at = db_user_profile_dict[steam_id].created_at
                    user_to_save_in_db.append(steam_user_profile_dict[steam_id])
            if idx>0 and idx%100==0:
                self.repo.save_player_info_list(user_to_save_in_db)
                user_to_save_in_db = []
        self.repo.save_player_info_list(user_to_save_in_db)
        return user_to_save_in_db

    def scrap_friend_list_batch(self, steam_id_list:List[str])->None:
        """
        Creates a new entry for friend list.
        :param steam_id_list: the list of steam id to retrieve the friend list
        :type steam_id: List[str]
        """
        if not self.is_friend_list_updated(steam_id):
            steam_friend_list = steam_api.fetch_player_friend_list(player_id=steam_id)
            if len(steam_friend_list)>0:
                steam_friend_list_obj = SteamFriendList(
                    steamid=steam_id,
                    friend_list=steam_friend_list,
                    created_at=self.current_time,
                    updated_at=self.current_time,
                    created_month=self.current_time.month,
                    created_year=self.current_time.year
                )
                self.repo.save_friend_list(steam_friend_list_obj)
                return steam_friend_list_obj
            return None
        return self.repo.get_friend_list_by_id(player_id=steam_id)[0]

    def scrap_friend_list(self, steam_id:str)->Union[SteamFriendList,None]:
        """
        Creates a new entry for friend list.
        :param steam_id: the steam id to retrieve the friend list
        :type steam_id: str
        """
        if not self.is_friend_list_updated(steam_id):
            steam_friend_list = steam_api.fetch_player_friend_list(player_id=steam_id)
            if len(steam_friend_list)>0:
                steam_friend_list_obj = SteamFriendList(
                    steamid=steam_id,
                    friend_list=steam_friend_list,
                    created_at=self.current_time,
                    updated_at=self.current_time,
                    created_month=self.current_time.month,
                    created_year=self.current_time.year
                )
                self.repo.save_friend_list(steam_friend_list_obj)
                return steam_friend_list_obj
            return None
        return self.repo.get_friend_list_by_id(player_id=steam_id)[0]

    def is_friend_list_updated(self, steam_id: str)->bool:
        """
        Decides if a friend_list should be scraped based on the current record and the frequency.

        :param player_id: the steam profile of the player
        :type player_id: SteamProfile
        """
        
        if self.frequency == "month":
            existing_friend_list = self.repo.get_friend_list_by_id(
                steam_id, 
                created_month=self.current_time.month, 
                created_year=self.current_time.year)
            if len(existing_friend_list) > 0:
                existing_friend_list_item = existing_friend_list[0]
                return self.is_model_updated(existing_friend_list_item)
        elif self.frequency == "year":
            existing_friend_list = self.repo.get_friend_list_by_id(
                steam_id,
                created_year=self.current_time.year)
            if len(existing_friend_list) > 0:
                existing_friend_list_item = existing_friend_list[0]
                return self.is_model_updated(existing_friend_list_item)
        return False


    def scrap_game_info(self, app_ids:str)->List[SteamGameinfo]:
        """
        Fetch information about the specified game, saves it, and return the GameInfo model list.
        """
        full_app_id_list = app_ids.split(",")
        final_gameinfo_list = []
        for app_id_list in tqdm(self.list_chunk(full_app_id_list, self.GAME_INFO_BATCH_SIZE), 
                                desc="GameInfo chunks", 
                                total=len(full_app_id_list)):
            # First fetch existing records
            db_gameinfo = self.repo.get_game_info_by_game_id_list(app_id_list)
            db_gameinfo_dict = { gameinfo.appid:gameinfo for gameinfo in db_gameinfo}
            db_gameinfo_ids = [gameinfo.appid for gameinfo in db_gameinfo]
            gameinfo_to_save_in_db = []
            for app_id in tqdm(app_id_list, 
                                desc="Game Info",
                                total=len(app_id_list)):
                if app_id in db_gameinfo_ids:
                    if not self.is_model_updated(db_gameinfo_dict[app_id]):
                        steam_gameinfo = steam_api.fetch_game_details(app_id)  
                        # profile not found in steam but existing in db
                        if app_id in db_gameinfo_ids and steam_gameinfo is None:
                            current_gameinfo = db_gameinfo_dict[app_id]
                            current_gameinfo.last_failed_update_attempt = self.current_time
                            gameinfo_to_save_in_db.append(current_gameinfo)
                        # profile found and already exists in db
                        else:
                            current_gameinfo = db_gameinfo_dict[app_id]
                            steam_gameinfo.created_at =  current_gameinfo.created_at
                            gameinfo_to_save_in_db.append(steam_gameinfo)
                else:
                    steam_gameinfo = steam_api.fetch_game_details(app_id)
                    # app does not exist both in steam and in db
                    if steam_gameinfo is None or app_id != steam_gameinfo.appid:
                        steam_gameinfo = SteamGameinfo(
                            appid=app_id,
                            name="",
                            type="Error",
                            min_age=0,
                            description="",
                            developers=[],
                            publishers=[],
                            genres=[],
                            categories=[],
                            about="",
                            is_free=False,
                            created_at=self.current_time,
                            updated_at=self.current_time,
                            last_failed_update_attempt=self.current_time
                        )
                    # new profile
                    gameinfo_to_save_in_db.append(steam_gameinfo)

                if len(gameinfo_to_save_in_db) % 100 == 0 and len(gameinfo_to_save_in_db)>0:
                    self.repo.save_game_info_list(gameinfo_to_save_in_db)
                    final_gameinfo_list += gameinfo_to_save_in_db
                    gameinfo_to_save_in_db = []
            final_gameinfo_list += gameinfo_to_save_in_db
            self.repo.save_game_info_list(gameinfo_to_save_in_db)
        return final_gameinfo_list
    
    def list_chunk(self,my_list:List, list_size:int)-> List: # type: ignore
        for i in range(0, len(my_list), list_size):  
            yield my_list[i:i + list_size] 

    def scrap_gameplay_info(self, steam_id:str)->Union[GameplayList,None]:
        """
        Fetch gameplay information, saves it, and returns the GameplayList information.
        """
        if not self.is_gameplay_info_updated(steam_id):
            gameplay_list = steam_api.fetch_player_gameplay_list(player_id=steam_id)
            if len(gameplay_list)>0:
                steam_gameplay_list_obj = GameplayList(
                    steamid=steam_id,
                    gameplay_list=gameplay_list,
                    created_at=self.current_time,
                    updated_at=self.current_time,
                    created_month=self.current_time.month,
                    created_year=self.current_time.year
                )
                self.repo.save_gameplay_info(steam_gameplay_list_obj)
                return steam_gameplay_list_obj
            return None
        return self.repo.get_gameplay_info_by_id(player_id=steam_id)[0]

    def is_gameplay_info_updated(self, steam_id:str)->bool:
        """
        Checks if the gameplay record for the given steam id was already saved to the repo for the given frequency.

        :param steam_id: the steam id for a player or user
        :type steam_id: str
        """
        if self.frequency == "month":
            existing_gameplay_list = self.repo.get_gameplay_info_by_id(
                steam_id, 
                created_month=self.current_time.month, 
                created_year=self.current_time.year)
            if len(existing_gameplay_list) > 0:
                existing_gameplay_item = existing_gameplay_list[0]
                return self.is_model_updated(existing_gameplay_item)
        elif self.frequency == "year":
            existing_gameplay_list = self.repo.get_gameplay_info_by_id(
                steam_id,
                created_year=self.current_time.year)
            if len(existing_gameplay_list) > 0:
                existing_gameplay_item = existing_gameplay_list[0]
                return self.is_model_updated(existing_gameplay_item)
        return False
    
    def is_model_updated(
            self, 
            timestamped_class: TimestampedBaseClass)->bool:
        """
        Decides if a timestamped base class should be scraped based 
        on the current record and the frequency.

        :param timestamped_class: the base class to be checked
        :type timestamped_class: TimestampedBaseClass
        """
        
        if self.frequency == "month":
            if timestamped_class.created_at.year == self.current_time.year and \
                timestamped_class.created_at.month == self.current_time.month:
                return True
            elif timestamped_class.last_failed_update_attempt is not None:
                if timestamped_class.last_failed_update_attempt.year == self.current_time.year and \
                    timestamped_class.last_failed_update_attempt.month == self.current_time.month:
                    return True
        elif self.frequency == "year":
            if timestamped_class.updated_at.year == self.current_time.year:
                return True
            elif timestamped_class.last_failed_update_attempt is not None:
                if timestamped_class.last_failed_update_attempt.year == self.current_time.year:
                    return True
        return False

