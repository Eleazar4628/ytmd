from setuptools import setup

setup(
    name="ymd",
    version="1.0.0",
    py_modules=["ytmd"],
    install_requires=[
        "yt-dlp",
        "requests",
    ],
    entry_points={
        'console_scripts': [
            'ymd=ytmd:main',
        ],
    },
)