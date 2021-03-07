import time

from unittest.mock import patch, MagicMock, Mock

from httpx import Response

from apns2.client import APNsClient, CertificateCredentials
from apns2.errors import BadDeviceToken, InternalServerError
from apns2.payload import Payload

TOPIC = "com.example.App"
TOKEN = "ee7b1a56a07a771b8a031b055a7c94c046913320a0b8563086ded4f96ae58cc6"


def test_send_notification_success():
    with patch(
        "apns2.credentials.CertificateCredentials.create_connection"
    ) as create_connection_mock:
        http_client_mock = MagicMock()
        http_client_mock.post.return_value = Mock(status_code=200)

        create_connection_mock.return_value = http_client_mock

        client = APNsClient(CertificateCredentials("test/mycert.pem"))
        client.send_notification(
            token_hex=TOKEN,
            notification=Payload(alert="Test alert"),
            topic=TOPIC,
        )

        http_client_mock.post.assert_called_once()


def test_send_notification_failure_410():
    with patch(
        "apns2.credentials.CertificateCredentials.create_connection"
    ) as create_connection_mock:
        http_client_mock = MagicMock()
        http_client_mock.post.return_value = Response(
            status_code=410, json={"reason": "BadDeviceToken", "timestamp": time.time()}
        )

        create_connection_mock.return_value = http_client_mock

        client = APNsClient(CertificateCredentials("test/mycert.pem"))

        exception_raised = False
        try:
            client.send_notification(
                token_hex=TOKEN,
                notification=Payload(alert="Test alert"),
                topic=TOPIC,
            )
        except BadDeviceToken:
            exception_raised = True

        http_client_mock.post.assert_called_once()
        assert exception_raised is True


def test_send_notification_failure_500():
    with patch(
        "apns2.credentials.CertificateCredentials.create_connection"
    ) as create_connection_mock:
        http_client_mock = MagicMock()
        http_client_mock.post.return_value = Response(
            status_code=500, json={"reason": "InternalServerError"}
        )

        create_connection_mock.return_value = http_client_mock

        client = APNsClient(CertificateCredentials("test/mycert.pem"))

        exception_raised = False
        try:
            client.send_notification(
                token_hex=TOKEN,
                notification=Payload(alert="Test alert"),
                topic=TOPIC,
            )
        except InternalServerError:
            exception_raised = True

        http_client_mock.post.assert_called_once()
        assert exception_raised is True
