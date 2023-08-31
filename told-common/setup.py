#
# Copyright (c) 2023, Magenta ApS
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

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
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MPL 2.0",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
)
