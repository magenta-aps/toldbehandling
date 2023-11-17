#!/bin/bash

# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

set -e
MAKE_MIGRATIONS=${MAKE_MIGRATIONS:=false}
MIGRATE=${MIGRATE:=false}
TEST=${TEST:=false}
MAKEMESSAGES=${MAKEMESSAGES:=false}
COMPILEMESSAGES=${COMPILEMESSAGES:=false}
DJANGO_DEBUG=${DJANGO_DEBUG:=false}

python manage.py wait_for_db

if [ "${MAKE_MIGRATIONS,,}" = true ]; then
  echo 'generating migrations'
  python manage.py makemigrations --no-input
fi
if [ "${MIGRATE,,}" = true ]; then
  echo 'running migrations'
  python manage.py migrate
fi

if [ "${MAKE_MIGRATIONS,,}" = true ]; then
  echo 'generating migrations'
  python manage.py makemigrations --no-input
fi
if [ "${MIGRATE,,}" = true ]; then
  echo 'running migrations'
  python manage.py migrate
fi
if [ "${TEST,,}" = true ]; then
  echo 'running tests'
  python manage.py test
fi
if [ "${MAKEMESSAGES,,}" = true ]; then
  echo 'making messages'
  python manage.py makemessages --all --no-obsolete --add-location file
fi
if [ "${COMPILEMESSAGES,,}" = true ]; then
  echo 'compiling messages'
  python manage.py compilemessages
fi
if [ "${DJANGO_DEBUG,,}" = false ]; then
  echo 'collecting static files'
  ./manage.py collectstatic --no-input --clear
fi

exec "$@"
