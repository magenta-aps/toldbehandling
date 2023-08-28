# Godsregistrering



## Running the app

You can run the app by running `docker-compose up`

## Interacting with the app

The app runs on `localhost:8000`. Locally you can log in with username = `admin` and
password = `admin`

You can find the TF10 form [here](http://localhost:8000/tf10).

And you can find the admin portal [here](http://localhost:8001/index).

The app also runs a REST api. It has a swagger interface which can be found
[here](http://localhost:7000/api/docs). To use it, first obtain a token using
`POST /api/token/pair` where you supply the following payload:

```
{
  "password": "admin",
  "username": "admin"
}
```

Then copy the `access` token (without quotation marks) and paste it in the box that pops
up when pressing the green `authorize` button. Now you can try the different api routes.

## Running the tests

You can run the tests as a part of the docker-compose up command by creating a
`docker-compose.override.yml` file. See the `docker-compose.override.template.yml` file
for an example.

You can also run tests locally by using `docker exec`:

```
docker exec godsregistrering-ui bash -c 'coverage run --source='.' --omit=manage.py,project/asgi.py,project/wsgi.py,project/test_mixins.py,*/admin.py,*/urls.py,*/tests.py,*/__init__.py,*/migrations/*,*/management/* manage.py test ; coverage report --show-missing'
```

and for the `rest` app:

```
docker exec godsregistrering-rest bash -c 'coverage run --source='.' --omit=manage.py,project/asgi.py,project/wsgi.py,project/test_mixins.py,*/admin.py,*/urls.py,*/tests.py,*/__init__.py,*/migrations/*,*/management/* manage.py test ; coverage report --show-missing'
```
