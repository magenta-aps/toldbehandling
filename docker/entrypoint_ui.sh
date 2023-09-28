#!/bin/bash
set -e
MAKE_MIGRATIONS=${MAKE_MIGRATIONS:=false}
MIGRATE=${MIGRATE:=false}
TEST=${TEST:=false}
MAKEMESSAGES=${MAKEMESSAGES:=true}
COMPILEMESSAGES=${COMPILEMESSAGES:=true}
DJANGO_DEBUG=${DJANGO_DEBUG:=false}

if [ "$MAKE_MIGRATIONS" = true ]; then
  echo 'generating migrations'
  python manage.py makemigrations --no-input
fi
if [ "$MIGRATE" = true ]; then
  echo 'running migrations'
  python manage.py migrate
fi
if [ "$TEST" = true ]; then
  echo 'running tests'
  python manage.py test
fi
if [ "$MAKEMESSAGES" = true ]; then
  echo 'making messages'
  python manage.py makemessages --all --no-obsolete --add-location file
fi
if [ "$COMPILEMESSAGES" = true ]; then
  echo 'compiling messages'
  python manage.py compilemessages
fi
if [ "$DJANGO_DEBUG" = false ]; then
  echo 'collecting static files'
  ./manage.py collectstatic --no-input
fi

exec "$@"
