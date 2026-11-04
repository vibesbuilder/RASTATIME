from setuptools import find_packages, setup

version = "1.1.0"  # x-release-please-version

setup(
    name="rastatime-playout",
    version=version,
    description="RASTATIME Playout",
    author="RASTATIME Project",
    url="https://github.com/vibesbuilder/RASTATIME",
    project_urls={
        "Bug Tracker": "https://github.com/vibesbuilder/RASTATIME/issues",
        "Source Code": "https://github.com/vibesbuilder/RASTATIME",
    },
    license="AGPLv3",
    packages=find_packages(exclude=["*tests*", "*fixtures*"]),
    package_data={"": ["**/*.liq", "**/*.liq.j2", "*.types"]},
    entry_points={
        "console_scripts": [
            "rastatime-playout-notify=rastatime_playout.notify.main:cli",
        ]
    },
    python_requires=">=3.8",
    install_requires=[
        "backports.zoneinfo>=0.2.1,<0.3;python_version<'3.9'",
        "jinja2>=3.0.3,<3.2",
        "lxml>=4.5.0,<6.0.0",
        "mutagen>=1.45.1,<1.48",
        "python-dateutil>=2.8.1,<2.10",
        "python-vlc>=3.0.0",
        "requests>=2.33.0,<2.35",
        # RASTATIME 2026-08-31 — multichannel line-in feeder (MME capture
        # via PortAudio; the wheel bundles the PortAudio DLL, no system
        # install needed).  See engine/linein_feeder.py.
        "sounddevice>=0.5.0,<0.6",
        # RASTATIME 2026-09-05 — Core Audio session API for the preflight
        # "main_output_session_missing" watchdog (which Windows render
        # endpoint does liquidsoap.exe actually play to?).  Pure Python +
        # comtypes; Windows-only at runtime, imports are guarded.
        "pycaw>=20240210",
        "comtypes>=1.4",
        "typing-extensions",
    ],
    extras_require={
        "dev": [
            "distro>=1.8.0,<2",
            "requests-mock>=1.10.0,<2",
            "syrupy>=4.0.0,<5",
            "types-lxml==2025.03.30",
            "types-backports>=0.1.3,<1",
            "types-python-dateutil>=2.8.1,<3",
            "types-requests>=2.31.0,<3",
        ],
        "sentry": [
            "sentry-sdk>=1.15.0,<2",
        ],
    },
    zip_safe=False,
)
