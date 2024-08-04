import click
import datetime as dt
import logging

from tqdm import tqdm

from repos.mongo_repo import SteamMongo
from config import config
from scrapper import SteamScrapper

@click.command()
@click.argument("player_id", type=str)
@click.argument("steam_key", envvar="STEAM_KEY", type=str)
@click.option("--mongo_db_url", envvar="MONGO_DB_URL", type=str)
@click.option("--output", default="mongo")
@click.option("--frequency", default="month")
@click.option("--fetch_friends/--dont_fetch_friends", default=False)
def steam_scrap(player_id,steam_key, mongo_db_url, output,frequency,fetch_friends):
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
    logging.info("Scrapping user data.")
    steam_scrapper.scrap_users(steam_ids=player_id)
    saved_user = repo.get_player_info_by_id_list([player_id])

    if len(saved_user)>0:
        target_profile = saved_user[0]
    else:
        logging.warning("Informed player ID was not retrieved properly.")
        return None
    # scrap friend list
    logging.info("Scrapping Friend List.")
    friend_list = steam_scrapper.scrap_friend_list(steam_id=player_id)
    # scrap gameplay info
    logging.info("Scrapping Gameplay Info.")
    gameplay_info = steam_scrapper.scrap_gameplay_info(steam_id=player_id)
    game_info_set = set()
    scrapped_game_info_ids_set = set()

    if gameplay_info is not None:
        # scrap game info
        game_id_list_str = ",".join(list(set([str(gameplay_item.appid) for gameplay_item in gameplay_info.gameplay_list])))
        logging.info("Scrapping Game Info.")
        scrapped_game_info = steam_scrapper.scrap_game_info(game_id_list_str)
        scrapped_game_info_ids_set = set([game_info.appid for game_info in scrapped_game_info])

    if friend_list is not None:
        # scrap friend information
        logging.info("Scrapping Friends Friend Lists.")
        friend_list_str = ",".join([friend.steamid for friend in friend_list.friend_list])
        steam_scrapper.scrap_users(steam_ids=friend_list_str)
        for friend_item in tqdm(
            friend_list.friend_list, 
            desc="Scrapping Friends Friend Lists", 
            total=len(friend_list.friend_list)):
            steam_scrapper.scrap_friend_list(steam_id=friend_item.steamid)

        if fetch_friends:
            logging.info("Scrapping Friends Gameplay Info.")
            for friend_item in tqdm(
                friend_list.friend_list, 
                desc="Scrapping Friends Gameplay", 
                total=len(friend_list.friend_list)):
                gameplay_info = steam_scrapper.scrap_gameplay_info(steam_id=friend_item.steamid)
                if gameplay_info is not None:
                    for gameplay_item in gameplay_info.gameplay_list:
                        game_info_set.add(gameplay_item.appid)
            game_info_set = game_info_set.difference(scrapped_game_info_ids_set)
            game_id_list_str = ",".join(list(game_info_set))
            logging.info("Scrapping Friends Game Info.")
            steam_scrapper.scrap_game_info(game_id_list_str)
    else:
        logging.info("Gameplay Info Empty. Skipping GameInfo, FriendsData, etc)")
    logging.info(f"Scrapping done! New information for Player {target_profile.persona_name} "+
                f"- Friends {len(friend_list.friend_list) if friend_list is not None else 0} "+
                f"- Game Info {len(game_info_set) + len(scrapped_game_info_ids_set)}")

def configure_logging():
    import sys
    logging.getLogger("pymongo").setLevel(logging.CRITICAL)
    logging.getLogger("backoff").setLevel(logging.CRITICAL)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

if __name__ == "__main__":
    configure_logging()
    steam_scrap()
