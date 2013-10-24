import time
import struct
import hashlib
import hmac
from base64 import urlsafe_b64encode as b64encode, urlsafe_b64decode as b64decode
from rockpack.mainsite import app


ACCESS_TOKEN_VERSION = 1
ACCESS_TOKEN_FMT = '>Hd16s16s'  # Version (unsigned short), Expiry (double), 16 byte id, 16 byte id

UNSUBSCRIBE_TOKEN_VERSION = 1
UNSUBSCRIBE_TOKEN_FMT = '>BB16s'    # Version (unsigned byte), List (unsigned byte), 16 byte id


class ExpiredTokenError(TypeError):
    pass


def _sign(value):
    return hmac.new(app.secret_key, value, hashlib.sha1).hexdigest()


# user & client ids are decoded so that the whole token can be recoded more efficiently
def _decode_id(id):
    return b64decode(str(id) + '==')


def _encode_id(id):
    return b64encode(id)[:-2]


def _create_token(format, version, *values):
    payload = struct.pack(format, version, *values)
    return _sign(payload) + b64encode(payload)


def _parse_token(format, token):
    signature, payload = token[:40], token[40:]
    try:
        payload = b64decode(str(payload))
    except TypeError:
        return
    if _sign(payload) == signature:
        return struct.unpack(format, payload)


def create_access_token(userid, clientid, age):
    """Create a signed access token that encodes the given user and client ids.

    >>> create_access_token('AAAAAAAAAAAAAAAAAAAAAA', '', 1500000000)
    '18b3fbfd1ee7447c0792c17dadaa8549fa8196c2AAFB1loLwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    >>> len(create_access_token('', ''))
    96
    """
    userid, clientid = (_decode_id(i) for i in (userid, clientid))
    expiry = time.time() + age
    return _create_token(ACCESS_TOKEN_FMT, ACCESS_TOKEN_VERSION, expiry, userid, clientid)


def parse_access_token(token):
    """Return encoded user and client id if passed valid token.

    >>> parse_access_token('18b3fbfd1ee7447c0792c17dadaa8549fa8196c2AAFB1loLwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
    'AAAAAAAAAAAAAAAAAAAAAA', 'AAAAAAAAAAAAAAAAAAAAAA'
    >>> parse_access_token('invalid')
    None
    """
    try:
        version, expiry, userid, clientid = _parse_token(ACCESS_TOKEN_FMT, token)
    except TypeError:
        pass
    else:
        if version == 1:
            if expiry < time.time():
                raise ExpiredTokenError()
            userid, clientid = (_encode_id(i) for i in (userid, clientid))
            return userid, clientid


def create_unsubscribe_token(listid, userid):
    return _create_token(UNSUBSCRIBE_TOKEN_FMT, UNSUBSCRIBE_TOKEN_VERSION, listid, _decode_id(userid))


def parse_unsubscribe_token(token):
    try:
        version, listid, userid = _parse_token(UNSUBSCRIBE_TOKEN_FMT, token)
    except TypeError:
        pass
    else:
        if version == 1:
            return listid, _encode_id(userid)
