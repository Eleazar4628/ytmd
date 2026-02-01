from setuptools import setup

setup(
    name="ytmd",
    version="1.2.1",
    py_modules=["ytmd"],
    install_requires=[
        "yt-dlp",
        "requests",
    ],
    entry_points={
        'console_scripts': [
            'ytmd=ytmd:main',
        ],
    },
)