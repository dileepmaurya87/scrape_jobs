import csv
from jobspy import scrape_jobs
import json
import datetime
import requests
from bs4 import BeautifulSoup
import random
import itertools
import time
from requests.exceptions import ReadTimeout

# Function to get free proxies from multiple public proxy list websites
def get_free_proxies():
    proxy_sources = [
        "https://free-proxy-list.net/",
        "https://www.sslproxies.org/",
        "https://www.us-proxy.org/"
    ]
    proxies = []

    for url in proxy_sources:
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            for row in soup.find('tbody').find_all('tr'):
                cols = row.find_all('td')
                if cols[6].text.strip() == 'yes':  # Filter for HTTPS proxies only
                    proxy = f"http://{cols[0].text.strip()}:{cols[1].text.strip()}"
                    proxies.append(proxy)
        except Exception as e:
            print(f"Error fetching proxies from {url}: {e}")

    return proxies

# Function to validate if a proxy is working
def is_proxy_valid(proxy):
    try:
        response = requests.get("https://httpbin.org/ip", proxies={"http": proxy, "https": proxy}, timeout=5)
        if response.status_code == 200:
            print(f"Valid proxy: {proxy}")
            return True
    except:
        pass
    print(f"Invalid proxy: {proxy}")
    return False

# Function to get a list of working proxies
# The number of proxies returned should match the results_wanted value
def get_working_proxies(proxies, limit):
    working_proxies = []
    for proxy in proxies:
        if is_proxy_valid(proxy):
            working_proxies.append(proxy)
        if len(working_proxies) >= limit:  # Limit the number of working proxies based on results_wanted
            break
    return working_proxies

# Main function to scrape jobs using proxy cycling
def scrape_jobs_with_proxies():
    results_wanted = 10  # Adjust this to the number of requests you want

    # Step 1: Fetch and validate free proxies
    proxies = get_free_proxies()
    print(f"Fetched {len(proxies)} proxies.")
    working_proxies = get_working_proxies(proxies, results_wanted)
    print(f"Found {len(working_proxies)} working proxies.")

    # Step 2: Ensure there are valid proxies to use
    if not working_proxies:
        print("No valid proxies found. Exiting.")
        return

    # Step 3: Create a cycle object to rotate through proxies indefinitely
    proxy_cycle = itertools.cycle(working_proxies)

    try:
        proxy = next(proxy_cycle)  # Get the first proxy
        current_attempt = 0
        max_attempts = len(working_proxies) * 2  # Max attempts to avoid infinite loops

        for i in range(results_wanted):
            while current_attempt < max_attempts:
                try:
                    # Scraping logic using the current proxy
                    jobs = scrape_jobs(
                        site_name=["linkedin"],
                        search_term="software engineer",
                        google_search_term="software engineer jobs near San Francisco, CA since yesterday",
                        location="San Francisco, CA",
                        results_wanted=10,  # Adjust as needed
                        hours_old=72,
                        country_indeed='USA',
                        linkedin_fetch_description=True,
                        proxies=[proxy]  # Use the current proxy
                    )
                    
                    print(f"Scraped data using proxy: {proxy}")
                    print(f"Found {len(jobs)} jobs")

                    if len(jobs) == 0:
                        raise Exception("No jobs found, possibly blocked or rate-limited.")

                    # Save jobs data to CSV
                    jobs.to_csv("jobs.csv", quoting=csv.QUOTE_NONNUMERIC, escapechar="\\", index=False, mode='a')

                    # Random delay to avoid rate limiting
                    time.sleep(random.randint(5, 15))
                    break  # Move to the next job request if successful

                except (ReadTimeout, Exception) as e:
                    print(f"Error with proxy {proxy}: {e}")
                    if "429" in str(e) or isinstance(e, ReadTimeout):
                        print(f"429 error or timeout encountered. Switching to next proxy.")
                        proxy = next(proxy_cycle)  # Switch to the next proxy
                        current_attempt += 1
                        time.sleep(10)  # Wait before trying the next proxy
                    else:
                        # For other errors, retry with the same proxy after waiting
                        time.sleep(10)

            # Reset proxy cycle after using all proxies
            if current_attempt >= max_attempts:
                print("All proxies used. Restarting from the first proxy.")
                current_attempt = 0
                proxy = next(proxy_cycle)

    except Exception as e:
        print(f"Error during job scraping: {e}")

# Run the main function
scrape_jobs_with_proxies()
