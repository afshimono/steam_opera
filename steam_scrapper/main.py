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
@click.argument("sleep_time_in_ms", envvar="SLEEP_TIME_IN_MS", type=int)
@click.option("--output", default="mongo")
@click.option("--frequency", default="month")
@click.option("--fetch_friends/--dont_fetch_friends", default=False)
def steam_scrap(steam_key, mongo_db_url,player_id, sleep_time_in_ms, output,frequency,fetch_friends):
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
    
    steam_scrapper = SteamScrapper(
        repo = repo, 
        frequency = frequency,
        sleep_time_in_ms = sleep_time_in_ms)
    # fetch target steam player:
    logging.info("Scrapping user data...")
    steam_scrapper.scrap_users(steam_ids=player_id)
    # scrap friend list
    friend_list = steam_scrapper.scrap_friend_list(steam_id=player_id)
    # scrap gameplay info
    gameplay_info = steam_scrapper.scrap_gameplay_info(steam_id=player_id)
    # scrap game info
    game_id_list_str = ",".join([str(gameplay_item.appid) for gameplay_item in gameplay_info.gameplay_list])
    gameinfo = steam_scrapper.scrap_game_info(game_id_list_str)
    # scrap friend information
    friend_list_str = ",".join([friend.steamid for friend in friend_list.friend_list])
    steam_scrapper.scrap_users(steam_ids=friend_list_str)
    for friend_item in tqdm(friend_list.friend_list, desc="Scrapping Friends", leave=False):
        steam_scrapper.scrap_friend_list(steam_id=friend_item.steamid)
        if fetch_friends:
            gameplay_info = steam_scrapper.scrap_gameplay_info(steam_id=friend_item.steamid)
            game_id_list_str = ",".join([gameplay_item.appid for gameplay_item in gameplay_info.gameplay_list])
            steam_scrapper.scrap_game_info(game_id_list_str)
if __name__ == "__main__":
    steam_scrap()
