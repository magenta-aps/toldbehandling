# Copyright (c) 2023, Magenta ApS
# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

import os
import subprocess

import setuptools


# Solution from https://stackoverflow.com/questions/34070103/
def create_mo_files():
    data_files = []
    localedir = "told_common/locale"
    po_dirs = [
        f"{localedir}/{locale}/LC_MESSAGES/" for locale in next(os.walk(localedir))[1]
    ]
    for folder in po_dirs:
        mo_files = []
        po_files = [
            f for f in next(os.walk(folder))[2] if os.path.splitext(f)[1] == ".po"
        ]
        for po_file in po_files:
            filename, extension = os.path.splitext(po_file)
            mo_file = filename + ".mo"
            subprocess.call(["msgfmt", "-o", folder + mo_file, folder + po_file])
            mo_files.append(folder + mo_file)
        data_files.append((folder, mo_files))
    return data_files


setuptools.setup(
    name="told_common",
    version="0.0.1",
    description="Common functionality for customs apps",
    author="Magenta ApS",
    author_email="info@magenta.dk",
    packages=setuptools.find_packages(),
    install_requires=[
        "django==4.2.24",
        "gunicorn==22.0.0",
        "requests==2.31.0",
        "dataclasses-json==0.6.7",
        "WeasyPrint==62.3",
        "holidays==0.81",
        "pypdf==5.9.0",
        "django-forms-dynamic==1.0.0",
        "django_compressor==4.5.1",
        "django-libsass==0.9",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MPL 2.0",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    data_files=create_mo_files(),
)
