Content
=======

### Categories

```http
GET /ws/categories/?locale=LOCALE HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Specifies the locale for the categories


Returns category hierarchy mapping - from id to locale-specific name and children (sub-categories).

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=3600

{
 "categories": {
  "items": [
   {
    "id": 1,
    "name": "Music",
    "sub_categories": [
     {
      "id": 2,
      "name": "Pop"
     },
     {
      "id": 3,
      "name": "Rock"
     }
    ]
   }
  ]
 }
}
```

### Videos

Browse latest popular videos.

```http
GET /ws/videos/?locale=LOCALE&category=CATID HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | The locale gives a regional bias to the results
category       | no        | Category id       | Filter the result by the specified category
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | Result page size  | Number of items to return - max 50.

Returns a list of video instances, with related video and channel data included.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=3600

{
  "videos": {
    "items": [
      {
        "title": "Star Trek Into Darkness - Extra Footage Japanese Teaser (HD)",
        "video": {
          "view_count": "4536",
          "star_count": "4455",
          "source": "youtube",
          "thumbnail_url": "http://i.ytimg.com/vi/BrHlQUXFzfw/0.jpg",
          "source_id": "BrHlQUXFzfw",
          "id": "RP000001TWSWZX4WH7EFFE44AUBVWI6OXALNKFTP"
        },
        "date_added": "2012-12-06T08:28:05.000Z",
        "position": 0,
        "id": "Tr3dHIt5_K9qdG",
        "channel": {
          "subscriber_count": 113,
          "title": "Trending and featured",
          "cover_thumbnail_large_url": "http://path/to/channel/large.jpg",
          "thumbnail_url": "http://path/to/channel/tmb.jpg",
          "cover_thumbnail_small_url": "http://path/to/channel/small.jpg",
          "owner": {
            "avatar_thumbnail_url": "http://path/to/avatar/small.jpg",
            "id": "Tr3dHIt5_K9qdGtR",
            "display_name": "joblomovienetwork"
          },
          "resource_url": "http://base/ws/USERID/channels/CHANNELID/",
          "id": "UCRX7UEyE8kp35mPrgC2sosA",
          "cover_background_url": "http://path/to/channel/bg.jpg"
        }
      }
    ],
    "total": 1
  }
}
```

### Channels

Browse latest popular channels.

```http
GET /ws/channels/?locale=LOCALE&category=CATID HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | The locale gives a regional bias to the results
category       | no        | Category id       | Filter the result by the specified category
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | Result page size  | Number of items to return - max 50.

Returns a list of channels, with owner data included.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=3600

{
 "channels": {
  "total": 105,
  "items": [
   {
    "position": 1,
    "id": "Unique channel id",
    "resource_url": "http://base/ws/USERID/channels/CHANNELID/",
    "title": "Channel title",
    "cover_background_url": "http://path/to/channel/bg.jpg",
    "cover_thumbnail_small_url": "http://path/to/channel/small.jpg",
    "cover_thumbnail_large_url": "http://path/to/channel/large.jpg",
    "owner": {
     "id": "Unique user id",
     "display_name": "User display name",
     "avatar_thumbnail_url": "https://path/to/avatar/small.jpg"
    },
    "subscriber_count": 119
   }
  ]
 }
}
```

### Cover Art

Get list of cover art images.

```http
GET /ws/cover_art/?locale=LOCALE&category=CATID HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | The locale gives a regional bias to the results
category       | no        | Category id       | Filter the result by the specified category
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | Result page size  | Number of items to return - max 50.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=3600

{
  "cover_art": {
    "total": 1,
    "items": [
      {
        "position": 0,
        "id": "1",
        "cover_ref": "img.png",
        "background_url": "http://path/to/background/img.jpg",
        "carousel_url": "http://path/to/carousel/img.jpg"
      }
    ]
  }
}
```

Also see `/ws/USERID/cover_art/`.
