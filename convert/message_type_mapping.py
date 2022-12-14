MSG_TYPE_TEXT = "text"
MSG_TYPE_IMAGE = "image"
MSG_TYPE_AUDIO = "audio"
MSG_TYPE_VIDEO = "video"
MSG_TYPE_CONTACT = "contact"
MSG_TYPE_LOCATION = "location"
MSG_TYPE_DOCUMENT = "document"
MSG_TYPE_GIF = "gif"
MSG_TYPE_STICKER = "sticker"

MSG_TYPE_TO_ANDROID_MSG_TYPE_MAPPING = {
    MSG_TYPE_TEXT: 0,
    MSG_TYPE_IMAGE: 1,
    MSG_TYPE_AUDIO: 2,
    MSG_TYPE_VIDEO: 3,
    MSG_TYPE_CONTACT: 4,
    MSG_TYPE_LOCATION: 5,
    MSG_TYPE_DOCUMENT: 9,
    MSG_TYPE_GIF: 13,
    MSG_TYPE_STICKER: 20
}

MSG_TYPE_TO_IPHONE_MSG_TYPE_MAPPING = {
    MSG_TYPE_TEXT: 0,
    MSG_TYPE_IMAGE: 1,
    MSG_TYPE_AUDIO: 3,
    MSG_TYPE_VIDEO: 2,
    MSG_TYPE_CONTACT: 4,
    MSG_TYPE_LOCATION: 5,
    MSG_TYPE_DOCUMENT: 8,
    MSG_TYPE_GIF: 11,
    MSG_TYPE_STICKER: 15
}

ANDROID_MSG_TYPE_TO_MSG_TYPE_MAPPING = {v: k for k, v in MSG_TYPE_TO_ANDROID_MSG_TYPE_MAPPING.items()}


def convert_iphone_message_type_to_android(android_message_type: int) -> int:
    return MSG_TYPE_TO_IPHONE_MSG_TYPE_MAPPING[ANDROID_MSG_TYPE_TO_MSG_TYPE_MAPPING[android_message_type]] if \
        android_message_type in ANDROID_MSG_TYPE_TO_MSG_TYPE_MAPPING else -1
