import base64
import struct
import requests
from rockpack.mainsite import app


def _myrrix_request(method, path, **kwargs):
    response = requests.request(method, app.config['MYRRIX_URL'] + path, **kwargs)
    response.raise_for_status()
    return response


# myrixx needs integer ids (using java (signed) long values)
# To construct we convert the first 8 bytes of the identifier
# There may be collisions but it's unlikely
def _to_int(s):
    return struct.unpack('q', base64.urlsafe_b64decode(str(s) + '==')[:8])[0]


def _from_int(i):
    return base64.urlsafe_b64encode(struct.pack('q', i))[:10]


def load_activity(activity):
    data = ('%d,%d,%d\n' % (_to_int(userid), _to_int(channelid[2:]), weight)
            for userid, channelid, weight in activity)
    return _myrrix_request('post', '/ingest', data=data,
                           headers={'Content-Type': 'application/csv'})


def record_activity(userid, channelid, weight=1):
    path = '/pref/%s/%s' % (_to_int(userid), _to_int(channelid[2:]))
    return _myrrix_request('post', path, data=str(weight))


def get_channel_recommendations(userid):
    try:
        response = _myrrix_request('get', '/recommend/%d' % _to_int(userid))
    except Exception, e:
        if hasattr(e, 'response') and e.response.status_code == 404:
            # No recommendations for this user yet
            return []
        raise
    return [(_from_int(c), s) for c, s in response.json()]
