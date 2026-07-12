"""
A simple web scraper to extract article titles from a news website.

This script demonstrates how to fetch a web page and parse its HTML content
using the requests and BeautifulSoup libraries.
"""

# Import the necessary libraries
import requests
from bs4 import BeautifulSoup
import csv


def fetch_page(url):
    """
    Fetch the HTML content of a web page.

    Args:
        url (str): The URL of the page to fetch.

    Returns:
        str: The HTML content of the page, or None if an error occurred.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url, timeout=10)
        # Check if the request was successful
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"An error occurred while fetching the page: {e}")
        return None


def parse_titles(html):
    """
    Parse the article titles from the HTML content.

    Args:
        html (str): The HTML content to parse.

    Returns:
        list: A list of article titles.
    """
    # Create a BeautifulSoup object to parse the HTML
    soup = BeautifulSoup(html, "html.parser")
    titles = []
    # Find all the article title elements
    for heading in soup.find_all("h2", class_="article-title"):
        # Extract the text and strip any whitespace
        titles.append(heading.get_text().strip())
    return titles


def save_to_csv(titles, filename):
    """
    Save the extracted titles to a CSV file.

    Args:
        titles (list): The list of titles to save.
        filename (str): The name of the output CSV file.
    """
    # Open the CSV file for writing
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Write the header row
        writer.writerow(["Title"])
        # Write each title as a row
        for title in titles:
            writer.writerow([title])
    print(f"Successfully saved {len(titles)} titles to {filename}")


# Example usage
if __name__ == "__main__":
    # Replace with your target URL
    url = "https://example.com/news"
    # Step 1: Fetch the page content
    html = fetch_page(url)
    if html:
        # Step 2: Parse the article titles
        titles = parse_titles(html)
        # Step 3: Save the results to a CSV file
        save_to_csv(titles, "titles.csv")
