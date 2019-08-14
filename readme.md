# bggdatadumper
Dumps boardgame data from boardgamegeek, via the public xml api, in to a csv file

##intro

bggdatadumper dumps boardgamegeek boardgame xml in to a fairly raw form
directly in to a csv file ready to be manipulated by Excel or any
spreadsheet. The dump preserves as all of the original data in the
xml from the BGG xml api by generically traversing the tags and 
attributes converting them in to long very column names.

##future updates

In future a facility will be provided to direct the dumper to
convert column names in to a format of your choice as the 
long column names are not in a convenient form.

##requirements and usage

It has been developed and tested only on Linux. It requires python 3.7

For usage run from the commandline as

'''   python3 -m bggdatadumper -h'''

It uses a few libraries which can be installed as follows:

'''python3 -m install''' 
