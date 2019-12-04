version="0.1beta"
config_version='1.0'

#(update: make imports specific)
import csv
import re
import json
import sys
import os

#our own stuff
from utils import init, isDebugging, RateLimiter 
from config import Config

import urllib.request
from progress import progress

from bs4 import BeautifulSoup as bs
from bs4 import element


if(sys.version[0]!='3'):
    raise Exception('Python 3 required. Found python '+sys.version+'\n')

init();

# using a class for convenient structuring, not genericity or re-use
class BGGdumper:  
    '''main class for processing code.
    Exludes configuration code, see config.py/Config class.
    '''



    def __init__(self):

        self._suppress_warnings=False
        self.config=Config(config_version)
        self.config.load()
        self._rate_limiter=RateLimiter(self.config.rate_limiter_minimum)

        self._game_ids=[]
        self._csv_cols={}
        self._csv_items=[]
    
    def _warning(self,s):
        if not self.config.suppress_warnings:
            print('##Warning## '+s)

    def scrapeGamePage(self):    
        #localise a few objects for convenient access    
        config=self.config
        game_ids=self._game_ids
        csv_cols=self._csv_cols
        csv_items=self._csv_items

        ##regular expression to extract the id from the html link        
        id_regex=re.compile(r"/(?P<id>\d+)/")
        start_page=config.start_page
        pages_to_fetch=config.pages_of_ids_to_fetch

        progress_str="Scraping boardgame pages"
        progress(0,pages_to_fetch,progress_str)
        
        for page_num in range(start_page,start_page+pages_to_fetch):        
            progress(page_num-start_page,pages_to_fetch,progress_str)
            url=config.base_url+config.html_path.format(page=page_num)
           
            
            self._rate_limiter.limit()
            page=urllib.request.urlopen(url)
            soup=bs(page,'lxml')

            #collect game ids from the main BGG pages (not xml)
            table = soup.find( 'table', {'class':'collection_table'})
            game_cells=table.find_all('td',{'class': 'collection_objectname'})

            links = []
            for cell in game_cells:
                links.append(cell.a['href'])
            for link in links:
                m=id_regex.search(link)
                if not m:
                    _warning("id not found in href for "+link+" in "+url)
                else:
                    game_ids.append(m.group('id'))
        progress(pages_to_fetch,pages_to_fetch,progress_str)


    def process_item_element_recursively( self ,csv_cols,csv_item,col_name,xml) -> str:
        '''Process subitems of item tags (individual games/items)
        Returns the built up col_name for unit testing purposes
        Most of the main xml processing occurs here. 
        '''

        config=self.config

        tagname=xml.name

        # 'None' mens dead whitespace '\n' etc; 
        # nothing to do and no children so bug out
        if tagname==None:         
            return
        
        col_name=col_name+'/'+tagname    

        tagHasString=xml.string!=None

        data_value=''

        if tagHasString:
            data_value=xml.string.strip()
        
        #is it a leaf node? spelled out for doc purposes
        #this isn't currently used in the code
        temp=xml.findChildren()
        if(len(temp)==0):
            isLeaf=True
        else:
            isLeaf=False

        attrs=xml.attrs 
        agg_reg=list(config.aggregates_regexes.values())
        force_val_reg=list(config.force_value_into_fieldname_regexes.values())
        #if has attributes
        if len(attrs)>0:
            # get list of attribute keys - attrs is
            # a dict - in insertion order
            attr_keys=list(attrs)

            # loop through ech attribute one by one
            # the last attribute will be treated as 
            # data value (unless tagHasString, which 
            # will be the data value instead)
            last_item_index=len(attr_keys)-1 
            aggregating=False
            for a in range(0,len(attr_keys)):
                k=attr_keys[a]
                v=attrs[k]

                # Aggregation? Instead of only the last attribute,
                # attributes and values aggregated
                # together and inserted into the field value 
                # instead of making up a colum name.
                # The new colum name hasn't been
                # set yet, which is wy we have +k
                # this test is for the attribute name,
                # later we repeat but in order to 
                # test for attribute value as well
                for r in range(0,len(agg_reg)):
                    if agg_reg[r].match(col_name+':'+k):
                        aggregating=True 

                
                #attribute label and value appended to the data value
                if aggregating:
                    data_value+=k+'='+v+','
                
                elif a==last_item_index and not tagHasString:
                    # attribute name goes in the col_name, 
                    # and value in to the field value
                    col_name+=':'+k                    
                    #the value of the last item is 
                    #not included in the fieldname, unless...                
                    for r in force_val_reg:
                        if r.match(col_name):
                            col_name+='='+v
                            #blank the data value
                            v=''
                    data_value+=v
                    col_name+=':'
                            
                
                #attribute becomes part of the field/column name
                elif not aggregating:
                    # not a data item, so put the 
                    # attribute's name AND value in col_name 
                    col_name+=':'+k+'='+v+':'

                #check for aggregation again, 
                # this time with the attribute value 
                # included in the column name
                # Does the new column name match 
                # with aggregation strings?
                for r in range(0,len(agg_reg)):
                    if agg_reg[r].match(col_name):
                        aggregating=True 

        if data_value!='':   
            #strip any trailing commas from aggregating
            data_value=data_value.strip(',')     
            if col_name in csv_item: # already data? then append
                s=csv_item[col_name]
                csv_item[col_name]=s+','+data_value
            else:
                csv_item[col_name]=data_value
            #save the column identifier
            csv_cols[col_name]=col_name

        for child in xml.children:
            ret=self.process_item_element_recursively(
                csv_cols,
                csv_item,
                col_name,
                child)


    def fetch_xml(self):  
        config=self.config
        game_ids=self._game_ids
        csv_cols=self._csv_cols
        csv_items=self._csv_items  

        progress_str="api queries: xml data for "+str(len(game_ids))+' games.'
        progress_counter=0;
        progress(0,len(game_ids),progress_str)

        url=config.base_url+config.xml_path
       
        
        #just trying out generators. The result is a bit clunky.
        # Also I'm certain it's a python crime to 
        # yield a terminating value. #revisit
        def id_generator(ids):
            n=0
            l=len(ids)
            while n<l:
                yield ids[n]
                n+=1
            # terminating value because I'm abusing
            # generators to try them out. #bad #shame #disappointedinmyself
            yield -1
        
        if config.debug:
            config.games_per_xml_fetch=1
            game_ids=['1','2']

        more=True
        id_gen=id_generator(game_ids)


        while more:
            working_url=url
            #print('passing')
            
            id_batch=[]
            for i in range(0,config.games_per_xml_fetch):
                id=next(id_gen)
                if id!=-1:
                    id_batch.append(id)
                else:#Klunk, gah!
                    more=False
                    break

            #print(id_batch)
            #print(len(id_batch))
            if len(id_batch)==0:
                break
            id_str=''
            for id in id_batch:
                id_str+=id+','
            #remove terminating comma
            id_str=id_str.strip(',')
            
            #if not config.debug:
            working_url=working_url.format(ids=id_str)

            self._rate_limiter.limit()
            xmlresponse=urllib.request.urlopen(working_url)
            xml=bs(xmlresponse,"lxml")     
        
            xml_items=xml.find_all('item')
            for xml_item in xml_items:
                # the first tag 'item' needs special treatment 
                # so is not processed by the recursive function
                # as otherwise we end up with multiple superfluous 
                # columns derived from the 'type'  
                csv_item={}
                col_name="/item"
                cn=col_name+':type'
                csv_cols[cn]=cn
                csv_item[cn]=xml_item.attrs['type']
                cn=col_name+':id'
                csv_cols[cn]=cn
                csv_item[cn]=xml_item.attrs['id']
                for child in xml_item.children:
                    self.process_item_element_recursively(
                        csv_cols,
                        csv_item,
                        col_name,
                        child)
                #check for dodgy values that might be spreadsheet formulas
                if config.option_strip_formula_equal_sign_for_csv:
                    for k in csv_item:
                        s=csv_item[k]
                        if len(s)==1:
                            if s[0]=='=':
                                csv_item[k]=s.strip('=')

                #now we have all the data, add the row
                csv_items.append(csv_item)
            progress_counter+=len(xml_items)
            progress(progress_counter,len(game_ids),progress_str)

    def rewrite_column_names(self):
        ''' Rewrite the auto-generated column names, which are mostly
        unreadable, can be renamed by setting regular 
        expressions in config.json->new_col_names. 
        This funtion defines two nested functions and 
        calls those at the end, see about 70 lines down.

        We use regexes instead of straight strings for comparison
        because many column names are similar and also because
        there are an indeterminate number of 'vote' columns but they
        follow the same pattern. Using regex 'groups' we can extract
        unique parts of the original columm names to aid constructing 
        the new column names. Groups are denoted by brackets (see config.json).
        '''
        new_col_names_lookup={}

        #create a hash lookup from the regexes in config.json
        #ready to do fast lookups when we go through the data.
        def make_new_col_names_lookup():

            for old_col_name in self._csv_cols:
                match=None
                #config.new_col_names is indexed by compiled regular expressions (this is legal)
                for new_name_regex in self.config.new_col_names:
                    new_name=self.config.new_col_names[new_name_regex]
                    #use the regular expression to see if we should rewrite the column name
                    match=new_name_regex.search(old_col_name);
                    if match:
                        # the regular expression can extract data from the 
                        # column name using regular expression 'groups'
                        dynamic_params=match.groups()
                        # *expands the list to arguments, to format 
                        # the string, using values from the 
                        # regex groups in to the new colum name.
                        # This is because some column names are
                        # almost the same only varying  
                        # by a number, like votes_best_numplayers_1,
                        # and so can be rewritten using just one 
                        # regular expression (with grouping to get 
                        # the number), and why we are using 
                        # regular expressions instead of straight strings.
                        new_name=new_name.format(*dynamic_params)
                        break
                lookup_key=old_col_name
                if match:
                    new_col_names_lookup[lookup_key]=new_name
                else:
                    new_col_names_lookup[lookup_key]=old_col_name

        #go through the data re-writing the column names.            
        def rewrite():
            
            #first do the columns hash, which is used for the csv header
            #this is a straight replacement. 
            self._csv_cols={} #blank it
            for cn in list(new_col_names_lookup.values()):
                self._csv_cols[cn]=cn
            
            #now do the actual data using the old column name to 
            # fetch the new one from the hash lookup
            new_items=[]
            for item in self._csv_items:
                new_item={}
                for old_col_name in item:
                    new_item[new_col_names_lookup[old_col_name]]=item[old_col_name]
                new_items.append(new_item)

            #finally, replace the old data    
            self._csv_items=new_items

        make_new_col_names_lookup()
        rewrite()
        

    #sort the csv cols after name
    #split etc
    def output(self):
        progress_str='writing csv'
        progress(0,len(self._csv_items),progress_str)
        with open(self.config.csvfilename, 'w', newline='') as csvfile:
            fieldnames = list(self._csv_cols)
            writer = csv.DictWriter(
                csvfile,
                fieldnames=fieldnames
            )
            writer.writeheader()
            c=0;
            for item in self._csv_items:
                writer.writerow(item)
                c+=1
                progress(c,len(self._csv_items),progress_str)
            print('\n')
        print('limiting: '+str(self._rate_limiter.count()))

#try

if __name__ == '__main__':
    bd=BGGdumper()
    bd.scrapeGamePage()
    bd.fetch_xml()
    bd.rewrite_column_names()
    bd.output()

'''
except Exception as e:
    sys.stderr.write('Error: '+str(e)+'\n')
    #sys.exit uses an exception, which we don't want when debugging
    if not isDebugging():
        sys.exit(1)
'''
