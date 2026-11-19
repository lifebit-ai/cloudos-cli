#!/bin/sh
# Smoke test for the image (FIPS build, see README.md): docker run --rm --entrypoint sh <image> /docker/fips/smoketest.sh
# Fails if the CLI doesn't start, if Python loads a libcrypto other than the system (FIPS-capable) one, or if, in FIPS
# mode, the certified provider is missing or a non-approved hash (MD5, HMAC-MD5, BLAKE2) still works.
set -e
# CI runners aren't FIPS hosts. RHEL's libcrypto treats OPENSSL_FORCE_FIPS_MODE=1 like a kernel with fips_enabled=1,
# so the checks below run in FIPS mode on any host.
export OPENSSL_FORCE_FIPS_MODE=1
rpm -q openssl-fips-provider-3.0.7-11.el10_2 >/dev/null
# The module version on CMVP certificate #5573.
grep -qa 3.0.7-cda111b5812c30d4 /usr/lib64/ossl-modules/fips.so
ps --version
cloudos --version
python -c 'import cloudos_cli, requests, click, rich_click, pandas, numpy'
# In FIPS mode SHA-256 only works if the provider (fips.so) loads, so this also covers a missing or broken provider.
python - <<'PY'
import _hashlib, hashlib, hmac, importlib.util
assert _hashlib.get_fips_mode() == 1, "not in FIPS mode"
assert importlib.util.find_spec("_blake2") is None, "CPython's built-in _blake2 is still there"
assert importlib.util.find_spec("_crypt") is None, "CPython's _crypt (libxcrypt) is still there"
hashlib.sha256(b"x")
hmac.new(b"k", b"x", "sha256")
refused = {
    "hashlib.md5": lambda: hashlib.md5(b"x"),
    "hashlib.new('md5')": lambda: hashlib.new("md5", b"x"),
    "hmac md5": lambda: hmac.new(b"k", b"x", "md5"),
    "hashlib.blake2b": lambda: hashlib.blake2b(b"x"),
    "hashlib.new('blake2b')": lambda: hashlib.new("blake2b", b"x"),
    # These OpenSSL names bypass hashlib's _blake2 lookup and go to _hashlib, which must refuse them in FIPS mode.
    "hashlib.new('blake2b512')": lambda: hashlib.new("blake2b512", b"x"),
    "hashlib.new('blake2s256')": lambda: hashlib.new("blake2s256", b"x"),
}
# Every refusal raises ValueError: _hashlib.UnsupportedDigestmodError subclasses it, and hashlib's patched
# __unsupported raises it. Anything else is a bug in this check and must fail it, not count as refused.
for name, call in refused.items():
    try:
        call()
    except ValueError:
        continue
    raise SystemExit(f"{name} works in FIPS mode")
PY
python -c 'import _hashlib, ssl, urllib3; print(open("/proc/self/maps").read())' | grep libcrypto > /tmp/maps
test -s /tmp/maps
test -z "$(grep -v ' /usr/lib64/libcrypto' /tmp/maps)"
# Any libcrypto/libssl outside /usr/lib64 itself, including wheel-style libcrypto-<hash>.so and /usr/lib64 subdirectories.
test -z "$(find / -xdev -type f \( -name "libcrypto*.so*" -o -name "libssl*.so*" \) ! -regex "/usr/lib64/[^/]*" 2>/dev/null)"
echo "smoketest: OK"
