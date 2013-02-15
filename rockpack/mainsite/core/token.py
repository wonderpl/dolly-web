import time
import struct
import hashlib
import hmac
from base64 import urlsafe_b64encode as b64encode, urlsafe_b64decode as b64decode
from rockpack.mainsite import app


ACCESS_TOKEN_VERSION = 1
ACCESS_TOKEN_FMT = '>Hd16s16s'  # Version (unsigned short), Expiry (double), 16 byte id, 16 byte id


def _sign(value):
    return hmac.new(app.secret_key, value, hashlib.sha1).hexdigest()


def create_access_token(userid, clientid, expiry=None):
    """Create a signed access token that encodes the given user and client ids.

    >>> create_access_token('AAAAAAAAAAAAAAAAAAAAAA', '', 1500000000)
    '18b3fbfd1ee7447c0792c17dadaa8549fa8196c2AAFB1loLwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    >>> len(create_access_token('', ''))
    96
    """
    # user & client ids are decoded so that the whole token can be recoded more efficiently
    userid, clientid = (b64decode(i + '==') for i in (userid, clientid))
    if not expiry:
        expiry = time.time() + app.config.get('ACCESS_TOKEN_EXPIRY', 3600)
    payload = struct.pack(ACCESS_TOKEN_FMT, ACCESS_TOKEN_VERSION, expiry, userid, clientid)
    return _sign(payload) + b64encode(payload)


def parse_access_token(token):
    """Return encoded user and client id if passed valid token.

    >>> parse_access_token('18b3fbfd1ee7447c0792c17dadaa8549fa8196c2AAFB1loLwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
    'AAAAAAAAAAAAAAAAAAAAAA', 'AAAAAAAAAAAAAAAAAAAAAA', 1500000000
    >>> parse_access_token('invalid')
    None
    """
    signature, payload = token[:40], token[40:]
    payload = b64decode(payload)
    if _sign(payload) == signature:
        version, expiry, userid, clientid = struct.unpack(ACCESS_TOKEN_FMT, payload)
        if version == 1 and expiry > time.time():
            userid, clientid = (b64encode(i)[:-2] for i in (userid, clientid))
            return userid, clientid
