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
                    achievement_percentage text,
                    play_time float
                    )""")
try:
    cur.execute("""CREATE UNIQUE INDEX idx_game ON achievements (name)""")
except sqlite3.OperationalError:
    pass

# Ask user if they have a steam profile or use an example
answer = input("""Welcome to the Steam Achievement Pandas Analysis app. 

Please choose whether you want to analyse your own Steam profile's achievement progress [Type "1"] or run the demo [Type "2"]. 
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
        cur.execute(
            """REPLACE INTO achievements (name, unlocked_achievements, total_achievements, achievement_percentage, play_time) VALUES (?, ?, ?, ?, ?)""", game)
else:
    print("Processing the example data for the demo")
    game_data_list = [("Sid Meier's Civilization V", "107", "286", "37%", 237), ("Dishonored", "28", "80", "35%", 50), ("The Elder Scrolls V: Skyrim", "3", "75", "4%", 145), ("Left 4 Dead 2", "54", "100", "54%", 83), ("Cities: Skylines", "26", "111", "23%", 21)]
    cur.execute("DELETE FROM achievements")
    for game in game_data_list:
        game_message = "{0}: {1} of {2} ({3}) achievements earned".format(game[0], game[1], game[2], game[3])
        steam_scraper.output_stats_message(game_message, game[3])
        cur.execute(
            """INSERT INTO achievements (name, unlocked_achievements, total_achievements, achievement_percentage, play_time) VALUES (?, ?, ?, ?, ?)""", game)

# Get all games with achievements enabled to calculate Average Game Rate Completion
df = pandas.read_sql_query("SELECT * FROM achievements", con=connection)

# Calculate Average Game Rate Completion
print("-" * 150)
number_of_games = len(df[df.achievement_percentage != '0%'])
sum_of_percentages = pandas.to_numeric(df.achievement_percentage.str.replace("%", "")).sum()
average_game_completion = math.floor(sum_of_percentages / number_of_games)
print("Average Game Completion Rate = {}%".format(str(average_game_completion)))

# Calculate total number of achievements unlocked
achievements_unlocked = pandas.to_numeric(df.unlocked_achievements).sum()
print("Total Number of Achievements Unlocked = {}".format(str(achievements_unlocked)))

# Calculate total number of locked achievements to be unlocked
total_achievements = pandas.to_numeric(df.total_achievements).sum()
print("Total Number of Locked Achievements = {}".format(str(total_achievements-achievements_unlocked)))

# Calculate total number of locked achievements to be unlocked
total_play_time = pandas.to_numeric(df.play_time).sum()
print("Total Play Time = {}".format(str(round(total_play_time, 1))))

# Plotting the Achievements bar chart
cur.execute("SELECT name, achievement_percentage FROM achievements")
achievements_data = cur.fetchall()
game_names, percentage_values = [], []

for row in achievements_data:
    if row[1] != "0%":
        game_names.append(row[0])
        percentage_values.append(int(row[1].rstrip("%"))/100)

plt.figure()
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


# Plotting the Play Time Bar Chart
cur.execute("SELECT name, play_time FROM achievements")
play_time_data = cur.fetchall()
game_names, play_times = [], []

for row in play_time_data:
    if row[1] != 0.0:
        game_names.append(row[0])
        play_times.append(row[1])

plt.figure()
plt.bar(game_names, play_times)
x_locations, x_labs = plt.xticks(rotation=90)
plt.tick_params(axis='x', which='major', labelsize=7.5)

for i, v in enumerate(play_times):
    plt.text(x_locations[i], v + 0.01, v)

plt.title('How long each game has been played')
plt.xlabel('Games')
plt.ylabel('Play Time (Hours)')
plt.tight_layout()
plt.show()

# Close chrome driver and connection to SQLite database
connection.close()
