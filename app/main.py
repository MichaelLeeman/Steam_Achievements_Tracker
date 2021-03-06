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
print("Total Number of Remaining Locked Achievements = {}".format(str(total_achievements-achievements_unlocked)))

# Calculate total number of locked achievements to be unlocked
total_play_time = pandas.to_numeric(df.play_time).sum()
print("Total Time Played across all Games = {}".format(str(int(round(total_play_time, 1)))) + " hours")


# Plotting bar graphs
def plot_bar_graph(x_data, y_data, y_data_type, title, x_label, y_label):
    plt.figure()
    plt.bar(x_data, y_data)
    x_locations, x_labs = plt.xticks(rotation=90)
    plt.tick_params(axis='x', which='major', labelsize=7.5)

    for i, value in enumerate(y_data):
        if y_data_type == "percentage":
            bar_value = str(round(value*100))+'%'
        elif y_data_type == "time":
            bar_value = str(round(value)) + " hrs"
        plt.text(x_locations[i], value + 0.01, bar_value)

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)

    if y_data_type == "percentage":
        plt.gca().yaxis.set_major_formatter(PercentFormatter(1))

    plt.tight_layout()


# Plotting the Achievements bar chart
cur.execute("SELECT name, achievement_percentage FROM achievements")
achievements_data = cur.fetchall()
game_names, percentage_values = [], []

for row in achievements_data:
    if row[1] != "0%":
        game_names.append(row[0])
        percentage_values.append(int(row[1].rstrip("%"))/100)

title = 'Percentage of unlocked achievements for each game'
x_label = 'Games'
y_label = 'Unlocked achievements(%)'
plot_bar_graph(game_names, percentage_values, "percentage", title, x_label, y_label)

# Plotting the Play Time Bar Chart
cur.execute("SELECT name, play_time FROM achievements")
play_time_data = cur.fetchall()
game_names, play_times = [], []

for row in play_time_data:
    if row[1] != 0.0:
        game_names.append(row[0])
        play_times.append(row[1])

title = 'Play time for each game(Hrs)'
x_label = 'Games'
y_label = 'Play Time(Hrs)'
plot_bar_graph(game_names, play_times, "time", title, x_label, y_label)

# Bar graph for number of unlocked achievements per game
cur.execute("SELECT name, unlocked_achievements FROM achievements")
unlocked_achievement_data = cur.fetchall()
game_names, number_of_unlocked_games = [], []

for row in unlocked_achievement_data:
    if row[1] != 0:
        game_names.append(row[0])
        number_of_unlocked_games.append(int(row[1]))

plt.figure()
plt.bar(game_names, number_of_unlocked_games)
x_locations, x_labs = plt.xticks(rotation=90)
plt.tick_params(axis='x', which='major', labelsize=7.5)

plt.title("Number of unlocked achievements per game")
plt.xlabel("Game")
plt.ylabel("Number of unlocked achievements")

plt.tight_layout()
plt.show()

# Close chrome driver and connection to SQLite database
connection.close()
