import pytest
from django.conf import settings


@pytest.fixture()
def api_client():
    # Lazy import: rest_framework.test triggers Django settings access at class
    # creation time. Importing inside the fixture ensures Django is fully
    # configured by pytest-django before this runs.
    from rest_framework.test import APIClient

    obj = APIClient()
    obj.credentials(
        HTTP_AUTHORIZATION=f"Api-Key {settings.CONFIG.general.api_key}",
    )
    return obj
