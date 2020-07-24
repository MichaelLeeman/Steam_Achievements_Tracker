import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from getpass import getpass
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


# Makes a GET request to the URL and retries the connection if a connection error occurs.
def get_request(URL_link, max_retry=3):
    current_page, request_worked, number_of_total_retries = None, False, 0
    while number_of_total_retries < max_retry and not request_worked:
        try:
            current_page = requests.get(URL_link, headers={"User-Agent": "Chrome/83.0"}, allow_redirects=False)
            request_worked = True
            return current_page
        except requests.exceptions.ConnectionError as err:
            print("Connection error to " + str(URL_link) + " has failed.")
            print("Retrying the connection to the URL attempt number: " + str(number_of_total_retries + 1))
            time.sleep((2 ** number_of_total_retries) - 1)  # Sleep times [ 0.0s, 1.0s, 3.0s]
            number_of_total_retries += 1
            if number_of_total_retries >= max_retry:
                raise err


URL = "https://steamcommunity.com/login/home/?goto=search%2Fusers%2F"

driver = webdriver.Chrome('./chromedriver')
driver.get(URL)

# Fill out the profile's username and password
username_element = driver.find_element_by_id('steamAccountName')
username = input("Steam username:")
username_element.send_keys(username)

password_element = driver.find_element_by_id('steamPassword')
password = getpass("Steam password:")
password_element.send_keys(password)

driver.find_element_by_id('SteamLogin').click()

# Wait for the pop-up to appear after logging in and ask the user to get the security code from their email
WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='auth_buttonset_entercode']/div[1]")))

email_code = input("Please type in your security code that was sent to your email address:").strip()
email_element = driver.find_element_by_id('authcode')
email_element.send_keys(email_code)

# Submit the security code and continue
driver.find_element_by_xpath("//div[@id='auth_buttonset_entercode']/div[1]").click()
driver.find_element_by_class_name("newmodal_close").click()

# Navigate to the user's games page by going to their profile first
time.sleep(5)
WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.XPATH, "//div[@class='responsive_page_content']/div[1]/div[1]/div[2]")))
driver.find_element_by_xpath("//div[@class='responsive_page_content']/div[1]/div[1]/div[2]").click()

WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.CLASS_NAME, "profile_menu_text")))
driver.find_element_by_class_name("profile_menu_text").click()
driver.find_element_by_xpath("//div[@class='responsive_count_link_area']/div[@class='profile_item_links']/div[1]/a[1]").click()

# Create a soup of the current page and iterate over the user's games
game_index = 1
games_soup = BeautifulSoup(driver.page_source, "html.parser")
time.sleep(5)
stats_buttons = games_soup.find_all("div", attrs={"id": re.compile(r"^stats_dropdown_")})

for game in games_soup.find_all(attrs={"class": "gameListRowItem"}):
    time.sleep(5)
    game_name = game.find("div", {"class": re.compile('^gameListRowItemName ellipsis.*')}).string

    # Some games that don't have achievements don't have the stats button available.
    time.sleep(5)
    button_links = game.find_all("div", attrs={"class": "pullup_item"})

    if len(button_links) >= 2:
        # Get the game's achievement page from the drop down menu
        stats_drop_down = stats_buttons[game_index-1]
        achievement_link = stats_drop_down.find("a")["href"]
        # Get the achievements stats from the game's achievements page
        driver.get(achievement_link)
        game_achievement_soup = BeautifulSoup(driver.page_source, "html.parser")
        time.sleep(5)

        # Some games without achievements returns a fatal error page
        if not game_achievement_soup.find_all("div", {"class": "profile_fatalerror"}):
            print("-" * 150)
            try:
                # Some games have their achievement percentage in the following way including Civ V
                game_achievement = game_achievement_soup.find(attrs={"id": "topSummaryAchievements"}).find("div").string
                print(game_name + ": " + game_achievement.strip().rstrip(":"))
            except AttributeError:
                try:
                    # Other games have the achievement percentage in a different element such as Holdfast
                    game_achievement = game_achievement_soup.find(attrs={"id": "topSummaryAchievements"}).stripped_strings
                    print(game_name + ": " + str(*(string for string in game_achievement)).rstrip(":").lower())
                except AttributeError:
                    # Games such as Team Fortress 2 represents the achievement page in a different format
                    game_achievement_text = game_achievement_soup.find("option",
                                                                       {"value": "all",
                                                                        "selected": "selected"}).string.strip()
                    words = game_achievement_text.split()
                    achievements_unlocked = words[2].strip().lstrip("(")
                    total_achievements = words[4].strip().rstrip(")")
                    achievements_percentage = str(round((int(achievements_unlocked) / int(total_achievements)) * 100))
                    print(
                        game_name + ": " + achievements_unlocked + " of " + total_achievements + " (" + achievements_percentage + "%) achievements earned")
            driver.back()
        else:
            print("-" * 150)
            print(game_name + ": 0 of 0 (0%) achievements earned")
            driver.back()
    else:
        print("-" * 150)
        print(game_name + ": 0 of 0 (0%) achievements earned")
        game_index -= 1

    game_index += 1
