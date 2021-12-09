
import os

from setuptools import setup

def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}

setup(
    name="payment_link",
    version="0.0.1",
    author="Luis Santana",
    author_email="luis.santana@uchile.cl",
    description=".",
    url="https://eol.uchile.cl",
    packages=["payment_link"],
    install_requires=[
        'XBlock',
        ],
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'xblock.v1': ['payment_link = payment_link:PaymentLinkXBlock']
    },
    package_data=package_data("payment_link", ["static", "public"]),
)
