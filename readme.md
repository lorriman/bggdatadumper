# bggdatadumper
Dumps boardgame data from boardgamegeek, via the public xml api, in to a csv file

##intro

bggdatadumper dumps boardgamegeek boardgame xml in to a fairly raw form
directly to a csv file ready to be manipulated by Excel or any
spreadsheet. The dump preserves all of the original data in the
xml from the BGG xml api by generically traversing the tags and 
attributes converting them in to long very column names. It works
with BGG xml quirks and is not generically usable for any XML.

##future updates

In future a facility will be provided to direct the dumper to
convert column names in to a format of your choice as the 
long column names are not in a convenient form.

Currently it only handles boardgame data. A future version
will handle other bgg data, such as collections, forums posts etc.

##requirements and usage

It has been developed and tested only on Linux. It requires python 3.7

It uses a few libraries which can be installed as follows:

'''python3 -m install''' 

For usage run from the commandline as

'''   python3 -m bggdatadumper -h'''

Fetches games in geek-rating order up to maximum pages you specify.
Pages are as found on https://boardgamegeek.com/browse/boardgame.
100 games per page. To fetch top 200 games specify 2 pages.
BGG rate-limits to 2 api calls per second (the utility rate-limits itself). 
Minimum time to download 5000 games is 8mins 20secs. 
For advanced options see config.json 
Settings in config.json are overriden by commandline args. 

example for 5000 games (assuming it works on windows) :
            
c:\>python3 scrape.py -s 3 test.csv 50

            

positional arguments:

csvfilename           destination

pages                 number of pages to scrape (100 games per page)

optional arguments:

-h, --help            show this help message and exit

-v, --version         show program's version number and exit

-s START, --start START

Start page, default 1

-r RATE, --rate RATE  *rate limiting, millisecs per call. Default 600

-g GAMES, --games GAMES

*How many games to fetch xml for at a time. Default 100.

-c CONFIG, --config CONFIG

*full path to a config.json

