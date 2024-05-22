import click


@click.command()
@click.argument("steam_key", envvar="STEAM_KEY", type=str)
@click.argument("mongo_db_url", envvar="MONGO_DB_URL", type=str)
@click.argument("player_id", envvar="PLAYER_ID", type=str)
@click.option("--fetch_friends", default=False)
def steam_scrap(steam_key, mongo_db_url, fetch_friends):
    # sets time values
    current_time = dt.datetime.now()
    year_month_day_str = f"{current_time.year}-{current_time.month}-{current_time.day}"
    print(f"Year-Month-Day = {year_month_day_str}")

    # connects to DB
    mongo_client = MongoClient(mongo_db_url)


if __name__ == "__main__":
    steam_scrap()
