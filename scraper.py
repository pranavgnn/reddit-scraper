from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime

class Scraper:

    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        # chrome_options.add_experimental_option("detach", True)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36")
        self.driver = webdriver.Chrome(options=chrome_options)


    def format_string(self, string: str):

        replacements = {
            u"\u2018": "'",
            u"\u2019": "'",
            u"\u201C": "\"",
            u"\u201D": "\"",
            u"\u2014": "-",
            u"\u2013": "-",
            u"\u2026": "...",
        }

        for key, value in replacements.items():
            string = string.replace(key, value)

        return string
    

    def extract_comments(self, container, visited_comment_ids = []):

        comments = []

        comment_divs = container.find_elements(By.XPATH, ".//div[contains(@id, 'thing_t1')]")

        for comment_div in comment_divs:
            id = comment_div.get_attribute("data-fullname").split("_")[-1]
            if id in visited_comment_ids:
                continue

            author = comment_div.get_attribute("data-author")

            tagline = comment_div.find_element(By.XPATH, ".//p[contains(@class, 'tagline')]")

            timestamp = tagline.find_element(By.XPATH, ".//time").get_attribute("datetime")
            timestamp = int(datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z").timestamp() * 1000)

            score = tagline.find_element(By.XPATH, ".//span[contains(@class, 'score')]").get_attribute("title")
            try:
                score = int(score.split(" ")[0])
            except:
                score = "hidden"

            content = comment_div.find_element(By.XPATH, ".//div[contains(@class, 'md')]").text
            content = self.format_string(content)

            data = {
                "id": id,
                "content": content,
                "score": score,
                "author": author,
                "timestamp": timestamp,
                "replies_count": 0,
                "replies": [],
            }

            try:
                reply_container = comment_div.find_element(By.XPATH, ".//div[contains(@id, 'siteTable_t1_')]")
                replies = self.extract_comments(reply_container, visited_comment_ids)

                data["replies_count"] = len(data["replies"])
                data["replies"] = replies
            except:
                pass

            comments.append(data)
            visited_comment_ids.append(id)

        return comments
    

    def scrape(self, url: str):
        if url.find("redd.it"):
            url = "https://old.reddit.com/" + url.split("/")[-1]
        else:
            url = url.replace("www", "old")

        self.driver.get(url)

        post_container = self.driver.find_element(By.XPATH, "//div[@id='siteTable']")
        meta_div = post_container.find_element(By.XPATH, ".//div")
        expando_container = post_container.find_element(By.XPATH, ".//div[contains(@class, 'expando')]")

        id = meta_div.get_attribute("data-fullname").split("_")[-1]
        author = meta_div.get_attribute("data-author")
        timestamp = int(meta_div.get_attribute("data-timestamp"))
        subreddit = meta_div.get_attribute("data-subreddit")
        comments_count = int(meta_div.get_attribute("data-comments-count"))
        score = int(meta_div.get_attribute("data-score"))

        title = post_container.find_element(By.XPATH, ".//a[contains(@class, 'title')]").text
        title = self.format_string(title)

        content = ""
        attachments = []
        try:
            content = expando_container.find_element(By.XPATH, ".//div[contains(@class, 'md')]").text
            attachments = [img.get_attribute("src") for img in expando_container.find_elements(By.XPATH, ".//img")]
        except:
            content = expando_container.text
        content = self.format_string(content)

        comments_container = self.driver.find_element(By.XPATH, "//div[starts-with(@id, 'siteTable_t3_')]")
        comments = self.extract_comments(comments_container)

        data = {
            "id": id,
            "title": title,
            "content": content,
            "attachments": attachments,
            "score": score,
            "author": author,
            "timestamp": timestamp,
            "subreddit": subreddit,
            "comments_count": comments_count,
            "comments": comments,
        }

        return data


if __name__ == "__main__":
    import json
    import sys

    scraper = Scraper()
    data = scraper.scrape(sys.argv[1]) # https://redd.it/1h78sw0, to test run `python scraper.py https://redd.it/1h78sw0`

    with open(f"{data["subreddit"]}-{data["id"]}.json", "w") as f:
        json.dump(data, f)