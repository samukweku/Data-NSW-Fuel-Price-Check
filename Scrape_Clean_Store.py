# import libraries
import sqlite3
from requests_html import HTMLSession
from fnmatch import fnmatch
from glom import glom
from openpyxl import load_workbook
from io import BytesIO
from itertools import islice

session = HTMLSession()
r = session.get("https://data.nsw.gov.au/data/dataset/fuel-check")

# The links(xlsx files) are in a json file.
# First step is to get the json file from the page, download it and extract all the xlsx files

# copy the xpath path from the webpage
# I used google chrome dev tools
# right click on the relevant link, click on copy element, and select full xpath
sel = "/html/body/div[3]/div/div[2]/div/article/div/ul/li[1]/a/@href"

# access the json url
json_link = r.html.xpath(sel)[0]

# Step 3: append json link to 'https://data.nsw.gov.au' and pass again to session.get
url = f"https://data.nsw.gov.au{json_link}"
json_data = session.get(url).json()

# The links are in the url key.<br>
# The path to the link is : json_data -> result -> resources -> url
# we'll filter urls for only those that end with 'xslx'
# the filter could also be on the format key that has 'xlsx' in its value

# create a specification to glom the relevant data
# glom's documentation is pretty detailed
spec = {"name": ("result.resources", ["name"]), "url": ("result.resources", ["url"])}

# extract data
outcome = glom(json_data, spec)

# get the names to be the keys, and urls to be the values
outcome = dict(zip(*outcome.values()))

# keep only entries where the file ends with 'xlsx'
# we'll use the fnmatch function from the fnmatch module
pattern = "*.xlsx"

urls = {key: value for key, value in outcome.items() if fnmatch(value, pattern)}


# connect to database
con = sqlite3.connect("fuel_nsw_price_data.db")
cur = con.cursor()

query = f"""SELECT fuel_month_year 
           from fuel_month_year
           ;"""

cur.execute(query)
# get current list of keys
db_table_list = cur.fetchall()
# get only urls that have not been downloaded
download_keys = set((urls.keys())) - set(db[0] for db in db_table_list)


def key_generator():
    for key in download_keys:
        yield (key,)


# add urls not downloaded to database
insert_query = f"INSERT INTO fuel_month_year (fuel_month_year) VALUES (?);"
cur.executemany(insert_query, key_generator())
# never forget to commit
con.commit()
# and cose connection
con.close()

# download list for our data
url_download_list = [urls[key] for key in download_keys]
print(len(url_download_list))

# no transformations needed here
# simply download and store in database
# pandas not needed
# plus openpyxl is faster than pandas for this task
collection = []

for xlsx_link in url_download_list:
    # download link
    r = session.get(xlsx_link)
    # read it in
    # note that they are bytes, hence the BytesIO usage
    wb = load_workbook(BytesIO(r.content), read_only=True)
    # initialize the first sheet
    ws = wb.active

    # get index of header
    index, header = next(
        (index, value)
        for index, value in enumerate(ws.values)
        if "ServiceStationName" in value
    )

    # get rest of data
    body = list(islice(ws.values, index + 1, None))

    # store away the data
    collection.extend(body)

# connect to database again
con = sqlite3.connect("fuel_nsw_price_data.db")
cur = con.cursor()
# we have eight columns in our database table
# and in the incoming data
# so eight question marks to represent our data
insert_params = ",".join(["?"] * 8)

# list of columns
columns_list = ",".join(
    [
        "service_station_name",
        "address",
        "suburb",
        "postcode",
        "brand",
        "fuelcode",
        "transaction_date",
        "price",
    ]
)

# query string
insert_query = f"INSERT INTO fuel_data({columns_list}) VALUES ({insert_params});"

# speedy multiple row insertions
cur.executemany(insert_query, collection)

# without this, the information will not be saved
con.commit()

con.close()
