#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Python client library for the Facebook Platform.

This client library is designed to support the Graph API and the official
Facebook JavaScript SDK, which is the canonical way to implement
Facebook authentication. Read more about the Graph API at
http://developers.facebook.com/docs/api. You can download the Facebook
JavaScript SDK at http://github.com/facebook/connect-js/.

If your application is using Google AppEngine's webapp framework, your
usage of this module might look like this:

    user = facebook.get_user_from_cookie(self.request.cookies, key, secret)
    if user:
        graph = facebook.GraphAPI(user["access_token"])
        profile = graph.get_object("me")
        friends = graph.get_connections("me", "friends")

"""

import cgi
import hashlib
import time
import urllib
import base64
import hmac
import re


from flask import json
_parse_json = lambda s: json.loads(s)


FACEBOOK_PICTURE_URL = 'http://graph.facebook.com/%s/picture/?type=large'


class GraphAPI(object):
    """A client for the Facebook Graph API.

    See http://developers.facebook.com/docs/api for complete documentation
    for the API.

    The Graph API is made up of the objects in Facebook (e.g., people, pages,
    events, photos) and the connections between them (e.g., friends,
    photo tags, and event RSVPs). This client provides access to those
    primitive types in a generic way. For example, given an OAuth access
    token, this will fetch the profile of the active user and the list
    of the user's friends:

       graph = facebook.GraphAPI(access_token)
       user = graph.get_object("me")
       friends = graph.get_connections(user["id"], "friends")

    You can see a list of all of the objects and connections supported
    by the API at http://developers.facebook.com/docs/reference/api/.

    You can obtain an access token via OAuth or by using the Facebook
    JavaScript SDK. See http://developers.facebook.com/docs/authentication/
    for details.

    If you are using the JavaScript SDK, you can use the
    get_user_from_cookie() method below to get the OAuth access token
    for the active user from the cookie saved by the SDK.
    """
    def __init__(self, access_token=None):
        self.access_token = access_token

    def get_object(self, id, **args):
        """Fetchs the given object from the graph."""
        return self.request(id, args)

    def get_objects(self, ids, **args):
        """Fetchs all of the given object from the graph.

        We return a map from ID to object. If any of the IDs are invalid,
        we raise an exception.
        """
        args["ids"] = ",".join(ids)
        return self.request("", args)

    def get_connections(self, id, connection_name, **args):
        """Fetchs the connections for given object."""
        return self.request(id + "/" + connection_name, args)

    def put_object(self, parent_object, connection_name, **data):
        """Writes the given object to the graph, connected to the given parent.

        For example,

            graph.put_object("me", "feed", message="Hello, world")

        writes "Hello, world" to the active user's wall. Likewise, this
        will comment on a the first post of the active user's feed:

            feed = graph.get_connections("me", "feed")
            post = feed["data"][0]
            graph.put_object(post["id"], "comments", message="First!")

        See http://developers.facebook.com/docs/api#publishing for all of
        the supported writeable objects.

        Most write operations require extended permissions. For example,
        publishing wall posts requires the "publish_stream" permission. See
        http://developers.facebook.com/docs/authentication/ for details about
        extended permissions.
        """
        assert self.access_token, "Write operations require an access token"
        return self.request(parent_object + "/" + connection_name, post_args=data)

    def put_wall_post(self, message, attachment={}, profile_id="me"):
        """Writes a wall post to the given profile's wall.

        We default to writing to the authenticated user's wall if no
        profile_id is specified.

        attachment adds a structured attachment to the status message being
        posted to the Wall. It should be a dictionary of the form:

            {"name": "Link name"
             "link": "http://www.example.com/",
             "caption": "{*actor*} posted a new review",
             "description": "This is a longer description of the attachment",
             "picture": "http://www.example.com/thumbnail.jpg"}

        """
        return self.put_object(profile_id, "feed", message=message, **attachment)

    def put_comment(self, object_id, message):
        """Writes the given comment on the given post."""
        return self.put_object(object_id, "comments", message=message)

    def put_like(self, object_id):
        """Likes the given post."""
        return self.put_object(object_id, "likes")

    def delete_object(self, id):
        """Deletes the object with the given ID from the graph."""
        self.request(id, post_args={"method": "delete"})

    def request(self, path, args=None, post_args=None):
        """Fetches the given path in the Graph API.

        We translate args to a valid query string. If post_args is given,
        we send a POST request to the given path with the given arguments.
        """
        if not args:
            args = {}
        if self.access_token:
            if post_args is not None:
                post_args["access_token"] = self.access_token
            else:
                args["access_token"] = self.access_token
        post_data = None if post_args is None else urllib.urlencode(post_args)
        file = urllib.urlopen("https://graph.facebook.com/" + path + "?" +
                              urllib.urlencode(args), post_data)
        try:
            response = _parse_json(file.read())
        finally:
            file.close()
        if response and response.get("error"):
            raise GraphAPIError(response["error"]["type"],
                                response["error"]["message"])
        elif response and response.get("error_code"):
            raise GraphAPIError('unknown',
                                response.get('error_msg', ''),
                                response['error_code'])
        return response


ERROR_CODE_RE = re.compile('\(#(\d+)\)')


class GraphAPIError(Exception):
    def __init__(self, type, message, code=None):
        Exception.__init__(self, message)
        self.type = type
        self._error_code = code

    @property
    def error_code(self):
        if self._error_code:
            return self._error_code
        match = ERROR_CODE_RE.match(self.message)
        return match and int(match.group(1))


def get_user_from_cookie(cookies, app_id, app_secret):
    """Parses the cookie set by the official Facebook JavaScript SDK.

    cookies should be a dictionary-like object mapping cookie names to
    cookie values.

    If the user is logged in via Facebook, we return a dictionary with the
    keys "uid" and "access_token". The former is the user's Facebook ID,
    and the latter can be used to make authenticated requests to the Graph API.
    If the user is not logged in, we return None.

    Download the official Facebook JavaScript SDK at
    http://github.com/facebook/connect-js/. Read more about Facebook
    authentication at http://developers.facebook.com/docs/authentication/.
    """
    cookie = cookies.get("fbsr_" + app_id, "")
    if cookie:
        return get_user_from_oauth_cookie(cookie, app_id, app_secret)

    cookie = cookies.get("fbs_" + app_id, "")
    if not cookie:
        return None
    args = dict((k, v[-1]) for k, v in cgi.parse_qs(cookie.strip('"')).items())
    payload = "".join(k + "=" + args[k] for k in sorted(args.keys())
                      if k != "sig")
    sig = hashlib.md5(payload + app_secret).hexdigest()
    expires = int(args["expires"])
    if sig == args.get("sig") and (expires == 0 or time.time() < expires):
        return args
    else:
        return None


# OAuth2 support based on https://gist.github.com/1190267 and
# https://github.com/martey/python-sdk

def _token_request(**kwargs):
    args = urllib.urlencode(kwargs)
    file = urllib.urlopen('https://graph.facebook.com/oauth/access_token?' + args)
    try:
        token_response = cgi.parse_qs(file.read())
    finally:
        file.close()

    if 'access_token' in token_response:
        return token_response['access_token'][0], int(token_response['expires'][0])
    else:
        return None, 0


def renew_token(token, app_id, app_secret):
    return _token_request(
        grant_type='fb_exchange_token',
        fb_exchange_token=token,
        client_id=app_id,
        client_secret=app_secret)


def validate_token(token, app_id, app_secret):
    app_token = app_id + '|' + app_secret
    args = urllib.urlencode(dict(input_token=token, access_token=app_token))
    file = urllib.urlopen('https://graph.facebook.com/debug_token?' + args)
    try:
        token_response = json.load(file)
    finally:
        file.close()

    if 'data' in token_response and token_response['data'].get('is_valid'):
        return token_response['data']


def get_user_from_oauth_cookie(cookie, app_id, app_secret):
    cookie_data = parse_signed_cookie(cookie, app_secret)
    if not cookie_data:
        return

    token, expires = _token_request(
        code=cookie_data['code'],
        redirect_uri='',
        client_id=app_id,
        client_secret=app_secret)

    return dict(access_token=token, uid=cookie_data['user_id'])


def parse_signed_cookie(signed_request, secret):
    """Return dictionary with signed cookie data, or None if invalid."""
    def decode(s):
        """Perform base64 decoding for strings with missing padding."""
        l = len(s)
        return base64.urlsafe_b64decode(s.ljust(l + (l % 4), '='))
    try:
        esig, payload = signed_request.encode('utf8').split('.', 2)
        sig = decode(esig)
        data = _parse_json(decode(payload))
        assert data['algorithm'].upper() == 'HMAC-SHA256'
    except Exception:
        return
    else:
        if hmac.new(secret, payload, hashlib.sha256).digest() == sig:
            return data
