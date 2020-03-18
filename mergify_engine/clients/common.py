# -*- encoding: utf-8 -*-
#
# Copyright © 2020 Mergify SAS
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import httpx

from mergify_engine import RETRY


DEFAULT_CLIENT_OPTIONS = {
    "headers": {
        "Accept": "application/vnd.github.machine-man-preview+json",
        "User-Agent": "Mergify/Python",
    },
    "trust_env": False,
}


class HTTPClientSideError(httpx.HTTPError):
    @property
    def message(self):
        # TODO(sileht): do something with errors and documentation_url when present
        # https://developer.github.com/v3/#client-errors
        return self.response.json()["message"]

    def status_code(self):
        return self.response.status_code


class HTTPNotFound(HTTPClientSideError):
    pass


httpx.HTTPClientSideError = HTTPClientSideError
httpx.HTTPNotFound = HTTPNotFound

STATUS_CODE_TO_EXC = {404: HTTPNotFound}


class HttpxHelpersMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # httpx doesn't support retries yet, but the sync client uses urllib3 like request
        # https://github.com/encode/httpx/blob/master/httpx/_dispatch/urllib3.py#L105

        real_url_open = self.dispatch.pool.url_open

        def _mergify_patched_url_open(*args, **kwargs):
            kwargs["retries"] = RETRY
            return real_url_open(*args, **kwargs)

        self.dispatch.pool.url_open = _mergify_patched_url_open

    def request(self, *args, **kwargs):
        try:
            return super().request(*args, **kwargs)
        except httpx.HTTPError as e:
            if e.response and 400 <= e.response.status_code < 500:
                exc_class = STATUS_CODE_TO_EXC.get(
                    e.reponse.status_code, HTTPClientSideError
                )
                raise exc_class(e.args, e.request, e.response) from e
            raise
