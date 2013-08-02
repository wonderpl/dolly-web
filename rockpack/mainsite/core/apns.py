import time
import datetime
import socket
import pkg_resources
import OpenSSL
from OpenSSL.SSL import WantReadError
import apnsclient
from rockpack.mainsite import app


def _refresh(self):
    """ Ensure socket is still alive. Reopen if needed. """
    if self._socket is None:
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.configure_socket()

            self._connection = OpenSSL.SSL.Connection(self._certificate.get_context(), self._socket)
            self.configure_connection()
            self._connection.connect(self._address)
            tries = 0
            while True:
                try:
                    self._connection.do_handshake()
                    break
                except WantReadError:
                    tries += 1
                    if tries >= 10:
                        raise
                    time.sleep(0.1)
        except Exception:
            self.close()
            raise

    self._readbuf = ""
    self._feedbackbuf = ""
    self._last_refresh = datetime.datetime.now()


apnsclient.Connection.refresh = _refresh

push_client = apnsclient

session = push_client.Session()

_con = session.get_connection(
    app.config['APNS_PUSH_TYPE'],
    cert_file=pkg_resources.resource_filename(__name__, app.config['APNS_CERT_NAME']),
    passphrase=app.config['APNS_PASSPHRASE']
)


push_client.connection = _con
