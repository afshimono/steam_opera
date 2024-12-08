import click
import datetime as dt
import logging
from typing import Optional

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


def calculate_gameplay_delta(
    current_gameplay: GameplayItem, previous_gameplay: GameplayItem, current_time: Optional[dt.datetime] = None
) -> GameplayMonthDeltaList:
    if not current_time:
        current_time = dt.datetime.now()
    previous_gameplay_dict = {item.appid: item for item in previous_gameplay.gameplay_list}
    gameplay_delta_items = []

    for gameplay_item in current_gameplay.gameplay_list:
        previous_playtime = previous_gameplay_dict.get(
            gameplay_item.appid, GameplayMonthDeltaItem(appid="", playtime=0)
        ).playtime
        delta = gameplay_item.playtime - previous_playtime
        if delta > 0:
            gameplay_delta_items.append(GameplayMonthDeltaItem(appid=gameplay_item.appid, playtime=delta))

    total_gameplay = sum(item.playtime for item in gameplay_delta_items)
    return GameplayMonthDeltaList(
        steamid=current_gameplay.steamid,
        gameplay_delta_list=gameplay_delta_items,
        total_playtime=total_gameplay,
        created_year=current_gameplay.created_year,
        created_month=current_gameplay.created_month,
        created_at=dt.datetime.now(),
        updated_at=dt.datetime.now(),
    )


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
        items_to_save = [
            calculate_gameplay_delta(current, previous_month_gameplay_dict[current.steamid], current_time=current_time)
            for current in current_items
            if current.steamid in previous_month_gameplay_dict
        ]
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
