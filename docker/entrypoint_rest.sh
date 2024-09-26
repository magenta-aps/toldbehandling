#!/bin/bash

# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

set -e
MAKE_MIGRATIONS=${MAKE_MIGRATIONS:=false}
MIGRATE=${MIGRATE:=false}
TEST=${TEST:=false}
CREATE_GROUPS=${CREATE_GROUPS:=true}
CREATE_USERS=${CREATE_USERS:=false}
CREATE_SYSTEM_USER=${CREATE_SYSTEM_USER:=false}
DUMMYDATA=${DUMMYDATA:=false}
DJANGO_DEBUG=${DJANGO_DEBUG:=false}
CREATE_POSTNUMRE=${CREATE_POSTNUMRE:=true}
CREATE_SPEDITORER=${CREATE_SPEDITORER:=true}

python manage.py wait_for_db

if [ "${MAKE_MIGRATIONS,,}" = true ]; then
  echo 'generating migrations'
  python manage.py makemigrations --no-input
fi
if [ "${MIGRATE,,}" = true ]; then
  echo 'running migrations'
  python manage.py migrate
fi

if [ "${CREATE_GROUPS,,}" = true ]; then
  echo 'create groups'
  python manage.py create_groups
fi

if [ "${CREATE_USERS,,}" = true ]; then
  echo 'create users'
  python manage.py create_dummy_users
fi
if [ "${CREATE_SYSTEM_USER,,}" = true ]; then
  echo 'create system user'
  python manage.py create_system_user
fi
if [ "${CREATE_POSTNUMRE,,}" = true ]; then
  echo 'creating postnumre'
  python manage.py create_postnumre
fi
if [ "${CREATE_SPEDITORER,,}" = true ]; then
  echo 'creating speditører'
  python manage.py create_speditører
fi
if [ "${TEST,,}" = true ]; then
  echo 'running tests!'
  python manage.py test
fi
if [ "${DUMMYDATA,,}" = true ]; then
  echo 'creating dummy aktører'
  python manage.py create_dummy_aktører
  echo 'creating dummy satser'
  python manage.py create_dummy_satser
  echo 'creating dummy forsendelser'
  python manage.py create_dummy_forsendelser
  echo 'creating dummy anmeldelser'
  python manage.py create_dummy_anmeldelser
fi

exec "$@"
