rockpack web services
=====================

[User registration & authentication](oauth.md)

[Channel browsing, cover art, & categories](content.md)

[User data, including channels](user.md)

[Channel & video search](search.md)

[Content sharing services](share.md)

### Common Response Codes

Code | Description
:--- | :----------
200  | OK
201  | Used when a new resource has been created.  The response should include a `Location` header with the new resource url.
400  | There was an issue with the data (url query param or request body) passed to the server. See discussion below.
401  | The credentials in the `Authorization` header were invalid.
403  | The user has been authenticated but doesn't have access to this resource.
404  | Not found
405  | The method used (GET, POST, etc) isn't allowed for this resource.
500  | Something messed up on the server side. Worth retrying such requests.
503  | The backend service is down, hopefully temporarily. Try again.
504  | Timeout from backend service. Try again.

### Error Responses

There are two general formats to `400` error responses.

When sending a single piece of data the response json will include a single error message in the `message` field.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "message": "Some error message goes here."
}
```

If the error response relates to form-like data then the response json will include a `form_errors` field,
which will  map form field names to a list of related error messages.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "form_errors": {
  "field1": [ "Error message #1.", "Error message #2." ],
  "field2": [ "Another error message." ]
 }
}
```

## Service discovery

```http
GET /ws/?locale=LOCALE HTTP/1.1
Host: api.rockpack.com
```

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: public, max-age=60

{
 "cover_art": "http://api.rockpack.com/ws/cover_art/?locale=en-gb",
 "channel_search_terms": "http://api.rockpack.com/ws/complete/channels/?locale=en-gb",
 "register": "https://secure.rockpack.com/ws/register/",
 "categories": "http://api.rockpack.com/ws/categories/?locale=en-gb",
 "reset_password": "https://secure.rockpack.com/ws/reset-password/",
 "video_search": "http://api.rockpack.com/ws/search/videos/?locale=en-gb",
 "channel_search": "http://api.rockpack.com/ws/search/channels/?locale=en-gb",
 "video_search_terms": "http://api.rockpack.com/ws/complete/videos/?locale=en-gb",
 "popular_channels": "http://api.rockpack.com/ws/channels/?locale=en-gb",
 "popular_videos": "http://api.rockpack.com/ws/videos/?locale=en-gb",
 "login": "https://secure.rockpack.com/ws/login/",
 "login_register_external": "https://secure.rockpack.com/ws/login/external/",
 "refresh_token": "https://secure.rockpack.com/ws/token/"
}
```

## Client Location

Some services require the client's geographic location to be passed as a url query parameter
(for content filtering).  In order to obtain the location country code, as mapped from the client's
IP address, the client should use the location service.

```http
GET /ws/location/ HTTP/1.1
Host: secure.rockpack.com
```

The response will include a single JSON string with the ISO-3166 code value.  An empty string
will be returned if the IP address cannot be mapped.

```http
HTTP/1.1 200 OK
Content-Type: application/json

"GB"
```

To avoid additional requests the client may also use the `X-Rockpack-Get-Client-Location` header
on any web-service request and the location will be returned in the response headers.

```http
GET /ws/ HTTP/1.1
Host: api.rockpack.com
X-Rockpack-Get-Client-Location: true
```

```http
HTTP/1.1 200 OK
X-Rockpack-Client-Location: GB
Content-Type: application/json

"some content"
```

Note that there is a very small performance penalty for looking up the location so this header
should not be used on every request.


## Feedback

Send a `POST` request to `/ws/feedback/` with a message and optional score to submit user feedback.

```http
POST /ws/feedback/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

{
 "message": "feedback message string",
 "score": 5
}
```

A `form_errors` mapping will be returned if there's an error with the request.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "form_errors": {
  "message": ["Field cannot be longer than 1024 characters."],
  "score": ["Number must be between 0 and 9."]
 }
}
```

No content is returned on success.

```http
HTTP/1.1 204 NO CONTENT
```
