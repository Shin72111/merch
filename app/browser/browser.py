from os import environ, path, remove
from selenium.webdriver import Chrome
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.common.exceptions import ElementNotVisibleException
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from time import sleep, time
from bs4 import BeautifulSoup
import urllib.parse
from re import sub as re_sub
from app.models import Products
from threading import Thread


AMZ_LINK = 'https://www.amazon.com'
WAITING_TIME_FOR_EXTENSION_LOAD = 10
DEFAULT_LOCATION_CODE = '10001'
DEFAULT_KEYWORD = '"Lightweight, Classic fit, Double-needle sleeve and bottom hem"'
LOADING_RANK_KEYWORD = 'Loading rank...'
DEFAULT_RANK_NOT_FOUND = 999_999_999_999

class Browser():
    def __init__(self, location_code=DEFAULT_LOCATION_CODE, wait4extention=WAITING_TIME_FOR_EXTENSION_LOAD):
        self.__setupChrome()
        #self.__setupLogging()
        self.location_code = location_code
        self.wait4extention = wait4extention

    def __setupChrome(self):
        self.dir = path.dirname(path.realpath(__file__))
        executable_path = self.dir + r'\chromedriver.exe'
        extension_path = self.dir + r'\modifiedDSAQV.crx'
        environ["webdriver.chrome.driver"] = executable_path
        chrome_options = Options()
        chrome_options.add_extension(extension_path)
        self.driver = Chrome(executable_path=executable_path,
            chrome_options=chrome_options)
        self.wait = WebDriverWait(self.driver,5)

    def setupLocation(self):
        self.__setupLocation()
        sleep(2)


    def __setupLocation(self):
        self.get(AMZ_LINK)
        self.wait.until(EC.presence_of_element_located(
            (By.ID, "nav-global-location-slot")))

        # Click on the change location button
        while True:
            try:
                location_button = self.driver.find_element_by_id('nav-global-location-slot')
                location_button.click()
            except WebDriverException as e:
                if 'is not clickable at point' in e.msg:
                    # Successfully click on the button
                    break
                else:
                    raise e

        # Attempt to click on change location code button
        while True:
            try:
                change_button = WebDriverWait(self.driver,2).until(
                    EC.presence_of_element_located((By.ID, "GLUXChangePostalCodeLink")))
                change_button.click()
                break
            except ElementNotVisibleException:
                # location code wasn't set
                break
            except TimeoutException as e:
                # Failed to click location button
                raise e

        # Input for location code
        code_input = self.driver.find_element_by_id('GLUXZipUpdateInput')
        code_input.send_keys(self.location_code)

        # Apply location code
        apply_button = self.driver.find_element_by_id('GLUXZipUpdate')
        apply_button.click()

        # Take 1 second sleep to make sure browser operate normally
        sleep(1)

        # Done the location change
        done_button = self.driver.find_element_by_name('glowDoneButton')
        done_button.click()

    def encodeUrl(self,keyword):
        keyword = urllib.parse.quote_plus(keyword)
        url = AMZ_LINK + '/s/ref=nb_sb_noss?url=search-alias%3Dfashion&keywords={}'.format(keyword)
        return url

    def get(self, url):
        self.driver.get(url)

    def __waitForRank(self):
        # Wait until finish loading rank.
        count = 0
        while True:
            if LOADING_RANK_KEYWORD in self.driver.page_source and count < 30:
                count += 1
                sleep(0.5)
            else:
                return

    def __findNextPage(self):
        next_page = self.page.find('a', {'title': 'Next Page'})
        if next_page:
            return AMZ_LINK + next_page.get('href')
        return None

    def __genBSpage(self):
        self.page = BeautifulSoup(self.driver.page_source, 'lxml')

    def quit(self):
        self.driver.quit()


    def __getProductsInPage(self, app, db):
        resultData = self.page.find('div', {'id': 'resultsCol'})
        if resultData is None or resultData == []:
            return None
        with app.app_context():
            products = []
            for result in resultData.find_all('div', {'class': 's-item-container'}):
                # Skip if empty
                if result.text is None or result.text == "":
                    continue

                # Count for product found
                self.counter['found'] += 1

                # Get the product features
                featuresTag = result.find('div', {'class': 'extension-features'})

                # Skip if it isn't a merch product
                if featuresTag is None or featuresTag.get('ismerch') != 'true':
                    continue

                # Count for merch product
                self.counter['merch'] += 1

                # Get product rank
                display_rank = result.find('span', {'class': 'extension-rank'})
                if display_rank:
                    rank = int(display_rank.text[1:].replace(',',''))
                    display_rank = display_rank.text
                else:
                    # Rank Not found, use the default extremely large value
                    rank = DEFAULT_RANK_NOT_FOUND
                    display_rank = 'Rank Not Found'

                # Get asin from asin tag
                asinTag = result.find('span', {'class': 'xtaqv-copy'})
                asin = asinTag.text

                # Check if the product exists in database, then update the rankself.
                # Otherwise, add new product info
                product = Products.query.filter_by(asin=asin).first()
                if product:
                    product.rank = rank
                    product.display_rank = display_rank
                else:
                    # Count for new merch product found
                    self.counter['new'] += 1

                    # Get features and remove redundant spaces
                    features = re_sub(r'\s{2,40}', ' ', featuresTag.text).lower()

                    # Get name, image link from img tag
                    imgTag = result.find('img', {'class': 's-access-image cfMarker'})
                    name = imgTag.get('alt')
                    image = imgTag.get('src')

                    # Create a new product
                    product = Products(name=name, asin=asin, image=image,
                        rank=rank, display_rank=display_rank, features=features)

                    # Add to the database session
                    db.session.add(product)
                db.session.commit()
            



    def getAllProducts(self, url,app,db):
        # Loop through all pages to get product info
        self.counter = {'found':0,'merch':0,'new':0}
        while url:
            self.get(url)
            self.__waitForRank()
            self.__genBSpage()
            self.__getProductsInPage(app,db)
            url = self.__findNextPage()


    def search4keyword(self, app,db,keyword=DEFAULT_KEYWORD):
        self.setupLocation()
        url = self.encodeUrl(keyword)
        self.getAllProducts(url,app,db)
        return self.counter

def crawl(app,db, keyword=DEFAULT_KEYWORD, location=DEFAULT_LOCATION_CODE):
    browser = Browser(location)
    searchTime = time()
    counter = browser.search4keyword(app,db,keyword)
    searchTime = time() - searchTime
    browser.quit()
    return searchTime, counter

def getCrawlerThread(app, db):
    keyword = DEFAULT_KEYWORD
    return Thread(target=crawl, args=(app, db,keyword, DEFAULT_LOCATION_CODE, ))
