#!/usr/bin/python3
from bs4 import BeautifulSoup
from time import gmtime, strftime
import aiohttp
import asyncio
import async_timeout
import datetime
import json
import re
import sys
import time

async def getUrl(init):
    if init == -1:
        url = "https://twitter.com/search?f=tweets&vertical=default&lang=en&q="
    else:
        url = "https://twitter.com/i/search/timeline?f=tweets&vertical=default"
        url+= "&lang=en&include_available_features=1&include_entities=1&reset_"
        url+= "error_state=false&src=typd&max_position={}&q=".format(init)

    # url+= "from%3A{0}".format('juliangabu')
    url += "%20{0}".format(company)
    url += "%20since%3A{0}".format(since)
    return url

async def fetch(session, url):
    with async_timeout.timeout(30):
        async with session.get(url) as response:
            return await response.text()

async def initial(response):
    soup = BeautifulSoup(response, "html.parser")
    feed = soup.find_all("li", "js-stream-item")
    init = "TWEET-{}-{}".format(feed[-1]["data-item-id"], feed[0]["data-item-id"])

    return feed, init

async def cont(response):
    json_response = json.loads(response)
    html = json_response["items_html"]
    soup = BeautifulSoup(html, "html.parser")
    feed = soup.find_all("li", "js-stream-item")
    split = json_response["min_position"].split("-")
    split[1] = feed[-1]["data-item-id"]
    init = "-".join(split)

    return feed, init

async def getFeed(init):
    async with aiohttp.ClientSession() as session:
        response = await fetch(session, await getUrl(init))
    feed = []
    try:
        if init == -1:
            feed, init = await initial(response)
        else:
            feed, init = await cont(response)
    except:
        pass
    return feed, init

async def outTweet(tweet):
    tweetid = tweet["data-item-id"]
    # Formatting the date & time stamps just how I like it.
    datestamp = tweet.find("a", "tweet-timestamp")["title"].rpartition(" - ")[-1]
    d = datetime.datetime.strptime(datestamp, "%d %b %Y")
    date = d.strftime("%Y-%m-%d")
    timestamp = str(datetime.timedelta(seconds=int(tweet.find("span", "_timestamp")["data-time"]))).rpartition(", ")[-1]
    t = datetime.datetime.strptime(timestamp, "%H:%M:%S")
    time = t.strftime("%H:%M:%S")
    # The @ in the username annoys me.
    username = tweet.find("span", "username").text.replace("@", "")
    timezone = strftime("%Z", gmtime())
    # The context of the Tweet compressed into a single line.
    text = tweet.find("p", "tweet-text").text.replace("\n", "").replace("http", " http").replace("pic.twitter", " pic.twitter")
    # Regex for gathering hashtags
    hashtags = ",".join(re.findall(r'(?i)\#\w+', text, flags=re.UNICODE))
    replies = tweet.find("span", "ProfileTweet-action--reply u-hiddenVisually").find("span")["data-tweet-stat-count"]
    retweets = tweet.find("span", "ProfileTweet-action--retweet u-hiddenVisually").find("span")["data-tweet-stat-count"]
    likes = tweet.find("span", "ProfileTweet-action--favorite u-hiddenVisually").find("span")["data-tweet-stat-count"]
    try:
        mentions = tweet.find("div", "js-original-tweet")["data-mentions"].split(" ")
        for i in range(len(mentions)):
            mention = "@{}".format(mentions[i])
            if mention not in text:
                text = "{} {}".format(mention, text)
    except:
        pass

    # output = ""
    # output = "{} {} {} {} <{}> {}".format(tweetid, date, time, timezone, username, text)
    output = "{} {} <@{}> {}".format(date, time, username, text)
    global tweets_output
    tweets_output.append("{} {} <@{}> {}\n".format(date, time, username, text))
    # if arg.hashtags:
    #     output+= " {}".format(hashtags)
    # if arg.stats:
    #     output+= " | {} replies {} retweets {} likes".format(replies, retweets, likes)

    return output

async def getTweets(init):
    tweets, init = await getFeed(init)
    count = 0
    for tweet in tweets:
        '''
        Certain Tweets get taken down for copyright but are still
        visible in the search. We want to avoid those.
        '''
        copyright = tweet.find("div","StreamItemContent--withheld")
        if copyright is None:
            count +=1
            print(await outTweet(tweet))

    return tweets, init, count

# async def getUsername():
#     async with aiohttp.ClientSession() as session:
#         r = await fetch(session, "https://twitter.com/intent/user?user_id={0.userid}".format(arg))
#     soup = BeautifulSoup(r, "html.parser")
#     return soup.find("a", "fn url alternate-context")["href"].replace("/", "")

async def main():
    feed = [-1]
    init = -1
    num = 0
    while True:
        if num > 800:
            break
        if len(feed) > 0:
            feed, init, count = await getTweets(init)
            num += count
        else:
            break

def Error(error, message):
    # Error formatting
    print("[-] {}: {}".format(error, message))
    sys.exit(0)

def get_tweets(input):
    global since
    global tweets_output
    tweets_output = []
    date = time.strftime("%Y-%m-%d").split('-')
    date[1] = str(int(date[1]) - 1)
    since = '-'.join(date)
    global company
    company = input
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    return tweets_output
