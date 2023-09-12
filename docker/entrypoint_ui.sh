#!/bin/bash
set -e
TEST=${TEST:=false}
MAKEMESSAGES=${MAKEMESSAGES:=true}
COMPILEMESSAGES=${COMPILEMESSAGES:=true}
DJANGO_DEBUG=${DJANGO_DEBUG:=false}

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
