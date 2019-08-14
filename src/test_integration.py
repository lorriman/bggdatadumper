import sys
import unittest

#for dealing with windows & linux paths
import ntpath
import subprocess

from bggdatadumper import BGGdumper
from utils import checkHost , strToArgv , sha1sum

#simple integration test.
#also need to monkey patch to mock out the need for a webserver.

class IntegrationTestCase(unittest.TestCase):
    
    def setUp(self):

        if not checkHost('localhost',8000):
            raise Exception('Webserver for test data not running. Run "python3 -m http.server" in project directory')

        sys.argv=strToArgv("test.csv 1")

        self.dmpr=BGGdumper()
        d=self.dmpr
        d.config.base_url='http://localhost:8000/'
        d.config.html_path='test_data/test_scrape1.html?id={page}'
        d.config.xml_path='test_data/test_apidata.xml'

    def tearDown(self):
        pass
  
    def test_integration(self):
        self.dmpr.scrapeGamePage()
        self.dmpr.fetch_xml()
        self.dmpr.output()

        digest=sha1sum('test.csv')
        self.assertEqual(digest,"91d66d2bc160f0095414f8ad3f4e5ddb13cecfc5", "sha1 checksum for test.csv does not match expected")
    

        
if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
        
        