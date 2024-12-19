#!/bin/bash

hosts_file="/hosts"

add_hosts=""
for hostname in toldbehandling-admin toldbehandling-ui toldbehandling-idp toldbehandling-er-web; do
  if ! grep $hostname $hosts_file; then
    add_hosts+=" $hostname"
  fi
done

if [ ! -z "$add_hosts" ]; then
    echo "127.0.0.1       $add_hosts    # Akitsuut hosts" >> $hosts_file
fi
