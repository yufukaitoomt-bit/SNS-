import time
from typing import Optional, List, Dict

try:
    import instaloader
    INSTALOADER_OK = True
except ImportError:
    INSTALOADER_OK = False


class InstagramScraper:
    def __init__(self):
        if not INSTALOADER_OK:
            raise RuntimeError("instaloader がインストールされていません")
        self.L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
        )

    def get_user_profile(
        self, username: str, max_posts: int = 30, viral_threshold: int = 1000
    ) -> Optional[Dict]:
        try:
            profile = instaloader.Profile.from_username(self.L.context, username)

            if profile.is_private:
                return {
                    "username": username,
                    "full_name": profile.full_name,
                    "bio": "",
                    "follower_count": profile.followers,
                    "following_count": profile.followees,
                    "post_count": profile.mediacount,
                    "is_private": True,
                    "viral_post_count": 0,
                    "viral_posts": [],
                    "all_posts": [],
                }

            posts = []
            viral_posts = []

            for post in profile.get_posts():
                post_data = {
                    "shortcode": post.shortcode,
                    "likes": post.likes,
                    "comments": post.comments,
                    "caption": (post.caption or "")[:120],
                    "date": str(post.date_utc.date()),
                    "url": f"https://www.instagram.com/p/{post.shortcode}/",
                }
                posts.append(post_data)
                if post.likes >= viral_threshold:
                    viral_posts.append(post_data)
                if len(posts) >= max_posts:
                    break
                time.sleep(0.5)

            posts.sort(key=lambda x: x["likes"], reverse=True)

            return {
                "username": username,
                "full_name": profile.full_name,
                "bio": profile.biography[:200] if profile.biography else "",
                "follower_count": profile.followers,
                "following_count": profile.followees,
                "post_count": profile.mediacount,
                "is_private": False,
                "viral_post_count": len(viral_posts),
                "viral_posts": viral_posts[:10],
                "all_posts": posts[:30],
            }

        except Exception as e:
            print(f"[Instagram] プロフィール取得エラー ({username}): {e}")
            return None

    def search_hashtag(
        self,
        hashtag: str,
        max_posts: int = 20,
        viral_threshold: int = 1000,
    ) -> List[Dict]:
        try:
            tag = hashtag.lstrip("#")
            hashtag_obj = instaloader.Hashtag.from_name(self.L.context, tag)
            results = []
            seen: set = set()

            for post in hashtag_obj.get_top_posts():
                owner = post.owner_username
                if owner in seen:
                    continue
                seen.add(owner)

                profile = self.get_user_profile(owner, viral_threshold=viral_threshold)
                if profile and not profile["is_private"]:
                    results.append({
                        "trigger_post": {
                            "shortcode": post.shortcode,
                            "likes": post.likes,
                            "comments": post.comments,
                            "url": f"https://www.instagram.com/p/{post.shortcode}/",
                        },
                        "creator": profile,
                    })

                if len(results) >= max_posts:
                    break
                time.sleep(1)

            return results

        except Exception as e:
            print(f"[Instagram] ハッシュタグ検索エラー ({hashtag}): {e}")
            return []

    def find_viral_accounts(
        self,
        hashtags: List[str],
        max_followers: int = 3000,
        min_viral_posts: int = 10,
        viral_threshold: int = 1000,
    ) -> List[Dict]:
        seen: set = set()
        results = []

        for tag in hashtags:
            print(f"[Instagram] 検索中: #{tag}")
            items = self.search_hashtag(tag, viral_threshold=viral_threshold)

            for item in items:
                creator = item["creator"]
                uname = creator["username"]

                if uname in seen:
                    continue
                seen.add(uname)

                followers = creator["follower_count"]
                if followers > max_followers and followers != 0:
                    continue

                viral_count = creator["viral_post_count"]
                if viral_count >= min_viral_posts:
                    results.append(creator)
                    print(f"  ✅ @{uname} フォロワー{followers:,} バズ{viral_count}件")

            time.sleep(2)

        results.sort(key=lambda x: x["viral_post_count"], reverse=True)
        return results
