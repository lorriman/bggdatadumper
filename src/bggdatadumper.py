version="0.2beta"
config_version='1.0'

#(update: make imports specific)
import csv
import re
import json
import sys
import os

#our own stuff
from utils import init, is_debugging, RateLimiter 
from config import Config

import urllib.request
from progress import progress_bar

from bs4 import BeautifulSoup as bs
from bs4 import element


if(sys.version_info < (3, 7)):
    raise Exception('Python 3.7+ required. Found python '+sys.version+'\n')

class Error(Exception):
    pass

class InsecureDataError(Error):
    '''Used to raise an exception if the xml or html has security violations, such as common xml hacks.'''
    pass



init();

'''
.. sidebar:: Rewriting column names

    currently disabled for testing (test code not written):

    There is an option for the user to add entries to *config.json* to rewrite column 
    names using regular expressions. The -r flag needs to be used to enable this and a familiarity 
    with regular expressions is needed, which are not trivial. A few columns already have this and
    serve as example regular expressions.
'''

# using a class for convenient structuring, not genericity or re-use
class BGGdumper:  
    """main class for processing code.

    (Exludes configuration code for processing config.json and commandline arguments, 
    see :py:mod:`config.Config`.)

    **Introduction**

    The dumper isn't trying for a comprehensive, user-friendly conversion of the xml data. 
    There are a lot of data points and that would take forever just for the boardgame 
    xml let alone the collections xml etc. 

    Rather the idea is to process the xml data as generically as reasonable without losing ANY information, 
    while flattening it ready for the rows/columns of a spreadsheet. The same code can then be 
    applied to other BGG xml sources of data (collections etc) without too much extra work. 
    
    It may seem like intelligetly dropping seemingly superfluous data/attributes
    from the xml woul dbe a good idea, but firstly it would be a presumption on the needs of the end user, 
    secondly it's a whole lot of extra work and judgments could be tricky.is
    Currently the dumper only does boardgame xml (not collections, geek buddies etc). 

    (below: :ref:`xml fragment<fragment>` )
        
    **The general rules are** 
    
    (as processed by :py:meth:`~bggdatadumper.BGGdumper.process_item_element_recursively` ):

    1. The BGG xml isn't two dimensional so column names are created by chaining together tag names along
    with their attributes including (most) attribute values. This results in a large number of columns.
    It also means Column names end up very large, but this preserves info encoded in to the xml tagging. 
    (Most attributes and their values are repeated/not-unique and so most will not create an explosion 
    of columns. Ones that would are dealt with as below, *'Some exceptions'*.) 

        (There is an option for the user to add entries to *config.json* to rewrite column 
        names using regular expressions. The -r flag needs to be used to enable this and a familiarity 
        with regular expressions is needed, which are not trivial. A few columns already have this and
        serve as example regular expressions.)


    2. Most 'datapoints' - what will become cell-values in the csv-file/spreadsheet - are 
    the value of the last attribute in a tag. Rarely a text node is the datapoint
    in which case the last attribute value instead becomes part of the column name with 
    the other attributes.

    3. Some tags are not unique, such as ``<name type="alternate".....`` which is repeated once for
    each alternate name. Each datapoint of these are aggregated in to one cell separated by commas.

    **Some exceptions:**

    4. A few exceptions where a datapoint is not the last attribute are accounted for with 
    regular expressions. See *config.json->aggregates_regexes*.    
    Such datapoints are treated simply by aggregating it and any attributes after it in to 
    one cell of attribute-name/value pairs seperated by commas. 
    
    I've not identified a general rule for such data points to avoid using regular expressions.
    These can also not be ignored as their values, being usually unique, would create an explosion of
    redundant columns. 
    This is the mandatory work that will also need doing for other BGG xml sources (collections etc). 

    5. Conversely, some last attribute values are not suitable datapoints and should instead makeup
    part of a column name. This is also handled with regular expressions. 
    See *config.json->force_value_into_fieldname_regexes*. (revisit, we should rename this to add the word final/last to the variable name for clarity)

    :py:meth:`~bggdatadumper.BGGdumper.process_item_element_recursively` handles the sub tags 
    of ``item`` tags. It does not handle the ``item`` tag itself because of its ``type`` attribute 
    which would create redundant columns.
    That code is instead found in :py:meth:`~bggdatadumper.BGGdumper.fetch_xml()` .

    While minimising processing code, thes rules give the user maximum data at the expense of some 
    unwieldliness and maybe a need to post-process in the spreadsheet with formulas if needed. 
    
    So for the following fragment of xml, you can see the data point is usually the final attribute.
    (There are almost no text nodes in the BGG xml.)
    The column name we create will be something gargantuan like ::

        /item/poll:name=suggested_numplayers:title=User Suggested Number of Players:totalvotes
    
    and the datapoint/cell-value is '699' 
    
    The next tag down adds even more stuff to that column name to create the next unique column name
    but of course missing out the previous datapoint.
    
    .. _fragment:

    .. code:: xml    

        <item type="boardgame" id="174430">
            <thumbnail>https://cf.geekdo-images.com/thumb/img/e7GyV4PaNtwmalU-EQAGecwoBSI=/fit-in/200x150/pic2437871.jpg</thumbnail>
            <image>https://cf.geekdo-images.com/original/img/lDN358RgcYvQfYYN6Oy2TXpifyM=/0x0/pic2437871.jpg</image>
            <name type="primary" sortindex="1" value="Gloomhaven" />
            <name type="alternate" sortindex="1" value="幽港迷城" />
            <name type="alternate" sortindex="1" value="글룸헤이븐" />
            <description>Gloomhaven  is a game of Euro-inspired tactical combat in a persistent world of shifting motives. Players will take on the role of a wandering adventurer with their own special set of skills and their own reasons for traveling to this dark corner of the world. Players must work together out of necessity to clear out menacing dungeons and forgotten ruins. In the process, they will enhance their abilities with experience and loot, discover new locations to explore and plunder, and expand an ever-branching story fueled by the decisions they make.&amp;#10;&amp;#10;This is a game with a persistent and changing world that is ideally played over many game sessions. After a scenario, players will make decisions on what to do, which will determine how the story continues, kind of like a &amp;ldquo;Choose Your Own Adventure&amp;rdquo; book. Playing through a scenario is a cooperative affair where players will fight against automated monsters using an innovative card system to determine the order of play and what a player does on their turn.&amp;#10;&amp;#10;Each turn, a player chooses two cards to play out of their hand. The number on the top card determines their initiative for the round. Each card also has a top and bottom power, and when it is a player&amp;rsquo;s turn in the initiative order, they determine whether to use the top power of one card and the bottom power of the other, or vice-versa. Players must be careful, though, because over time they will permanently lose cards from their hands. If they take too long to clear a dungeon, they may end up exhausted and be forced to retreat.&amp;#10;&amp;#10;</description>
            <yearpublished value="2017" />
            <minplayers value="1" />
            <maxplayers value="4" />
            <poll name="suggested_numplayers" title="User Suggested Number of Players" totalvotes="699">
                <results numplayers="1">
                    <result value="Best" numvotes="78" />
        

    """

    def load_config(self):
        self.config.load()
        self._rate_limiter.init(self.config.rate_limiter_minimum)

    def __init__(self):

        self._suppress_warnings=False
        self._rate_limiter=RateLimiter()

        self._game_ids=[]
        self._csv_cols={}
        self._csv_items=[]

        self.config=Config(config_version)


    def __warning(self,s):
        if not self.config.suppress_warnings:
            print('##Warning## '+s)

    def scrape_to_get_ids(self):    
        '''scrapes the game listing pages at http://www.boardgamegeek.com/boardgames to collect game ids
        into self._game_ids array.  '''

        #localise a few objects for convenient access    
        config=self.config
        game_ids=self._game_ids
        csv_cols=self._csv_cols
        csv_items=self._csv_items

        start_page=config.start_page
        #this is a count #revisit:change name
        pages_to_fetch=config.pages_of_ids_to_fetch

        #update the visible progress bar so the user can see action.      
        progress_str="Scraping boardgame pages"
        progress_bar(0,pages_to_fetch,progress_str)
        
        for page_num in range(start_page,start_page+pages_to_fetch):  

            progress_bar(page_num-start_page,pages_to_fetch,progress_str)

            url=config.base_url+config.html_path.format(page=page_num)
           
            #invoke the rate limiter to slow access and avoid BGG server errors
            self._rate_limiter.limit()

            page=urllib.request.urlopen(url)
            soup=bs(page,'lxml')

            #collect game ids from the main BGG pages (not xml)
            table = soup.find( 'table', {'class':'collection_table'})
            game_cells=table.find_all('td',{'class': 'collection_objectname'})


            links = []
            for cell in game_cells:
                links.append(cell.a['href'])

            ##regular expression to extract the ids from the links        
            id_regex=re.compile(r"/(?P<id>\d+)/")

            for link in links:
                m=id_regex.search(link)
                if not m:
                    __warning("id not found in href for "+link+" in "+url)
                else:
                    game_ids.append(m.group('id'))

        progress_bar(pages_to_fetch,pages_to_fetch,progress_str)


    def process_item_element_recursively( self, csv_cols, csv_item, col_name, xml) -> str:
        '''Process sub-tags of `item`  tags (individual games/items)
        
        Returns the built up col_name for unit testing purposes
        
        Most of the main xml processing occurs here. A small amount of
        top-level `item` attributes can't be generically processed and are 
        done by the :py:meth:`fetch_ids_xml_and_process()` caller. 
        
        **important:**
        
        Read this: :py:mod:`bggdatadumper.BGGdumper` for the introduction
        needed to understand the code here, including a description of the xml and its quirks. 
        '''

        #localise variables for convenience
        config=self.config
        tag_name=xml.name

        # 'None' mens dead whitespace '\n' etc; 
        # nothing to do and no children so bug out
        if tag_name==None:         
            return
        
        col_name=col_name+'/'+tag_name    

        # mostly the final attribute of a tag will become the data-value/cell-value,
        # but rarely there is a text node which will relegate the final attribute to
        # being part of the column name like all other attributes prior the final attibute.
        tag_has_text_node=xml.string!=None

        data_value=''

        if tag_has_text_node:
            data_value=xml.string.strip()
        
        #is it a leaf node? spelled out for doc purposes
        #this isn't currently used in the code
        temp=xml.findChildren()
        if(len(temp)==0):
            is_leaf=True
        else:
            is_leaf=False


        attributes=xml.attrs #a dict

        # get the two regular expression lists for the exceptions.
        # Handling the regular expresisons is the most fiddly part ofthe code
        agg_reg=list(config.aggregates_regexes.values())
        force_val_reg=list(config.force_value_into_fieldname_regexes.values())
                
        if len(attributes)>0:
            # get list of attribute keys - attributess is
            # a dict - in insertion order
            attribute_keys=list(attributes)

            # loop through each attribute one by one
            # the last attribute will be treated as 
            # data value (unless tagHasString, which 
            # will be the data value instead)
            
            last_item_index=len(attribute_keys)-1 

            aggregating=False
            for a in range(0,len(attribute_keys)):

                #note the following code is dealing with just one attribute/value pair

                k=attribute_keys[a]
                v=attributes[k]

                # Set the Aggregation flag. 
                # If matches the regex, then all subsequent 
                # attribute-names+values for the tag are lumped
                # together as one data value INSTEAD
                # of using only the last attribute's value 
                # as the data value. 
                # (This is because except for the final attibute value,
                # most attribute/value pairs go in to the column name not 
                # the data value as they are not true data values but rather
                # labels, but there are some exceptions 
                # and that will cause columns explosion, hence the regexes).
                # The new colum name hasn't been
                # set yet, which is why we have `+k`
                # to create it here.
                # This test is for attribute names,
                # later we repeat the test but for 
                # for the attribute values as well.
                for r in range(0,len(agg_reg)):
                    if agg_reg[r].match(col_name+':'+k):
                        aggregating=True 

                #attribute label and value appended to the data value
                if aggregating:
                    data_value+=k+'='+v+','
                elif a==last_item_index and not tag_has_text_node:
                    # attribute name goes in the col_name, 
                    # and value in to the field value
                    col_name+=':'+k                    
                    #the value of the last item is 
                    #not included in the fieldname, unless...                
                    for r in force_val_reg: 
                        if r.match(col_name): #excepting a text-node there will be no data-value for this tag 
                            col_name+='='+v
                            #blank the data value
                            v=''
                    data_value+=v
                    col_name+=':'
                #attribute becomes part of the field/column name
                else: #not aggregating
                    # not a data item, so put the 
                    # attribute's name AND value in col_name 
                    col_name+=':'+k+'='+v+':'

                # Set the agreggation flag, 
                # this time for the attribute value 
                for r in range(0,len(agg_reg)):
                    if agg_reg[r].match(col_name):
                        aggregating=True 
                
                #process the next attribute.

        #finished processing all the attributes, so....

        if data_value!='':#not a redundant test if a final attribute value was forced in to the column name there will be no data value
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


    def _security_neutralise_spreadsheet_formulas(self,csv_item : dict):
        for k in csv_item:
            s=csv_item[k]
            if len(s)==1:
                if s[0]=='=':
                    csv_item[k]=s.strip('=')


    def _process_security_regexes(self,data):
        regexes=self.config.security_regexes
        for k, r in regexes.items():
            if r.match(data):
                raise InsecureDataError("Bad data from source. Type: "+k)

    def fetch_xml(self,url):
        '''Utility method that requests the xml and returns a beautiful soup object.
        This method also passes the data to :py:meth:`~bggdatadumper.BGGdumper._process_security_regexes` 
        to check for malformed hacker xml.'''

        xmlresponse=urllib.request.urlopen(url)
        raw=xmlresponse.read() 
        #print(raw)
        
        try:
            self._process_security_regexes(raw.decode("utf-8"))       
        except InsecureDataError as e:
            raise Exception('For url: '+url+', '+str(e))
        
        return bs(raw,"lxml")      

    def fetch_ids_xml_and_process(self): 
        ''' Fetches the xml for batches of ids and processes them to extract the data
        in to the arrays/dicts _csv_items and _csv_cols ready for exporting to a csv. 
        '''

        #localise variables for convenience
        config=self.config
        game_ids=self._game_ids
        csv_cols=self._csv_cols
        csv_items=self._csv_items  

        #update the visible progress bar
        progress_str="api queries: xml data for "+str(len(game_ids))+' games.'
        progress_counter=0;
        progress_bar(0,len(game_ids),progress_str)

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
        
        #revisit: is this being used by the testcode?
        if config.debug:
            config.games_per_xml_fetch=1
            game_ids=['1','2']

        #more ids to process
        is_more_ids=True
        id_gen=id_generator(game_ids)


        while is_more_ids:
            working_url=url
            #print('passing')
            
            #get the next lot of ids using the generator 
            id_batch=[]
            for i in range(0,config.games_per_xml_fetch):
                id=next(id_gen)
                if id!=-1:
                    id_batch.append(id)
                else:#Klunk, gah!, this is why we need to revisit and straighten out the generator
                    is_more_ids=False
                    break
            
            #no more ids, bug out.
            if len(id_batch)==0:
                break

            #make the comma separated list of ids for the url
            id_str=''
            for id in id_batch:
                id_str+=id+','
            #remove terminating comma
            id_str=id_str.strip(',')
            
            #make the url
            working_url=working_url.format(ids=id_str)

            #invoke the rate limiter to slow access and avoid BGG server errors
            self._rate_limiter.limit()

            xml=self.fetch_xml(working_url)
            
            xml_items=xml.find_all('item')
            for xml_item in xml_items:
                # the first tag 'item' needs special treatment 
                # so is not processed by the recursive function
                # as otherwise we end up with multiple superfluous 
                # columns derived from the 'type'  
                csv_item={}
                col_name="/item"
                cn=col_name+':type'

                #set the column name in the dict, accessible by itself for quick lookups.
                #(this repeats overwriting itself which is pointless, 
                # but for ease of flow-control and readability it's not optimised out)
                csv_cols[cn]=cn
                #start adding data-points/cells 
                csv_item[cn]=xml_item.attrs['type']

                #the items actual BGG id
                cn=col_name+':id'
                csv_cols[cn]=cn
                csv_item[cn]=xml_item.attrs['id']
                
                #having done those two data points, the rest of the item's sub-xml can be done quasi-generically

                for child in xml_item.children:
                    #call the (quasi)generic processor which processes a single tag and then calls itself for any subtags
                    self.process_item_element_recursively(
                        csv_cols,
                        csv_item,
                        col_name,
                        child)

                #check and neutralise dodgy data values that might be spreadsheet formulas
                #revisit: needs test code
                if config.option_strip_formula_equal_sign_for_csv:
                    self._security_neutralise_spreadsheet_formulas(csv_item)

                #now we have all the data, add the row
                csv_items.append(csv_item)
            
            #update the visible progress_bar
            progress_counter+=len(xml_items)
            progress_bar(progress_counter,len(game_ids),progress_str)


    def rewrite_column_names(self):
        ''' Rewrite the auto-generated column names, which are mostly
        unreadable, can be renamed by setting regular 
        expressions in config.json->new_col_names. 
        This function defines two nested functions and 
        calls those at the end, see about 70 lines down.

        We use regexes instead of straight strings for comparison
        because many column names are similar and also because
        there are an indeterminate number of 'vote' columns but they
        follow the same pattern. Using regex 'groups' we can extract
        unique parts of the original columm names to aid constructing 
        the new column names. Groups are denoted by brackets (see config.json).
        '''
        new_col_names_lookup={}

        #create a dict/hash lookup from the regexes in config.json
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
            
            # first do the columns dict, which is used for 
            # the csv header/first-line in output()
            # this is a straight replacement. 
            self._csv_cols={} #blank it
            for cn in list(new_col_names_lookup.values()):
                self._csv_cols[cn]=cn
            
            # now do the actual data using the old column name to 
            # fetch the new one from the dict/hash lookup
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
    def export_csv(self):
        progress_str='writing csv'
        progress_bar(0,len(self._csv_items),progress_str)
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
                progress_bar(c,len(self._csv_items),progress_str)
            print('\n')
        print('limiting: '+str(self._rate_limiter.count()))

#try

if __name__ == '__main__':
    bd=BGGdumper()
    bd.load_config();
    bd.scrape_to_get_ids()
    bd.fetch_ids_xml_and_process()
    #bd.rewrite_column_names()
    bd.export_csv()

'''
except Exception as e:
    sys.stderr.write('Error: '+str(e)+'\n')
    #sys.exit uses an exception, which we don't want when debugging
    if not isDebugging():
        sys.exit(1)
'''
