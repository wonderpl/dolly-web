from flask.ext.rauth import RauthResponse
from flask.ext.rauth import parse_response


def patch_rauth():
    # We need to patch RauthResponse because obj.response
    # might be a callable which returns a dict (which Rauth
    # isn't expecting), so we need to call it if it is

    def patched_content(obj):
            '''
            The content associated with the response. The content is parsed into a
            more useful format, if possible, using :func:`parse_response`.

            The content is cached, so that :func:`parse_response` is only run once.
            '''
            if obj._cached_content is None:
                # the parsed content from the server
                r = parse_response(obj.response)
                if callable(r):
                    obj._cached_content = r()
                else:
                    obj._cached_content = r
            return obj._cached_content

    setattr(RauthResponse,'content', property(patched_content))
