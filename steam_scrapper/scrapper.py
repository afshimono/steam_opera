import datetime as dt
from typing import List, Optional, Union
import logging
import time

from tqdm import tqdm

from repos.repo import Repo
from repos.mongo_repo import SteamMongo
from models import SteamProfile, SteamFriendList, SteamGameinfo, GameplayList
import steam_api

class SteamScrapper:
    def __init__(self, repo:Repo, frequency:str, sleep_time_in_ms:Optional[int]=500):
        self.repo = repo
        self.steam_api = steam_api
        self.frequency = frequency
        self.sleep_time_in_ms = sleep_time_in_ms
        self.current_time = dt.datetime.now()


    def scrap_users(self, steam_ids: str)->List[SteamProfile]:
        """
        Populates a list with the required steam_ids.
        If they exist in the DB but are not found in SteamAPI, the status of missing_in_action
        or killed_in_action is populated.

        :param steam_ids: Comma separated list of steam ids to be scrapped.
        :type steam_ids: str
        """
        steam_id_list = steam_ids.split(",")
        steam_user_profiles = steam_api.fetch_player_info(steam_ids)
        time.sleep(float(self.sleep_time_in_ms)/1000.0) 
        steam_user_profile_ids = [steam_profile.steamid for steam_profile in steam_user_profiles]
        steam_user_profile_dict = { user.steamid:user for user in steam_user_profiles}
        db_user_profiles = self.repo.get_player_info_by_id_list(steam_id_list)
        db_user_profile_dict = { user.steamid:user for user in db_user_profiles}
        db_profile_ids = [steam_profile.steamid for steam_profile in db_user_profiles]
        user_to_save_in_db = []
        for idx, steam_id in enumerate(tqdm(steam_id_list, desc="User Info", leave=False)):
            # profile does not exist both in steam and in db
            if steam_id not in db_profile_ids and steam_id not in steam_user_profile_ids:
                continue
            # new profile
            elif steam_id not in db_profile_ids and steam_id in steam_user_profile_ids:
                user_to_save_in_db.append(steam_user_profile_dict[steam_id])
            # profile not found in steam but existing in db
            elif steam_id in db_profile_ids and steam_id not in steam_user_profile_ids:
                if not self.is_user_updated(db_user_profile_dict[steam_id]):
                    db_user_profile_dict[steam_id].missing_in_action = True
                    user_to_save_in_db.append(db_user_profile_dict[steam_id])
            # profile found and already exists in db
            else:
                if not self.is_user_updated(db_user_profile_dict[steam_id]):
                    steam_user_profile_dict[steam_id].created_at = db_user_profile_dict[steam_id].created_at
                    user_to_save_in_db.append(steam_user_profile_dict[steam_id])
            if idx>0 and idx%100==0:
                self.repo.save_player_info_list(user_to_save_in_db)
                user_to_save_in_db = []
        self.repo.save_player_info_list(user_to_save_in_db)
        return user_to_save_in_db
    
    def is_user_updated(self, player_profile: SteamProfile)->bool:
        """
        Decides if a user should be scraped based on the current record and the frequency.

        :param player_id: the steam profile of the player
        :type player_id: SteamProfile
        """
        if self.frequency == "month":
            if player_profile.updated_at.year == self.current_time.year and \
                player_profile.updated_at.month == self.current_time.month:
                return True
            elif player_profile.last_failed_update_attempt is not None:
                if player_profile.last_failed_update_attempt.year == self.current_time.year and \
                    player_profile.last_failed_update_attempt.month == self.current_time.month:
                    return True
        elif self.frequency == "year":
            if player_profile.updated_at.year == self.current_time.year:
                return True
            elif player_profile.last_failed_update_attempt.year == self.current_time.year:
                return True
        return False


    def scrap_friend_list(self, steam_id:str)->Union[SteamFriendList,None]:
        """
        Creates a new entry for friend list.
        :param steam_id: the steam id to retrieve the friend list
        :type steam_id: str
        """
        if not self.is_friend_list_updated(steam_id):
            steam_friend_list = steam_api.fetch_player_friend_list(player_id=steam_id)
            time.sleep(float(self.sleep_time_in_ms)/1000.0)
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
                if existing_friend_list_item.created_year == self.current_time.year and \
                    existing_friend_list_item.created_month == self.current_time.month:
                    return True
        elif self.frequency == "year":
            existing_friend_list = self.repo.get_friend_list_by_id(
                steam_id,
                created_year=self.current_time.year)
            if len(existing_friend_list) > 0:
                existing_friend_list_item = existing_friend_list[0]
                if existing_friend_list_item.updated_at.year == self.current_time.year:
                    return True
        return False


    def scrap_game_info(self, app_ids:str)->List[SteamGameinfo]:
        """
        Fetch information about the specified game, saves it, and return the GameInfo model list.
        """
        app_id_list = app_ids.split(",")
        # First fetch existing records
        db_gameinfo = self.repo.get_game_info_by_game_id_list(app_id_list)
        db_gameinfo_dict = { gameinfo.appid:gameinfo for gameinfo in db_gameinfo}
        db_gameinfo_ids = [gameinfo.appid for gameinfo in db_gameinfo]
        gameinfo_to_save_in_db = []
        for idx, app_id in enumerate(tqdm(app_id_list, desc="Game Info", leave=False)):
            if app_id in db_gameinfo_ids:
                if not self.is_game_info_updated(db_gameinfo_dict[app_id]):
                    steam_gameinfo = steam_api.fetch_game_details(app_id)  
                    time.sleep(float(self.sleep_time_in_ms)/1000.0) 
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
                time.sleep(float(self.sleep_time_in_ms)/1000.0)
                # app does not exist both in steam and in db
                if steam_gameinfo is None:
                    continue
                # new profile
                gameinfo_to_save_in_db.append(steam_gameinfo)
            

            if idx % 100 == 0:
                self.repo.save_game_info_list(gameinfo_to_save_in_db)
                gameinfo_to_save_in_db = []

        self.repo.save_game_info_list(gameinfo_to_save_in_db)
        return gameinfo_to_save_in_db

    def is_game_info_updated(self, gameinfo:SteamGameinfo)->bool:
        """
        Given a SteamGameinfo, checks if the record is updated

        :param gameinfo: model that contains game details
        :type gameinfo: SteamGameinfo
        """
        if self.frequency == "month":
            if gameinfo.updated_at.year == self.current_time.year and \
                gameinfo.updated_at.month == self.current_time.month:
                return True
        elif self.frequency == "year":
            if gameinfo.updated_at.year == self.current_time.year:
                return True
        return False

    def scrap_gameplay_info(self, steam_id:str)->Union[GameplayList,None]:
        """
        Fetch gameplay information, saves it, and returns the GameplayList information.
        """
        if not self.is_gameplay_info_updated(steam_id):
            gameplay_list = steam_api.fetch_player_gameplay_list(player_id=steam_id)
            time.sleep(float(self.sleep_time_in_ms)/1000.0)
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
                if existing_gameplay_item.created_year == self.current_time.year and \
                    existing_gameplay_item.created_month == self.current_time.month:
                    return True
        elif self.frequency == "year":
            existing_gameplay_list = self.repo.get_friend_list_by_id(
                steam_id,
                created_year=self.current_time.year)
            if len(existing_gameplay_list) > 0:
                existing_gameplay_item = existing_gameplay_list[0]
                if existing_gameplay_item.updated_at.year == self.current_time.year:
                    return True
        return False

