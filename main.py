import time
import pickle
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================
# 1. Setup Selenium
# ==========================
options = webdriver.ChromeOptions()
# options.add_argument("--headless=new")   # comment this if you want to see the browser
driver = webdriver.Chrome(service=Service(), options=options)

cookies_file = "amazon_cookies.pkl"

#save the cookies
def save_cookies():
    pickle.dump(driver.get_cookies(), open(cookies_file, "wb"))
    print("💾 Cookies saved!")
# load cookies
def load_cookies(url):
    try:
        cookies = pickle.load(open(cookies_file, "rb"))
        driver.get(url)
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()
        print("✅ Cookies loaded successfully")
        return True
    except Exception as e:
        print("⚠️ Could not load cookies:", e)
        return False

# ==========================
# Login manually (one-time)
# ==========================
def manual_login(reviews_url):
    print("🔐 Please log in manually...")
    driver.get(reviews_url)
    input("👉 Press ENTER here *after* you finish logging in (including OTP).")
    save_cookies()
    print("✅ Login completed and cookies saved!")
# ==========================
# 5. Scraping Products
# ==========================
search_query = "lancome"
url = f"https://www.amazon.sa/s?k={search_query}"

# First try to load cookies
load_cookies(url)
time.sleep(3)
current_product_page = 1
max_product_pages = 7
number_product = 0
all_reviews = []
while current_product_page <= max_product_pages:
    search_query = "lancome"
    url = f"https://www.amazon.sa/s?k={search_query}&page={current_product_page}"

    # # First try to load cookies
    # load_cookies(url)
    # time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")


    products = soup.select("div.s-main-slot div[data-asin]")
    print(f"🔎 Found {len(products)} products")
    
    i = 1
    # loop in each product 
    for p in products:
        asin = p.get("data-asin")
        if not asin:
            continue

        # select title, link, rating and price
        title_tag = p.select_one("a h2 span")
        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        link_tag = p.select_one(".a-link-normal")
        product_link = "https://www.amazon.sa" + link_tag["href"] if link_tag else "N/A"
        overal_rating = p.select_one("i span.a-icon-alt")
        overal_rating = overal_rating.get_text(strip=True) if overal_rating else "N/A"
        price_tag = p.select_one("span.a-price span.a-offscreen")
        price = price_tag.get_text(strip=True) if price_tag else "N/A"
        # print the products features in the console 
        print(f"\n============================")
        print(f"📦 Product {number_product + i}: {title}")
        print(f"Price : {price}")
        print(f"overal rating : {overal_rating}")
        print(f"🔗 {product_link}")
        print(f"ASIN: {asin}")

        # Build reviews URL
        reviews_url = f"https://www.amazon.sa/product-reviews/{asin}"
        driver.get(reviews_url)
        time.sleep(3)

        current_url = driver.current_url
        print(f"🌍 Opened reviews page: {current_url}")
        if "signin" in current_url:
            print(f"❌ Login required again for {asin}, retrying login...")
            manual_login(reviews_url)
            driver.get(reviews_url)
            time.sleep(3)
        
        page = 1
        max_pages = 10
        number_reviews = 0
        # while loop to navigate in many review page 
        while page <= max_pages:
            review_soup = BeautifulSoup(driver.page_source, "html.parser")
            reviews = review_soup.select(".review")  # keep your working selector

            if not reviews:
                print(f"⚠️ No reviews found on page {page} for {title}")
                break
            for r in reviews:
                #select all the reviews in the page 
                reviewer = r.select_one("span.a-profile-name")
                reviewer = reviewer.get_text(strip=True) if reviewer else "N/A"
                rating = r.select_one("i span.a-icon-alt")
                rating = rating.get_text(strip=True) if rating else "N/A"
                review_title = r.select_one(".review-title span.cr-original-review-content")
                review_title = review_title.get_text(strip=True) if review_title else "N/A"
                review_text = r.select_one("span.review-text-content span")
                review_text = review_text.get_text(strip=True) if review_text else "N/A"
                review_date = r.select_one(".review-date")
                review_date = review_date.get_text(strip=True) if review_date else "N/A"
                # print Reviewer, Rating , Title, Review, Review Datein the console 
                print(f"👤 Reviewer: {reviewer}")
                print(f"⭐ Rating: {rating}")
                print(f"📝 Title: {review_title}")
                print(f"💬 Review: {review_text[:200]}...")
                print(f"📅 Review Date: {review_date}")
                print(" ----------- \n")
                # add the reviews 
                all_reviews.append({
                    "reviewer": reviewer,
                    "product_title": title,
                    "rating": rating,
                    "review_title": review_title,
                    "review_date": review_date,
                    "review_text": review_text,
                    "product_url": product_link,
                    "product_price": price,
                    "overal rating" : overal_rating,
                    "Product Id": asin
                })
            number_reviews += len(reviews)
            print(f"✅ Collected {number_reviews} reviews,  page {page} for {title}")
            try:
                # wait for the "Next page" button (li.a-last a)
                next_page_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "li.a-last a")))

                # click the button to go to the next review page 
                driver.execute_script("arguments[0].click();", next_page_btn)

                page += 1
                time.sleep(3)  # let the reviews load

            except:
                print("🚪 No more review pages (button not found)")
                break
        i += 1
        number_product += 1
    print(f"➡ Moving to next search page...")
    current_product_page += 1

# ==========================
# 6. Save to Excel
# ==========================
if all_reviews:
    df = pd.DataFrame(all_reviews)
    df.to_csv("lancome_reviews.csv", index=False)
    print("💾 Reviews saved to amazon_reviews.xlsx")
else:
    print("⚠️ No reviews collected at all")

driver.quit()
