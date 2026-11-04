from setuptools import find_packages, setup

version = "1.1.0"  # x-release-please-version

setup(
    name="rastatime-analyzer",
    version=version,
    description="RASTATIME Analyzer",
    author="RASTATIME Project",
    url="https://github.com/vibesbuilder/RASTATIME",
    project_urls={
        "Bug Tracker": "https://github.com/vibesbuilder/RASTATIME/issues",
        "Source Code": "https://github.com/vibesbuilder/RASTATIME",
    },
    license="AGPLv3",
    packages=find_packages(exclude=["*tests*", "*fixtures*"]),
    entry_points={
        "console_scripts": [
            "rastatime-analyzer=rastatime_analyzer.main:cli",
        ]
    },
    python_requires=">=3.8",
    install_requires=[
        "mutagen>=1.45.1,<1.48",
        "pika>=1.0.0,<1.4",
        "requests>=2.33.0,<2.35",
        "typing_extensions",
    ],
    extras_require={
        "dev": [
            "distro>=1.8.0,<2",
            "types-requests>=2.31.0,<3",
        ],
        "sentry": [
            "sentry-sdk>=1.15.0,<2",
        ],
    },
    zip_safe=False,
)
