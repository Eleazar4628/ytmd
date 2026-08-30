from setuptools import setup

setup(
    name="ytmd",
    version="1.6",
    py_modules=["ytmd"],
    python_requires=">=3.7",
    install_requires=[
        "yt-dlp",
        "requests",
        "colorama",
    ],
    entry_points={
        'console_scripts': [
            'ytmd=ytmd:main',
        ],
    },
)
