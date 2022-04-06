from hypothesis import settings
from resource import setrlimit, RLIMIT_AS

MAIN_PROFILE = "main"

GB4 = 4*2**30


def pytest_sessionstart(session):
    setrlimit(RLIMIT_AS, (GB4, GB4))
    settings.register_profile(MAIN_PROFILE, print_blob=True)
    settings.load_profile(MAIN_PROFILE)
