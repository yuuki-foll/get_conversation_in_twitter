import tweepy
import re
from datetime import timedelta
import sqlite3
import argparse
import utils
import time

consumer_key = ""
consumer_secret = ""
access_key = ""
access_secret = ""


class OverTimesError(Exception):
    """420エラーが起こった（取得制限かな?）"""
    pass


class Tweet:
    def __init__(self, status):
        self.in_reply_to_status_id = status.in_reply_to_status_id
        self.text = status.text
        self.created_at = status.created_at
        self.screen_name = status.user.screen_name
        self.username = status.user.name
        self.user_id = status.user.id


#override tweepy.StreamListener to add logic to on_status
class StreamingListener(tweepy.StreamListener):
    def __init__(self, api, db_path):
        super(StreamingListener, self).__init__()
        self.api = api
        self.db = db_path
        self.lookup_ids = []
        self.reply_list = {}

    def on_status(self, status):
        #print("status:", status)
        # リプライか？
        if self.is_status_tweet(status):
            return

        # フィルタリング
        if self.is_invalid_tweet(status):
            return
        self.lookup_ids.append(status.in_reply_to_status_id)
        self.reply_list[status.in_reply_to_status_id] = Tweet(status)
        print(".", end='', flush=True)
        if len(self.lookup_ids) >= 100:
            print("\nCalling statuses_lookup API...")
            statuses = self.api.statuses_lookup(self.lookup_ids)

            for status in statuses:
                if self.is_status_tweet(status):
                    continue

                if self.is_invalid_tweet(status):
                    continue

                reply = self.reply_list[status.id]
                # リプライ先が同じユーザー？
                if status.user.id == reply.user_id:
                    continue

                self.add_conversation(status, reply)
                self.print_conversation(status, reply)

            self.lookup_ids = []
            self.reply_list = {}

    def print_conversation(self, reply1, reply2):
        print('------------ 会話 ------------')
        print("reply1:@{}({}): {}".format(
            reply1.user.screen_name, reply1.created_at + timedelta(hours=+9),
            reply1.text))
        print("reply2:@{}({}): {}".format(
            reply2.screen_name, reply2.created_at + timedelta(hours=+9),
            reply2.text))
        print('-' * 30)

    def is_status_tweet(self, status):
        # リプライではないただのツイートか確認
        if status.in_reply_to_status_id is None:
            return True

    def is_invalid_tweet(self, status):
        # いらないツイートか調べる
        #if status.user.lang != "ja":
        if status.lang != "ja":
            # 日本語か確認
            return True

        if "bot" in status.user.screen_name:
            return True

        if re.search(r"https?://", status.text):
            return True

        if re.search(r"#(\w+)", status.text):
            # ハッシュタグ
            return True

        # 複数の相手にリプライしているか？
        tweet = re.sub(r"@([A-Za-z0-9_]+)", "<unk>", status.text)
        if tweet.split().count("<unk>") > 1:
            return True

        # 長いツイートか？
        if len(tweet.replace("<unk>", "")) > 30:
            return True

        return False

    def cleanup_text(self, status):
        text = re.sub(r"@([A-Za-z0-9_]+) ", "", status.text)
        text = re.sub("\s+", ' ', text).strip()
        return text.replace("&gt;", ">").replace("&lt;",
                                                 "<").replace("&amp;", "&")

    def on_error(self, code):
        print("エラーコード：", code)
        raise OverTimesError("取得制限")
        pass

    def add_conversation(self, reply1, reply2):
        reply1 = self.cleanup_text(reply1)
        reply2 = self.cleanup_text(reply2)
        conn = sqlite3.connect(self.db)
        cur = conn.cursor()
        cur.execute("insert into seq2seq"
                    "(reply1, reply2)"
                    "values (?, ?)", [reply1, reply2])
        conn.commit()
        conn.close()


if __name__ == "__main__":
    # データベースのpath
    db_path = "./reply2reply.db"
    sql = """create table seq2seq(reply1 text NOT NULL,reply2 text NOT NULL);"""

    parser = argparse.ArgumentParser()
    parser.add_argument("--new",
                        type=int,
                        default=0,
                        help="0 indicates the database is already there.")

    args = parser.parse_args()
    if args.new:
        utils.build_database(db_path, sql)
    """認証系"""
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    api = tweepy.API(auth)

    # Streaming API
    listener = StreamingListener(api, db_path)
    streaming = tweepy.Stream(auth, listener)
    while True:
        try:
            streaming.sample()
        except KeyboardInterrupt:
            streaming.disconnect()
            break

        except OverTimesError as e:
            print(e)
            time.sleep(1000)
            pass

        except Exception as e:
            streaming.disconnect()
            print(e)