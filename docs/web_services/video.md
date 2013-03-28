Channel
=======

Get a list of channels.

```http
GET /ws/channels/?locale=LOCALE HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | Yes       | IETF language tag |
start          | no        | 0-based integer   | Used for paging through the channel's video items
size           | no        | video page size   | Number of videos to return - 100 by default

Responds with a channel list.


```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=60

{
    "channels": {
        "total": 24,
            "items": [
            {
                "category": 338,
                "subscribe_count": 0,
                "description": "My favourite Ted Talks",
                "title": "MY FAVOURITE TED TALKS",
                "cover_thumbnail_large_url": "http://media.dev.rockpack.com/images/channel/thumbnail_large/hJSke4WyRci0mqhHzlZSZg.jpg",
                "thumbnail_url": "http://media.dev.rockpack.com/images/channel/thumbnail_large/hJSke4WyRci0mqhHzlZSZg.jpg",
                "cover_thumbnail_small_url": "http://media.dev.rockpack.com/images/channel/thumbnail_small/hJSke4WyRci0mqhHzlZSZg.jpg",
                "owner": {
                    "resource_url": "http://demo.rockpack.com/ws/ziCAgGxbRpW-HNYTloYkQg/",
                    "avatar_thumbnail_url": "http://media.dev.rockpack.com/images/avatar/thumbnail_small/wbHLckR0Tg25CEly3HElqQ.jpg",
                    "name": "Jimmy Wales",
                    "id": "ziCAgGxbRpW-HNYTloYkQg"
                },
                "position": 1,
                "resource_url": "http://demo.rockpack.com/ws/ziCAgGxbRpW-HNYTloYkQg/channels/chHRF0V4rMT4CqULiSajAP2Q/",
                "id": "chHRF0V4rMT4CqULiSajAP2Q",
                "ecommerce_url": "",
                "cover_background_url": "http://media.dev.rockpack.com/images/channel/background/hJSke4WyRci0mqhHzlZSZg.jpg"
            }
        ]
    }
}
```
