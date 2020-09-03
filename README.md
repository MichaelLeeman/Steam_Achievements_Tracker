# Steam Achievements Database
This project scrapes data from the steam website about the user's game achievement stats, performs analyse on the data and stores it in a SQLite database. 

## About
The purpose of this project to learn more about web-scraping and how to use SQLite with Python. 

So far, this program scrapes the user's steam profile to collect data on the user's games and the achievements they have unlocked. The program then inserts this data into a SQLite database and peforms simple analysis such as calculate the Total Achievements Unlocked and The Average Completion Rate.

The next plans are to implement Pandas to create graphs and calculate other statistics. 

## Features
So far, the program has the following features:
* Steam Login-in
* Handle Log-in Errors
* Scrape game achievement data
* Save data to SQLite database
* Calculate stats (including Total Number of Achievements)
* Print stats to terminal

## Technologies
Project was created with:
* Python 3.8
* requests 2.24.0
* beautifulsoup4 4.9.1
* selenium 3.141.0
* SQLite3

## Requirements
To run this Project you will need
* A steam account
* Google Chromedriver 85.0

## How To Setup
To setup the project, you need to clone the repo using Git, create a virtual environment and install dependencies from requirements.txt. You can do this from the terminal:

```buildoutcfg
# Clone project repository and enter project directory
$ git clone https://github.com/MichaelLeeman/Job_Web_Scraper
$ cd Job_Web_Scraper

# Creating virtualenv and activate it
$ python3 -m venv my_venv
$ source ./my_venv/bin/activate

# Install dependencies
$ pip3 install -r ./requirements.txt
```
Next, you need to install [Chrome driver](https://sites.google.com/a/chromium.org/chromedriver/downloads) to allow Selenium to interface with Google Chrome. This application is built for Google Driver version 85.0 but other versions can be used by changing the header parameters in GET requests. The chrome driver needs to be installed in the app's directory.

Finally, you can run the program inside the app directory. 
```buildoutcfg
# Run Python program
$ python3 main.py
```

## Running The Program
The program starts by asking for your Steam username and password. After entering these credentials into the terminal, you need to enter the security code that is sent to your email by Steam. 
 
Once you have successfully entered the security code, the program will start scraping data from your Steam profile. You should see the achievements stats of each of your Steam game being printed to the terminal. At the very end of the program, stats such as the Total Number of Achievements are printed and your data is saved to a SQLite database. 

The program should take less than 10 minutes to complete with a stable internet connection. 