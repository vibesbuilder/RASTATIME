from setuptools import find_packages, setup

version = "1.0.0"  # x-release-please-version

setup(
    name="rastatime-api",
    version=version,
    description="RASTATIME API",
    author="RASTATIME Project",
    url="https://github.com/vibesbuilder/RASTATIME",
    project_urls={
        "Bug Tracker": "https://github.com/vibesbuilder/RASTATIME/issues",
        "Source Code": "https://github.com/vibesbuilder/RASTATIME",
    },
    license="AGPLv3",
    packages=find_packages(exclude=["*tests*", "*fixtures*"]),
    package_data={
        "rastatime_api": ["legacy/migrations/sql/*.sql"],
    },
    include_package_data=True,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "rastatime-api=rastatime_api.manage:main",
        ]
    },
    install_requires=[
        "bcrypt>=4.0,<6",
        "django-cors-headers>=4.4.0,<5",
        "django-filter>=25.1,<26",
        "django>=5.2,<5.3",
        "djangorestframework>=3.18.2,<3.19",
        "drf-spectacular>=0.22.1,<0.29",
        "requests>=2.33.0,<2.35",
        "waitress>=3.0.0,<4",
    ],
    extras_require={
        "prod": [
            "psycopg[binary]>=3.1.8,<4",
        ],
        "dev": [
            "django-coverage-plugin>=3.0.0,<4",
            "django-stubs>=5.1.0,<6",
            "djangorestframework-stubs>=1.8.0,<4",
            "model_bakery>=1.10.1,<2",
            "psycopg[binary]>=3.1.8,<4",
            "pylint-django>=2.5.3,<3",
            "pytest-django>=4.5.2,<5",
            "requests-mock>=1.10.0,<2",
        ],
        "sentry": [
            "sentry-sdk[django]>=1.15.0,<2",
        ],
    },
)
