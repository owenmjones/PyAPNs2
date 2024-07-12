import json
import logging

from enum import Enum
from typing import Dict, Optional, Tuple, Union
from httpx import Response

from .credentials import CertificateCredentials
from .errors import exception_class_for_reason
from .payload import Payload


class NotificationPriority(Enum):
    Immediate = "10"
    Delayed = "5"


class NotificationType(Enum):
    Alert = "alert"
    Background = "background"
    VoIP = "voip"
    Complication = "complication"
    FileProvider = "fileprovider"
    MDM = "mdm"


DEFAULT_APNS_PRIORITY = NotificationPriority.Immediate
MAX_CONNECTION_RETRIES = 3

logger = logging.getLogger(__name__)


class APNsClient(object):
    SANDBOX_SERVER = "api.development.push.apple.com"
    LIVE_SERVER = "api.push.apple.com"

    DEFAULT_PORT = 443
    ALTERNATIVE_PORT = 2197

    def __init__(
        self,
        credentials: Union[CertificateCredentials, str],
        use_sandbox: bool = False,
        use_alternative_port: bool = False,
    ) -> None:
        if isinstance(credentials, str):
            self.__credentials = CertificateCredentials(credentials)
        else:
            self.__credentials = credentials
        self._init_connection(use_sandbox, use_alternative_port)

    def _init_connection(self, use_sandbox: bool, use_alternative_port: bool) -> None:
        server = self.SANDBOX_SERVER if use_sandbox else self.LIVE_SERVER
        port = self.ALTERNATIVE_PORT if use_alternative_port else self.DEFAULT_PORT
        self._http_client = self.__credentials.create_connection(server, port)

    def send_notification(
        self,
        token_hex: str,
        notification: Payload,
        topic: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: Optional[int] = None,
        collapse_id: Optional[str] = None,
    ) -> None:
        response = self.send_request(
            token_hex, notification, topic, priority, expiration, collapse_id
        )
        result = self.get_notification_result(response)
        if result != "Success":
            if isinstance(result, tuple):
                reason, info = result
                raise exception_class_for_reason(reason)(info)
            else:
                raise exception_class_for_reason(result)

    def send_request(
        self,
        token_hex: str,
        notification: Payload,
        topic: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: Optional[int] = None,
        collapse_id: Optional[str] = None,
        push_type: Optional[NotificationType] = None,
    ) -> Response:

        headers = {}

        inferred_push_type = None  # type: Optional[str]
        if topic is not None:
            headers["apns-topic"] = topic
            if topic.endswith(".voip"):
                inferred_push_type = NotificationType.VoIP.value
            elif topic.endswith(".complication"):
                inferred_push_type = NotificationType.Complication.value
            elif topic.endswith(".pushkit.fileprovider"):
                inferred_push_type = NotificationType.FileProvider.value
            elif any(
                [
                    notification.alert is not None,
                    notification.badge is not None,
                    notification.sound is not None,
                ]
            ):
                inferred_push_type = NotificationType.Alert.value
            else:
                inferred_push_type = NotificationType.Background.value

        if push_type:
            inferred_push_type = push_type.value

        if inferred_push_type:
            headers["apns-push-type"] = inferred_push_type

        if priority != DEFAULT_APNS_PRIORITY:
            headers["apns-priority"] = priority.value

        if expiration is not None:
            headers["apns-expiration"] = "%d" % expiration

        auth_header = self.__credentials.get_authorization_header()
        if auth_header is not None:
            headers["authorization"] = auth_header

        if collapse_id is not None:
            headers["apns-collapse-id"] = collapse_id

        url = "/3/device/{}".format(token_hex)
        return self._http_client.post(url, json=notification.dict(), headers=headers)

    def get_notification_result(
        self, response: Response
    ) -> Union[str, Tuple[str, str]]:
        """
        Get result for specified response
        The function returns: 'Success' or 'failure reason' or ('Unregistered', timestamp)
        """
        if response.status_code == 200:
            return "Success"
        else:
            raw_data = response.read().decode("utf-8")
            data = json.loads(raw_data)  # type: Dict[str, str]
            if response.status_code == 410:
                return data["reason"], data["timestamp"]
            else:
                return data["reason"]
