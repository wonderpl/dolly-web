Share
=====

Services for sharing content.

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
