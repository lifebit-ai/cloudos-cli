"""
S3 multipart upload for ``cloudos datasets upload``, signed by the Lifebit Platform.

The platform never gives the CLI an AWS secret key. It returns an opaque credentials
blob, and its signing endpoint computes the SigV4 signature for each S3 request
(the same flow the web uploader uses). This module builds those requests and sends
them straight to S3, with no AWS SDK dependency.
"""

import base64
import hashlib
import math
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import quote
from xml.etree import ElementTree as ET

import requests
import urllib3

from cloudos_cli.utils.requests import retry_requests_delete, retry_requests_post, retry_requests_put

_REGION_RE = re.compile(r"[a-z]{2}(-[a-z0-9]+)+-\d+")
_BUCKET_RE = re.compile(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]")
# (connect, read) seconds for direct S3 calls
S3_TIMEOUT = (30, 300)

EMPTY_PAYLOAD_SHA256 = hashlib.sha256(b"").hexdigest()
# Part integrity is enforced by Content-MD5 instead, as in the web uploader.
UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"

DEFAULT_PART_SIZE = 8 * 1024 * 1024
MAX_PARTS = 10000  # S3's limit per multipart upload
MAX_OBJECT_SIZE = 5 * 1024 ** 4  # 5 TiB, S3's maximum object size


def compute_part_size(file_size):
    """8 MiB, or the smallest whole number of MiB that keeps the upload within 10,000 parts."""
    mib = 1024 * 1024
    return max(DEFAULT_PART_SIZE, math.ceil(file_size / MAX_PARTS / mib) * mib)


def s3_uri_encode(key):
    """Percent-encode each '/'-separated segment of an S3 key, as SigV4 requires."""
    return "/".join(quote(part, safe="~") for part in key.split("/"))


class S3UploadError(Exception):
    """A signed S3 request returned an error status."""

    def __init__(self, action, response):
        self.status_code = response.status_code
        try:
            message = ET.fromstring(response.content).findtext("Message")
        except ET.ParseError:
            message = None
        super().__init__(f"S3 {action} failed ({response.status_code}): {message or response.reason}")


class TransferError(Exception):
    """A network-level failure, with a message that never includes the request URL."""


@contextmanager
def scrubbed_transport_errors(action):
    """Re-raise requests and urllib3 errors without their message.

    Their text embeds the full request URL, whose query string can hold a
    presigned signature or an STS session token.
    """
    try:
        yield
    except (requests.RequestException, urllib3.exceptions.HTTPError) as e:
        raise TransferError(f"{action} failed: {type(e).__name__} (network error, details withheld)") from None


class SignedS3MultipartUploader:
    """Multipart upload to one S3 object, with every request signed by the platform.

    Parameters
    ----------
    datasets_client : cloudos_cli.datasets.datasets.Datasets
        Used to call ``sign_upload_for_evaporate`` for each request.
    bucket, key, region : str
        Destination bucket, object key (not URI-encoded) and AWS region, from the platform.
    content_type : str
        Content-Type stored with the object.
    access_key_id, session_token : str
        The temporary AWS access key id and STS session token.
    credentials_blob : str
        Opaque credentials blob for the platform signer. Never logged or persisted.
    verify : bool or str
        TLS verification, as for ``requests`` (honours ``--ssl-cert`` and
        ``--disable-ssl-verification``).
    """

    def __init__(self, datasets_client, bucket, key, region, content_type,
                 access_key_id, session_token, credentials_blob, verify=True):
        # Both values end up in the request host, so a bad value must not redirect the upload.
        if not region or not _REGION_RE.fullmatch(region):
            raise ValueError(f"Refusing to upload: unexpected AWS region value {region!r} from the platform.")
        if not bucket or not _BUCKET_RE.fullmatch(bucket):
            raise ValueError(f"Refusing to upload: unexpected S3 bucket name {bucket!r} from the platform.")
        self.client = datasets_client
        self.region = region
        self.content_type = content_type or "application/octet-stream"
        self.access_key_id = access_key_id
        self.session_token = session_token
        self.credentials_blob = credentials_blob
        self.verify = verify
        # The global endpoint (s3.amazonaws.com) 301-redirects buckets outside us-east-1.
        self.host = f"s3.{region}.amazonaws.com"
        self._canonical_uri = f"/{bucket}/{s3_uri_encode(key)}"

    def _request(self, send, method, action, query, payload_hash, extra_headers=None, body=None):
        """Sign one S3 request with the platform signer, send it and return the response."""
        amz_datetime = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        headers = {"host": self.host, "x-amz-date": amz_datetime,
                   "x-amz-security-token": self.session_token, **(extra_headers or {})}
        names = sorted(headers)
        signed_headers = ";".join(names)
        canonical_request = "\n".join([
            method, self._canonical_uri, query,
            "".join(f"{name}:{headers[name].strip()}\n" for name in names),
            signed_headers, payload_hash,
        ])
        scope = f"{amz_datetime[:8]}/{self.region}/s3/aws4_request"
        to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_datetime, scope,
                             hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()])
        signature = self.client.sign_upload_for_evaporate(
            to_sign=to_sign, amz_datetime=amz_datetime,
            canonical_request=canonical_request, credentials_blob=self.credentials_blob,
        )
        del headers["host"]
        headers["x-amz-content-sha256"] = payload_hash
        headers["Authorization"] = (f"AWS4-HMAC-SHA256 Credential={self.access_key_id}/{scope}, "
                                    f"SignedHeaders={signed_headers}, Signature={signature}")
        with scrubbed_transport_errors(f"S3 {action}"):
            response = send(f"https://{self.host}{self._canonical_uri}" + (f"?{query}" if query else ""), headers=headers,
                            data=body, verify=self.verify, timeout=S3_TIMEOUT)
        if response.status_code >= 300:
            raise S3UploadError(action, response)
        return response

    def create_multipart_upload(self):
        """Start the upload and return its ``UploadId``."""
        response = self._request(
            retry_requests_post, "POST", "CreateMultipartUpload", "uploads=", EMPTY_PAYLOAD_SHA256,
            {"content-type": self.content_type, "x-amz-server-side-encryption": "AES256"}, b"")
        upload_id = ET.fromstring(response.content).findtext("{*}UploadId")
        if not upload_id:
            raise S3UploadError("CreateMultipartUpload", response)
        return upload_id

    def upload_part(self, part_number, data, upload_id):
        """Upload one part and return its ``ETag``."""
        content_md5 = base64.b64encode(hashlib.md5(data, usedforsecurity=False).digest()).decode("ascii")
        query = f"partNumber={part_number}&uploadId={quote(upload_id, safe='')}"
        response = self._request(
            retry_requests_put, "PUT", f"UploadPart (part {part_number})", query, UNSIGNED_PAYLOAD,
            {"content-md5": content_md5, "content-type": self.content_type}, data)
        return response.headers.get("ETag", "").strip('"')

    def complete_multipart_upload(self, upload_id, parts):
        """Finish the upload from ``(part_number, etag)`` pairs in ascending order.

        ``If-None-Match: *`` makes S3 refuse (412) to replace an object already at this key,
        e.g. one written by another upload of the same name after the CLI checked the folder.
        """
        body = ("<CompleteMultipartUpload>" + "".join(
            f'<Part><PartNumber>{number}</PartNumber><ETag>"{etag}"</ETag></Part>' for number, etag in parts
        ) + "</CompleteMultipartUpload>").encode("utf-8")
        response = self._request(retry_requests_post, "POST", "CompleteMultipartUpload",
                                 f"uploadId={quote(upload_id, safe='')}", hashlib.sha256(body).hexdigest(),
                                 {"content-type": self.content_type, "if-none-match": "*"}, body)
        # S3 can report a failed completion with a 200 status and an <Error> body.
        if ET.fromstring(response.content).tag.endswith("Error"):
            raise S3UploadError("CompleteMultipartUpload", response)

    def delete_object(self):
        """Delete the completed object, e.g. after the platform refused to register it."""
        self._request(retry_requests_delete, "DELETE", "DeleteObject", "", EMPTY_PAYLOAD_SHA256)

    def abort_multipart_upload(self, upload_id):
        """Abort the upload so S3 discards the parts already sent."""
        self._request(retry_requests_delete, "DELETE", "AbortMultipartUpload",
                      f"uploadId={quote(upload_id, safe='')}", EMPTY_PAYLOAD_SHA256)
