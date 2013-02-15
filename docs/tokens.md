refresh tokens
--------------

random string saved with user record

access tokens
-------------

    # create:
    payload = '%s:%s:%f' % (uid, client_id, expiry)
    sig = hmac.new(app.secret_key, payload, hashlib.sha1).hexdigest()
    token = sig + payload

    # verify:
    sig, payload = token[:40], token[40:]
    hmac.new(app.secret_key, payload, hashlib.sha1) == sig
