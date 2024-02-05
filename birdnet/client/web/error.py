MESSAGES = {
    "NsfwLoggedOut": "NSFW tweet, please log in",
    "Protected": "Protected tweet, you may try logging in if you have access",
    "Suspended": "This account has been suspended",
}


def error_message_by_reason(reason: str):
    if reason in MESSAGES:
        return MESSAGES[reason]
    return reason
