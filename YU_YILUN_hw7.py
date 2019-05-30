from selenium import webdriver
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import argparse
import requests
import sqlite3
import datetime
import pandas as pd
import sys
import os

###########################  Thia part scrapes the information from web
#provide year in string format, current air quality for the cities in the state
def epa(state, num=100):  # select only 20 cities from a state
    sys.stdout = open(os.devnull, 'w')
    url1 = "https://airnow.gov/index.cfm?action=airnow.main"
    driver = webdriver.Chrome(ChromeDriverManager().install())
    driver.get(url1)          #open the url

    #select the state we desire
    select = Select(driver.find_element_by_id('stateid'))
    try:
        select.select_by_visible_text(state)
    except:
        print("Incorrect input for state name. Input like: 'California'.")   # catch state input error
        return []

    #click the 'go' button
    go = driver.find_element_by_xpath("//form[@name='frmStateSearch']/input")   #to select data in whole US
    go.click()

    #scrape air qualitu information for all the cities(who has info on the website)in the state
    trs = driver.find_elements_by_xpath("//div[@id='StateSummaryArea']/table/tbody/tr")

    count = 0
    city_aqi = []
    for tr in trs:  #iterate through the cities in the state
        info = tr.find_elements_by_xpath("./td/table/tbody/tr/td")
        if len(info) > 0:
            city = info[0].text.strip()       # locate the city name
            aqi = info[3].find_element_by_xpath("./table/tbody/tr/td").text.strip()  # locate the current AQI info
            if aqi != '' and aqi is not None:  #filter out the none information
                city_aqi.append((city, int(aqi)))
                count += 1
        else:
            continue
        if count == num:   # sample output for 20 cities
            break
    sys.stdout = sys.__stdout__
    return city_aqi  # returns the list with (city, AQI) tuple as its element



# api function for air visual, current weather for the location
def airvisual(lat, lng):
    key = ""    #api key
    # make request through API
    request = ("https://api.airvisual.com/v2/nearest_city?lat={}&lon={}&key={}".format(lat, lng, key))

    try:
        response = requests.get(request).json()
    except:
        print("Request for Air Visual failed.")  # catch air visual api limit
        return None

    if response['status'] == "fail":
        return None
    else:
        weather = response['data']['current']["weather"]  #get the relative information from json data
        temperature = weather['tp']
        wind_speed = weather['ws']
        wind_dir = weather["wd"]
        cond = weather['ic'][0:2]  # ignore the day or night information

    return (temperature, wind_speed, wind_dir, int(cond))


# api function for air now, historical air quality info for the location
def airnow(lat, long, year_month_date):
    key = ""   #api key
    dist = "50"
    # make request through API
    request = "http://www.airnowapi.org/aq/forecast/latLong/?format=application/json&latitude={}&longitude={}&" \
    "date={}&distance={}&API_KEY={}".format(lat, long, year_month_date, dist, key)

    try:
        response = requests.get(request).json()
    except:
        print("Air Now API request limit reached. Try another time.")  # catch air now api limit
        exit()

    if len(response) == 0:
        return -1  # No data found

    aqi_list = []
    # extract the corresponding information
    for dic in response:
        date = dic["DateIssue"]
        area = dic['ReportingArea']
        param = dic['ParameterName']
        aqi = dic['AQI']
        #quality = dic["Category"]["Name"]
        if aqi == -1:  # no information
            continue
        aqi_list.append(aqi)
    if len(aqi_list) == 0:
        return -1    # no infomation cought
    AQI = max(aqi_list)   # find the aqi which is the highest parameter
    return AQI

# this api is to find the geo location from city and state input
def city_geo(city, state):
    key = ""
    url = "https://maps.googleapis.com/maps/api/geocode/json?address={},+{}&key={}".format(city, state, key)
    try:
        response = requests.get(url).json()
    except:
        print("Request for Google Geocoding failed.")  # catch request failure
        return None, None

    latitude, longitude = None, None  #set the default value

    if response['status'] == 'OK':  #successful request
        latitude = response['results'][0]['geometry']['location']['lat']  # extract the latitude and longitude from response
        longitude = response['results'][0]['geometry']['location']['lng']

    return latitude, longitude



def get_historical_aqi(lat, lng):
    date = datetime.datetime.today()  # get the current date
    month_day = date.strftime('%m-%d')
    aqi_list = []
    for year in range(2015, 2019): # get the aqi data for the past 4 years
        year_month_date = "{}-{}".format(year, month_day)
        aqi = airnow(lat, lng, year_month_date)
        if aqi == -1:  # no data on this year
            continue
        aqi_list.append(aqi)
    if len(aqi_list) == 0:   # when no data found at all
        return -1

    return sum(aqi_list)/len(aqi_list)



########d####################ata base model part of code
# create the database
def create_db():
    conn = sqlite3.connect('Weather_AirQuality_local.db')
    cur = conn.cursor()

    # SQLite3 command script to create tables in tables
    # create Weather table
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS Weather(
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    city_id INTEGER NOT NULL, 
    weather_type INTEGER,
    temp INTEGER,
    wind_speed FLOAT,
    wind_dir FLOAT);
    ''')

    # create AQ table
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS AQ(
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    city_id INTEGER NOT NULL,
    current_aq INTEGER NOT NULL,
    historical_avg_aq FLOAT NOT NULL,
    AQI_diff FLOAT NOT NULL
    );''')

    # create Weather_Types table
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS Weather_Types(
    id  INTEGER NOT NULL PRIMARY KEY,
    weather TEXT NOT NULL
    );''')

    # create City table
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS City(
    id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL
    );''')
    return conn, cur




# add current weather info into table
# this function adds data into city table, this part of code was copied from lab
def add_city(conn, cur, city, state, lat, lng):
    cur.execute("""SELECT * FROM City WHERE (city="{}" AND state="{}")""".format(city, state))
    entry = cur.fetchone()   # add info if the key does not exist
    if entry is None:
        cur.execute(
            """INSERT INTO City (city, state, latitude, longitude) VALUES ("{}","{}",{},{})"""
                .format(city, state, lat, lng))
        conn.commit()


# add information to weather table
def add_weather(conn, cur, city_id, weather_type, temp, wind_speed, wind_dir):
    cur.execute("""SELECT * FROM Weather WHERE (city_id={})""".format(city_id))
    entry = cur.fetchone()
    if entry is None:
        cur.execute(
            """INSERT INTO Weather (city_id, weather_type, temp, wind_speed, wind_dir) VALUES ({},{},{},{},{})"""
                .format(city_id, weather_type, temp, wind_speed, wind_dir))
        conn.commit()


# add aqi into databse
def add_AQ(conn, cur, city_id, aqi, historical_aqi, AQI_diff):
    cur.execute("""SELECT * FROM AQ WHERE (city_id={})""".format(city_id))
    entry = cur.fetchone()
    if entry is None:
        cur.execute(
            """INSERT INTO AQ (city_id, current_aq, historical_avg_aq, AQI_diff) VALUES ({},{},{},{})"""
            .format(city_id, aqi, historical_aqi, AQI_diff))
        conn.commit()



# add weather into table
def add_weather_types(conn, cur, id, weather):
    cur.execute("""SELECT * FROM Weather_Types WHERE (id={})""".format(id))
    entry = cur.fetchone()
    if entry is None:
        cur.execute("""INSERT INTO Weather_Types (id ,weather) VALUES ({},"{}")""".format(id, weather))
        conn.commit()

# supporting function
def add_weather_and_AQ_tables(conn, cur, city, state, weather_type, temp, wind_speed
                      , wind_dir, latitude, longitude, aqi, historical_aqi, AQI_diff):
    add_city(conn, cur, city, state, latitude, longitude)
    cur.execute("""SELECT id FROM City WHERE (city="{}" AND state="{}")""".format(city, state))
    city_id = int(cur.fetchone()[0])  # extract the id from City table for adding to other 2 tables
    add_weather(conn, cur, city_id, weather_type, temp, wind_speed, wind_dir)
    add_AQ(conn, cur, city_id, aqi, historical_aqi, AQI_diff)





############################ pipeline, combines previous functions
def remote(state):
    city_aqi_list = epa(state)
    info = []
    i = 0   # number counter
    for city_aqi in city_aqi_list:
        city = city_aqi[0]
        current_aqi = city_aqi[1]    # get the city name and the current AQI

        lat, lng = city_geo(city, state)  # get the geo location of the city

        if lat == None or lng == None:
            continue

        historical_aqi = get_historical_aqi(lat, lng)   # get the 5 year average historical AQI
        if historical_aqi == -1:
            continue

        current_weather = airvisual(lat, lng)   # get the weather information for the city
        if current_weather == None:
            continue

        info.append((current_weather, city, state, current_aqi, lat, lng, historical_aqi))

        # limit the output numbers
        i += 1
        if i == 6:
            break
    return info


# get a result from the data
def generate_result(conn, cur):
    # generate conclusion from data
    cmd = "SELECT Weather_Types.weather, AQ.AQI_diff FROM Weather_Types JOIN AQ " \
          "JOIN Weather ON Weather.city_id=AQ.city_id AND Weather.weather_type=Weather_Types.id"
    weather_impact = pd.read_sql(cmd, conn)
    weather_impact["Average Impact"] = weather_impact.groupby('weather').transform("mean")#.AQI_diff.mean()
    weather_impact = weather_impact.drop_duplicates(subset='weather', keep='first')
    print("This pandas dataframe gives the impact of each kind of weather on air quality index on average.\n"
          "Negative number means it makes the air quality better, vice versa.\n")
    print("Result:")
    print(weather_impact[["weather", "Average Impact"]], "\n")





############################ Main function part
def main():

    # parse in the comment using argparser and limit the commend line arguments
    parser = argparse.ArgumentParser(description='Study the effect of weather to ')
    parser.add_argument('-source', default='local', choices=['local', 'remote'],
                        help='define the function to get data from local or remote')
    args = parser.parse_args()

    weather_icons = {1: 'clear sky', 2: 'few clouds', 3: 'scattered clouds',
                     4: 'broken clouds', 9: 'shower rain', 10: 'rain',
                     11: 'thunderstorm', 13: 'snow', 50: 'mist'}  # weather icons indicaged by api

    # when accessing local file
    if args.source == "local":
        conn = sqlite3.connect('Weather_AirQuality_local.db')
        cur = conn.cursor()
        print("The results are generated from pre-stored local database.\n")
        generate_result(conn, cur)
        cur.close()
        return 0

    # when scrape from internet
    else:
        conn, cur = create_db()
        for id, weather in weather_icons.items():
            add_weather_types(conn, cur, id, weather)

        # this part was used to create the local databse to store the cities in all states
        #states = ["California", "New Jersey", "Washington", "New Mexico", "Florida", "Oklahoma"]
        #states = ['Alabama', 'Arizona', 'Arkansas', 'Colorado', 'Connecticut', 'Delaware', 'Georgia']
        #states = ['Hawaii', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland']
        #states = ['Michigan', 'Massachusetts','Minnesota', 'Mississippi' ,'Missouri', 'Montana', 'Nebraska', 'Nevada']
        #states = ['New Hampshire', 'New York', 'North Carolina', 'North Dakota',
        # 'Ohio', 'Oregon', 'Pennsylvania', 'Rhode Island']
        states = ['South Carolina', 'South Dakota', 'Tennessee', 'Texas',
                  'Utah', 'Vermont', 'Virginia', 'West Virginia', 'Wisconsin', 'Wyoming']
        information = []   # store all the information in this list
        print("Scraping data online...\n")
        for state in states:
            state_info = remote(state)
            information.extend(state_info)


        #info->(current_weather, city, state, current_aqi, lat, lng, historical_aqi)
        #current_weather-> (temperature, wind_speed, wind_dir, cond)
        ###################This part adds the information into data bse
        print("Adding the scraped data to remote database...\n")
        for individual_info in information:
            # extract info from lsit
            city = individual_info[1]
            state = individual_info[2]
            weather_type = individual_info[0][3]
            temp = individual_info[0][0]
            wind_speed = individual_info[0][1]
            wind_dir = individual_info[0][2]
            latitude = individual_info[4]
            longitude = individual_info[5]
            aqi = individual_info[3]
            historical_aqi = individual_info[6]
            AQI_diff = aqi - historical_aqi
            # add the info to data base
            add_weather_and_AQ_tables(conn, cur, city, state, weather_type, temp, wind_speed
                                      , wind_dir, latitude, longitude, aqi, historical_aqi, AQI_diff)
            # generate a temperory result
        print("The results are generated from the extended table after new information added.\n")
        generate_result(conn, cur)
        cur.close()
        return 1

# calling from commend line
if __name__ == "__main__":
    main()

