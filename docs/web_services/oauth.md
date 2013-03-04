Register User
=============

Register a user.

```http
POST /ws/register/ HTTP/1.1
Authorization: Basic TOKEN
```

Parameter  | Required | Value  | Description
:--------- | :------- | :----- | :----------
username   | Yes      | String | Characters allowed should match regex [a-zA-Z0-9]
password   | Yes      | String |
first_name | No       | String
last_name  | No       | String
locale     | Yes      | IETF language tag
email      | Yes      | String

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

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
  "form_errors":
    {
      "email": [
        "Email address already registered"
      ]
    }
}
```

Register/Login Facebook User
======================

Both registrationa and login for external systems use the same resource.

Registrering a Facebook user.

```http
POST /ws/login/external/ HTTP/1.1
Authorization: Basic TOKEN
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
      "external_system":
        ["external system invalid"]
    }
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

