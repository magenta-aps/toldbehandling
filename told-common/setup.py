# Copyright (c) 2023, Magenta ApS
# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import setuptools

setuptools.setup(
    name="told_common",
    version="0.0.1",
    description="Common functionality for customs apps",
    author="Magenta ApS",
    author_email="info@magenta.dk",
    packages=setuptools.find_packages(),
    install_requires=[
        "django==4.2.2",
        "gunicorn==20.1.0",
        "requests==2.31.0",
        "dataclasses-json==0.6.0",
        "WeasyPrint==60.1",
        "holidays==0.38",
        "pypdf==3.17.3",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MPL 2.0",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
)
