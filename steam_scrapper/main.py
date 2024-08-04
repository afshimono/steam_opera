import click
import datetime as dt
import logging

from tqdm import tqdm

from repos.mongo_repo import SteamMongo
from config import config
from scrapper import SteamScrapper

@click.command()
@click.argument("player_ids", type=str)
@click.argument("steam_key", envvar="STEAM_KEY", type=str)
@click.option("--mongo_db_url", envvar="MONGO_DB_URL", type=str)
@click.option("--output", default="mongo")
@click.option("--frequency", default="month")
@click.option("--fetch_friends/--dont_fetch_friends", default=False)
def steam_scrap(player_ids,steam_key, mongo_db_url, output,frequency,fetch_friends):
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
    
    logging.info(f"Scrapping for Player ID(s) {player_ids}")
    
    steam_scrapper = SteamScrapper(
        repo = repo, 
        frequency = frequency)
    player_id_list = player_ids.split(",")
    for idx, player_id in enumerate(player_id_list):
        logging.info(f"Scrapping user {idx+1} out of {len(player_id_list)}")
        steam_scrapper.scrap_all_user_data(
            player_id=player_id,
            fetch_friends=fetch_friends)
    

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
