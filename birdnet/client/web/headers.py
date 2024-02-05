from birdnet.client.web.authorization import AuthorizationToken


class HeadersKeyName:
    AUTHORIZATION = "Authorization"
    GUEST_TOKEN = "x-guest-token"
    CSRF_TOKEN = "x-csrf-token"
    AUTH_TYPE = "x-twitter-auth-type"
    RATE_LIMIT_LIMIT = "x-rate-limit-limit"
    RATE_LIMIT_RESET = "x-rate-limit-reset"


DEFAULT_HEADERS = {
    "Authorization": AuthorizationToken.GUEST,
    "Origin": "https://twitter.com",
    "Referer": "https://twitter.com",
    HeadersKeyName.GUEST_TOKEN: "",
    "x-twitter-client-language": "en",
    "x-twitter-active-user": "yes",
}
