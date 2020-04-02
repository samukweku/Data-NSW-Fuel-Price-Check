import sqlite3

Fuel_Month_Year = (
    """\nCREATE TABLE IF NOT EXISTS fuel_month_year (fuel_month_year TEXT);"""
)

Fuel_Data = """
CREATE TABLE IF NOT EXISTS fuel_data (service_station_name TEXT,\n
                                      address TEXT,\n
                                      suburb TEXT,\n
                                      postcode TEXT,\n
                                      brand TEXT,\n
                                      fuelcode TEXT,\n
                                      transaction_date TEXT,\n
                                      price REAL
                                      );"""


create_tables = ("\n\n".join([Fuel_Month_Year, Fuel_Data]))

#run queries
con = sqlite3.connect('fuel_nsw_price_data.db')
cur = con.cursor()
cur.executescript(create_tables)
con.close()
