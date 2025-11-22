# MIT License
#
# Copyright (c) [Year] [Your Name or Handle]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import requests
import sys
import time

class ModemError(Exception):
    """Base exception for modem communication errors."""
    pass

class ModemControl:
    """
    Handles low-level communication with the modem.
    Implements specific headers to mimic Chrome and handles rate limiting.
    """
    def __init__(self, modem_ip, username, password, debug=False, min_interval=2.0):
        self.modem_ip = modem_ip
        self.base_url = f"https://{modem_ip}/cgi"
        self.origin_url = f"https://{modem_ip}"
        self.username = username
        self.password = password
        self.debug = debug
        self.min_interval = min_interval
        self.last_request_time = 0.0

        self.session = requests.Session()
        self.session.verify = False

        # MIMIC CHROME HEADERS EXACTLY
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Origin': self.origin_url,
            'X-Requested-With': 'XMLHttpRequest',
            'Accept-Language': 'en-US,en;q=0.9',
            'DNT': '1'
        })

        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning
        )

    def _log(self, message):
        if self.debug:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def _enforce_rate_limit(self):
        """Ensures we do not flood the modem with requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            self._log(f"Rate limit: Sleeping {sleep_time:.2f}s...")
            time.sleep(sleep_time)

    def _send_request(self, method, url, **kwargs):
        """
        Internal wrapper to handle retries and session headers.
        """
        # CRITICAL: Only retry GET. Never retry POST (Write).
        max_retries = 3 if method == 'GET' else 1

        for attempt in range(1, max_retries + 1):
            self._enforce_rate_limit()

            try:
                if method == 'GET':
                    response = self.session.get(url, **kwargs)
                else:
                    response = self.session.post(url, **kwargs)

                self.last_request_time = time.time()

                # If the modem sends a 500, we want to know.
                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                self._log(f"Request failed (Attempt {attempt}/{max_retries}): {e}")

                if attempt == max_retries:
                    # For POST requests, or the final GET attempt, we bubble the error up.
                    # The higher level logic will decide if it was a success or failure
                    # by checking the state (idempotency).
                    raise ModemError(f"Communication failed: {e}")

                # Only GET requests retry
                backoff = 2.0 * attempt
                self._log(f"Backing off for {backoff}s before retry...")
                time.sleep(backoff)

        raise ModemError("Unexpected unreachable code in _send_request")

    def login(self):
        """Establishes an authenticated session using correct Referer."""
        print("Logging in...")

        # Set Referer for Login Page
        headers = {'Referer': f"{self.origin_url}/login.html"}

        try:
            # Reset timer
            self.last_request_time = 0
            self._enforce_rate_limit()

            response = self.session.post(
                f"{self.base_url}/cgi_action",
                data={"username": self.username, "password": self.password},
                headers=headers
            )
            self.last_request_time = time.time()

            if 'Session-Id' in self.session.cookies:
                print("Login successful.")
                return True

            print("Login failed. Check credentials.", file=sys.stderr)
            return False
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to modem: {e}", file=sys.stderr)
            return False

    def get_request(self, object_path):
        """
        Sends a GET request.
        """
        self._log(f"Sending GET for Object: {object_path}")
        # GET requests technically don't need the Referer as strictly,
        # but let's use a generic one just in case.
        headers = {'Referer': f"{self.origin_url}/index.html"}

        response = self._send_request('GET', f"{self.base_url}/cgi_get",
                                      params={'Object': object_path},
                                      headers=headers)
        try:
            data = response.json()
            if data is None:
                raise ValueError("Modem returned 'null' JSON.")
            return data
        except (ValueError, TypeError) as e:
            self._log(f"Failed to parse JSON from {object_path}: {e}")
            raise ModemError(f"Invalid response data from modem for {object_path}")

    def set_request(self, payload, post_write_delay=7.0):
        """
        Sends a SET request with the correct configuration Referer.
        post_write_delay: Defaults to 7.0s to match browser UI spinner.
        """
        self._log(f"Sending SET with Payload: {payload}")

        # Set Referer for Configuration Page
        headers = {'Referer': f"{self.origin_url}/configuring_applysettings.html"}

        self._send_request('POST', f"{self.base_url}/cgi_set",
                           data=payload,
                           headers=headers)

        if post_write_delay > 0:
            self._log(f"Write safety: Pausing {post_write_delay}s for firmware commit...")
            time.sleep(post_write_delay)

        return True
