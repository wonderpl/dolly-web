Share
=====

Services for sharing content.

### Email Share

Share a channel or video by sending an email to a specific address.

```http
POST /ws/share/email/?locale=LOCALE HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

{
 "object_type": "channel",
 "object_id": "chuGtvlm1YkfeNcZ6akic8uw",
 "email": "email@address.com",
 "external_system": "email",
 "external_uid": "123",
 "name": null
}
```

Parameter       | Required? | Value                         | Description
:-------------- | :-------- | :---------------------------- | :----------
object_type     | yes       | `channel` or `video_instance` | Specifies the type of content
object_id       | yes       | unique content id             | The id of the channel or video
email           | yes       | recipient email address       |
name            | no        | recipient full name           |
external_system | no        | `email`, `facebook`, `google` |
external_uid    | no        | String user identifier        | Must be unique for the user and external_system
locale          | no        | IETF language tag             |

On success will return a `204` and will send an email to the specified email recipient.
If values for `external_system` and `external_uid` are provided then the email address (and optionally
the full name) of the associated friend will be updated.  If `external_system` is `email` and an
associated friend record does not exist then a new record will be created.
The updated friend record with email address can be accessed again with the friends service -
see [user services](user.md).

```http
HTTP/1.1 204 NO CONTENT
```

On error returns a `400` with a `form_errors` field:

```http
HTTP/1.1 400 ERROR
Content-Type: application/json

{
 "error": "invalid_request",
 "form_errors": {
  "email": [ "Invalid email address." ],
  "external_system": [ "Not a valid choice" ],
  "object_id": [ "invalid id" ]
 }
}
```

### Share link

Used to generate a link for sharing a channel or video.

```http
POST /ws/share/link/?locale=LOCALE HTTP/1.1
Authorization: Bearer TOKEN
Content-Type: application/json

{
 "object_type": "video_instance",
 "object_id": "viCXo9WGggTYuvOcTicC3YMw"
}
```

Parameter      | Required? | Value                         | Description
:------------- | :-------- | :---------------------------- | :----------
object_type    | yes       | `channel` or `video_instance` | Specifies the type of content
object_id      | yes       | unique content id             | The id of the channel, video, or user
locale         | no        | IETF language tag             |

On success, responds with a `201` with the url specified both in the `resource_url` and
in the `Location` header.

The response also includes a `message` value, which can be used as the default text for
the sharing message.

```http
HTTP/1.1 201 CREATED
Location: http://base/s/LINKID
Content-Type: application/json

{
 "id": "LINKID",
 "resource_url": "http://base/s/LINKID",
 "message": "Watch \"X\" on rockpack"
}
```

On error the `form_errors` field will specify the cause of the issue.

```http
HTTP/1.1 400 BAD REQUEST
Content-Type: application/json

{
 "error": "invalid_request",
 "form_errors": {
  "object_id": ["invalid id"]
 }
}
```
