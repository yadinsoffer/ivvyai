import time
import schedule
import webbrowser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import random
import pyautogui  # Import pyautogui for GUI automation
import subprocess  # Import subprocess to run shell commands
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to join the meeting
def join_meeting(meeting_url):
    logging.info(f"Attempting to join meeting: {meeting_url}")
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("user-data-dir=/Users/yadinsoffer/Library/Application Support/Google/Chrome")  # User data directory
    chrome_options.add_argument("profile-directory=Profile 2")  # Use the correct profile
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Add additional options to help with session creation
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
   # chrome_options.add_argument("--headless")  # Uncomment this line to run in headless mode

    # Specify the path to the downloaded ChromeDriver
    chrome_driver_path = '/Users/yadinsoffer/Downloads/chromedriver-mac-arm64/chromedriver'  # Update this path
    
    try:
        # Initialize the Chrome driver
        logging.debug("Initializing Chrome driver...")
        service = Service(executable_path=chrome_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logging.info("Chrome driver initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Chrome driver: {e}")
        return  # Exit the function if driver initialization fails

    # Open the meeting URL
    try:
        logging.info(f"Opening meeting URL: {meeting_url}")
        driver.get(meeting_url)
    except Exception as e:
        logging.error(f"Failed to open meeting URL: {e}")
        driver.quit()
        return

    # Wait for the page to load
    time.sleep(random.uniform(2, 5))  # Sleep for a random time between 2 and 5 seconds
    logging.debug("Waited for the page to load.")

    # Check if the meeting URL is for Google Meet or Zoom
    if "meet.google.com" in meeting_url:
        logging.info("Detected Google Meet URL.")
        # Logic for Google Meet
        try:
            join_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Join now')]")
            join_button.click()
            logging.info("Clicked 'Join now' button.")
        except Exception as e:
            logging.error(f"Error joining the Google Meet: {e}")
    elif "zoom.us" in meeting_url:
        logging.info("Detected Zoom URL.")
        # Logic for Zoom
        print("If prompted, please allow the browser to open the Zoom application.")
        
        # Wait for the Zoom application to open
        time.sleep(5)  # Adjust this time as needed to ensure the Zoom app is open

        # Enter the name in the Zoom application
        pyautogui.typewrite("Ivvy")  # Replace with the desired name
        time.sleep(1)  # Wait a moment for the text to be entered

        # Click the "Join" button
        pyautogui.press('enter')  # Press Enter to click the "Join" button

    # Keep the browser open for a while to allow user interaction
    logging.info("Joined the meeting. Press Ctrl+C to exit.")

    # Start the OpenAI Realtime Console
    start_openai_console()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Exiting the meeting.")
        driver.quit()

# Function to start the OpenAI Realtime Console
def start_openai_console():
    print("Starting OpenAI Realtime Console...")
    # Run the command to start the console
    subprocess.run(["npm", "start"], cwd="/Users/yadinsoffer/ivvyai/ivprod/openai-realtime-console")

# Function to schedule multiple meetings
def schedule_meetings():
    response = requests.get('http://localhost:61372/api/meetings')  # Fetch meeting details from the API
    meetings = response.json()  # Assuming the response is a JSON list of meeting details

    for meeting in meetings:  # Assuming 'meetings' is a list of meeting dictionaries
        
        # Check if 'link' key exists and is not None before accessing it
        if 'link' in meeting and meeting['link'] is not None:
            meeting_url = meeting['link']  # Use 'link' instead of 'url'
            meeting_time = meeting['time']
            meeting_date = meeting['date']
            
            # Schedule the meeting
            schedule.every().day.at(meeting_time).do(join_meeting, meeting_url)

            # Print only the required parameters
            print(f"Date: {meeting_date}, Time: {meeting_time}, Link: {meeting_url}")
        else:
            # Optionally, you can print a warning if you want to keep track of skipped meetings
            # print("Warning: 'link' is None or not found in meeting dictionary:", meeting)
            continue  # Skip this meeting or handle it as needed

    while True:
        schedule.run_pending()
        time.sleep(1)

# Example usage
if __name__ == "__main__":
    schedule_meetings()
