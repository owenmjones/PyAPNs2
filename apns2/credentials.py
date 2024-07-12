import time

from typing import Optional, Tuple
from httpx import Client

DEFAULT_TOKEN_LIFETIME = 2700
DEFAULT_TOKEN_ENCRYPTION_ALGORITHM = "ES256"


class CertificateCredentials(object):
    """
    Credentials for certificate authentication
    """

    def __init__(self, cert: str) -> None:
        self.__cert = cert

    def create_connection(self, server: str, port: int) -> Client:
        return Client(
            base_url=f"https://{server}:{port}",
            cert=self.__cert,
            http2=True,
            verify=True,
        )

    def get_authorization_header(self) -> None:
        return None

