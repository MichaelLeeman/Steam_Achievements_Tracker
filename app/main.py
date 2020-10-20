from app import steam_scraper
import pandas
import math
import sqlite3
from getpass import getpass
from selenium import webdriver
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


# Create the sqlite3 database in memory. If the database doesn't have the achievements table then create it.
connection = sqlite3.connect("achievement.db")
cur = connection.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS achievements (
                    name text,
                    unlocked_achievements text,
                    total_achievements text,
                    achievement_percentage
                    )""")
try:
    cur.execute("""CREATE UNIQUE INDEX idx_game ON achievements (name)""")
except sqlite3.OperationalError:
    pass

# Ask user if they have a steam profile or use an example
answer = input("""Welcome to the Steam Achievement Pandas Analysis app. 

Please choose whether you want to analyse your own Steam profile's achievement progress [Type "1"] or use an example [Type "2"]. 
""")

if answer == "1":
    # Starts selenium in the steam login page
    sign_in_URL = "https://steamcommunity.com/login/home/?goto=search%2Fusers%2F"
    driver = webdriver.Chrome('./chromedriver')
    driver.get(sign_in_URL)
    logged_in, correct_code = False, False

    # Log in to steam. Loop around until the correct credentials are given
    while not logged_in:
        username = input("Steam username:")
        password = getpass("Steam password:")
        logged_in = steam_scraper.log_in(driver, username, password)

    # Enter the security code sent to the user's email
    while not correct_code:
        email_code = input("Please type in your security code that was sent to your email address:").strip()
        correct_code = steam_scraper.enter_email_code(driver, email_code)

    # Go to the user's game page
    output_message = steam_scraper.go_to_games_page(driver)
    print(output_message)

    # Scrape the user's game data and add it to the SQLite database
    game_data_list = steam_scraper.get_game_data(driver)
    driver.close()
    for game in game_data_list:
        with connection:
            cur.execute(
                """REPLACE INTO achievements (name, unlocked_achievements,total_achievements,achievement_percentage) VALUES (?, ?, ?, ?)""", game)
else:
    print("Loading an example of game progression")
    game_data_list = [("Sid Meier's Civilization V", "107", "286", "37%"), ("Dishonored", "28", "80", "35%"), ("The Elder Scrolls V: Skyrim", "3", "75", "4%"), ("Left 4 Dead 2", "54", "100", "54%"), ("Cities: Skylines", "26", "111", "23%")]
    with connection:
        cur.execute("DELETE FROM achievements")
    for game in game_data_list:
        print(game)
        with connection:
            cur.execute(
                """INSERT INTO achievements (name, unlocked_achievements,total_achievements,achievement_percentage) VALUES (?, ?, ?, ?)""", game)

# Get all games with achievements enabled to calculate Average Game Rate Completion
with connection:
    df = pandas.read_sql_query("SELECT * FROM achievements", con=connection)

# Calculate Average Game Rate Completion
print("-" * 150)
number_of_games = len(df[df.achievement_percentage != '0%'])
sum_of_percentages = pandas.to_numeric(df.achievement_percentage.str.replace("%", "")).sum()
average_game_completion = math.floor(sum_of_percentages / number_of_games)
print("Average Game Completion Rate = {}%".format(str(average_game_completion)))

# Calculate total number of achievements unlocked
total_achievements_unlocked = pandas.to_numeric(df.unlocked_achievements).sum()
print("Total Number of Achievements Unlocked = {}".format(str(total_achievements_unlocked)))

# Plotting the Achievements bar chart
cur.execute("SELECT name, achievement_percentage FROM achievements")
data = cur.fetchall()
game_names = []
percentage_values = []

for row in data:
    if row[1] != "0%":
        game_names.append(row[0])
        percentage_values.append(int(row[1].rstrip("%"))/100)

plt.bar(game_names, percentage_values)
x_locations, x_labs = plt.xticks(rotation=90)
plt.tick_params(axis='x', which='major', labelsize=7.5)

for i, v in enumerate(percentage_values):
    plt.text(x_locations[i], v + 0.01, str(round(v*100))+"%")

plt.title('Percentage of unlocked achievements for each game')
plt.xlabel('Games')
plt.ylabel('Unlocked achievements(%)')
plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
plt.tight_layout()
plt.show()

# Close chrome driver and connection to SQLite database
connection.close()
