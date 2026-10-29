import http.client
import json
import os
import socket
import tempfile
import unittest
import urllib.parse

from skyhook.server import start_server_in_thread

ALLOWED_ORIGIN = "http://localhost:3000"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ServerSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = free_port()
        cls.thread, cls.server = start_server_in_thread(port=cls.port, allowed_origins=[ALLOWED_ORIGIN])

    @classmethod
    def tearDownClass(cls):
        cls.server.stop_listening()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read().decode()

    def test_get_path_is_never_evaluated(self):
        marker = os.path.join(tempfile.mkdtemp(), "pwned")
        payload = f"__import__('pathlib').Path({marker!r}).touch()"
        status, _, _ = self.request("GET", "/" + urllib.parse.quote(payload) + "&%7B%7D")
        self.assertEqual(status, 400)
        self.assertFalse(os.path.exists(marker))

    def test_get_calls_loaded_function(self):
        status, _, body = self.request("GET", "/%22echo_message%22&%7B%22message%22:%22a&b%22%7D")
        self.assertEqual(status, 200)
        self.assertIn("I printed: a&b", body)

    def test_post_from_non_browser_client(self):
        body = json.dumps({"FunctionName": "is_online", "Parameters": {}})
        status, headers, response = self.request("POST", "/", body, {"Content-Length": str(len(body))})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(response)["Success"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_browser_requests_from_other_sites_are_rejected(self):
        body = json.dumps({"FunctionName": "is_online", "Parameters": {}})
        cases = {
            "cross-origin fetch": ("POST", {"Origin": "https://evil.example"}),
            "<img src> drive-by": ("GET", {"Sec-Fetch-Site": "cross-site"}),
            "DNS rebinding": ("GET", {"Host": f"evil.example:{self.port}", "Sec-Fetch-Site": "same-origin"}),
            "CORS preflight": ("OPTIONS", {"Origin": "https://evil.example"}),
        }
        for name, (method, headers) in cases.items():
            with self.subTest(name):
                headers = dict(headers, **{"Content-Length": str(len(body))})
                status, _, _ = self.request(method, "/%22is_online%22&%7B%7D", body, headers)
                self.assertEqual(status, 403)

    def test_allowed_origin_gets_cors_headers(self):
        status, headers, _ = self.request("GET", "/%22is_online%22&%7B%7D", headers={"Origin": ALLOWED_ORIGIN})
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], ALLOWED_ORIGIN)


if __name__ == "__main__":
    unittest.main()
