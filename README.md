<!--
SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>

SPDX-License-Identifier: MPL-2.0
-->

# Toldbehandling

This repository contains the Toldbehandling applications (internal and
public-facing) created by Magenta ApS for Naalakkersuisut, the
Government of Greenland.

## Running the app

You can run the app by running `docker-compose up`

## Interacting with the app

The app runs on `localhost:8000`. Locally you can log in with username =
`admin` and password = `admin`

You can find the TF10 form [here](http://localhost:8000/tf10).

And you can find the admin portal [here](http://localhost:8001/index).

The app also runs a REST api. It has a Swagger interface which can be
found [here](http://localhost:7000/api/docs). To use it, first obtain a
token using `POST /api/token/pair` where you supply the following
payload:

```
{
  "password": "admin",
  "username": "admin"
}
```

Then copy the `access` token (without quotation marks) and paste it in
the box that pops up when pressing the green `authorize` button. Now you
can try the different api routes.

## Running the tests

You can run the tests as a part of the docker-compose up command by
creating a `docker-compose.override.yml` file. See the
`docker-compose.override.template.yml` file for an example.

You can also run tests locally by using `docker exec`:

```
docker exec toldbehandling-ui bash -c 'coverage run manage.py test ; coverage report --show-missing'
```

and for the `rest` app:

```
docker exec toldbehandling-rest bash -c 'coverage run manage.py test ; coverage report --show-missing'
```

and for the `admin` app:

```
docker exec toldbehandling-admin bash -c 'coverage run manage.py test ; coverage report --show-missing'
```


## Licensing and copyright


Copyright (c) 2023, Magenta ApS.

The Toldbehandling software is free software and may be used, studied,
modified and shared under the terms of Mozilla Public License, version
2.0. A copy of the license text may be found in the LICENSE file.
