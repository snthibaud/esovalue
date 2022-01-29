from hypothesis import settings

MAIN_PROFILE = "main"


def pytest_sessionstart(session):
    settings.register_profile(MAIN_PROFILE, print_blob=True)
    settings.load_profile(MAIN_PROFILE)
