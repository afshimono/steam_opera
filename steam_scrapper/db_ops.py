import click
import datetime as dt
import logging

from tqdm import tqdm

from repos.mongo_repo import SteamMongo
from config import config
from scrapper import SteamScrapper
from models import GameplayMonthDeltaItem, GameplayItem, GameplayMonthDeltaList

CREATE_BATCH_SIZE = 200


@click.command()
@click.option("--delete_type", type=str)
@click.option("--create_type", type=str)
@click.option("--created_month", type=int)
@click.option("--created_year", type=int)
def db_ops(delete_type, create_type, created_month, created_year):
    repo = None

    logging.info("Connecting to Mongo DB...")
    if config.mongodb_url is None:
        raise ValueError("Missing MongoDB URL Env Variable.")
    repo = SteamMongo(mongo_url=config.mongodb_url)
    logging.info("Connected.")

    if delete_type is not None:
        delete_by_type(delete_type, repo, created_month, created_year)
    elif create_type is not None:
        create_by_type(create_type, repo, created_month, created_year)


def delete_by_type(delete_type, repo, created_month, created_year):
    if delete_type == "friend_list":
        repo.delete_friend_list(created_month=created_month, created_year=created_year)
    elif delete_type == "gameplay_info":
        repo.delete_gameplay_info(created_month=created_month, created_year=created_year)


def create_by_type(create_type, repo, created_month, created_year):
    if create_type == "gameplay_delta":
        create_gameplay_delta(repo=repo, created_month=created_month, created_year=created_year)


def create_gameplay_delta(repo, created_month, created_year):
    current_time = dt.datetime.now()
    existing_gameplay_list = repo.get_gameplay_info_by_id(created_year=created_year, created_month=created_month)
    for batch_start in tqdm(range(0, len(existing_gameplay_list), CREATE_BATCH_SIZE)):
        current_items = existing_gameplay_list[batch_start : batch_start + CREATE_BATCH_SIZE]
        current_items_ids = [item.steamid for item in current_items]
        previous_month = (created_month - 1) if created_month > 1 else 12
        previous_year = created_year if previous_month != 12 else (created_year - 1)
        previous_month_gameplay_list = repo.get_gameplay_info_by_id_list(
            player_id_list=current_items_ids, created_year=previous_year, created_month=previous_month
        )
        previous_month_gameplay_dict = {item.steamid: item for item in previous_month_gameplay_list}
        items_to_save = []
        for current_gameplay in current_items:
            if previous_gameplay := previous_month_gameplay_dict.get(current_gameplay.steamid):
                previous_gameplay_item_dict = {item.appid: item for item in previous_gameplay.gameplay_list}
                gameplay_delta_item_list = []
                for gameplay_item in current_gameplay.gameplay_list:
                    empty_gameplay_item = GameplayMonthDeltaItem(appid="", playtime=0)
                    previous_playtime = previous_gameplay_item_dict.get(
                        gameplay_item.appid, empty_gameplay_item
                    ).playtime
                    calulated_gameplay_time = gameplay_item.playtime - previous_playtime
                    if calulated_gameplay_time > 0:
                        gameplay_delta_item_list.append(
                            GameplayMonthDeltaItem(
                                appid=gameplay_item.appid,
                                playtime=calulated_gameplay_time,
                            )
                        )
                total_gameplay = sum([item.playtime for item in gameplay_delta_item_list])
                items_to_save.append(
                    GameplayMonthDeltaList(
                        steamid=current_gameplay.steamid,
                        gameplay_delta_list=gameplay_delta_item_list,
                        total_playtime=total_gameplay,
                        created_year=current_gameplay.created_year,
                        created_month=current_gameplay.created_month,
                        created_at=current_time,
                        updated_at=current_time,
                    )
                )
        repo.save_gameplay_delta_info_list(gameplay_delta_info_list=items_to_save)


def configure_logging():
    import sys

    logging.getLogger("pymongo").setLevel(logging.CRITICAL)
    logging.getLogger("backoff").setLevel(logging.CRITICAL)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)


if __name__ == "__main__":
    configure_logging()
    db_ops()
