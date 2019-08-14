import sys
import unittest
#for dealing with windows & linux paths
import ntpath
from  config import Config 
from utils import strToArgs 

class ConfigTestCase(unittest.TestCase):
    
    def setUp(self):
        
        test_args='-s 3 -r 500 -g 50 -c config.json file.txt 2'
        argStr=strToArgs(test_args)
        self.config_short=Config('1.0',argStr)
        test_args='''
            --start 3
            --rate 500
            --games 50
            --config config.json           
            file.txt 2''' 
        argStr=strToArgs(test_args)
        self.config_long=Config('1.0',argStr)
        self.config_no_args=Config('1.0',strToArgs("file.txt 2"))


    def test_config_short(self):
        self.config_short.load()
        with_args_matching=[   
                3,
                0.5,
                50,
                'config.json',
                #True,
                'file.txt',
                2               
            ]
        with_args_short_results=[
                self.config_short.start_page,
                self.config_short.rate_limiter_minimum,
                self.config_short.games_per_xml_fetch,
                self.config_short.config_file,
                #self.config_short.suppress_warnings,
                self.config_short.csvfilename,
                self.config_short.pages_of_ids_to_fetch 
            ]
        self.assertEqual( with_args_short_results , with_args_matching )


    def test_config_long(self):
        self.config_long.load()
        with_args_matching=[   
                3,
                0.5,
                50,
                'config.json',
                #True,
                'file.txt',
                2               
            ]
        with_args_long_results=[
                self.config_long.start_page,
                self.config_long.rate_limiter_minimum,
                self.config_long.games_per_xml_fetch,
                self.config_long.config_file,
                #self.config_long.suppress_warnings,
                self.config_long.csvfilename,
                self.config_long.pages_of_ids_to_fetch 
            ]
        self.assertEqual( with_args_long_results , with_args_matching )

    def test_config_noargs(self):
        self.config_no_args.load()
        no_args_matching=[   
                1,
                0.6,
                100,
                'config.json',
                #True,
                'file.txt',
                2               
            ]
        no_args_results=[
                self.config_no_args.start_page,
                self.config_no_args.rate_limiter_minimum,
                self.config_no_args.games_per_xml_fetch,
                #windows compatible basename() func
                ntpath.basename(self.config_no_args.config_file),
                #self.config_no_args.suppress_warnings,
                self.config_no_args.csvfilename,
                self.config_no_args.pages_of_ids_to_fetch 
            ]
        self.assertEqual( no_args_results , no_args_matching )


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
