#!/bin/sh
set -eu
# Railway mounts its persistent volume as root. Only initialize the private
# media directory, then drop privileges before migrations and API startup.
mkdir -p /data/media
chown ditto:ditto /data/media
chmod 700 /data/media
exec runuser -u ditto -- "$@"
