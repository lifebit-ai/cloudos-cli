#!/bin/sh
# Smoke test for the image (FIPS build, see README.md): docker run --rm --entrypoint sh <image> /docker/fips/smoketest.sh
# Fails if the CLI doesn't start, or if Python loads a libcrypto other than the system (FIPS-capable) one.
set -e
ps --version
cloudos --version
python -c 'import cloudos_cli, requests, click, rich_click, pandas, numpy'
python -c 'import _hashlib, ssl, urllib3; print(open("/proc/self/maps").read())' | grep libcrypto > /tmp/maps
test -s /tmp/maps
test -z "$(grep -v ' /usr/lib64/libcrypto' /tmp/maps)"
test -z "$(find / -xdev -type f \( -name "libcrypto.so*" -o -name "libssl.so*" \) ! -path "/usr/lib64/*" 2>/dev/null)"
echo "smoketest: OK"
