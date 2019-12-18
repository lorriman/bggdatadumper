import sys
import unittest
#for dealing with windows & linux paths
import ntpath
import subprocess

from  config import Config 
from bs4 import BeautifulSoup as bs
from bs4 import element

from bggdatadumper import BGGdumper
from utils import check_host , str_to_argv

#quick and dirty unit tests. Must revisit.
#also need to monkey patch to mock out the need for a webserver.
#Only process_item_element_recursively() is put through significant
#testing, as it does the main work

class DumperTestCase(unittest.TestCase):
    
    

    def setUp(self):

        if not check_host('localhost',8000):
            raise Exception('Webserver for test data not running. Run "python3 -m http.server" in project directory')

        sys.argv=str_to_argv("placeholder.csv 2")

        self.dmpr=BGGdumper()
        d=self.dmpr
        d.load_config();
        d.config.base_url='http://localhost:8000/'
        d.config.html_path='test_data/test_scrape1.html?id={page}'
        d.config.xml_path='test_data/test_apidata.xml'

    def tearDown(self):
        pass



  
    def test_scrapeGamePage(self):
        self.dmpr.scrape_to_get_ids()
        #first 3 game ids on page 2
        self.assertTrue( set(['194655','14996','43111'])==set(self.dmpr._game_ids) )
        #self.dmpr.fetch_xml()
        
    def test_process_item_element_recursively(self):
        
        #utility funcs
        def reset():
            self._cols={}
            self._item={}
            self._items=[]
            self._colname=''
        def strToXml(s,root):
            xml=bs(s,'lxml');
            return xml.find(root)
        def process(frag,root):
            reset()
            xml=strToXml(frag,root)
            self.dmpr.process_item_element_recursively(self._cols,self._item,self._colname,xml)
            self._colname=list(self._cols)[-1]
        def colnameReport() -> str:
            return self._colname+" derives incorrectly from "+frag
    
            
        reset()

        frag='''<test>test</test>'''
        xml=process(frag,'test')
        self.assertTrue('/test'==self._colname,colnameReport())
        self.assertEqual(self._item['/test'],"test")


        frag='''<test id="1"></test>'''
        process(frag,'test')
        self.assertTrue('/test:id:'==self._colname,colnameReport())
        self.assertEqual(self._item['/test:id:'],'1')

        frag='''<test >
                    <test1 name="board" id="1"/>
                </test>'''
        process(frag,'test')
        self.assertTrue('/test/test1:name=board::id:'==self._colname,colnameReport() )
        self.assertEqual(self._item['/test/test1:name=board::id:'],'1')
        
        ##aggregation test
        frag='''<unittest>
                    <unittest1 name="board" id="1" text="string" number="zero"/>
                </unittest>'''
        process(frag,'unittest')
        self.assertTrue('/unittest/unittest1:name=board:'==self._colname,colnameReport())
        self.assertEqual(self._item['/unittest/unittest1:name=board:'],'id=1,text=string,number=zero')

        #force_value_into_fieldname test
        frag='''<unittest>
                    <unittest1 number="1"><pollvalue value="1"/></unittest1>
                </unittest>'''
        process(frag,'unittest')
        self.assertTrue('/unittest/unittest1:number=1:/pollvalue:value:'==self._colname,colnameReport())
        self.assertEqual(self._item['/unittest/unittest1:number=1:/pollvalue:value:'],'1')


        
if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

