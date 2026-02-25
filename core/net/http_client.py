import requests
from core.net.policy import NetPolicy

_policy = NetPolicy()


def get(url: str, **kwargs):
    _policy.check_outbound(url)
    return requests.get(url, **kwargs)


def post(url: str, **kwargs):
    _policy.check_outbound(url)
    return requests.post(url, **kwargs)
