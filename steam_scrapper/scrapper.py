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

    def scrap_all_user_data(self, player_id: str, fetch_friends: bool) -> None:
        """
        Extracts all information for a single steam id and stores all information
        in the repo.

        :param steam_id: Steam id to be scrapped.
        :type steam_id: str
        :param fetch_friends: Switch if player friends will be also scrapped
        :type fetch_friends: bool
        """
        # fetch target steam player:
        logging.info("Scrapping user data.")
        self.scrap_users(steam_ids=player_id)
        saved_user = self.repo.get_player_info_by_id_list([player_id])

        if len(saved_user)>0:
            target_profile = saved_user[0]
        else:
            logging.warning("Informed player ID was not retrieved properly.")
            return None
        # scrap friend list
        logging.info("Scrapping Friend List.")
        friend_list = self.scrap_friend_list(steam_id=player_id)
        # scrap gameplay info
        logging.info("Scrapping Gameplay Info.")
        gameplay_info = self.scrap_gameplay_info(steam_id=player_id)
        game_info_set = set()
        scrapped_game_info_ids_set = set()

        if gameplay_info is not None:
            # scrap game info
            game_id_list_str = ",".join(list(set([str(gameplay_item.appid) for gameplay_item in gameplay_info.gameplay_list])))
            logging.info("Scrapping Game Info.")
            scrapped_game_info = self.scrap_game_info(game_id_list_str)
            scrapped_game_info_ids_set = set([game_info.appid for game_info in scrapped_game_info])

        if friend_list is not None:
            # scrap friend information
            logging.info("Scrapping Friends Friend Lists.")
            friend_friends_list = [friend.steamid for friend in friend_list.friend_list]
            friend_list_str = ",".join(friend_friends_list)
            logging.info(f"Friend list ids for {target_profile.persona_name}: {friend_list_str}")
            self.scrap_users(steam_ids=friend_list_str)
            self.scrap_friend_list_batch(steam_id_list=friend_friends_list)

            if fetch_friends:
                logging.info("Scrapping Friends Gameplay Info.")
                gameplay_info_list = self.scrap_gameplay_batch(steam_id_list=friend_friends_list)
                for gameplay_info in gameplay_info_list:
                    for gameplay_item in gameplay_info.gameplay_list:
                        game_info_set.add(gameplay_item.appid)
                game_info_set = game_info_set.difference(scrapped_game_info_ids_set)
                game_id_list_str = ",".join(list(game_info_set))
                logging.info("Scrapping Friends Game Info.")
                self.scrap_game_info(game_id_list_str)
        else:
            logging.info("Gameplay Info Empty. Skipping GameInfo, FriendsData, etc)")
        logging.info(f"Scrapping done! New information for Player {target_profile.persona_name} "+
                    f"- Friends {len(friend_list.friend_list) if friend_list is not None else 0} "+
                    f"- Game Info {len(game_info_set) + len(scrapped_game_info_ids_set)}")


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
        Scrapes a list of friend_lists for the informed ids.
        :param steam_id_list: the list of steam id to retrieve the friend list
        :type steam_id: List[str]
        """
        query_year = self.current_time.year if self.frequency in ["year","month"] else None
        query_month = self.current_time.month if self.frequency == "month" else None
        db_friend_list_ids = self.repo.get_existing_friend_list_ids(
            player_id_list=steam_id_list,
            created_month=query_month,
            created_year=query_year)
        steam_id_list_to_fetch = [steam_id for steam_id in steam_id_list if steam_id not in db_friend_list_ids]
        for steam_id in tqdm(steam_id_list_to_fetch,
                             desc="Fetching FriendList"):
            steam_friend_list = steam_api.fetch_player_friend_list(player_id=steam_id)
            steam_friend_list_obj = SteamFriendList(
                steamid=steam_id,
                friend_list=steam_friend_list,
                created_at=self.current_time,
                updated_at=self.current_time,
                created_month=self.current_time.month,
                created_year=self.current_time.year
            )
            self.repo.save_friend_list(steam_friend_list_obj)


    def scrap_friend_list(self, steam_id:str)->Union[SteamFriendList,None]:
        """
        Creates a new entry for friend list.
        :param steam_id: the steam id to retrieve the friend list
        :type steam_id: str
        """
        if not self.is_friend_list_updated(steam_id):
            steam_friend_list = steam_api.fetch_player_friend_list(player_id=steam_id)
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
    


    def scrap_gameplay_batch(self, steam_id_list:List[str])->List[GameplayList]:
        """
        Scrapes a list of gameplays for the informed ids.
        :param steam_id_list: the list of steam id to retrieve the friend list
        :type steam_id: List[str]
        """
        query_year = self.current_time.year if self.frequency in ["year","month"] else None
        query_month = self.current_time.month if self.frequency == "month" else None
        db_gameinfo_ids = self.repo.get_existing_gameplay_info_ids(
            player_id_list=steam_id_list,
            created_month=query_month,
            created_year=query_year)
        steam_id_list_to_fetch = [steam_id for steam_id in steam_id_list if steam_id not in db_gameinfo_ids]
        final_result = []
        for steam_id in tqdm(steam_id_list_to_fetch,
                             desc="Fetching Gameplay"):
            gameplay_list = steam_api.fetch_player_gameplay_list(player_id=steam_id)
            steam_gameplay_list_obj = GameplayList(
                    steamid=steam_id,
                    gameplay_list=gameplay_list,
                    created_at=self.current_time,
                    updated_at=self.current_time,
                    created_month=self.current_time.month,
                    created_year=self.current_time.year
                )
            final_result.append(steam_gameplay_list_obj)
            self.repo.save_gameplay_info(steam_gameplay_list_obj)
        return final_result

    def scrap_gameplay_info(self, steam_id:str)->Union[GameplayList,None]:
        """
        Fetch gameplay information, saves it, and returns the GameplayList information.
        """
        if not self.is_gameplay_info_updated(steam_id):
            gameplay_list = steam_api.fetch_player_gameplay_list(player_id=steam_id)
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
    
    def list_chunk(self,my_list:List, list_size:int)-> List: # type: ignore
        for i in range(0, len(my_list), list_size):  
            yield my_list[i:i + list_size] 