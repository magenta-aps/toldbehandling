#!/bin/bash
set -e
MAKE_MIGRATIONS=${MAKE_MIGRATIONS:=false}
MIGRATE=${MIGRATE:=false}
TEST=${TEST:=false}
CREATE_USERS=${CREATE_USERS:=false}
DUMMYDATA=${DUMMYDATA:=false}
DJANGO_DEBUG=${DJANGO_DEBUG:=false}
MAKEMESSAGES=${MAKEMESSAGES:=true}
COMPILEMESSAGES=${COMPILEMESSAGES:=true}

if [ "$MAKE_MIGRATIONS" = true ] || [ "$MIGRATE" = true ] || [ "$TEST" = true ] || [ "$CREATE_USERS" = true ] || [ "$CREATE_DUMMY_USERS" = true ] || [ "$DUMMYDATA" = true ] || [ "$MAKEMESSAGES" == true ] || [ "$COMPILEMESSAGES" == true ]; then
  python manage.py wait_for_db
fi

if [ "$MAKE_MIGRATIONS" = true ]; then
  echo 'generating migrations'
  python manage.py makemigrations
fi
if [ "$MIGRATE" = true ]; then
  echo 'running migrations'
  python manage.py migrate
fi
if [ "$CREATE_USERS" = true ]; then
  echo 'create users'
  python manage.py create_dummy_users
fi
if [ "$TEST" = true ]; then
  echo 'running tests!'
  python manage.py test
fi
if [ "$DUMMYDATA" = true ]; then
  echo 'creating dummy data!'
  python manage.py create_dummy_aktører
  python manage.py create_dummy_satser
  python manage.py create_dummy_forsendelser
  python manage.py create_dummy_anmeldelser
fi

exec "$@"
