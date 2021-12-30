from contextlib import contextmanager

import requests
from requests.adapters import HTTPAdapter, Retry


@contextmanager
def get_requests_session(retries=3):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=0.1,
        status_forcelist=(408, 429, 500, 502, 503, 504),
        method_whitelist=["GET", "PUT", "POST", "PATCH", "DELETE"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    try:
        yield session
    except Exception:
        raise
    finally:
        session.close()
