#!/bin/bash

exec python /app/db_init.py &
exec python /app/main.py