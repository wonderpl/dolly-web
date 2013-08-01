import time
import datetime
import socket
import OpenSSL
from OpenSSL.SSL import WantReadError
import apnsclient


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
