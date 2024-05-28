import click

from repos.mongo_repo import SteamMongo
import steam_api

@click.command()
@click.argument("steam_key", envvar="STEAM_KEY", type=str)
@click.argument("mongo_db_url", envvar="MONGO_DB_URL", type=str)
@click.argument("player_id", envvar="PLAYER_ID", type=str)
@click.option("--db", default="mongo")
@click.option("--fetch_friends", default=False)
def steam_scrap(steam_key, mongo_db_url,player_id, db, fetch_friends):
    # gets repo
    if db == "mongo":
        repo = SteamMongo()
    # fetch user if it exists:
    current_user_profile = steam_api.fetch_player_info(player_id)
    current_user_profile_in_db = repo.get_player_info_by_id_list([player_id])
    if len(current_user_profile_in_db) < 1:
        print(current_user_profile)
        repo.save_player_info_list(current_user_profile)

if __name__ == "__main__":
    steam_scrap()
