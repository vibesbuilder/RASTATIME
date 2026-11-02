from setuptools import find_packages, setup

version = "1.0.0"  # x-release-please-version

setup(
    name="rastatime-shared",
    version=version,
    description="RASTATIME Shared",
    url="https://github.com/vibesbuilder/RASTATIME",
    author="RASTATIME Project",
    license="AGPLv3",
    packages=find_packages(exclude=["*tests*", "*fixtures*"]),
    package_data={"": ["py.typed"]},
    install_requires=[
        # zoneinfo has no IANA database on Windows without this package
        # (RASTATIME 2026-11-01: the CI runner failed on timezone "UTC";
        # locally it arrives as a dependency of Django).
        "tzdata>=2024.1;sys_platform=='win32'",
        "click>=8.0.4,<8.2",
        "pydantic>=2.9.0",
        "pyyaml>=5.3.1,<6.1",
    ],
    extras_require={
        "dev": [
            "types-backports>=0.1.3,<1",
            "types-pyyaml>=5.3.1,<7",
        ],
    },
)
