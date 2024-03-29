#!/bin/bash

# SPDX-FileCopyrightText: 2023 Magenta ApS <info@magenta.dk>
#
# SPDX-License-Identifier: MPL-2.0

set -e

GENERATE_DB_DOCUMENTATION=${GENERATE_DB_DOCUMENTATION:=true}
if [[ "${GENERATE_DB_DOCUMENTATION,,}" = true ]]; then

  RESULT=1
  while [[ $RESULT != "0" ]] ; do
    if [[ "$ENVIRONMENT" == "development" ]]; then
    RESULT=$(bash -c 'exec 3<> /dev/tcp/localhost/7000; echo $?' 2>/dev/null);
    else
    RESULT=$(bash -c 'exec 3<> /dev/tcp/toldbehandling-rest/8000; echo $?' 2>/dev/null);
    fi
    sleep 1
  done

  java -jar /usr/local/share/schemaspy.jar -dp /usr/local/share/postgresql.jar -t pgsql -db $POSTGRES_DB -host $POSTGRES_HOST -u $POSTGRES_USER -p $POSTGRES_PASSWORD -o /doc
  exec "$@"

fi
