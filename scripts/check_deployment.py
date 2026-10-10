"""Contrôles HTTP sans écriture pour un déploiement Ventisax autorisé."""
import argparse
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("--preparing", action="store_true")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.path:
        parser.error("Fournir une origine HTTPS sans chemin.")
    opener = build_opener(NoRedirect())

    def get(url):
        try:
            return opener.open(Request(url, headers={"User-Agent": "Ventisax-deployment-check"}), timeout=30)
        except HTTPError as response:
            return response

    expected = 503 if args.preparing else 200
    for path, code in [("/fr/", expected), ("/en/", expected), ("/static/hub/site.css", 200),
                       ("/.env", 404), ("/db.sqlite3", 404), ("/media/.env", 404),
                       ("/admin/", 302), ("/account/login/", 200)]:
        with get(base + path) as response:
            assert response.code == code, (path, response.code, code)
            if path.startswith(("/admin/", "/account/")):
                assert "no-store" in response.headers.get("Cache-Control", "")
                assert response.headers.get("X-Frame-Options") == "DENY"
            if path == "/account/login/":
                cookies = response.headers.get_all("Set-Cookie", [])
                assert any("sessionid=" in cookie and "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie for cookie in cookies), "Cookie de session protégé absent"
                assert response.headers.get("Strict-Transport-Security", "").startswith("max-age=31536000")
            print(f"{path}: {response.code}")
    with get("http://" + parsed.netloc + "/fr/") as response:
        assert response.code in (301, 302, 308)
        assert response.headers.get("Location") == base + "/fr/"
        print("HTTP → HTTPS vérifié")


if __name__ == "__main__":
    main()
