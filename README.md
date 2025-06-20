# Steam Opera

A tool to fetch data and generate stories/reports based on public steam profile data.

### Steam API Key and the Steam Profile ID

Those are needed to fetch information in some API endpoints.
The API Key can be requested in this link: https://steamcommunity.com/dev/apikey
To find your Steam Profile ID, you can use a online tutorial such as this one: https://support.nexon.net/hc/en-us/articles/360001118286-How-do-I-find-my-Steam-ID-

### Postman

There is a postman collection in the `/postman` folder with the most used Steam API Endpoints.
You will need to configure the variables for `STEAM_KEY` and `STEAM_PROFILE_ID` with the values obtained in the previous steps.

### Python Dependencies

As always, create a `venv` ( for example, `python3 -m venv venv` which will create a `venv` folder for it, and activate it with `source venv/bin/activate` in Linux ),
install the depencies with `pip install -r notebooks/requirements.txt` for the notebooks.

Finally, just run `jupyter notebook` to start the server and access the link displayed in the terminal.

### Jupyter Notebooks

We have an experimental notebook to see what sort of data can be generated from the APIs.
Currently it is generating reports based only in the all-time player gameplay.

It uses TinyDB to save information about games, players and gameplay in the `db.json` file.
The repo already has some game data saved to it, so this is why the file already has around 20 Mb.

It will save and retrieve data for the current month, so if you keep running this in your machine once a month, you should be able to
calculate the monthly gameplay time by subtracting the gameplay of each month. But this would be a next step in the analysis, which will not
be covered by the Notebook. I plan implement the library to populate a MongoDB instance with data and have the script to fetch data run every
first day of the month on a regular basis.

The description of what each graph represents can be found in the Notebook itself, as a text/content block instead of code.

There are some ENV variables that can be configured for the notebooks, which are available in the `sample.env` file. Those are:

```
STEAM_KEY => The Steam Key
PLAYER_ID => Your Steam Player ID
RUN_FRIENDS_STATS => This will run the Notebook part that generates some graphs comparing your data with you friends. Since fetching data for all your friend list might be an expensive operation, you can switch it off if you are just running a simple test here.
CLEAN_USER_DB => This is used to remove all the data from the users from your TinyDB, in case you want to push to your repo without player_ids.
CLEAN_GAMEPLAY_DB =>  The same thing for gameplay info.
```

Converting a notebook to html:
```
jupyter nbconvert notebooks/<NOTEBOOK_NAME>.ipynb --no-input --no-prompt --to html --output <STEAM_ID>
```

Sample to run and save in command line:
```
export $(grep -v '^#' .env | xargs) && export PLAYER_ID=<ID> && jupyter nbconvert --to notebook --inplace --execute notebooks/SteamProfileOperaPlotlyMongoDB.ipynb && jupyter nbconvert notebooks/SteamProfileOperaPlotlyMongoDB.ipynb --no-input --no-prompt --to html --output $PLAYER_ID
```

### Library

Work In Progress

### TO-DO by Devs

-   [x] Experimental Notebook to generate reports with all-time gameplay
-   [x] Save results to TinyDB to avoid Steam API consumption
-   [x] README Notebook Section
-   [ ] Makefile
-   [x] Steam API
-   [x] Steam Scrapper
-   [ ] Tests
-   [ ] Pipelines
-   [ ] README Lib Section

### TO-DO by Users

-   [x] Top 10 Game by Playtime
-   [x] Playtime by Genre
-   [x] Game count by Genre
-   [ ] Check how many friends are available for the report
-   [x] Show names of the games by developer
-   [x] Show names of friends in the top played games
-   [ ] Show how many games were not available
-   [ ] Include Steam Reviews data as another source of game quality besides metacritic
-   [ ] Check if the number of friends and friends DF contains duplicates
