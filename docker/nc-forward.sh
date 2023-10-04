#!/usr/bin/env bash

while nc -l -p 8080 -k -c "nc toldbehandling-test-idp 8080" || true; do true; done &

tail -f /dev/null # Or any other command that never exits
