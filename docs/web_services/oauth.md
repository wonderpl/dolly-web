Log-in User
===========

Retrieve access token credentials for a user.

```http
POST /ws/login/ HTTP/1.1
Authorization: Basic CLIENT_APP_CREDENTIALS
Content-Type: application/x-www-form-urlencoded

{
    "username": "ironman",
    "password": "pepperpots"
}
```

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
  "resource_url:" "/ws/USERID/"
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
Content-Type: application/x-www-form-urlencoded

{
  "username": "theamazingspiderman",
  "password": "venom",
  "first_name": "Peter",
  "last_name": "Parker",
  "date_of_birth": "2003-01-24",
  "locale": "en-us",
  "spidey@theavengers.com"
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
  "resource_url:" "/ws/USERID/"
}
```

Possible errors.

Errors occurred with the form data.
```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
  "form_errors": {
      "email": ["Email address already registered"]
    },
  "error": "invalid_request"
}
```

Register/Login Facebook User
======================

Both registrationa and login for external systems use the same resource.

Registrering a Facebook user.

```http
POST /ws/login/external/ HTTP/1.1
Authorization: Basic CLIENT_APP_CREDENTIALS
Content-Type: application/x-www-form-urlencoded

{
    "external_system": "facebook",
    "external_token": "some_fb_access_token"
}
```

Parameter       | Required | Value     | Description
:-------------- | :------- | :-------- | :----------
external_system | Yes      | `facebook`| Identifier for external service
external_token  | Yes      | String    | Access token provided by service

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
  "resource_url:" "/ws/USERID/"
}
```

If no user is found for the Facebook token provided, a user record (using information like fb username etc) will be used to generate a Rockpack account, before returning a Rockpack token/

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

```http
POST /ws/token/ HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/x-www-form-urlencoded

{
    "grant_type": "refresh_token",
    "refresh_token": "some_long_string"
}
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
