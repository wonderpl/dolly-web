Access to private resources require a `Bearer` access token, as returned
but the [oauth services](oauth.md).

See the OAuth 2.0 [Bearer Token Usage]
(http://self-issued.info/docs/draft-ietf-oauth-v2-bearer.html)
spec for further detail.

User
====

### Get all users

```http
GET /ws/users/?locale=LOCALE&start=START&size=SIZE&category=CATEGORY HTTP/1.1
Authorization: Bearer TOKEN
```

Get list of users.

Responds with basic user information.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=3600

{
  "user": {
    "items": [
      {
        "avatar_thumbnail_url": "http://path/to/avatar/medium.jpg",
        "categories": [ ],
        "description": "",
        "display_name": "display name",
        "id": "userid",
        "position": 0,
        "profile_cover_url": "",
        "resource_url": "http://path/to/user/",
        "username": "username"
      }
    ],
    "total": 19289
  }
}
```

Parameter      | Required? | Value               | Description
:------------- | :-------- | :------------------ | :----------
locale         | yes       | IETF language tag   | Bias result list for the specified locale
start          | no        | 0-based integer     | Used for paging through the result items
size           | no        | Integer             | Number of users to return - 100 by default
category       | no        | Category ID         | Filter on category from a channel owned by a user

### Get user

Get data for a specific user.

```http
GET /ws/USERID/?data=DATA1&data=DATA2&size=SIZE HTTP/1.1
Authorization: Bearer TOKEN
```

Responds with user information (names & avatar) and channels.

The token is not required when accessing other user's data.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=60

{
  "id": "userid",
  "username": "username",
  "display_name": "display name",
  "avatar_thumbnail_url": "http://path/to/avatar/small.jpg",
  "profile_cover_url": "",
  "description": "Description of user",
  "subscriber_count": 123,
  "brand": True,
  "site_url": "http://link/to/external/site",
  "channels": {
    "total": 1,
    "items": [
      {
        "id": "channelid",
        "resource_url": "http://path/to/users/channels/channelid/",
        "description": "channel description",
        "title": "channel title",
        "subscriber_count": 123,
        "cover": {
          "thumbnail_url": "http://path/to/channel/cover.jpg",
          "aoi": [0, 0, 1, 1],
        },
        "videos": {
          "total": 123
        }
      }
    ]
  }
}
```

If `Bearer` token matches requested `USERID` then private channels will be included
and additional fields and resource url links will be returned.  The following parameters are also valid.

Parameter      | Required? | Value               | Description
:------------- | :-------- | :------------------ | :----------
data           | no        | Data section names  | The names of data sections to be returned directly in the response. Default: `channels`.
size           | no        | Data item page size | Number of data items to return - 100 by default

If the `data` parameter is specified then the data associated with each resource given will be included directly in the response.
The supported resource names are `channels`, `subscriptions`, `external_accounts`, `flags` & `activity`.
The format of the data will be the same as if returned by the corresponding resource url.
For example if `data=channels&data=subscriptions&size=2` is used then the first 2 items of the `channels` and `subscriptions`
sub-resources will be included in the user resource response.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private

{
 "id": "userid",
 "username": "username",
 "display_name": "first last",
 "first_name": "first",
 "last_name": "last",
 "email": "user@mail.com",
 "locale": "en-us",
 "gender": null,
 "avatar_thumbnail_url": "http://path/to/avatar.img",
 "profile_cover_url": "",
 "description": "",
 "subscriber_count": 0,
 "date_of_birth": "1900-01-21",
 "subscriptions": {
  "resource_url": "https://path/to/subscriptions/resource/base/url/",
  "updates": "https://path/to/subscriptions/resource/recent_videos/"
 },
 "activity": {
  "resource_url": "https://path/to/activity/resource/base/url/"
 },
 "external_accounts": {
  "resource_url": "http://path/to/external/accounts/resource/base/url/"
 },
 "friends": {
  "resource_url": "http://path/to/friends/resource/base/url/"
 },
 "notifications": {
  "unread_count": 3,
  "resource_url": "https://path/to/notifications/resource/base/url/"
 },
 "cover_art": {
  "resource_url": "https://path/to/cover_art/resource/base/url/"
 },
 "channels": {
  "resource_url": "https://path/to/channels/resource/base/url/",
   "total": 0,
   "items": []
 },
 "flags": {
  "resource_url": "https://path/to/flags/resource/base/url/"
 }
}
```

### Update profile

Change an individual attribute for a user, for example, username.

```http
PUT /ws/USERID/ATTRIBUTE/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

"porkchopexpress"
```

Where `ATTRIBUTE` can be one of:

Attribute     | Value  | Description
:------------ | :----- | :----------
username      | String | Characters allowed should match regex [a-zA-Z0-9]
first_name    | String |
last_name     | String |
date_of_birth | String | YYYY-MM-DD formatted date string
locale        | String | IETF language tag
email         | String | Email address
gender        | String | `m` or `f`
password      |        | Special case. See [Change Password](#change-password) below
description   | String | Profile description or tag-line

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
See the Registration section of [oauth documentation](oauth.md) for a comprehensive list of errors


### Change password

Change a users password. The old password must be supplied to validate the change, except if
the user has never been assigned a password (e.g. logged in with Facebook), in which case an
empty string is accepted.

```http
PUT /ws/USERID/password/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

{
    "old": "oldpassword",
    "new": "newpassword"
}
```

New password must be:

Value  | Description
:----- | :----------
String | Minimum 6 characters

Responds with a `200` and new access credentials

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "token_type": "Bearer",
  "access_token": "some_new_access_token",
  "expires_in": "3600",
  "refresh_token": "some_new_refresh_token",
  "user_id": "USERID",
  "resource_url:" "http://path/to/user/info/"
}
```

Possible errors

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid request",
    "message": ["Field must be at least 6 characters long."]
}
```

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid request",
    "message": ["Old password is incorrect."]
}
```

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid request",
    "message": ["Both old and new passwords must be supplied."]
}
```

### Toggle display of full name

Set whether a user's full name or username is displayed in the User's `display_name` field.

```http
PUT /ws/USERID/display_fullname/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

false
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
               | Yes       | `true` or `false` | Toggles display of fullname (`true`) or username (`false`) in `display_name` `User` field

Responds with a `204`

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

Possible errors

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid request",
    "message": "Value must be a boolean."
}
```

Flags
=====

Boolean flags or switches associated with a user.  Currently supported flags:
`facebook_autopost_star`, & `facebook_autopost_add`.

### Get

`GET` a list of enabled flags for the user:

```http
GET /ws/USERID/flags/ HTTP/1.1
Authorization: Bearer TOKEN
```

Returns a list where each item contains the `flag` label and a `resource_url` to unset.

```http
HTTP/1.1 200 OK
Cache-Control: private, max-age=60
Content-Type: application/json

{
 "total": 1,
 "items": [
  {
   "flag": "FLAG",
   "resource_url": "http://path/to/user/flags/FLAG/"
  }
 ]
}
```

### Set

`PUT` a `true` value to a new flag resource to set a flag.

```http
PUT /ws/USERID/flags/FLAG/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

true
```

Returns a `201` if the flag is set.

```http
HTTP/1.1 201 CREATED
Location: http://path/to/user/flags/FLAG/

{
 "resource_url": "http://path/to/user/flags/FLAG/"
}
```

Returns a `204` if the flag was already set.

```http
HTTP/1.1 204 NO CONTENT
```

Returns a `400` if the flag label is invalid.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "message": "Invalid user flag."
}
```

### Unset

`DELETE` a flag resource to unset/disable a flag.

```http
DELETE /ws/USERID/flags/FLAG/ HTTP/1.1
Authorization: Bearer TOKEN
```

Returns a `204` if unset.

```http
HTTP/1.1 204 NO CONTENT
```

Avatar
======

### Update

`PUT` new image data to update the users avatar.

```http
PUT /ws/USERID/avatar/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: image/png

.........IMAGE DATA....
```

If invalid data:

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "message": "cannot identify image file"
}
```

If successful:

```http
HTTP/1.1 200 OK
Location: http://path/uploaded/media.png
Content-Type: application/json

{
 "thumbnail_url": "http://path/uploaded/media.png"
}
```

Profile Cover
=============

### Update

`PUT` new image data to update the user's profile cover.

```http
PUT /ws/USERID/profile_cover/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: image/png

.........IMAGE DATA....
```

If invalid data:

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "message": "cannot identify image file"
}
```

If successful:

```http
HTTP/1.1 200 OK
Location: http://path/uploaded/media.png
Content-Type: application/json

{
 "thumbnail_url": "http://path/uploaded/media.png"
}
```

Channel
=======

### Get

Get data for an individual channel.

```http
GET /ws/USERID/channels/CID/?locale=LOCALE&location=COUNTRYCODE&start=START&size=SIZE HTTP/1.1
Authorization: Bearer TOKEN
```

`Bearer` token is required only when accessing a private channel.

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Some videos may be excluded if not marked as visible for the specified locale
location       | no        | ISO-3166 code     | Geographic location is used to filter videos not available in the specified country
start          | no        | 0-based integer   | Used for paging through the channel's video items
size           | no        | video page size   | Number of videos to return - 100 by default


Otherwise returns metadata and video list for the requested channel.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=60

{
 "id": "Unique channel id",
 "description": "Channel description",
 "resource_url": "http://base/ws/USERID/channels/CHANNELID/",
 "title": "Channel title",
 "ecommerce_url": "",
 "favourites": false,
 "subscriber_count": 119,
 "cover": {
   "thumbnail_url": "http://path/to/channel/cover.jpg",
   "aoi": [0, 0, 1, 1],
 },
 "owner": {
  "id": "Unique user id",
  "display_name": "User display name",
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
      "source": "youtube",
      "source_id": "BrHlQUXFzfw",
      "source_username": "yt user",
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

### Create

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
description    | Yes       | unicode string    | May be empty string. Maximum 200 chars (line-breaks are stripped).
category       | Yes       | category id       | Id of assigned category. May be empty string to leave unassigned.
cover          | Yes       | cover image ref   | Reference for cover art image. May be empty string to leave unassigned.
public         | Yes       | `true` or `false` | Toggles whether a channel is public. May be empty string, but will default to `true`. If other fields are unassigned, field will default to `false`.

Responds with a channel resource url.

```http
HTTP/1.1 201 CREATED
Location: http://some_domain/ws/USERID/channels/CHANNELID/

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

### Update

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

Set `cover` to `"KEEP"` to leave the cover unmodified.

Responds '200' with the original channel resource url.

```http
HTTP/1.1 200 OK
Location: http://some_domain/ws/USERID/channels/CHANNELID/

{
    "id": "CHANNELID",
    "resource_url": "http://some_domain/ws/USERID/channels/CHANNELID/"
}
```

### Update privacy

To toggle a channel's privacy settings `PUT` json data to a channel's `public` resource.

```http
PUT /ws/USERID/channels/CHANNELID/public/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

false
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
               | Yes       | `true` or `false` | Toggles public viewing of the channel

Returns current state for `public`

```http
HTTP/1.1 200 OK
Content-Type: application/json

false
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
Authorization: Bearer TOKEN
```

Responds with  `204` on success

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

Channel Videos
==============

### Get

Get a list of videos for a channel.

```http
GET /ws/USERID/channels/CID/videos/?locale=LOCALE&location=COUNTRYCODE&start=START&size=SIZE HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Some videos may be excluded if not marked as visible for the specified locale
location       | no        | ISO-3166 code     | Geographic location is used to filter videos not available in the specified country
start          | no        | 0-based integer   | Used for paging through the channel's video items
size           | no        | video page size   | Number of videos to return - 100 by default

Returns an ordered list of videos for a channel.

```http
HTTP/1.1 200 OK
Cache-Control: public, max-age=60
Content-Type: application/json

{
 "videos": {
  "total": 1,
  "items":
   [
    {
     "position": 0,
     "id": "Tr3dHIt5_K9qdG",
     "title": "Star Trek Into Darkness - Extra Footage Japanese Teaser (HD)",
     "date_added": "2012-12-06T08:28:05.000Z",
     "category": 124,
     "child_instance_count": 0,
     "channel_title": "Trending and featured",
     "video": {
      "id": "RP000001TWSWZX4WH7EFFE44AUBVWI6OXALNKFTP",
      "source": "youtube",
      "source_id": "BrHlQUXFzfw",
      "source_username": "yt user",
      "thumbnail_url": "http://i.ytimg.com/vi/BrHlQUXFzfw/0.jpg",
      "star_count": "4455"
     }
    }
   ]
 }
}
```

### Individual Video

Get a single video instance

```http
GET /ws/USERID/channels/CID/videos/INSTANCEID/ HTTP/1.1
```

Returns a single video instance


```http
HTTP/1.1 200 OK
Cache-Control: public, max-age=60
Content-Type: application/json


    {
     "position": 0,
     "id": "Tr3dHIt5_K9qdG",
     "title": "Star Trek Into Darkness - Extra Footage Japanese Teaser (HD)",
     "date_added": "2012-12-06T08:28:05.000Z",
     "category": 124,
     "child_instance_count": 0,
     "channel_title": "Trending and featured",
     "video": {
      "id": "RP000001TWSWZX4WH7EFFE44AUBVWI6OXALNKFTP",
      "source": "youtube",
      "source_id": "BrHlQUXFzfw",
      "source_username": "yt user",
      "thumbnail_url": "http://i.ytimg.com/vi/BrHlQUXFzfw/0.jpg",
      "star_count": "4455"
     }
    }

```


### Update

To add or delete videos from a channel, `PUT` a list of video instance ids that the
channel needs to contain. Any videos not included, but are currently in the channel,
will be removed.

Additionally, the order in which the video ids occur in the list will dictate the order in which they
will be returned in the `GET` above.

```http
PUT /ws/USERID/channels/CHANNELID/videos/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

["VIDEOINSTANCEID", "VIDEOINSTANCEID"]
```

To add new videos only, keeping any existing, `POST` a list of video instance ids.

```http
POST /ws/USERID/channels/CHANNELID/videos/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

["VIDEOINSTANCEID"]
```

For videos from external sources the video instance can be defined as a `(source, source-id)`
pair:

```http
POST /ws/USERID/channels/CHANNELID/videos/ HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

[["youtube", "9bZkp7q19f0"]]
```

On success:

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

Possible errors.

If the channel is private and the owner's token is not provided then a 403 will be returned.

```http
HTTP/1.1 403 FORBIDDEN
Content-Type: application/json

{
 "error":"insufficient_scope"
}
```

Invalid ids:

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "message": "Invalid video instance ids",
 "data": [ "aaa", "bbb" ]
}
```

Channel Subscribers
===================

### Get

Get a list of users who are subscribed to a channel.

```http
GET /ws/USERID/channels/CHANNELID/subscribers/ HTTP/1.1
```

Returns a list of user records.

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
 "users": {
  "items": [
   {
    "display_name": "Paul Egan",
    "resource_url": "http://path/to/user/detail/",
    "avatar_thumbnail_url": "http://path/to/user/avatar/img.jpg",
    "id": "4vsl71w2T12q1k2RwVhdzg",
    "position": 0
   }
  ],
  "total": 1
 }
}
```

User Activity
=============

### Store

Record a view, starring, or selection of a video instance.

```http
POST /ws/USERID/activity/?locale=LOCALE&tracking_code=CODE HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

{
 "action": "ACTION",
 "object_type": "video_instance",
 "object_id": "VIDEOINSTANCEID"
}
```

Parameter      | Required? | Value                                  | Description
:------------- | :-------- | :------------------------------------- | :----------
action         | yes       | `star`¦`unstar`¦`view`¦<br>`select`¦`open`¦<br>`subscribe_all`¦`unsubscribe_all` | Specifies the action type
object_type    | yes       | `user`¦`channel`¦`video_instance`      | The type of object
object_id      | yes       | string                                 | The id of the object that was acted upon
locale         | no        | IETF language tag                      | The action will be recorded for the given locale
tracking_code  | no        | string                                 | The value for the last retrieved tracking_code

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

### Retrieve

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
 "subscribed": [ "channel id", "..." ],
 "user_subscribed": [ "user id", "..." ]
}
```

User Notifications
==================

### Retrieve

Get a list of notification messages for the user.

```http
GET /ws/USERID/notifications/ HTTP/1.1
Authorization: Bearer TOKEN
```

Each notification item in the list has a `message_type` and `message` data.  The message data
contains a `user` record representing the user who's action triggered the notification and a
content record representing the video or channel that was acted upon.

Message Type  | Content Record | Description
:------------ | :------------- | :----------
`subscribed`  | `channel`      | Message contains data on the channel to which the user subscribed
`starred`     | `video`        | Message contains data for the video which was starred
`joined`      |                | Message contains user record only
`repack`      | `video`        | Message contains data for the video which was created from the users
`unavailable` | `video`        | Message contains data for the video which is no longer available

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=60

{
 "notifications": {
  "total": 5,
  "items": [
   {
    "id": 1,
    "message_type": "starred",
    "date_created": "2013-04-29T18:16:05.950486",
    "read": false,
    "message": {
     "video": {
      "id": "VIDEOINSTANCEID",
      "resource_url": "http://path/to/video/resource/url/",
      "thumbnail_url": "http://i.ytimg.com/vi/m04evx91lh8/mqdefault.jpg",
      "channel": {
       "resource_url": "http://path/to/channel/resource/url/",
       "id": "CHANNELID"
      }
     },
     "user": {
      "id": "USERID",
      "resource_url": "http://path/to/user/resource/url/",
      "display_name": "user",
      "avatar_thumbnail_url": "http://path/to/avatar/img.jpg"
     }
    }
   },
   {
    "id": 2,
    "message_type": "subscribed",
    "date_created": "2013-04-29T12:23:13.762358",
    "read": true,
    "message": {
     "channel": {
      "id": "CHANNELID",
      "resource_url": "http://path/to/channel/resource/url/",
      "title": "a channel",
      "thumbnail_url": "http://path/to/channel/cover.jpg"
     },
     "user": {
      "id": "USERID",
      "resource_url": "http://path/to/user/resource/url/",
      "display_name": "user",
      "avatar_thumbnail_url": "http://path/to/avatar/img.jpg"
     }
    }
   },
   {
    "id": 3,
    "message_type": "joined",
    "read": false,
    "date_created": "2013-07-11T17:48:29.932114",
    "message": {
     "user": {
      "id": "USERID",
      "resource_url": "http://path/to/user/resource/url/",
      "display_name": "user",
      "avatar_thumbnail_url": "http://path/to/avatar/img.jpg"
     }
    }
   }
  ]
 }
}
```

### Unread count

Get the number of unread notifications messages.
Note: This count is also available on the user service.

```http
GET /ws/USERID/notifications/unread_count/ HTTP/1.1
Authorization: Bearer TOKEN
```

Returns a single integer value.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=60

88
```

### Mark read

Post a list of message ids to mark as read.
If the list is empty then all unread messages will be marked.

```http
POST /ws/oCRwcy5MRIiWmsJjvbFbHA/notifications/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

{
 "mark_read": [1, 2]
}
```

Responds with a 204 if successful.

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "message":"Invalid id list",
 "error":"invalid_request"
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
        "position": 0,
        "id": "123",
        "cover_ref": "coverartref",
        "thumbnail_url": "http://path/to/thumbnail/img.jpg"
      }
    ]
  }
}
```

### Upload

`POST` image data to cover_art service:

```http
POST /ws/USERID/cover_art/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: image/png

.........IMAGE DATA....
```

To specify an aoi (area of interest) use a multipart post with an `image` and `aoi` part.
The aoi should be of the form `[x1, y1, x2, y2]`, where each value is a float between 0 and 1.

```http
POST /ws/USERID/cover_art/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: multipart/form-data; boundary=----------------------------95229d819206

------------------------------95229d819206
Content-Disposition: form-data; name="image"; filename="image.png"
Content-Type: image/png

.........IMAGE DATA....
------------------------------95229d819206
Content-Disposition: form-data; name="aoi"
Content-Type: application/json

[0, 0, 1, 1]
------------------------------95229d819206--
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
 "thumbnail_url": "http://path/to/thumbnail/img.jpg"
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

Returns a list of channel records, similar to the popular channels service but
including `subscription_resource_url` field (used for deleting/unsubscribing).

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
 "channels": {
  "items": [
   {
    "position": 0,
    "id": "chsE-yf_sySKqvLvV0_SVw1A",
    "resource_url": "http://path/to/channel/detail/",
    "subscription_resource_url": "http://path/to/subscription/resource/",
    "category": 215,
    "subscriber_count": 30,
    "description": "desc",
    "title": "title",
    "public": true,
    "cover": {
      "thumbnail_url": "http://path/to/channel/cover.jpg",
      "aoi": [0, 0, 1, 1],
    },
    "videos": {
      "total": 123
    },
    "owner": {
     "id": "qC3ZtYRqQNCAUzrsIeWmUg",
     "avatar_thumbnail_url": "http://path/to/user/avatar/img.jpg",
     "resource_url": "http://path/to/user/resource/",
     "display_name": "user name"
    }
   }
  ],
  "total": 1
 }
}
```

### Subscribe

`POST` the channel url to create a new subscription.

```http
POST /ws/USERID/subscriptions/?tracking_code=CODE HTTP/1.1
Content-Type: application/json
Authorization: Bearer TOKEN

"http://path/to/channel"
```

Parameter      | Required? | Value    | Description
:------------- | :-------- | :------- | :----------
tracking_code  | no        | string   | The value for the last retrieved tracking_code

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

To subscribe to all channels owned by a specific user POST to the activity service.

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
Authorization: Bearer TOKEN
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Some videos may be excluded if not marked as visible for the specified locale
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | video page size   | Number of items to return - 100 by default

List of all video instances recently added to user's subscribed channels.

```http
HTTP/1.1 200 OK
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
     "source_username": "yt user",
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
     "subscriber_count": 0,
     "cover": {
       "thumbnail_url": "http://path/to/channel/cover.jpg",
       "aoi": [0, 0, 1, 1],
     },
     "owner": {
      "id": "BJsFQkw7SpyNfi6xOBlA1Q",
      "resource_url": "http://rockpack.com/ws/BJsFQkw7SpyNfi6xOBlA1Q/",
      "display_name": "some user",
      "avatar_thumbnail_url": "http://media.rockpack.com/images/avatar/thumbnail_small/b1V2MgQqT5u-gT2iTFUjJw.jpg"
     }
    }
   }
  ]
 }
}
```

Content Feed
============

Returns a list of new or recommended content for the user based on their subscriptions.

```http
GET /ws/USERID/content_feed/?locale=LOCALE&location=COUNTRYCODE&start=START&size=SIZE HTTP/1.1
Authorization: Bearer TOKEN
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Some videos may be excluded if not marked as visible for the specified locale
location       | no        | ISO-3166 code     | Geographic location is used to filter videos not available in the specified country
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | item page size    | Number of content items to return - 100 by default

The response lists content items, which may be either a video or a channel.

Video items can contain an additional `starring_users` field which will list up to 3 users who
starred the video.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=60

{
 "content": {
  "total": 2,
  "items": [
   {
    "position": 0,
    "aggregation": "123",
    "id": "VIDEOINSTANCEID",
    "date_added": "2013-06-04T15:15:11.963565",
    "title": "Video title",
    "video": {
     "id": "RP000001XDPBVMXPADH6X7XA3FHBMJWD75QCIDSX",
     "source": "youtube",
     "source_id": "9EVEmZ2c_es",
     "source_username": "TEDtalksDirector",
     "thumbnail_url": "http://i.ytimg.com/vi/9EVEmZ2c_es/mqdefault.jpg",
     "duration": 1408,
     "star_count": 0,
     "view_count": 0
    },
    "channel": {
     "id": "CHANNELID",
     "resource_url": "http://path/to/channel/detail/",
     "title": "TED Talks",
     "date_published": "2013-03-13T12:02:55",
     "category": 217,
     "subscriber_count": 7,
     "cover": {
      "thumbnail_url": "http://path/to/channel/cover.jpg",
      "aoi": null
     },
     "owner": {
      "id": "USERID",
      "resource_url": "http://path/to/user/resource/",
      "display_name": "CHANNEL OWNER",
      "avatar_thumbnail_url": "http://path/to/user/avatar/img.jpg"
     }
    },
    "starring_users": [
     {
      "id": "USERID",
      "resource_url": "http://path/to/user/resource/",
      "display_name": "LIKING USER",
      "avatar_thumbnail_url": "http://path/to/user/avatar/img.jpg"
     }
    ],
   },
   {
    "position": 1,
    "id": "CHANNELID",
    "resource_url": "http://path/to/channel/detail/",
    "date_published": "2013-07-02T12:32:48.935224",
    "title": "test",
    "category": null,
    "subscriber_count": 0,
    "tracking_code": "some opaque string",
    "cover": {
     "thumbnail_url": "",
     "aoi": null
    },
    "owner": {
     "id": "USERID",
     "resource_url": "http://path/to/user/resource/",
     "display_name": "user",
     "avatar_thumbnail_url": "http://path/to/user/avatar/img.jpg"
    }
   }
  ],
  "aggregations": {
   "123": {
    "type": "video",
    "title": "Some channels",
    "count": 10,
    "covers": [4]
   }
  }
 }
}
```

As well as the usual `items` & `total` fields, the `content` response object includes a dictionary
of `aggregations`. These aggregation objects describe groupings of items which could be
displayed together on the client UI. Each content item may include an `aggregation` field which
refers to an aggregation object by dictionary key.
The aggregation objects contain the following fields:

Field   | Type             | Description
:------ | :--------------- | :----------
type    | string           | Can be either `video` or `channel`.
count   | integer          | The total number of content items in the aggregation.
covers  | list of integers | A list of items that could be displayed on the cover of the grouping, referred to by their position number.
title   | string or `null` | An optional title for the group.  If specified, it should override any coded title in the client.

Note: The requested page size specifies the number of content items independent of the aggregations.
The returned content items could be aggregated into a number of visual groupings much less than the page size.
To mitigate this the client should request a reasonably large page size and server will try to avoid extreme cases (such as 1 aggregation for 100 result items).

##### Example code for processing the aggregations:

```python
data = requests.get(feed_url).json()['content']
channel_group = []
print 'item count: {}, agg count: {}'.format(data['total'], len(data['aggregations']))
for item in data['items']:
    if 'aggregation' in item:
        aggregation = data['aggregations'][item['aggregation']]
        if item['id'] not in aggregation['covers']:
            # Skip over "hidden" items in aggregation
            continue
    else:
        aggregation = None

    if 'video' in item:   # Item is a video instance
        print '{position:02d} video   {channel[owner][id]}/{channel[id]}'.format(**item),
        if aggregation:
            print 'AGG: +{count}'.format(**aggregation),
        stars = item['video']['star_count'], item.get('starring_users', [])
        starring_users = ', '.join(u['display_name'] for u in stars[1])
        print '{} likes{}'.format(stars[0], ' including ' + starring_users if starring_users else '')

    elif 'cover' in item:   # Item is a channel
        if aggregation:
            channel_group.append(item)
            if len(channel_group) == len(aggregation['covers']):
                print '{position:02d} channel {owner[id]}/{id}'.format(**channel_group[0]),
                print 'AGG: +{count} {title}'.format(**aggregation)
                channel_group = []
        else:
            print '{position:02d} channel {owner[id]}/{id}'.format(**item)
```

Channel Recommendations
=======================

Returns a list of channels recommended based on user demographic and usage data.

```http
GET /ws/USERID/channel_recommendations/?locale=LOCALE&start=START&size=SIZE HTTP/1.1
Authorization: Bearer TOKEN
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Results will be biased towards popularity in the specified locale
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | item page size    | Number of content items to return - 100 by default

The response lists channel items in the same format as `/ws/channels/`.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=3600

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
    "tracking_code": "some opaque string",
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
    "subscriber_count": 119
   }
  ]
 }
}
```

User Recommendations
====================

Returns a list of channel owners which the current user is suggested to subscribe to.

```http
GET /ws/USERID/user_recommendations/?locale=LOCALE&start=START&size=SIZE HTTP/1.1
Authorization: Bearer TOKEN
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
locale         | yes       | IETF language tag | Results may be biased for the given locale
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | item page size    | Number of content items to return - 100 by default

The response lists user items, including the assigned category and the profile description.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: private, max-age=3600

{
 "users": {
  "total": 1,
  "items": [
   {
    "position": 0,
    "category": 122,
    "id": "USERID",
    "resource_url": "http://path/to/user/",
    "display_name": "USERNAME",
    "avatar_thumbnail_url": "http://path/to/avatar/medium.jpg",
    "description": "some desc"
   }
  ]
 }
}
```

Friends
=======

### Get

Retrieve a list of friends (from external systems).

```http
GET /ws/USERID/friends/?device_filter=DEVICE_TYPE&share_filter= HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
device_filter  | no        | `ios`, `android`  | Exclude any users who don't have the specified device type
share_filter   | no        | `true`            | Include only those users with whom the user has shared content

The list can contain two user types: rockpack and external.  Rockpack users include a `resource_url` for
full profile detail.  External users include `external_system` and `external_uid` fields to identify the user.

The `last_shared_date` field specifies the date on which the user last shared some content with this
friend (or `null` if never shared).
If `share_filter` is specified then the result list is sorted by descending `last_shared_date`,
otherwise the list is sorted alphabetically by `display_name`.

```http
HTTP/1.1 200 OK
Cache-Control: private, max-age=600
Content-Type: application/json

{
 "total": 2,
 "users": {
  "items": [
   {
    "position": 0,
    "resource_url": "http://user/resource/url/",
    "id": "0nXumv5EBp8NCCDeDzvxpg",
    "display_name": "Allan B",
    "email": "allan@rockpack.com",
    "avatar_thumbnail_url": "http://rockpack/avatar/img.jpg",
    "last_shared_date": "2013-08-28T16:26:02.222917"
   },
   {
    "position": 1,
    "external_system": "facebook",
    "external_uid": "504775065",
    "display_name": "Gregory Talon",
    "email": null,
    "avatar_thumbnail_url": "http://facebook/picture.jpg",
    "has_ios_device": true,
    "last_shared_date": null
   }
  ]
 }
}
```

External Accounts
=================

### Get

Retrieve a list of external accounts connected with a rockpack user.

```http
GET /ws/USERID/external_accounts/ HTTP/1.1
Authorization: Bearer TOKEN
```

Each item in the result list includes the system label, the id of the user on that system,
and the user's token for that system.

The current supported list of systems is: `facebook`, `twitter`, `google`, & `apns`.

```http
HTTP/1.1 200 OK
Cache-Control: private, max-age=60
Content-Type: application/json

{
 "external_accounts": {
  "total": 1,
  "items": [
   {
    "resource_url": "http://resource/url/for/connection/",
    "external_system": "SYSTEM LABEL",
    "external_uid": "123",
    "external_token": "xxx",
    "token_expires": "2013-01-01T00:00:00",
    "token_permissions": "read,write",
    "meta": null
   }
  ]
 }
}
```

### Connect

Add a new connection to an external account.

```http
POST /ws/USERID/external_accounts/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

{
 "external_system": "facebook",
 "external_token": "xxx",
 "token_expires": "2013-03-28T19:16:13",
 "token_permissions": "read,write",
 "meta": {
  "key": "value"
 }
}
```

Parameter         | Required | Value      | Description
:---------------- | :------- | :--------- | :----------
external_system   | Yes      | `facebook` | Identifier for the external service
external_token    | Yes      | String     | Access token provided by service
token_expires     | No       | String     | ISO format datetime string, as provided by external service
token_permissions | No       | String     | Comma-separated list of external permissions (e.g. Facebook scope)
meta              | No       | Object     | Any additional metadata, as a JSON object or dictionary

A `201` is returned if the connection is created successfully and a `204` if existing account data is updated.

```http
HTTP/1.1 201 CREATED
Location: http://resource/url/for/connection/

{
 "resource_url": "http://resource/url/for/connection/",
 "id": 123
}
```

An error is returned if the user is already connected with a different external account
for the same system, or if another user is connected with the account.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "message": "External account mismatch",
 "error": "invalid_request"
}
```

### Disconnect

Delete the associated resource to disconnect an external account from a user.

```http
DELETE /ws/USERID/external_accounts/ID/ HTTP/1.1
Authorization: Bearer TOKEN
```

A `204` is returned on success and a `404` is returned if the resource doesn't exist.

```http
HTTP/1.1 204 NO CONTENT
```

```http
HTTP/1.1 404 BAD REQUEST
Content-Type: application/json

{
 "error": "Not Found"
}
```

Content Report
==============

### Post

Post a record of content the user has flagged as inappropriate.

```http
POST /ws/USERID/content_reports/?locale=LOCALE&tracking_code=CODE HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

{
 "object_type": "channel",
 "object_id": "123",
 "reason": "just because"
}
```

Parameter      | Required? | Value                       | Description
:------------- | :-------- | :-------------------------- | :----------
object_type    | yes       | `channel`, `video`, `user`  | Specifies the type of content
object_id      | yes       | unique content id           | The id of the channel, video, or user
reason         | yes       | string                      | Limited to 256 characters
locale         | no        | IETF language tag           |
tracking_code  | no        | string                      | The value for the last retrieved tracking_code

On error:

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "form_errors": {
  "object_id": [
   "invalid id"
  ]
 }
}
```

On success:

```http
HTTP/1.1 204 NO CONTENT
Content-Type: application/json
```
