Relation Between Weather and Air Quality


README:
1.
If the command line is already in the folder contains my python file (and also potentially
 with the data base file), the command to run the python would be "python YU_YILUN_hw6.py -source=local" (for accessing local database) or "python YU_YILUN_hw6.py -source=remote" (for scraping the data online add to the database or create a new one). Input any other command line argument will case the program to raise an exception and print the help information to guide the user.
When remote is invoked, my program will scrape information online and then append it to database(if not duplicate). And then, calling the local would evaluate the new databased to generate the result. Due to the limited calling to air now API, the remote function can only be ran once every hour.


2.
The code involves user interaction on webpages, so I have to use Selenium library. However, every time a page is need to be opened for scraping, the program will actually open a Chrome browser which can be a bit slow. Also, for a lot of cities, there are information on one website but not on the API, the data has to be abandoned casing the total data to be relatively small. If more APIs/webpages are used, the data size can be much bigger.


3.
The conclusion is not so robust due to the low amount of data and also the limited calls to the API. For example, air visual only allows 500 calls in one hour. I cannot have the previous average air quality to be traced too far back. I only scraped the previous 3 years to get the average air quality on the specific city.

Covered Under MIT Liscense
