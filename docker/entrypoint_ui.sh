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
SKIP_IDP_METADATA=${SKIP_IDP_METADATA:=false}

python manage.py wait_for_db


if [ "${MAKE_MIGRATIONS,,}" = true ]; then
  echo 'generating migrations'
  python manage.py makemigrations --no-input
fi
if [ "${MIGRATE,,}" = true ]; then
  echo 'running migrations'
  python manage.py migrate
fi
python manage.py createcachetable
if [ "${SKIP_IDP_METADATA,,}" = false ]; then
  python manage.py update_mitid_idp_metadata
fi

echo 'collecting static files'
./manage.py collectstatic --no-input

if [ "${TEST,,}" = true ]; then
  echo 'running tests'
  python manage.py test
fi
if [ "${MAKEMESSAGES,,}" = true ]; then
  echo 'making messages'
  ls "/app/told_common/"
  python manage.py makemessages --locale=kl --no-obsolete --add-location file
  python manage.py makemessages --locale=da --no-obsolete --add-location file
fi
if [ "${COMPILEMESSAGES,,}" = true ]; then
  echo 'compiling messages'
  python manage.py compilemessages --locale=kl
  python manage.py compilemessages --locale=da
fi

exec "$@"
