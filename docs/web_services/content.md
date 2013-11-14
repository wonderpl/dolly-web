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
    "colour": "#00ff00",
    "priority": 100,
    "sub_categories": [
     {
      "id": 2,
      "name": "Pop",
      "priority": 50
     },
     {
      "id": 3,
      "name": "Other",
      "priority": -1,
      "default": true
     }
    ]
   }
  ]
 }
}
```

The `priority` field should be used to order the categories when displayed as a list.
The item with highest priority value should be give the top/left-most position.
A nagative priority denotes categories that should be hidden from the user interface.

If a sub-category is labelled `default` then it should be used as the assigned category
if the user selects the respective parent category.

The `colour` field is optional and will be returned only if a value is specified in the
underlying datasource.

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
          "id": "RP000001TWSWZX4WH7EFFE44AUBVWI6OXALNKFTP",
          "source": "youtube",
          "source_id": "BrHlQUXFzfw",
          "source_username": "yt user",
          "thumbnail_url": "http://i.ytimg.com/vi/BrHlQUXFzfw/0.jpg",
          "view_count": "4536",
          "star_count": "4455"
        },
        "date_added": "2012-12-06T08:28:05.000Z",
        "position": 0,
        "id": "Tr3dHIt5_K9qdG",
        "channel": {
          "id": "UCRX7UEyE8kp35mPrgC2sosA",
          "resource_url": "http://base/ws/USERID/channels/CHANNELID/",
          "title": "Trending and featured",
          "subscriber_count": 113,
          "cover": {
            "thumbnail_url": "http://path/to/channel/cover.jpg",
            "aoi": [0, 0, 1, 1],
          },
          "owner": {
            "avatar_thumbnail_url": "http://path/to/avatar/small.jpg",
            "id": "Tr3dHIt5_K9qdGtR",
            "display_name": "joblomovienetwork"
          }
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
  "total": 1,
  "items": [
   {
    "position": 0,
    "id": "Unique channel id",
    "resource_url": "http://base/ws/USERID/channels/CHANNELID/",
    "title": "Channel title",
    "category": 123,
    "description": "channel desc",
    "public": true,
    "date_published": "2013-12-01T12:00:00",
    "ecommerce_url": "",
    "cover": {
      "thumbnail_url": "http://path/to/channel/cover.jpg",
      "aoi": [0, 0, 1, 1]
    },
    "owner": {
     "id": "Unique user id",
     "resource_url": "http://base/ws/USERID/",
     "display_name": "User display name",
     "avatar_thumbnail_url": "https://path/to/avatar/small.jpg"
    },
    "tracking_code": "some opaque string",
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
        "thumbnail_url": "http://path/to/thumbnail/img.jpg"
      }
    ]
  }
}
```

Also see `/ws/USERID/cover_art/`.

Player Services
===============

### Player Detail

Get a mapping from player identifier to html/javascript content that defines the player.

```http
GET /ws/videos/players/ HTTP/1.1
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=7200

{
 "rockpack": "",
 "youtube": "<html><script>player def</script></html>"
}
```

### Player Errors

Record an error when playing a specific video.

```http
POST /ws/videos/player_error/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

{
 "video_instance": "VIDEOINSTANCEID",
 "error": "some error code or description"
}
```

A `form_errors` mapping will be returned if there's an error with the request.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "form_errors": {
  "error": [
   "This field is required."
  ]
 }
}
```

No content returned on success.


```http
HTTP/1.1 204 NO CONTENT
```
