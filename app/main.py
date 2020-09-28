from app import steam_web_scraper
import pandas
import math
import re
import sqlite3
import time
from getpass import getpass
from bs4 import BeautifulSoup
from selenium import webdriver
import matplotlib.pyplot as plt


# Create the sqlite3 database in memory. If the database doesn't have the achievements table then create it.
from app.steam_web_scraper import go_to_games_page

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

# Starts selenium in the steam login page
sign_in_URL = "https://steamcommunity.com/login/home/?goto=search%2Fusers%2F"
driver = webdriver.Chrome('./chromedriver')
driver.get(sign_in_URL)
logged_in, correct_code = False, False

# Log in to steam. Loop around until the correct credentials are given
while not logged_in:
    username = input("Steam username:")
    password = getpass("Steam password:")
    logged_in = steam_web_scraper.log_in(driver, username, password)

# Enter the security code sent to the user's email
while not correct_code:
    email_code = input("Please type in your security code that was sent to your email address:").strip()
    correct_code = steam_web_scraper.enter_email_code(driver, email_code)

# Go to the user's game page
output_message = steam_web_scraper.go_to_games_page(driver)
print(output_message)

# Create a soup of the current page and iterate over the user's games
game_index = 1
games_soup = BeautifulSoup(driver.page_source, "html.parser")
time.sleep(5)
stats_buttons = games_soup.find_all("div", attrs={"id": re.compile(r"^stats_dropdown_")})

for game in games_soup.find_all(attrs={"class": "gameListRowItem"}):
    game_name = game.find("div", {"class": re.compile('^gameListRowItemName ellipsis.*')}).string

    # Some games that don't have achievements, some don't have the stats button available.
    button_links = game.find_all("div", attrs={"class": "pullup_item"})
    if len(button_links) >= 2:
        # Get the game's achievement page from the drop down menu
        stats_drop_down = stats_buttons[game_index - 1]
        achievement_link = stats_drop_down.find("a")["href"]
        # Get the achievements stats from the game's achievements page
        driver.get(achievement_link)
        game_achievement_soup = BeautifulSoup(driver.page_source, "html.parser")
        time.sleep(5)
        achievements_unlocked, total_achievements, achievements_percentage = None, None, None
        # If the game has achievements then the game's achievement page should not return a fatal error
        if not game_achievement_soup.find_all("div", {"class": "profile_fatalerror"}):
            print("-" * 150)
            try:
                # Some games has their achievement percentage in the following element including Civ V
                achievement_stats = game_achievement_soup.find(attrs={"id": "topSummaryAchievements"}).find(
                    "div").string.strip().rstrip(":")
                print(game_name + ": " + achievement_stats)
                stats_in_text = achievement_stats.split()
                achievements_unlocked = stats_in_text[0].strip()
                total_achievements = stats_in_text[2].strip()
                achievements_percentage = stats_in_text[3].rstrip(")").lstrip("(")
            except AttributeError:
                try:
                    # Other games have the achievement percentage in a different element such as Holdfast
                    achievement_stats_text = game_achievement_soup.find(
                        attrs={"id": "topSummaryAchievements"}).stripped_strings
                    achievement_stats = str(*(string for string in achievement_stats_text)).rstrip(":").lower()
                    print(game_name + ": " + achievement_stats)
                    stats_in_text = achievement_stats.split()
                    achievements_unlocked = stats_in_text[0].strip()
                    total_achievements = stats_in_text[2].strip()
                    achievements_percentage = stats_in_text[3].rstrip(")").lstrip("(")
                except AttributeError:
                    # Games such as Team Fortress 2 presents the achievement page in a different format
                    achievement_stats_text = game_achievement_soup.find("option",
                                                                        {"value": "all",
                                                                         "selected": "selected"}).string.strip()
                    words_in_text = achievement_stats_text.split()
                    achievements_unlocked = words_in_text[2].strip().lstrip("(")
                    total_achievements = words_in_text[4].strip().rstrip(")")
                    achievements_percentage = str(
                        round((int(achievements_unlocked) / int(total_achievements)) * 100)) + "%"
                    print("{0}: {1} of {2} ({3}) achievements earned".format(game_name, achievements_unlocked,
                                                                             total_achievements,
                                                                             achievements_percentage))
        else:
            # If the game's achievement page does return a fatal error then it has no achievements
            print("-" * 150)
            print(game_name + ": 0 of 0 (0%) achievements earned")

        # Add data to the SQLite database
        with connection:
            cur.execute(
                """REPLACE INTO achievements (name, unlocked_achievements,total_achievements,achievement_percentage) VALUES (?, ?, ?, ?)""",
                (game_name, achievements_unlocked, total_achievements, achievements_percentage))
        driver.back()
    else:
        # Some games don't provide a stats button on the user's games page meaning that these games don't have achievements
        print("-" * 150)
        print(game_name + ": 0 of 0 (0%) achievements earned")
        game_index -= 1
    game_index += 1

print("-" * 150)

# Get all games with achievements enabled to calculate Average Game Rate Completion
with connection:
    df = pandas.read_sql_query("SELECT * FROM achievements", con=connection)

# header=0, delim_whitespace=True
# Calculate Average Game Rate Completion
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
plt.tight_layout()

for i, v in enumerate(percentage_values):
    plt.text(x_locations[i], v + 0.01, str(round(v*100))+"%")

plt.title('Percentage of unlocked achievements for each game')
plt.xlabel('Games')
plt.ylabel('Unlocked achievements')
plt.show()

# Close chrome driver and connection to SQLite database
connection.close()
driver.close()