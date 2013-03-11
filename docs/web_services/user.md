User
====

Get data for a specific user.

```http
GET /ws/USERID/ HTTP/1.1
Authorization: Bearer TOKEN
```

Responds with user information (names & avatar) and channels.
If `Bearer` token matches requested `USERID` then private channels will be included.
The token is not required when accessing other user's data.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=60

{
  "name": "username",
  "display_name": "display name",
  "avatar_thumbnail_url": "http://path/to/avatar/small.jpg",
  "channels": [
    {
      "id": "channelid",
      "resource_url": "http://path/to/users/channels/channelid/",
      "description": "channel description",
      "title": "channel title",
      "subscribe_count": 123,
      "cover_background_url": "http://path/to/channel/bg.jpg",
      "cover_thumbnail_small_url": "http://path/to/channel/small.jpg",
      "cover_thumbnail_large_url": "http://path/to/channel/large.jpg"
    }
  ]
}
```

### Change username

Change the current username for a user

```http
PUT /ws/USERID/username/ HTTP/1.1
Content-Type: application/json

"foo"
```

Parameter  | Required | Value      | Description
:--------- | :------- | :--------- | :----------
           | Yes      | String     | Characters allowed should match regex [a-zA-Z0-9]

Responds with a `204`

```http
HTTP/1.1 204 OK
Content-Type: application/json
```

Possible errors

Username has already been taken

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid_request",
    "message": "Username is already taken",
    "suggested_username": "foo"
}
```

Username has already been changed a maximum number of times

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid_request",
    "message": "Limit for changing username has been reached"
}
```

Invalid username

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid_request",
    "message": "Not a valid username"
}
```

Channel
=======

### Get

Get data for an individual channel.

```http
GET /ws/USERID/channels/CID/?locale=LOCALE&start=START&size=SIZE HTTP/1.1
Authorization: Bearer TOKEN
```

`Bearer` token is required only when accessing a private channel.

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Some videos may be excluded if not marked as visible for the specified locale
start          | no        | 0-based integer   | Used for paging through the channel's video items
size           | no        | video page size   | Number of videos to return - 100 by default


Otherwise returns metadata and video list for the requested channel.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=60

{
 "id": "Unique channel id",
 "public": true,
 "description": "Channel description",
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

Possible errors.

If the channel is private and the owner's token is not provided; or; if accessed via a secure sub-domain,
`public` is `false`, and user is not channel owner, then a `403` will be returned.

```http
HTTP/1.1 403 FORBIDDEN
Content-Type: application/json

{"error":"insufficient_scope"}
```

Channel Create
==============

To create a new channel `POST` json data to channels service.

```http
POST /ws/USERID/channels/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

{
    "title": "channel title",
    "description": "channel description",
    "category": 1,
    "cover": "COVERARTID",
    "public": true
}
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
title          | Yes       | unicode string    | May be empty string. If not specified, a default title will be assigned.
description    | Yes       | unicode string    | May be empty string.
category       | Yes       | category id       | Id of assigned category. May be empty string to leave unassigned.
cover          | Yes       | cover image ref   | Reference for cover art image. May be empty string to leave unassigned.
public         | Yes       | `true` or `false` | Toggles whether a channel is public. May be empty string, but will default to `true`. If other fields are unassigned, field will default to `false`.

Responds with a channel resource url.

```http
HTTP/1.1 201 CREATED
Location: http://some_doman/ws/USERID/channels/CHANNELID/

{
    "id": "CHANNELID",
    "resource_url": "http://some_domain/ws/USERID/channels/CHANNELID/"
}
```

Possible errors.

Errors occurred with the form data.
```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
  "form_errors": {
      "category": ["Invalid category: 111111111"],
      "cover": ["Invalid cover reference"],
      "description": ["This field is required, but can be an empty string."],
      "title": ["Duplicate title"]
    },
  "error": "invalid_request"
}
```

Channel Updates
===============

To change the data for a channel `PUT` new json data to the resource url, as per Channel Create above.

```http
PUT /ws/USERID/channels/CHANNELID/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

{
    "title": "channel title",
    "description": "channel description",
    "category": 1,
    "cover": "COVERARTID",
    "public": true
}
```

Responds '200' with the original channel resource url.

```http
HTTP/1.1 200 OK
Location: http://some_doman/ws/USERID/channels/CHANNELID/

{
    "id": "CHANNELID",
    "resource_url": "http://some_domain/ws/USERID/channels/CHANNELID/"
}
```

Channel Privacy
===============

To toggle a channel's privacy settings `POST` json data to a channel's `public` resource.

```http
PUT /ws/USERID/channel/CHANNELID/public/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

"false"
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
               | Yes       | `true` or `false` | Toggles public viewing of the channel

Returns current state for `public`

```http
HTTP/1.1 200 OK
Content-Type: application/json

"false"
```

Possible errors.

Missing or incorrect value for `public`.
```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid_request",
    "form_errors": "Value should be 'true' or 'false'"
}
```

### Delete

Delete a channel

```http
DELETE /ws/USERID/channels/CHANNELID/ HTTP/1.1
```

Responds with  `204` on success

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

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
video_instance | yes       | instance id       | The id of the video instance that was viewed or starred

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

User Cover Art
==============

### Get

Get list of users uploaded cover images.

```http
GET /ws/USERID/cover_art/?start=START&size=SIZE HTTP/1.1
Authorization: Bearer TOKEN
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
start          | no        | 0-based integer   | Used for paging through the user's cover art items
size           | no        | video page size   | Number of items to return - 100 by default

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=60

{
  "cover_art": {
    "total": 1,
    "items": [
      {
        "cover_ref": "coverartref",
        "background_url": "http://path/to/background/img.jpg",
        "carousel_url": "http://path/to/carousel/img.jpg"
      }
    ]
  }
}
```

### Upload

`POST` image data to cover_art service:

```http
POST /ws/USERID/cover_art/ HTTP/1.1
Content-Type: image/png
Authorization: Bearer TOKEN

.........IMAGE DATA....
```

If the image data cannot be processed you'll get an `400` response:
```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "message": "cannot identify image file"
}
```

On success a `201` will include the `cover_ref` value for adding to a channel.

```http
HTTP/1.1 201 CREATED
Content-Type: application/json
Location: http://path/to/cover/art/resource/url.png

{
 "cover_ref": "coverartref",
 "resource_url": "http://path/to/cover/art/resource/url.png",
 "background_url": "http://path/to/uploaded/image/background/size.jpg",
 "carousel_url": "http://path/to/uploaded/image/carousel/size.jpg"
}
```

### Remove

Remove a users cover art item with a `DELETE` request:

```http
DELETE /ws/USERID/cover_art/COVER_REF HTTP/1.1
Authorization: Bearer TOKEN
```

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

Subscriptions
=============

### List

Get a list of all channel subscriptions for the user.

```http
GET /ws/USERID/subscriptions/ HTTP/1.1
Authorization: Bearer TOKEN
```

Each item in the response includes a `resource_url`, used for deleting/unsubscribing,
and a `channel_url` for retrieving detail about the channel.

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
 "subscriptions": {
  "items": [
   {
    "resource_url": "http://path/to/channel/subscription/item/",
    "channel_url": "http://path/to/associated/channel/info/"
   }
  ],
  "total": 1
 }
}
```

### Subscribe

`POST` the channel url to create a new subscription.

```http
POST /ws/USERID/subscriptions/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

"http://path/to/channel"
```

If the channel url is invalid a `400` will be returned:

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "message": "Invalid channel url"
}
```

If the subscription is created a `201` with the new resource url will be returned.

```http
HTTP/1.1 201 CREATED
Location: http://resource/url/for/new/subscription/
Content-Type: application/json

{
 "resource_url": "http://resource/url/for/new/subscription/",
 "id": "ID"
}
```

### Unsubscribe

Delete the subscription resource to unsubscribe.

```http
DELETE /ws/USERID/subscriptions/SUBSCRIPTION/ HTTP/1.1
Authorization: Bearer TOKEN
```

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

### Subscription Updates

```http
GET /ws/USERID/subscriptions/recent_videos/?locale=LOCALE&start=START&size=SIZE HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Some videos may be excluded if not marked as visible for the specified locale
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | video page size   | Number of items to return - 100 by default

List of all video instances recently added to user's subscribed channels.

```http
HTTP/1.0 200 OK
Content-Type: application/json
Cache-Control: private, max-age=60

{
 "videos": {
  "total": 71,
  "items": [
   {
    "position": 0,
    "id": "viYMCzy5ZwQ_6HWBhaIcWI5g",
    "title": "I Wasn't Talking To You",
    "date_added": "2013-02-20T22:57:08.197668+00:00",
    "video": {
     "id": "RP000001ZALXK3ETZHWTCI6MVJSOBRVZY5KNL7DK",
     "source": "youtube",
     "source_id": "vSV8un-UscU",
     "duration": 62,
     "thumbnail_url": "http://i.ytimg.com/vi/vSV8un-UscU/mqdefault.jpg",
     "view_count": 2,
     "star_count": 6
    },
    "channel": {
     "id": "chEK9lwEXBTNCBp9Xp8g1FAV",
     "resource_url": "http://rockpack.com/ws/BJsFQkw7SpyNfi6xOBlA1Q/channels/chEK9lwEXBTNCBp9Xp8g1FAV/",
     "title": "favourites",
     "description": "",
     "cover_background_url": "",
     "cover_thumbnail_large_url": "",
     "cover_thumbnail_small_url": "",
     "subscribe_count": 0,
     "owner": {
      "id": "BJsFQkw7SpyNfi6xOBlA1Q",
      "resource_url": "http://rockpack.com/ws/BJsFQkw7SpyNfi6xOBlA1Q/",
      "name": "some user",
      "avatar_thumbnail_url": "http://media.rockpack.com/images/avatar/thumbnail_small/b1V2MgQqT5u-gT2iTFUjJw.jpg"
     }
    }
   }
  ]
 }
}
```

# Channel Videos

### Get

Get a list of videos for a channel.

```http
GET /ws/USERID/channels/CHANNELID/videos/ HTTP/1.1
Authorization: Bearer TOKEN
```

Returns an ordered list of videos for a channel.

```http
HTTP/1.1 200 OK
Content-Type: application/json

["VIDEOID", "VIDEOID"]
```

### Add/Delete Videos

To add or delete videos from a channel, send a list of the videos that the channel needs to contain.
Any videos not included, but are currently in the channel, will be removed.

Additionally, the order in which the video ids occur in the list will dictate the order in which they
will be returned in the `GET` above.

```http
GET /ws/USERID/channels/CHANNELID/videos/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

["VIDEOID", "VIDEOID"]
```

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

Possible errors.

If the channel is private and the owner's token is not provided then a 403 will be returned.

```http
HTTP/1.1 403 FORBIDDEN
Content-Type: application/json

{"error":"insufficient_scope"}
```

Missing list if video ids

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid_request",
    "message": "List can be empty, but must be present"
}
```

Item in list is not a string

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid_request",
    "message": "List item must be a video id"
}
```
