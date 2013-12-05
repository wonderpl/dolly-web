Search
======

### Videos

A wrapper around youtube search.

```http
GET /ws/search/videos/?locale=LOCALE&q=QUERY&order=ORDER&&start=START&size=SIZE HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
q              | yes       | Unicode string    | The search term string
locale         | no        | IETF language tag | The locale gives a regional bias to the results
order          | no        | default, latest   | Specifies the order in which the results are returned
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | Result page size  | Number of items to return - max 50.

Response lists "fake" video instances similar to `/ws/videos/`.
View count and date uploaded from youtube are included.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=300

{
  "videos": {
    "total": 1,
    "items": [
      {
        "position": 0,
        "category": 124,
        "id": "Svi0xYzZY-01-hg64Qofzoyo",
        "title": "video title",
        "channel_title": "A channel title",
        "owner": {
          "id": "ziCAgGxbRpW-HNYTloYkQg",
          "username": "littlejimmy",
          "display_name": "Jimmy Wales",
          "avatar_thumbnail_url": "http://path/to/avatar/small.jpg",
          "resource_url": "http://dev.rockpack.com/ws/ziCAgGxbRpW-HNYTloYkQg/",
          "subscriber_count": 0,
          "profile_cover_url": "http://path/to/cover.jpg",
          "description": "something about me"
        },
        "video": {
          "id": "RP000001PXGLP4XTKU4VDFO37XZKEBMURKPOB6RQ",
          "source": "youtube",
          "source_id": "guFf8zveF0M",
          "source_username": "Some Youtube User",
          "source_view_count": 1000,
          "source_date_uploaded": "2012-12-01T02:06:14.000Z",
          "duration": 123,
          "thumbnail_url": "http://i.ytimg.com/vi/guFf8zveF0M/mqdefault.jpg"
        }
      }
    ]
  }
}
```

### Channels

List channels matching a specific search term.

```http
GET /ws/search/channels/?locale=LOCALE&q=QUERY&order=ORDER&start=START&size=SIZE HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
q              | yes       | Unicode string    | The search term string
locale         | no        | IETF language tag | The locale gives a regional bias to the results
order          | no        | default, latest   | Specifies the order in which the results are returned
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | Result page size  | Number of items to return - max 50.

Response is same format as `/ws/channels/`.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=300

{
  "channels": {
    "items": [
      {
        "position": 0,
        "id": "chHRF0V4rMT4CqULiSajAP2Q",
        "resource_url": "http://dev.rockpack.com/ws/ziCAgGxbRpW-HNYTloYkQg/channels/chHRF0V4rMT4CqULiSajAP2Q/",
        "title": "MY FAVOURITE TED TALKS",
        "subscriber_count": 69,
        "cover": {
          "thumbnail_url": "http://path/to/channel/cover.jpg",
          "aoi": [0, 0, 1, 1],
        },
        "owner": {
          "id": "ziCAgGxbRpW-HNYTloYkQg",
          "name": "Jimmy Wales",
          "avatar_thumbnail_url": "http://path/to/avatar/small.jpg"
        }
      }
    ],
    "total": 1
  }
}
```

### Users

List users matching or containing a specific search term.

```http
GET /ws/search/users/?q=QUERY&start=START&size=SIZE HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
q              | yes       | Unicode string    | The search term string
start          | no        | 0-based integer   | Used for paging through the result items
size           | no        | Result page size  | Number of items to return - max 50.

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=300

{
  "users": {
    "items": [
      {
        "id": "ziCAgGxbRpW-HNYTloYkQg",
        "username": "littlejimmy",
        "display_name": "Jimmy Wales",
        "avatar_thumbnail_url": "http://path/to/avatar/small.jpg",
        "resource_url": "http://dev.rockpack.com/ws/ziCAgGxbRpW-HNYTloYkQg/"
      }
    ],
    "total": 1
  }
}

```

Complete
========

### Videos

Wrapper around google's search suggest service.

```http
GET /ws/complete/videos/?locale=LOCALE&q=QUERY HTTP/1.1
```

Parameter      | Required? | Value             | Description
:------------- | :-------- | :---------------- | :----------
q              | yes       | Unicode string    | The search term string
locale         | no        | IETF language tag | The locale gives a regional bias to the results

Maximum 10 results returned.

NB: The result is JSONP format, with `window.google.ac.h()` function call wrapper.

```http
HTTP/1.1 200 OK
Content-Type: text/javascript
Cache-Control: public, max-age=3600

window.google.ac.h(
 [
  "QUERY",
  [
   ["SUGGESTION 1",0],
   ["SUGGESTION 2",0]
  ],
  {"some": "metadata"}
 ]
)
```

### Channels

```http
GET /ws/complete/channels/?locale=LOCALE&q=QUERY HTTP/1.1
```

Same as `/ws/complete/videos/` but returns suggested channel names.

### Users

```http
GET /ws/complete/users/?locale=LOCALE&q=QUERY HTTP/1.1
```

Same as `/ws/complete/videos/` but returns suggested user names.


### All

```http
GET /ws/complete/all/?locale=LOCALE&q=QUERY HTTP/1.1
```

Same as `/ws/complete/videos/` but returns a mix of username, channel & video titles.
