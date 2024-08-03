import click
import datetime as dt
import logging

from tqdm import tqdm

from repos.mongo_repo import SteamMongo
from config import config
from scrapper import SteamScrapper

@click.command()
@click.argument("steam_key", envvar="STEAM_KEY", type=str)
@click.argument("mongo_db_url", envvar="MONGO_DB_URL", type=str)
@click.argument("player_id", envvar="PLAYER_ID", type=str)
@click.option("--output", default="mongo")
@click.option("--frequency", default="month")
@click.option("--fetch_friends/--dont_fetch_friends", default=False)
def steam_scrap(steam_key, mongo_db_url,player_id, output,frequency,fetch_friends):
    repo = None
    # gets repo
    if output == "mongo":
        logging.info("Creating output type Mongo DB...")
        if config.mongodb_url is None:
            raise ValueError("Missing MongoDB URL Env Variable.")
        repo = SteamMongo(mongo_url=config.mongodb_url)
        logging.info("Mongo DB output created.")
    if repo is None:
        raise ValueError("No Repository has been assigned to scrap.")
    
    logging.info(f"Scrapping for Player ID {player_id}")
    
    steam_scrapper = SteamScrapper(
        repo = repo, 
        frequency = frequency)
    # fetch target steam player:
    logging.info("Scrapping user data...")
    target_profile_response = steam_scrapper.scrap_users(steam_ids=player_id)
    if len(target_profile_response)>0:
        target_profile = target_profile_response[0]
    else:
        logging.warning("Informed player ID was not retrieved properly.")
        return None
    # scrap friend list
    friend_list = steam_scrapper.scrap_friend_list(steam_id=player_id)
    # scrap gameplay info
    gameplay_info = steam_scrapper.scrap_gameplay_info(steam_id=player_id)
    # scrap game info
    game_id_list_str = ",".join([str(gameplay_item.appid) for gameplay_item in gameplay_info.gameplay_list])
    scrapped_game_info = steam_scrapper.scrap_game_info(game_id_list_str)
    scrapped_game_info_ids_set = set([game_info.appid for game_info in scrapped_game_info])
    # scrap friend information
    friend_list_str = ",".join([friend.steamid for friend in friend_list.friend_list])
    steam_scrapper.scrap_users(steam_ids=friend_list_str)
    for friend_item in tqdm(friend_list.friend_list, desc="Scrapping Friends Friend Lists", leave=False):
        steam_scrapper.scrap_friend_list(steam_id=friend_item.steamid)

    if fetch_friends:
        game_info_set = set()
        for friend_item in tqdm(friend_list.friend_list, desc="Scrapping Friends Gameplay"):
            gameplay_info = steam_scrapper.scrap_gameplay_info(steam_id=friend_item.steamid)
            if gameplay_info is not None:
                for gameplay_item in gameplay_info.gameplay_list:
                    game_info_set.add(gameplay_item.appid)
        game_info_set = game_info_set.difference(scrapped_game_info_ids_set)
        game_id_list_str = ",".join(list(game_info_set))
        steam_scrapper.scrap_game_info(game_id_list_str)
    logging.info(f"Scrapping done! Player {target_profile.persona_name} - Friends {len(friend_list)} - Game Info {len(game_info_set) + len(scrapped_game_info_ids_set)}")

def configure_logging():
    import sys
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    root.addHandler(handler)

if __name__ == "__main__":
    configure_logging()
    steam_scrap()
