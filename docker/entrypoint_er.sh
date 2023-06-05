#!/bin/bash
set -e

GENERATE_DB_DOCUMENTATION=${GENERATE_DB_DOCUMENTATION:=true}
if [[ "$GENERATE_DB_DOCUMENTATION" = true ]]; then

  RESULT=1
  while [[ $RESULT != "0" ]] ; do
    if [[ "$ENVIRONMENT" == "development" ]]; then
    RESULT=$(bash -c 'exec 3<> /dev/tcp/localhost/8000; echo $?' 2>/dev/null);
    else
    RESULT=$(bash -c 'exec 3<> /dev/tcp/web/443; echo $?' 2>/dev/null);
    fi
    sleep 1
  done

  java -jar /usr/local/share/schemaspy.jar -dp /usr/local/share/postgresql.jar -t pgsql -db $POSTGRES_DB -host $POSTGRES_HOST -u $POSTGRES_USER -p $POSTGRES_PASSWORD -o /doc/er_html
  exec "$@"

fi
