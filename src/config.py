import os
import re

import json

import argparse
from argparse import RawTextHelpFormatter

class Config:

    def _warning(self,s):
        if not self.config.suppress_warnings:
            print('##Warning## '+s)

    def _init_args(self, version, arg_str=None):
        #ARGS SETUP (see _load_args for assigments)    
        ap = argparse.ArgumentParser(argument_default=argparse.SUPPRESS, formatter_class=RawTextHelpFormatter,
            description='''
            Fetch and dump boardgamegeek.com xmlapi2 boardgame data in to a csv file.
            All data is preserved via long column names.
            Fetches games in geek-rating order up to maximum pages you specify.
            Pages are as found on https://boardgamegeek.com/browse/boardgame.
            100 games per page. To fetch top 200 games specify 2 pages.
            BGG rate-limits to 2 api calls per second (the utility rate-limits itself). 
            Minimum time to download 5000 games is 8mins 20secs. 
            For advanced options see config.json 
            Settings in config.json are overriden by commandline args. 
            [requires python3. Developed and tested on linux/python 3.7.4]

            example for 5000 games : c:\\>python3 scrape.py -s 3 test.csv 50

            ''',
            epilog="*denotes settings that only need changing if BGG changes.")
        ap.add_argument('-v', '--version', action='version', version='%(prog)s '+version)
        ap.add_argument('csvfilename', help="destination")
        ap.add_argument('pages',type=int,help="number of pages to scrape (100 games per page)")
        ap.add_argument('-s', '--start', type=int, help="Start page, default 1", default=None)
        ap.add_argument('-r', '--rate', type=int, help="*rate limiting, millisecs per call. Default 600", default=None )
        ap.add_argument('-g', '--games', type=int, help="*How many games to fetch xml for at a time. Default 100.", default=None)
        ap.add_argument('-c', '--config', help="*full path to a config.json", default=None)
        ap.add_argument('-u', '--base_url', help="*base url of bgg", default=None)
        ap.add_argument('-p', '--html_path', help="*path to bgg pages", default=None)
        ap.add_argument('-x', '--xml_path', help="*path to bgg api", default=None)
        ap.add_argument('-d', '--debug', help="*for debugging", default=False)
        
        
        
        #ap.add_argument('-w', '--suppress_warnings', action='store_true', help="suppress warnings", default= False )
        args=ap.parse_args(arg_str)
        #self.suppress_warnings=args.suppress_warnings
        return args


    def __init__(self, version, arg_str=None):
    #version is for matching config.json structure check. 

        self.version=version

        
        self._args=self._init_args(version,arg_str)

        #config.json isn't optional, so ensure we have one
        if self._args.config:
            self.config_file=self._args.config
        else:
            #get the local config.json file
            path=os.path.dirname(os.path.realpath(__file__))
            self.config_file=os.path.join(path,'config.json')

        self.csvfilename=self._args.csvfilename
        self.start_page=None
        
        self.aggregates_regexes=None
        self.force_value_into_fieldname_regexes=None
        self.new_col_names={}
        self.rate_limiter_minimum=None      
        self.games_per_xml_fetch=None
        self.base_url=None
        self.html_path=None
        self.xml_path=None
        self.debug=False
        #security, to neuter spreadsheet formulas if BGG were hacked
        self.option_strip_formula_equal_sign_for_csv=None
        self.games_per_xml_fetch=None

        self.suppress_warnings=False


    def _load_json(self,version, args, filestr):
        #read config.json
        
        with open(self.config_file) as json_file:
            config = json.load(json_file)
            if config["version"]!=version:
                raise Exception("config.json version 1.0 required.")
            
            #FROM CONFIG.JSON
            self.rate_limiter_minimum=float(config["rate"])/1000        
            self.games_per_xml_fetch=config["games_per_xml_fetch"]
            self.start_page=config["start_page"]
            self.base_url=config["base_url"]
            self.xml_path=config["xml_path"]
            self.html_path=config["html_path"]
            
            
            #security, to neuter spreadsheet forumulas if BGG were hacked
            self.option_strip_formula_equal_sign_for_csv=\
                config["strip_formula_equal_sign_for_csv"]

            # Attribute Aggregation: 
            # 
            # To handle a BGG xml quirk. 
            # At least one tag includes unique id numbers, 
            # and since we build up column names using 
            # attributes as well as tags
            # this can result in an explosion of
            # redundant columns with unique ids. 
            # So instead of including them in the
            # column name as normal we aggregate 
            # the attributes and put them in to the data value. 
            # (Non-unique ids are processed normally.)
            # We match on the colum name; see regex below. 
            # On a match all attributes from that 
            # point on, but not before, in the
            # tag are aggregated as a single data 
            # value. 
            # (Prior attributes are processed 
            # normally: added to the column name.)
            # Seperators are used to distinguish 
            # each part and appended to any existing 
            # data already added to that column/field value.

            # using raw strings as these are going 
            # to be used in a regular expression match
            # key is just a label, but also means config.json can
            # easily replace these defaults if desired by the user

            #but first, func to aid inserting 
            # config regex data in to dicts
            # dict of compiled regexes keyed by strings
            def fill_string_dict_of_regex(config,target_dict,config_key):
                try:
                    conf_dict=config[config_key] #dict
                    for key in conf_dict:
                        # (python needs quad escaping)
                        regex_str=(conf_dict[key]).replace('\\','\\\\') 
                        target_dict[key]=re.compile(regex_str)
                except Exception as e:
                    raise Exception(f"Structure of config.json for section \
                        {config_key}? Details: "+ str(e))

            #dict of string keyed with compiled regexes
            def fill_regex_dict_of_string(config,target_dict,config_key):
                try:
                    conf_dict=config[config_key] #dict
                    for key in conf_dict:
                        # (python needs quad escaping)
                        regex_str=key.replace('\\','\\\\')
                        regex=re.compile(regex_str)
                        target_dict[regex]=conf_dict[key]
                except Exception as e:
                    raise Exception(f"Structure of config.json for section \
                        {config_key}? Details: "+ str(e))
           


            
            fill_regex_dict_of_string(
                config,
                self.new_col_names,
                "col_names")

            # regexes to match columns for agregating 
            # (the key is not strictly needed, 
            # but useful for config.json and as documentation)
            self.aggregates_regexes={
                "item-link-type": 
                    re.compile(r'/item/link:type=[a-z]{1,}')
            }
            # then also load the regexes from 
            # the config file, potentially
            # replacing defaults, above, 
            # if the key name is the same
            fill_string_dict_of_regex(
                config,
                self.aggregates_regexes,
                "aggregates_regexes")

            self.force_value_into_fieldname_regexes={
                "item-poll-numplayers" : 
                    re.compile(r'/item/poll.{1,}/results:numplayers$')
            }
            fill_string_dict_of_regex(
                config,
                self.force_value_into_fieldname_regexes,
                "force_value_into_fieldname_regexes")

        


    def _load_args(self,args):
        self.csvfilename=args.csvfilename
        if args.start: self.start_page=args.start
        self.pages_of_ids_to_fetch=args.pages
        if args.rate: self.rate_limiter_minimum=args.rate/1000        
        if args.games: self.games_per_xml_fetch=args.games
        if args.base_url : self.base_url=args.base_url
        if args.html_path : self.html_path=args.html_path
        if args.xml_path : self.xml_path=args.xml_path
        if args.debug: self.debug=True
        
        #ap.add_argument('-x' '--xml_path', help="*path to bgg api", default=None)

    def _check_n_warn(self):
        #check values and issue warnings
        if self.rate_limiter_minimum<0.500:
            _warning("time between fetches is less\
                than 500millisecs and may exceed BGG rate limits.")
        if self.games_per_xml_fetch<100:
            _warning("ids_per_fetch is less than 50 and may\
                be unnecesarily slow.")
        if self.games_per_xml_fetch>100:
            _warning("BGG supported a maximum of 100 'thing' items at a time.")
        

    def load(self):

        try:            
            self._load_json(self.version, self._args, self.config_file)
            self._load_args(self._args)
            #self._check_n_warn();
            
        except Exception as e:
            raise Exception('option arguments or config.json. \
                See readme.txt. '+str(e))
    