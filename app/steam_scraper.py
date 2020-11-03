import sys
import time
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from bs4 import BeautifulSoup
import re


# Log in to Steam with the user's username and password
def log_in(driver, username, password):
    username_element = driver.find_element_by_id('input_username')
    username_element.click()
    username_element.clear()
    username_element.send_keys(username)

    password_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'input_password')))
    password_element.click()
    password_element.clear()
    password_element.send_keys(password)

    driver.find_element_by_xpath("//div[@id='login_btn_signin']/button[1]").click()

    # Handle login errors including too many log-ins and wrong credentials
    time.sleep(5)
    if driver.find_element_by_id('error_display').is_displayed():
        error_text = driver.find_element_by_id('error_display').text
        print(error_text)
        # If the error is "too many logins" error then close the application
        if "too many login failures" in error_text:
            sys.exit("Stopping application. Try again later")
        else:
            # While the login credentials are incorrect, keep asking the user for the correct credentials
            while driver.find_element_by_id('error_display').is_displayed():
                print("Please give your Steam username and password again.\n")
                return False
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'error_display')))
    else:
        return True


# After logging in, ask the user for the security code from their email
def enter_email_code(driver, email_code):
    # wait for the email code pop-up to appear before entering it
    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable((By.XPATH, "//div[@id='auth_buttonset_entercode']/div[1]")))
    email_element = driver.find_element_by_id('authcode')
    email_element.send_keys(email_code)

    # Submit the security code and continue
    driver.find_element_by_xpath("//div[@id='auth_buttonset_entercode']/div[1]").click()
    try:
        driver.find_element_by_class_name("newmodal_close").click()
    except ElementNotInteractableException:
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "success_continue_btn"))).click()

    # If the provided email code is incorrect then ask again
    time.sleep(3)
    if driver.current_url == "https://steamcommunity.com/login/home/?goto=search%2Fusers%2F":
        print("\nSecurity code is incorrect. Please try again.\n")
        return False
    else:
        return True


# Navigate to the user's games page by going to their profile first
def go_to_games_page(driver):
    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable((By.XPATH, "//div[@class='responsive_page_content']/div[1]/div[1]/div[2]"))).click()

    WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.CLASS_NAME, "profile_menu_text"))).click()
    driver.find_element_by_xpath(
        "//div[@class='responsive_count_link_area']/div[@class='profile_item_links']/div[1]/a[1]").click()
    return "\nNavigating to your games page"


# Formatting the output string of game data
def string_format(achievement_stats, unlocked_achievements_pos=0, total_achievements_pos=2):
    print(achievement_stats)
    stats_in_text = achievement_stats.split()
    achievements_unlocked = stats_in_text[unlocked_achievements_pos].strip().lstrip("(")
    total_achievements = stats_in_text[total_achievements_pos].strip().rstrip(")")
    achievements_percentage = str(round((int(achievements_unlocked) / int(total_achievements)) * 100)) + "%"
    return achievements_unlocked, total_achievements, achievements_percentage


# Prints the output message for the game's achievement stats
def output_stats_message(achievement_text, playtime_text):
    print("-" * 150)
    print(achievement_text + '\n' + playtime_text)


# Create a soup of the current page and iterate over the user's games
def get_game_data(driver):
    game_index, game_data_list = 1, []
    games_soup = BeautifulSoup(driver.page_source, "html.parser")
    stats_buttons = games_soup.find_all("div", attrs={"id": re.compile(r"^stats_dropdown_")})

    for game in games_soup.find_all(attrs={"class": "gameListRowItem"}):
        game_name = game.find("div", {"class": re.compile('^gameListRowItemName ellipsis.*')}).string
        hours_played = game.find("h5", {"class": 'ellipsis hours_played'}).string

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
                try:
                    # Some games has their achievement percentage in the following element including Civ V
                    achievement_stats = game_achievement_soup.find(attrs={"id": "topSummaryAchievements"}).find(
                        "div").string.strip().rstrip(":")
                    output_stats_message(game_name + ": " + achievement_stats, hours_played)
                    achievements_unlocked, total_achievements, achievements_percentage = string_format(
                        achievement_stats)
                except AttributeError:
                    try:
                        # Other games have the achievement percentage in a different element such as Holdfast
                        achievement_stats_text = game_achievement_soup.find(
                            attrs={"id": "topSummaryAchievements"}).stripped_strings
                        achievement_stats = str(*(string for string in achievement_stats_text)).rstrip(":").lower()
                        output_stats_message(game_name + ": " + achievement_stats, hours_played)
                        achievements_unlocked, total_achievements, achievements_percentage = string_format(
                            achievement_stats)
                    except AttributeError:
                        # Games such as Team Fortress 2 presents the achievement page in a different format
                        achievement_stats = game_achievement_soup.find("option",
                                                                       {"value": "all",
                                                                        "selected": "selected"}).string.strip()
                        achievements_unlocked, total_achievements, achievements_percentage = string_format(
                            achievement_stats, unlocked_achievements_pos=2, total_achievements_pos=4)
                        output_stats_message(
                            "{0}: {1} of {2} ({3}) achievements earned".format(game_name, achievements_unlocked,
                                                                               total_achievements,
                                                                               achievements_percentage), hours_played)
            else:
                # If the game's achievement page does return a fatal error then it has no achievements
                output_stats_message(game_name + ": No unlockable steam achievements", hours_played)

            game_data_list.append((game_name, achievements_unlocked, total_achievements, achievements_percentage))
            driver.back()
        else:
            # Some games don't provide a stats button on the user's games page meaning that these games don't have achievements
            output_stats_message(game_name + ": No unlockable steam achievements", hours_played)
            game_index -= 1
        game_index += 1
    return game_data_list
