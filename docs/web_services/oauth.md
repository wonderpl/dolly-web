Based on [OAuth 2.0](http://self-issued.info/docs/rfc6749.html).

All these services require clients to be authenticed using an `Authorization`
header with the encoded client id and secret.
For further detail see [OAuth 2.0 Client Authentication]
(http://self-issued.info/docs/rfc6749.html#client-authentication).

On successful login or registration a `Bearer` token will be returned.
See OAuth 2.0 Bearer Token Usage [Access Token Response]
(http://self-issued.info/docs/draft-ietf-oauth-v2-bearer.html#ExAccTokResp).


Check Username Availability
===========================

Check if the username supplied is availavble to register


```http
POST /ws/register/availability/ HTTP/1.1
Authorization: Basic CLIENT_APP_CREDENTIALS

username=tonystark
```

Parameter  | Required | Value      | Description
:--------- | :------- | :--------- | :----------
username   | Yes      | String


Responds with whether the username supplied is available.


```http
HTTP/1.1 200 OK
Content-Type: application/json

{"available": true}
```

or

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"available": false}
```

Invalid_request errors are also returned where appropriate. See below.


Log-in User
===========

Retrieve access token credentials for a user.

```http
POST /ws/login/ HTTP/1.1
Authorization: Basic CLIENT_APP_CREDENTIALS
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=USER&password=PASS
```

This service follows the OAuth 2 [Resource Owner Password Credentials Grant flow]
(http://self-issued.info/docs/rfc6749.html#grant-password).

Parameter  | Required | Value      | Description
:--------- | :------- | :--------- | :----------
grant_type | Yes      | `password` | The type of grant that will be used when accessing the resource
username   | Yes      | String
password   | Yes      | String

Responds with an access token information.

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "token_type": "Bearer",
  "access_token": "some_access_token",
  "expires_in": "3600",
  "refresh_token": "some_refresh_token",
  "user_id": "USERID",
  "resource_url:" "http://path/to/user/info/"
}
```

Possible errors.

Insufficient content was passed to perform the log-in.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid_request"
}
```

The credentials supplied invalid for the user, or the user does not exists.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid_grant"
}
```

The `grant_type` specified for this request is invalid or not supported.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "unsupported_grant_type"
}
```

Register User
=============

Register a user.

```http
POST /ws/register/ HTTP/1.1
Authorization: Basic CLIENT_APP_CREDENTIALS
Content-Type: application/json

{
  "username": "theamazingspiderman",
  "password": "venom",
  "first_name": "Peter",
  "last_name": "Parker",
  "date_of_birth": "2003-01-24",
  "locale": "en-us",
  "email": "spidey@theavengers.com"
}
```

Parameter     | Required | Value  | Description
:------------ | :------- | :----- | :----------
username      | Yes      | String | Characters allowed should match regex [a-zA-Z0-9]
password      | Yes      | String | Minimum 6 characters
first_name    | No       | String |
last_name     | No       | String |
date_of_birth | Yes      | String | YYYY-MM-DD formatted date string
locale        | Yes      | String | IETF language tag
email         | Yes      | String | Email address

Responds with an access token information.

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "token_type": "Bearer",
  "access_token": "some_access_token",
  "expires_in": "3600",
  "refresh_token": "some_refresh_token",
  "user_id": "USERID",
  "resource_url:" "http://path/to/user/info/"
}
```

Possible errors.

Errors occurred with the form data.
```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "form_errors": {
  "username": [ "\"USERNAME\" is reserved" ],
  "locale": [ "This field is required." ],
  "password": [ "Field must be at least 6 characters long." ],
  "email": [ "Invalid email address." ]
 }
}
```

Login/Register User With External Credentials
======================

Log in or register a user with an external token, e.g. a Facebook access token.

```http
POST /ws/login/external/ HTTP/1.1
Authorization: Basic CLIENT_APP_CREDENTIALS
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

Parameter         | Required | Value     | Description
:---------------- | :------- | :-------- | :----------
external_system   | Yes      | `facebook`| Identifier for external service
external_token    | Yes      | String    | Access token provided by service
token_expires     | No       | String    | ISO format datetime string, as provided by external service
token_permissions | No       | String    | Comma-separated list of external permissions (e.g. Facebook scope)
meta              | No       | Object    | Any additional metadata, as a JSON object or dictionary

Responds with access token information on success.

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "token_type": "Bearer",
  "access_token": "some_access_token",
  "expires_in": "3600",
  "refresh_token": "some_refresh_token",
  "user_id": "USERID",
  "resource_url:" "http://path/to/user/info/"
}
```

If the token is valid but the external system id determined from the provided token does not match an existing record
then a new user record is created.  In this case the response will include a `registered` field.

Possible errors.

`external_system` provided is not supported:

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
  "form_errors":
    {
      "external_system": ["external system invalid"]
    },
  "error": "invalid_request"
}
```

`external_token` failed validation by the `external_system`

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
  "error": "unauthorized_client"
}
```

Refreshing Tokens
=================

This service follows the OAuth 2 [Refreshing an Access Token flow]
(http://self-issued.info/docs/rfc6749.html#token-refresh).

```http
POST /ws/token/ HTTP/1.1
Authorization: Basic CLIENT_APP_CREDENTIALS
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=TOKEN
```

Parameter       | Required | Value           | Description
:-------------- | :------- | :-------------- | :----------
grant_type      | Yes      | `refresh_token` | The type of grant that will be used when accessing the resource
refresh_token   | Yes      | String          | The `refresh_token` supplied along with the `access_token` at login

Possible errors.


Insufficient content was passed.
```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
  "error": "invalid_request"
}
```

The credentials supplied invalid for the user, or the user does not exists.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "invalid_grant"
}
```

The `grant_type` specified for this request is invalid or not supported.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
    "error": "unsupported_grant_type"
}
```

Reset Password
==============

Initiate a password reset flow

```http
POST /ws/reset-password/ HTTP/1.1
Authorization: Basic CLIENT_APP_CREDENTIALS
Content-Type: application/x-www-form-urlencoded

username=USER
```

Parameter       | Required | Value     | Description
:-------------- | :------- | :-------- | :----------
username        | Yes      | String    | Username or email address of user

If user isn't found then a `400` response will be returned.

```http
HTTP/1.1 400 OK
Content-Type: application/json

{
 "error": "invalid_request"
}
```

If request was accepted and the reset email sent then a `204` will be returned.

```http
HTTP/1.1 204 OK
Content-Type: application/json
```

Sessions
========

Record a new session by `POST`ing a session description:

```http
GET /ws/session/ HTTP/1.1
Host: secure.rockpack.com
Authorization: Bearer xxx
Content-Type: application/json

"a value"
```

If there is a logged-in user on the client then the access token should be provided with the
`Authorization` header, otherwise it can be omitted.
The request body is optional but if provided should define a JSON string describing the session.

A `204` will be returned on success.

```http
HTTP/1.1 204 NO CONTENT
```
