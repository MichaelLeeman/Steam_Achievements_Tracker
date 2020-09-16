import pandas
import math
import re
import requests
import sqlite3
import sys
import time
from getpass import getpass
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


# Makes a GET request to the URL and retries the connection if a connection error occurs.
def get_request(URL_link, max_retry=3):
    current_page, request_worked, number_of_total_retries = None, False, 0
    while number_of_total_retries < max_retry and not request_worked:
        try:
            current_page = requests.get(URL_link, headers={"User-Agent": "Chrome/85.0"}, allow_redirects=False)
            request_worked = True
            return current_page
        except requests.exceptions.ConnectionError as err:
            print("Connection error to " + str(URL_link) + " has failed.")
            print("Retrying the connection to the URL attempt number: " + str(number_of_total_retries + 1))
            time.sleep((2 ** number_of_total_retries) - 1)  # Sleep times [ 0.0s, 1.0s, 3.0s]
            number_of_total_retries += 1
            if number_of_total_retries >= max_retry:
                raise err


# Sign in to Steam with the user's username and password
def steam_sign_in():
    username_element = driver.find_element_by_id('steamAccountName')
    username_element.click()
    username_element.clear()
    username = input("Steam username:")
    username_element.send_keys(username)

    password_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'steamPassword')))
    password_element.click()
    password_element.clear()
    password = getpass("Steam password:")
    password_element.send_keys(password)

    driver.find_element_by_id('SteamLogin').click()


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

# Starts selenium in the steam login page and sign-in
sign_in_URL = "https://steamcommunity.com/login/home/?goto=search%2Fusers%2F"
driver = webdriver.Chrome('./chromedriver')
driver.get(sign_in_URL)
steam_sign_in()

# Handle login errors including too many log-ins and wrong credentials
time.sleep(2)
if driver.find_element_by_id('error_display').is_displayed():
    error_text = driver.find_element_by_id('error_display').text
    print(error_text)
    # If the error is "too many logins" error then close the application
    if "too many login failures" in error_text:
        sys.exit("Stopping application. Try again later")
    else:
        # While the login credentials are incorrect, keep asking the user for the correct credentials
        while driver.find_element_by_id('error_display').is_displayed():
            print("Username or password incorrect. Please give your Steam username and password again.\n")
            steam_sign_in()
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'error_display')))

# Wait for the pop-up to appear after logging in and ask the user to get the security code from their email
WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='auth_buttonset_entercode']/div[1]")))
email_code = input("Please type in your security code that was sent to your email address:").strip()
email_element = driver.find_element_by_id('authcode')
email_element.send_keys(email_code)

# Submit the security code and continue
driver.find_element_by_xpath("//div[@id='auth_buttonset_entercode']/div[1]").click()
driver.find_element_by_class_name("newmodal_close").click()

# Check whether the given email code is correct by seeing whether the user is still stuck at the log-in page.
time.sleep(3)
while driver.current_url == sign_in_URL:
    print("\nSecurity code is incorrect. Please try again.\n")
    new_email_code = input("Please type in your security code that was sent to your email address:").strip()
    email_element = driver.find_element_by_id("authcode")
    email_element.click()
    email_element.clear()
    email_element.send_keys(new_email_code)
    driver.find_element_by_xpath("//div[@id='auth_buttonset_entercode']/div[1]").click()
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.ID, "success_continue_btn"))).click()
    except TimeoutException:
        pass
    time.sleep(3)

# Navigate to the user's games page by going to their profile first
WebDriverWait(driver, 60).until(
    EC.element_to_be_clickable((By.XPATH, "//div[@class='responsive_page_content']/div[1]/div[1]/div[2]"))).click()

WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.CLASS_NAME, "profile_menu_text"))).click()
driver.find_element_by_xpath(
    "//div[@class='responsive_count_link_area']/div[@class='profile_item_links']/div[1]/a[1]").click()

# Create a soup of the current page and iterate over the user's games
game_index = 1
games_soup = BeautifulSoup(driver.page_source, "html.parser")
time.sleep(5)
stats_buttons = games_soup.find_all("div", attrs={"id": re.compile(r"^stats_dropdown_")})

for game in games_soup.find_all(attrs={"class": "gameListRowItem"}):
    game_name = game.find("div", {"class": re.compile('^gameListRowItemName ellipsis.*')}).string

    # Some games that don't have achievements also don't have the stats button available.
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
                # Some games have their achievement percentage in the following way including Civ V
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
                    # Games such as Team Fortress 2 represents the achievement page in a different format
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
    df = pandas.read_sql_query(""" SELECT DISTINCT name, unlocked_achievements, total_achievements,
                 achievement_percentage FROM achievements""", con=connection)

# Calculate Average Game Rate Completion
number_of_games = len(df[df.achievement_percentage != '0%'])
sum_of_percentages = pandas.to_numeric(df.achievement_percentage.str.replace("%", "")).sum()
average_game_completion = math.floor(sum_of_percentages / number_of_games)
print("Average Game Completion Rate = {}%".format(str(average_game_completion)))

# Calculate total number of achievements unlocked
total_achievements_unlocked = pandas.to_numeric(df.unlocked_achievements).sum()
print("Total Number of Achievements Unlocked = {}".format(str(total_achievements_unlocked)))

connection.close()
driver.close()
