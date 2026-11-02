from setuptools import find_packages, setup

version = "1.0.0"  # x-release-please-version

setup(
    name="rastatime-api-client",
    version=version,
    description="RASTATIME API Client",
    author="RASTATIME Project",
    url="https://github.com/vibesbuilder/RASTATIME",
    project_urls={
        "Bug Tracker": "https://github.com/vibesbuilder/RASTATIME/issues",
        "Source Code": "https://github.com/vibesbuilder/RASTATIME",
    },
    license="AGPLv3",
    packages=find_packages(exclude=["*tests*", "*fixtures*", "libretime_*"]),
    package_data={"": ["py.typed"]},
    python_requires=">=3.8",
    install_requires=[
        "python-dateutil>=2.8.1,<2.10",
        "requests>=2.33.0,<2.35",
    ],
    extras_require={
        "dev": [
            "requests-mock>=1.10.0,<2",
            "types-python-dateutil>=2.8.1,<3",
            "types-requests>=2.31.0,<3",
        ],
    },
    zip_safe=False,
)
