USER
====

Get data for a specific user.

```http
GET /ws/USERID/ HTTP/1.1
Authorization: Bearer TOKEN
```

Responds with user information (names & avatar) and channels.
If `Bearer` token matches requested `USERID` then private channels will be included.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=60

{
  "name": "username",
  "display_name": "display name",
  "avatar_thumbnail_url": "http://path/to/avatar/small.jpg",
  "channels": [
    {
      "id": "channelid",
      "resource_url": "http://path/to/users/channels/channelid/",
      "description": "",
      "title": "lotr",
      "subscribe_count": 0,
      "cover_background_url": "http://path/to/channel/bg.jpg",
      "cover_thumbnail_small_url": "http://path/to/channel/small.jpg",
      "cover_thumbnail_large_url": "http://path/to/channel/large.jpg"
    }
  ]
}
```

CHANNEL
=======

Get data for an individual channel.

```http
GET /ws/USERID/channels/CID/?locale=LOCALE HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Some videos may be excluded if not marked as visible for the specified locale
start          | no        | 0-based integer   | Used for paging through the channel's video items
size           | no        | video page size   | Number of videos to return - 100 by default

Returns metadata and video list for the requested channel.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: max-age=60

{
 "id": "Unique channel id",
 "resource_url": "http://base/ws/USERID/channels/CHANNELID/",
 "title": "Channel title",
 "cover_background_url": "http://path/to/channel/bg.jpg",
 "cover_thumbnail_small_url": "http://path/to/channel/small.jpg",
 "cover_thumbnail_large_url": "http://path/to/channel/large.jpg",
 "subscribe_count": 119,
 "owner": {
  "id": "Unique user id",
  "name": "User display name",
  "avatar_thumbnail_url": "https://path/to/avatar/small.jpg"
 },
 "videos": {
  "total": 1,
  "items":
   [
    {
     "id": "Tr3dHIt5_K9qdG",
     "title": "Star Trek Into Darkness - Extra Footage Japanese Teaser (HD)",
     "date_added": "2012-12-06T08:28:05.000Z",
     "video": {
      "id": "RP000001TWSWZX4WH7EFFE44AUBVWI6OXALNKFTP",
      "source_id": "BrHlQUXFzfw",
      "source": "youtube",
      "thumbnail_url": "http://i.ytimg.com/vi/BrHlQUXFzfw/0.jpg",
      "star_count": "4455"
     }
    }
   ]
 }
}
```

Create a new channel.
```http

User Activity
=============

Record a view or a starring of a video instance.

```http
POST /ws/USERID/activity/?locale=LOCALE HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/x-www-form-urlencoded

action=ACTION&video_instance=VIDEOINSTANCEID
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | The action will be recorded for the given locale
action         | yes       | `star` or `view`  | Specifies the action type
video_instance | no        | instance id       | The id of the video instance that was viewed or starred

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

Get list of item identifies associated with recent activity: views, stars & subscriptions.
Useful for changing the UI of items from other WS responses.

```http
GET /ws/USERID/activity/ HTTP/1.1
Authorization: Bearer TOKEN
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=60

{
 "recently_viewed": [ "video instance id", "..." ],
 "recently_starred": [ "video id", "..." ],
 "subscribed": [ "channel id", "..." ]
}
```

Subscription Updates
====================

```http
GET /ws/USERID/subscriptions/recent_videos/ HTTP/1.1
```

List of all video instances recently added to user's subscribed channels.

User Cover Art
==============

Get list of users uploaded cover images.

```http
GET /ws/USERID/cover_art/ HTTP/1.1
Authorization: Bearer TOKEN
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=60

{
  "cover_art": {
    "total": 1,
    "items": [
      {
        "cover_ref": "img.png",
        "background_url": "http://path/to/background/img.jpg",
        "carousel_url": "http://path/to/carousel/img.jpg"
      }
    ]
  }
}
```


