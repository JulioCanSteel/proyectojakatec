from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import threading
import time
import base64
import binascii
import email.utils
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("CIVICMX_DB_PATH", DATA_DIR / "civicmx.sqlite3"))
PORT = int(os.environ.get("PORT", "8000"))
SESSION_COOKIE = "civicmx_session"
SESSION_SECONDS = 60 * 60 * 24 * 7
PASSWORD_ITERATIONS = 310_000
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
NEWS_CACHE_SECONDS = 300
NEWS_CACHE: tuple[float, dict] | None = None
NEWS_CACHE_LOCK = threading.Lock()
DAILY_MISSIONS = {
    "daily_login": {
        "title": "Entra a la app hoy",
        "description": "Tu primera sesión del día suma a tu racha.",
        "icon": "bi-box-arrow-in-right",
        "points": 5,
        "coins": 5,
        "action": "auto",
    },
    "report_incident": {
        "title": "Reporta un problema de tu comunidad",
        "description": "Al publicar tu primer reporte del día completas esta misión.",
        "icon": "bi-exclamation-triangle-fill",
        "points": 20,
        "coins": 20,
        "action": "report",
    },
    "safety_guide": {
        "title": "Consulta una guía de seguridad",
        "description": "Lee una recomendación útil para tu comunidad.",
        "icon": "bi-shield-check",
        "points": 10,
        "coins": 10,
        "action": "complete",
    },
    "safe_route": {
        "title": "Planea un trayecto",
        "description": "Prepara indicaciones desde el Centro de Seguridad.",
        "icon": "bi-sign-turn-right",
        "points": 15,
        "coins": 15,
        "action": "route",
    },
}
DEMO_REPORTS = (
    ("tabasco_nacajuca_robo", "DEMO · Reporte comunitario", "Punto de muestra en Nacajuca; no representa un incidente real.", "Robo / asalto", 18.1667, -93.0667, 0),
    ("tabasco_nacajuca_alumbrado", "DEMO · Alumbrado", "Dato sintético para probar el mapa de calor.", "Alumbrado", 18.1667, -93.0667, 1),
    ("tabasco_nacajuca_vial", "DEMO · Incidente vial", "Dato sintético para probar el mapa de calor.", "Accidente vial", 18.1667, -93.0667, 2),
    ("tabasco_villahermosa_robo", "DEMO · Reporte comunitario", "Punto de muestra en Villahermosa; no representa un incidente real.", "Robo / asalto", 17.9895, -92.9475, 1),
    ("tabasco_cardenas_alumbrado", "DEMO · Alumbrado", "Dato sintético para probar el mapa de calor.", "Alumbrado", 17.9940, -93.3780, 3),
    ("cdmx_robo", "DEMO · Reporte comunitario", "Punto de muestra en Ciudad de México; no representa un incidente real.", "Robo / asalto", 19.4326, -99.1332, 1),
    ("monterrey_vial", "DEMO · Incidente vial", "Punto de muestra en Monterrey; no representa un incidente real.", "Accidente vial", 25.6866, -100.3161, 2),
    ("guadalajara_alumbrado", "DEMO · Alumbrado", "Punto de muestra en Guadalajara; no representa un incidente real.", "Alumbrado", 20.6597, -103.3496, 4),
    ("merida_robo", "DEMO · Reporte comunitario", "Punto de muestra en Mérida; no representa un incidente real.", "Robo / asalto", 20.9674, -89.5926, 2),
    ("oaxaca_vandalismo", "DEMO · Vandalismo", "Punto de muestra en Oaxaca; no representa un incidente real.", "Vandalismo", 17.0732, -96.7266, 5),
    ("tijuana_robo", "DEMO · Reporte comunitario", "Punto de muestra en Tijuana; no representa un incidente real.", "Robo / asalto", 32.5149, -117.0382, 6),
)

#feed de comunidad

@contextmanager
def database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database() -> None:
    with database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                business_name TEXT NOT NULL DEFAULT '',
                daily_goal INTEGER NOT NULL DEFAULT 30,
                role TEXT NOT NULL DEFAULT 'user',
                avatar_url TEXT NOT NULL DEFAULT '',
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'report',
                category TEXT NOT NULL DEFAULT 'General',
                latitude REAL,
                longitude REAL,
                anonymous INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pendiente',
                image_url TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS post_comments (
                id INTEGER PRIMARY KEY,
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS post_comments_post_id ON post_comments(post_id, created_at);
            CREATE TABLE IF NOT EXISTS demo_reports (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS security_alerts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                alert_type TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activity_events (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                event_key TEXT NOT NULL,
                event_date TEXT NOT NULL,
                points INTEGER NOT NULL DEFAULT 0,
                coins INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, event_key)
            );
            CREATE TABLE IF NOT EXISTS missions (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                icon TEXT NOT NULL DEFAULT 'bi-flag-fill',
                points INTEGER NOT NULL DEFAULT 0,
                coins INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """
        )
        user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
        if "business_name" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN business_name TEXT NOT NULL DEFAULT ''")
        if "daily_goal" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN daily_goal INTEGER NOT NULL DEFAULT 30")
        if "role" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        if "avatar_url" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT NOT NULL DEFAULT ''")
        post_columns = {row["name"] for row in connection.execute("PRAGMA table_info(posts)")}
        for column, definition in (
            ("kind", "TEXT NOT NULL DEFAULT 'report'"),
            ("category", "TEXT NOT NULL DEFAULT 'General'"),
            ("latitude", "REAL"),
            ("longitude", "REAL"),
            ("anonymous", "INTEGER NOT NULL DEFAULT 0"),
            ("image_url", "TEXT NOT NULL DEFAULT ''"),
        ):
            if column not in post_columns:
                connection.execute(f"ALTER TABLE posts ADD COLUMN {column} {definition}")
        admin_emails = {
            email.strip().lower()
            for email in os.environ.get("HEROESMX_ADMIN_EMAILS", "").split(",")
            if email.strip()
        }
        if admin_emails:
            placeholders = ",".join("?" for _ in admin_emails)
            connection.execute(
                f"UPDATE users SET role = 'admin' WHERE lower(email) IN ({placeholders}) AND role != 'admin'",
                tuple(sorted(admin_emails)),
            )
        if os.environ.get("HEROESMX_DEMO_DATA") == "1":
            for demo_id, title, description, category, latitude, longitude, age_days in DEMO_REPORTS:
                created_at = (now_utc() - timedelta(days=age_days)).isoformat(timespec="seconds")
                connection.execute(
                    """INSERT OR IGNORE INTO demo_reports
                       (id, title, description, category, latitude, longitude, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (demo_id, title, description, category, latitude, longitude, created_at),
                )


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_mexico_news() -> dict:
    global NEWS_CACHE

    with NEWS_CACHE_LOCK:
        cached = NEWS_CACHE
        if cached and time.monotonic() - cached[0] < NEWS_CACHE_SECONDS:
            return cached[1]

        query = urllib.parse.urlencode(
            {
                "q": "México",
                "hl": "es-419",
                "gl": "MX",
                "ceid": "MX:es-419",
            }
        )
        request = urllib.request.Request(
            f"https://news.google.com/rss/search?{query}",
            headers={
                "Accept": "application/rss+xml, application/xml, text/xml",
                "User-Agent": "Mozilla/5.0 (compatible; HeroesMX/1.0)",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            feed_content = response.read(1_048_577)
        if len(feed_content) > 1_048_576:
            raise ValueError("Google News devolvió una respuesta demasiado grande.")
        feed = ET.fromstring(feed_content)
        channel = feed.find("channel")
        if channel is None:
            raise ValueError("Google News devolvió un RSS sin canal.")

        articles = []
        for item in channel.findall("item"):
            title = item.findtext("title")
            url = item.findtext("link")
            published_date = item.findtext("pubDate")
            source = item.findtext("source")
            if not all(isinstance(value, str) and value.strip() for value in (title, url, published_date)):
                continue

            parsed_url = urllib.parse.urlsplit(url)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                continue

            try:
                published_at = email.utils.parsedate_to_datetime(published_date)
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue

            articles.append(
                {
                    "title": title.strip()[:300],
                    "url": url.strip(),
                    "source": (source.strip() if source and source.strip() else parsed_url.netloc)[:120],
                    "published_at": published_at.isoformat(timespec="seconds"),
                }
            )
            if len(articles) == 2:
                break

        result = {
            "articles": articles,
            "updated_at": now_utc().isoformat(timespec="seconds"),
        }
        NEWS_CACHE = (time.monotonic(), result)
        return result


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )


class CivicMxHandler(BaseHTTPRequestHandler):
    server_version = "HeroesMX/1.0"

    def do_GET(self) -> None:
        path = urlsplit(self.path).path

        # Si entran a la raíz '/', redirigir a login
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/login/loguin.html")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path == "/api/auth/me":
            user = self.current_user()
            if user is None:
                self.send_json({"error": "Inicia sesión para continuar."}, 401)
            else:
                self.send_json({"user": user})
            return

        if path == "/api/dashboard":
            user = self.current_user()
            if user is None:
                self.send_json({"error": "Inicia sesión para ver tu progreso."}, 401)
            else:
                self.send_json(self.get_dashboard(user))
            return

        if path == "/api/missions":
            user = self.current_user()
            if user is None:
                self.send_json({"error": "Inicia sesión para ver tus misiones."}, 401)
            else:
                self.send_json({"missions": self.get_missions(user)})
            return

        if path == "/api/admin/overview":
            self.admin_overview()
            return

        if path == "/api/admin/users":
            self.admin_users()
            return

        if path == "/api/news":
            try:
                self.send_json(get_mexico_news())
            except (OSError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
                print(f"No se pudieron consultar las noticias: {error}")
                self.send_json(
                    {"error": "Las noticias no están disponibles por el momento. Intenta actualizar en unos minutos."},
                    502,
                )
            return

        if path == "/api/posts":
            with database() as connection:
                rows = connection.execute(
                  """SELECT * FROM (
                      SELECT posts.id,
                          CASE WHEN posts.anonymous = 1 THEN 'Anónimo' ELSE users.name END AS author,
                          CASE WHEN posts.anonymous = 1 THEN '' ELSE users.avatar_url END AS avatar_url,
                          posts.title, posts.description, posts.kind, posts.category,
                          posts.latitude, posts.longitude, posts.anonymous,
                          posts.status, posts.image_url, posts.created_at, 0 AS is_demo,
                          (SELECT COUNT(*) FROM post_comments WHERE post_id = posts.id) AS comment_count
                      FROM posts JOIN users ON users.id = posts.user_id
                      UNION ALL
                      SELECT 'demo-' || id AS id, 'DEMO' AS author, '' AS avatar_url,
                          title, description, 'report' AS kind, category,
                          latitude, longitude, 1 AS anonymous, 'Demostración' AS status,
                          '' AS image_url, created_at, 1 AS is_demo, 0 AS comment_count
                      FROM demo_reports
                  ) ORDER BY created_at DESC"""
                ).fetchall()
            self.send_json({"posts": [dict(row) for row in rows]})
            return

        if path.startswith("/api/posts/") and path.endswith("/comments"):
            self.list_post_comments(path.removeprefix("/api/posts/").removesuffix("/comments").strip("/"))
            return

        self.serve_static(path)

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        try:
            if path == "/api/auth/register":
                self.register()
            elif path == "/api/auth/login":
                self.login()
            elif path == "/api/auth/logout":
                self.logout()
            elif path == "/api/posts":
                self.create_post()
            elif path.startswith("/api/posts/") and path.endswith("/comments"):
                self.create_post_comment(path.removeprefix("/api/posts/").removesuffix("/comments").strip("/"))
            elif path == "/api/profile/avatar":
                self.update_profile_avatar()
            elif path == "/api/alerts":
                self.create_alert()
            elif path == "/api/profile/business":
                self.update_business_name()
            elif path == "/api/profile/goal":
                self.update_daily_goal()
            elif path == "/api/missions/complete":
                self.complete_mission()
            elif path == "/api/admin/missions":
                self.create_admin_mission()
            elif path == "/api/admin/posts":
                self.create_admin_post()
            elif path == "/api/admin/users":
                self.create_admin_user()
            elif path.startswith("/api/admin/posts/") and path.endswith("/status"):
                self.update_admin_post_status(path.removeprefix("/api/admin/posts/").removesuffix("/status").strip("/"))
            elif path.startswith("/api/admin/users/") and path.endswith("/role"):
                self.update_admin_user(path.removeprefix("/api/admin/users/").removesuffix("/role").strip("/"), "role")
            elif path.startswith("/api/admin/users/") and path.endswith("/avatar"):
                self.update_admin_user(path.removeprefix("/api/admin/users/").removesuffix("/avatar").strip("/"), "avatar")
            else:
                self.send_json({"error": "No se encontró esa ruta."}, 404)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, binascii.Error) as error:
            self.send_json({"error": str(error) or "Solicitud no válida."}, 400)
        except sqlite3.IntegrityError:
            self.send_json({"error": "Ya existe una cuenta con ese correo."}, 409)
        except OSError as error:
            print(f"No se pudo guardar un archivo de la solicitud: {error}")
            self.send_json({"error": "No se pudo guardar la imagen en el servidor."}, 500)

    def do_DELETE(self) -> None:
        path = urlsplit(self.path).path
        if path.startswith("/api/admin/posts/"):
            self.delete_admin_post(path.removeprefix("/api/admin/posts/"))
        elif path.startswith("/api/admin/missions/"):
            self.delete_admin_mission(path.removeprefix("/api/admin/missions/"))
        else:
            self.send_json({"error": "No se encontró esa ruta."}, 404)

    def register(self) -> None:
        data = self.read_json()
        name = self.text_field(data, "name", "El nombre es obligatorio.").strip()
        email = self.text_field(data, "email", "El correo es obligatorio.").strip().lower()
        password = self.text_field(data, "password", "La contraseña es obligatoria.")

        if not 3 <= len(name) <= 80:
            raise ValueError("El nombre debe tener entre 3 y 80 caracteres.")
        if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Ingresa un correo válido.")
        if not 6 <= len(password) <= 256:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")

        salt = secrets.token_bytes(16)
        password_hash = hash_password(password, salt)
        token = secrets.token_urlsafe(32)
        created_at = now_utc().isoformat(timespec="seconds")

        with database() as connection:
            cursor = connection.execute(
                """INSERT INTO users (name, email, password_salt, password_hash, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, email, salt, password_hash, created_at),
            )
            user_id = cursor.lastrowid
            today = self.today_date()
            self.record_event(connection, user_id, f"mission:daily_login:{today}", today, 5, 5)
            self.store_session(connection, token, user_id)

        self.send_json(
            {"user": {"id": user_id, "name": name, "email": email, "role": "user", "avatar_url": ""}},
            201,
            [("Set-Cookie", self.session_cookie(token))],
        )

    def login(self) -> None:
        data = self.read_json()
        email = self.text_field(data, "email", "El correo es obligatorio.").strip().lower()
        password = self.text_field(data, "password", "La contraseña es obligatoria.")

        with database() as connection:
            row = connection.execute(
                "SELECT id, name, email, role, avatar_url, password_salt, password_hash FROM users WHERE email = ?",
                (email,),
            ).fetchone()

            if row is None or not hmac.compare_digest(
                hash_password(password, row["password_salt"]), row["password_hash"]
            ):
                self.send_json({"error": "Correo o contraseña incorrectos."}, 401)
                return

            token = secrets.token_urlsafe(32)
            self.store_session(connection, token, row["id"])
            today = self.today_date()
            self.record_event(connection, row["id"], f"mission:daily_login:{today}", today, 5, 5)

        self.send_json(
            {"user": {"id": row["id"], "name": row["name"], "email": row["email"], "role": row["role"], "avatar_url": row["avatar_url"]}},
            headers=[("Set-Cookie", self.session_cookie(token))],
        )

    def logout(self) -> None:
        token = self.session_token()
        if token:
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            with database() as connection:
                connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        self.send_json(
            {"ok": True},
            headers=[("Set-Cookie", f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")],
        )

    def create_post(self) -> None:
        user = self.current_user()
        if user is None:
            self.send_json({"error": "Inicia sesión para publicar."}, 401)
            return

        data = self.read_json(max_bytes=7_200_000)
        kind = data.get("kind", "report")
        if kind not in {"post", "report"}:
            raise ValueError("Selecciona una publicación o un reporte válido.")
        status = "Publicado" if kind == "post" else "Pendiente"
        self.insert_post(user, data, status, award_points=True, kind=kind)

    def create_admin_post(self) -> None:
        user = self.require_admin()
        if user is None:
            return
        data = self.read_json(max_bytes=7_200_000)
        data["anonymous"] = False
        data["kind"] = "post"
        self.insert_post(user, data, "Publicado", award_points=False, kind="post")

    def insert_post(
        self,
        user: dict,
        data: dict,
        status: str,
        award_points: bool,
        kind: str = "report",
    ) -> None:
        title = self.text_field(data, "title", "El título es obligatorio.").strip()
        description = self.text_field(data, "description", "La descripción es obligatoria.").strip()
        category = self.text_field(data, "category", "El tipo de incidente no es válido.").strip()
        if kind not in {"post", "report"}:
            raise ValueError("Selecciona una publicación o un reporte válido.")
        anonymous = data.get("anonymous", False)
        if not isinstance(anonymous, bool):
            raise ValueError("La opción de anonimato no es válida.")
        if not title or len(title) > 120:
            raise ValueError("El título debe tener entre 1 y 120 caracteres.")
        if not description or len(description) > 2000:
            raise ValueError("La descripción debe tener entre 1 y 2000 caracteres.")
        if not category or len(category) > 60:
            raise ValueError("El tipo de incidente no es válido.")
        latitude = self.optional_coordinate(data.get("latitude"), -90, 90)
        longitude = self.optional_coordinate(data.get("longitude"), -180, 180)
        if (latitude is None) != (longitude is None):
            raise ValueError("La ubicación está incompleta.")
        if kind == "post" and (latitude is not None or anonymous):
            raise ValueError("Las publicaciones no admiten ubicación ni anonimato.")
        image_url = self.store_image(data.get("image_data", ""))

        created_at = now_utc().isoformat(timespec="seconds")
        with database() as connection:
            cursor = connection.execute(
                """INSERT INTO posts (
                       user_id, title, description, kind, category, latitude, longitude,
                       anonymous, status, image_url, created_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user["id"], title, description, kind, category, latitude, longitude,
                 int(anonymous), status, image_url, created_at),
            )
            post_id = cursor.lastrowid
            if award_points:
                today = self.today_date()
                self.record_event(connection, user["id"], f"post:{post_id}", today, 15, 15)
                if kind == "report":
                    self.record_event(connection, user["id"], f"mission:report_incident:{today}", today, 20, 20)

        self.send_json(
            {
                "post": {
                    "id": post_id,
                    "author": "Anónimo" if anonymous else user["name"],
                    "title": title,
                    "description": description,
                    "kind": kind,
                    "category": category,
                    "latitude": latitude,
                    "longitude": longitude,
                    "anonymous": anonymous,
                    "status": status,
                    "image_url": image_url,
                    "avatar_url": "" if anonymous else user.get("avatar_url", ""),
                    "comment_count": 0,
                    "created_at": created_at,
                }
            },
            201,
        )

    def list_post_comments(self, post_id: str) -> None:
        if not post_id.isdecimal():
            self.send_json({"error": "No se encontró esa publicación."}, 404)
            return
        with database() as connection:
            post = connection.execute("SELECT id FROM posts WHERE id = ?", (int(post_id),)).fetchone()
            if post is None:
                self.send_json({"error": "No se encontró esa publicación."}, 404)
                return
            rows = connection.execute(
                """SELECT post_comments.id, post_comments.content, post_comments.created_at,
                          users.name AS author, users.avatar_url
                   FROM post_comments JOIN users ON users.id = post_comments.user_id
                   WHERE post_comments.post_id = ? ORDER BY post_comments.created_at ASC""",
                (int(post_id),),
            ).fetchall()
        self.send_json({"comments": [dict(row) for row in rows]})

    def create_post_comment(self, post_id: str) -> None:
        user = self.current_user()
        if user is None:
            self.send_json({"error": "Inicia sesión para comentar."}, 401)
            return
        if not post_id.isdecimal():
            self.send_json({"error": "No se encontró esa publicación."}, 404)
            return
        data = self.read_json()
        content = self.text_field(data, "content", "Escribe un comentario.").strip()
        if not content or len(content) > 1000:
            raise ValueError("El comentario debe tener entre 1 y 1000 caracteres.")
        created_at = now_utc().isoformat(timespec="seconds")
        with database() as connection:
            if connection.execute("SELECT id FROM posts WHERE id = ?", (int(post_id),)).fetchone() is None:
                self.send_json({"error": "No se encontró esa publicación."}, 404)
                return
            cursor = connection.execute(
                """INSERT INTO post_comments (post_id, user_id, content, created_at)
                   VALUES (?, ?, ?, ?)""",
                (int(post_id), user["id"], content, created_at),
            )
        self.send_json({
            "comment": {
                "id": cursor.lastrowid,
                "content": content,
                "author": user["name"],
                "avatar_url": user.get("avatar_url", ""),
                "created_at": created_at,
            }
        }, 201)

    def update_profile_avatar(self) -> None:
        user = self.current_user()
        if user is None:
            self.send_json({"error": "Inicia sesión para actualizar tu foto."}, 401)
            return
        data = self.read_json(max_bytes=7_200_000)
        avatar_url = self.store_image(data.get("image_data", ""))
        with database() as connection:
            connection.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (avatar_url, user["id"]))
        self.send_json({"avatar_url": avatar_url})

    @staticmethod
    def store_image(image_data: object) -> str:
        if image_data == "":
            return ""
        if not isinstance(image_data, str) or len(image_data) > 7_100_000:
            raise ValueError("La imagen debe pesar 5 MB o menos.")
        match = re.fullmatch(r"data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/]+=*)", image_data)
        if not match:
            raise ValueError("Usa una imagen JPG, PNG o WebP.")
        image_bytes = base64.b64decode(match.group(2), validate=True)
        if not image_bytes or len(image_bytes) > 5 * 1024 * 1024:
            raise ValueError("La imagen debe pesar 5 MB o menos.")
        image_type = match.group(1)
        valid_signature = (
            image_type == "jpeg" and image_bytes.startswith(b"\xff\xd8\xff")
            or image_type == "png" and image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
            or image_type == "webp" and image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP"
        )
        if not valid_signature:
            raise ValueError("El contenido no coincide con el formato de imagen.")
        extension = {"jpeg": ".jpg", "png": ".png", "webp": ".webp"}[image_type]
        upload_dir = ROOT / "uploads"
        upload_dir.mkdir(mode=0o750, exist_ok=True)
        file_name = f"{secrets.token_hex(20)}{extension}"
        with (upload_dir / file_name).open("xb") as image_file:
            image_file.write(image_bytes)
        return f"/uploads/{file_name}"

    def create_alert(self) -> None:
        user = self.current_user()
        if user is None:
            self.send_json({"error": "Inicia sesión para registrar una alerta."}, 401)
            return

        data = self.read_json()
        alert_type = self.text_field(data, "type", "El tipo de alerta es obligatorio.").strip()
        if alert_type not in {"manual", "voice"}:
            raise ValueError("El tipo de alerta no es válido.")
        latitude = self.optional_coordinate(data.get("latitude"), -90, 90)
        longitude = self.optional_coordinate(data.get("longitude"), -180, 180)
        if (latitude is None) != (longitude is None):
            raise ValueError("La ubicación está incompleta.")

        created_at = now_utc().isoformat(timespec="seconds")
        with database() as connection:
            cursor = connection.execute(
                """INSERT INTO security_alerts (user_id, alert_type, latitude, longitude, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user["id"], alert_type, latitude, longitude, created_at),
            )

        self.send_json(
            {
                "alert": {
                    "id": cursor.lastrowid,
                    "created_at": created_at,
                    "message": "Alerta guardada en este servidor. No se contactó a emergencias.",
                }
            },
            201,
        )

    def update_business_name(self) -> None:
        user = self.current_user()
        if user is None:
            self.send_json({"error": "Inicia sesión para guardar el comercio."}, 401)
            return

        data = self.read_json()
        business_name = self.text_field(data, "business_name", "El nombre del comercio no es válido.").strip()
        if len(business_name) > 100:
            raise ValueError("El nombre del comercio no puede superar 100 caracteres.")

        with database() as connection:
            connection.execute(
                "UPDATE users SET business_name = ? WHERE id = ?",
                (business_name, user["id"]),
            )
        self.send_json({"business_name": business_name})

    def update_daily_goal(self) -> None:
        user = self.current_user()
        if user is None:
            self.send_json({"error": "Inicia sesión para guardar tu objetivo."}, 401)
            return
        data = self.read_json()
        daily_goal = data.get("daily_goal")
        if isinstance(daily_goal, bool) or not isinstance(daily_goal, int) or not 10 <= daily_goal <= 200:
            raise ValueError("El objetivo diario debe ser de 10 a 200 puntos.")
        with database() as connection:
            connection.execute("UPDATE users SET daily_goal = ? WHERE id = ?", (daily_goal, user["id"]))
        self.send_json({"daily_goal": daily_goal})

    def complete_mission(self) -> None:
        user = self.current_user()
        if user is None:
            self.send_json({"error": "Inicia sesión para completar misiones."}, 401)
            return
        data = self.read_json()
        mission_id = self.text_field(data, "mission_id", "La misión no es válida.")
        mission = DAILY_MISSIONS.get(mission_id)
        if mission is None and mission_id.startswith("admin-"):
            try:
                custom_id = int(mission_id.removeprefix("admin-"))
            except ValueError as error:
                raise ValueError("La misión no es válida.") from error
            if mission_id != f"admin-{custom_id}":
                raise ValueError("La misión no es válida.")
            with database() as connection:
                custom_mission = connection.execute(
                    "SELECT points, coins FROM missions WHERE id = ? AND active = 1",
                    (custom_id,),
                ).fetchone()
            if custom_mission is not None:
                mission = {
                    "action": "complete",
                    "points": custom_mission["points"],
                    "coins": custom_mission["coins"],
                }
        if mission is None or mission["action"] not in {"complete", "route"}:
            raise ValueError("Esa misión se completa realizando su actividad.")

        event_key = f"mission:{mission_id}:{self.today_date()}"
        with database() as connection:
            completed = self.record_event(
                connection,
                user["id"],
                event_key,
                self.today_date(),
                mission["points"],
                mission["coins"],
            )
        self.send_json({"completed": True, "already_completed": not completed})

    def get_missions(self, user: dict) -> list[dict]:
        today = self.today_date()
        with database() as connection:
            rows = connection.execute(
                "SELECT event_key FROM activity_events WHERE user_id = ? AND event_date = ?",
                (user["id"], today),
            ).fetchall()
        completed_keys = {row["event_key"] for row in rows}
        missions = []
        for mission_id, mission in DAILY_MISSIONS.items():
            event_key = f"mission:{mission_id}:{today}"
            completed = event_key in completed_keys
            missions.append({
                "id": mission_id,
                "title": mission["title"],
                "description": mission["description"],
                "icon": mission["icon"],
                "points": mission["points"],
                "coins": mission["coins"],
                "action": mission["action"],
                "completed": completed,
                "progress": int(completed),
                "total": 1,
            })
        with database() as connection:
            custom_missions = connection.execute(
                "SELECT id, title, description, icon, points, coins FROM missions WHERE active = 1 ORDER BY created_at DESC"
            ).fetchall()
        for mission in custom_missions:
            event_key = f"mission:admin-{mission['id']}:{today}"
            completed = event_key in completed_keys
            missions.append({
                "id": f"admin-{mission['id']}",
                "title": mission["title"],
                "description": mission["description"],
                "icon": mission["icon"],
                "points": mission["points"],
                "coins": mission["coins"],
                "action": "complete",
                "completed": completed,
                "progress": int(completed),
                "total": 1,
            })
        return missions

    def admin_overview(self) -> None:
        actor = self.require_staff()
        if actor is None:
            return
        today = self.today_date()
        week_start = (datetime.fromisoformat(today).date() - timedelta(days=6)).isoformat()
        month_start = (datetime.fromisoformat(today).date() - timedelta(days=29)).isoformat()
        with database() as connection:
            users_total = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            active_users = connection.execute(
                "SELECT COUNT(DISTINCT user_id) FROM activity_events WHERE event_date >= ?",
                (month_start,),
            ).fetchone()[0]
            reports_total = connection.execute(
                "SELECT COUNT(*) FROM posts WHERE kind = 'report'"
            ).fetchone()[0]
            reports_today = connection.execute(
                "SELECT COUNT(*) FROM posts WHERE kind = 'report' AND substr(created_at, 1, 10) = ?", (today,)
            ).fetchone()[0]
            reports_week = connection.execute(
                "SELECT COUNT(*) FROM posts WHERE kind = 'report' AND substr(created_at, 1, 10) >= ?", (week_start,)
            ).fetchone()[0]
            alerts_total = connection.execute("SELECT COUNT(*) FROM security_alerts").fetchone()[0]
            missions_total = connection.execute("SELECT COUNT(*) FROM missions WHERE active = 1").fetchone()[0]
            categories = connection.execute(
                """SELECT category, COUNT(*) AS count FROM posts WHERE kind = 'report'
                   GROUP BY category ORDER BY count DESC"""
            ).fetchall()
            report_rows = connection.execute(
                """SELECT posts.id,
                          CASE WHEN posts.anonymous = 1 THEN 'Anónimo' ELSE users.name END AS author,
                          CASE WHEN posts.anonymous = 1 THEN '' ELSE users.email END AS email,
                          CASE WHEN posts.anonymous = 1 THEN '' ELSE users.avatar_url END AS avatar_url,
                          posts.title, posts.description, posts.kind, posts.category, posts.latitude, posts.longitude,
                          posts.status, posts.image_url, posts.created_at,
                          0 AS is_demo
                   FROM posts JOIN users ON users.id = posts.user_id WHERE posts.kind = 'report'
                   UNION ALL
                   SELECT 'demo-' || id AS id, 'DEMO' AS author, '' AS email, '' AS avatar_url,
                          title, description, 'report' AS kind,
                          category, latitude, longitude, 'Demostración' AS status, '' AS image_url,
                          created_at, 1 AS is_demo
                   FROM demo_reports
                   ORDER BY created_at DESC"""
            ).fetchall()
            community_post_rows = connection.execute(
                """SELECT posts.id, users.name AS author, users.avatar_url, posts.title,
                          posts.description, posts.category, posts.image_url, posts.created_at
                   FROM posts JOIN users ON users.id = posts.user_id
                   WHERE posts.kind = 'post' ORDER BY posts.created_at DESC"""
            ).fetchall() if actor["role"] == "admin" else []
            alert_rows = connection.execute(
                """SELECT security_alerts.id, users.name AS author, users.email, alert_type,
                          latitude, longitude, security_alerts.created_at AS created_at
                   FROM security_alerts JOIN users ON users.id = security_alerts.user_id
                   ORDER BY security_alerts.created_at DESC LIMIT 200"""
            ).fetchall()
            mission_rows = connection.execute(
                """SELECT id, title, description, icon, points, coins, active, created_at
                   FROM missions ORDER BY created_at DESC"""
            ).fetchall()
            if actor["role"] != "admin":
                mission_rows = []
            trend_rows = connection.execute(
                """SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count FROM posts
                   WHERE kind = 'report' AND substr(created_at, 1, 10) >= ? GROUP BY day""",
                (week_start,),
            ).fetchall()
            user_rows = connection.execute(
                """SELECT id, name, email, role, avatar_url, created_at
                   FROM users ORDER BY created_at DESC"""
            ).fetchall() if actor["role"] == "admin" else []
        trend_counts = {row["day"]: row["count"] for row in trend_rows}
        today_date = datetime.fromisoformat(today).date()
        trend = [
            {
                "date": (today_date - timedelta(days=offset)).isoformat(),
                "count": trend_counts.get((today_date - timedelta(days=offset)).isoformat(), 0),
            }
            for offset in range(6, -1, -1)
        ]
        self.send_json({
            "stats": {
                "users": users_total,
                "active_users_30d": active_users,
                "reports": reports_total,
                "reports_today": reports_today,
                "reports_week": reports_week,
                "alerts": alerts_total,
                "missions": missions_total,
            },
            "reports_by_category": [dict(row) for row in categories],
            "report_trend": trend,
            "reports": [dict(row) for row in report_rows],
            "community_posts": [dict(row) for row in community_post_rows],
            "alerts": [dict(row) for row in alert_rows],
            "users": [dict(row) for row in user_rows],
            "missions": [dict(row) for row in mission_rows],
        })

    def admin_users(self) -> None:
        user = self.require_admin()
        if user is None:
            return
        with database() as connection:
            rows = connection.execute(
                """SELECT id, name, email, role, avatar_url, created_at
                   FROM users ORDER BY created_at DESC"""
            ).fetchall()
        self.send_json({"users": [dict(row) for row in rows]})

    def create_admin_user(self) -> None:
        if self.require_admin() is None:
            return
        data = self.read_json()
        name = self.text_field(data, "name", "El nombre es obligatorio.").strip()
        email = self.text_field(data, "email", "El correo es obligatorio.").strip().lower()
        password = self.text_field(data, "password", "La contraseña es obligatoria.")
        role = self.text_field(data, "role", "El rol no es válido.")
        avatar_url = self.validate_avatar_url(data.get("avatar_url", ""))
        if not 3 <= len(name) <= 80:
            raise ValueError("El nombre debe tener entre 3 y 80 caracteres.")
        if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Ingresa un correo válido.")
        if not 8 <= len(password) <= 256:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        if role not in {"admin", "moderator"}:
            raise ValueError("El personal debe tener rol de administrador o moderador.")
        salt = secrets.token_bytes(16)
        created_at = now_utc().isoformat(timespec="seconds")
        with database() as connection:
            cursor = connection.execute(
                """INSERT INTO users (name, email, role, avatar_url, password_salt, password_hash, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, email, role, avatar_url, salt, hash_password(password, salt), created_at),
            )
            new_user_id = cursor.lastrowid
            row = connection.execute(
                """SELECT id, name, email, role, avatar_url, created_at
                   FROM users WHERE id = ?""",
                (new_user_id,),
            ).fetchone()
        self.send_json({"user": dict(row)}, 201)

    def update_admin_user(self, user_id: str, field: str) -> None:
        actor = self.require_admin()
        if actor is None:
            return
        if not user_id.isdecimal():
            self.send_json({"error": "No se encontró esa cuenta."}, 404)
            return
        data = self.read_json()
        with database() as connection:
            target = connection.execute(
                "SELECT id, role FROM users WHERE id = ?", (int(user_id),)
            ).fetchone()
            if target is None:
                self.send_json({"error": "No se encontró esa cuenta."}, 404)
                return
            if field == "role":
                role = self.text_field(data, "role", "El rol no es válido.")
                if role not in {"user", "moderator", "admin"}:
                    raise ValueError("Selecciona usuario, moderador o administrador.")
                if target["id"] == actor["id"] and role != "admin":
                    raise ValueError("No puedes retirar tus propios permisos de administrador.")
                if target["role"] == "admin" and role != "admin":
                    total_admins = connection.execute(
                        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
                    ).fetchone()[0]
                    if total_admins <= 1:
                        raise ValueError("Debe quedar al menos una cuenta con control total.")
                connection.execute("UPDATE users SET role = ? WHERE id = ?", (role, int(user_id)))
                result = {"role": role}
            else:
                avatar_url = self.validate_avatar_url(data.get("avatar_url", ""))
                connection.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (avatar_url, int(user_id)))
                result = {"avatar_url": avatar_url}
        self.send_json({"user_id": int(user_id), **result})

    @staticmethod
    def validate_avatar_url(value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("La dirección de la foto no es válida.")
        avatar_url = value.strip()
        if not avatar_url:
            return ""
        if re.fullmatch(r"/uploads/[a-f0-9]{40}\.(?:jpg|png|webp)", avatar_url):
            if (ROOT / avatar_url.lstrip("/")).is_file():
                return avatar_url
            raise ValueError("No se encontró la foto cargada.")
        parsed_url = urllib.parse.urlsplit(avatar_url)
        if len(avatar_url) > 500 or parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("La foto debe usar una dirección HTTPS válida.")
        return avatar_url

    def update_admin_post_status(self, post_id: str) -> None:
        if self.require_staff() is None:
            return
        if not post_id.isdecimal():
            self.send_json({"error": "No se encontró ese reporte."}, 404)
            return
        data = self.read_json()
        status = self.text_field(data, "status", "El estado no es válido.")
        allowed_statuses = {"Pendiente", "En revisión", "Atendido", "Descartado"}
        if status not in allowed_statuses:
            raise ValueError("Selecciona un estado válido para el reporte.")
        with database() as connection:
            cursor = connection.execute(
                "UPDATE posts SET status = ? WHERE id = ? AND kind = 'report'",
                (status, int(post_id)),
            )
        if cursor.rowcount == 0:
            self.send_json({"error": "No se encontró ese reporte."}, 404)
            return
        self.send_json({"id": int(post_id), "status": status})

    def create_admin_mission(self) -> None:
        if self.require_admin() is None:
            return
        data = self.read_json()
        title = self.text_field(data, "title", "El título es obligatorio.").strip()
        description = self.text_field(data, "description", "La descripción es obligatoria.").strip()
        icon = self.text_field(data, "icon", "El ícono no es válido.").strip()
        points = data.get("points")
        coins = data.get("coins")
        allowed_icons = {"bi-flag-fill", "bi-shield-check", "bi-map", "bi-people-fill"}
        if not 3 <= len(title) <= 80:
            raise ValueError("El título debe tener entre 3 y 80 caracteres.")
        if not 1 <= len(description) <= 500:
            raise ValueError("La descripción debe tener entre 1 y 500 caracteres.")
        if icon not in allowed_icons:
            raise ValueError("El ícono seleccionado no es válido.")
        if isinstance(points, bool) or not isinstance(points, int) or not 0 <= points <= 1000:
            raise ValueError("Los puntos deben ser un número entre 0 y 1000.")
        if isinstance(coins, bool) or not isinstance(coins, int) or not 0 <= coins <= 1000:
            raise ValueError("Las monedas deben ser un número entre 0 y 1000.")
        created_at = now_utc().isoformat(timespec="seconds")
        with database() as connection:
            cursor = connection.execute(
                """INSERT INTO missions (title, description, icon, points, coins, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (title, description, icon, points, coins, created_at),
            )
        self.send_json({
            "mission": {
                "id": cursor.lastrowid,
                "title": title,
                "description": description,
                "icon": icon,
                "points": points,
                "coins": coins,
                "active": 1,
                "created_at": created_at,
            }
        }, 201)

    def delete_admin_post(self, post_id: str) -> None:
        if self.require_admin() is None:
            return
        if not post_id.isdecimal():
            self.send_json({"error": "No se encontró esa publicación."}, 404)
            return
        with database() as connection:
            cursor = connection.execute("DELETE FROM posts WHERE id = ?", (int(post_id),))
        if cursor.rowcount == 0:
            self.send_json({"error": "No se encontró esa publicación."}, 404)
            return
        self.send_json({"deleted": True})

    def delete_admin_mission(self, mission_id: str) -> None:
        if self.require_admin() is None:
            return
        if not mission_id.isdecimal():
            self.send_json({"error": "No se encontró esa misión."}, 404)
            return
        with database() as connection:
            cursor = connection.execute("DELETE FROM missions WHERE id = ?", (int(mission_id),))
        if cursor.rowcount == 0:
            self.send_json({"error": "No se encontró esa misión."}, 404)
            return
        self.send_json({"deleted": True})

    def require_admin(self) -> dict | None:
        user = self.current_user()
        if user is None:
            self.send_json({"error": "Inicia sesión para acceder al panel administrativo."}, 401)
            return None
        if user["role"] != "admin":
            self.send_json({"error": "Tu cuenta no tiene permisos administrativos."}, 403)
            return None
        return user

    def require_staff(self) -> dict | None:
        user = self.current_user()
        if user is None:
            self.send_json({"error": "Inicia sesión para acceder al panel administrativo."}, 401)
            return None
        if user["role"] not in {"admin", "moderator"}:
            self.send_json({"error": "Tu cuenta no tiene permisos de personal."}, 403)
            return None
        return user

    def get_dashboard(self, user: dict) -> dict:
        today = self.today_date()
        week_start = (datetime.fromisoformat(today).date() - timedelta(days=6)).isoformat()
        with database() as connection:
            user_row = connection.execute(
                "SELECT daily_goal FROM users WHERE id = ?", (user["id"],)
            ).fetchone()
            events = connection.execute(
                """SELECT event_key, event_date, points, coins FROM activity_events
                   WHERE user_id = ? ORDER BY event_date DESC""",
                (user["id"],),
            ).fetchall()
            post_count = connection.execute(
                "SELECT COUNT(*) FROM posts WHERE user_id = ?", (user["id"],)
            ).fetchone()[0]
            weekly_reports = connection.execute(
                "SELECT COUNT(*) FROM posts WHERE user_id = ? AND substr(created_at, 1, 10) >= ?",
                (user["id"], week_start),
            ).fetchone()[0]
            mission_count = connection.execute(
                "SELECT COUNT(*) FROM activity_events WHERE user_id = ? AND event_key LIKE 'mission:%'",
                (user["id"],),
            ).fetchone()[0]

        total_points = sum(row["points"] for row in events)
        total_coins = sum(row["coins"] for row in events)
        today_points = sum(row["points"] for row in events if row["event_date"] == today)
        weekly_points = sum(row["points"] for row in events if week_start <= row["event_date"] <= today)
        weekly_missions = sum(
            row["event_key"].startswith("mission:") and week_start <= row["event_date"] <= today
            for row in events
        )
        active_days = {row["event_date"] for row in events}
        streak_cursor = datetime.fromisoformat(today).date()
        if streak_cursor.isoformat() not in active_days:
            streak_cursor -= timedelta(days=1)
        streak = 0
        while streak_cursor.isoformat() in active_days:
            streak += 1
            streak_cursor -= timedelta(days=1)

        week_days = []
        day_names = ("L", "M", "X", "J", "V", "S", "D")
        today_date = datetime.fromisoformat(today).date()
        for offset in range(6, -1, -1):
            day = today_date - timedelta(days=offset)
            week_days.append({
                "label": day_names[day.weekday()],
                "date": day.isoformat(),
                "active": day.isoformat() in active_days,
            })

        achievements = []
        if post_count:
            achievements.append({"id": "first_report", "label": "Primer aporte", "icon": "bi-flag-fill"})
        if streak >= 3:
            achievements.append({"id": "three_day_streak", "label": "Racha de 3 días", "icon": "bi-fire"})
        if total_points >= 100:
            achievements.append({"id": "hundred_points", "label": "100 puntos", "icon": "bi-star-fill"})

        daily_goal = user_row["daily_goal"]
        return {
            "user": user,
            "stats": {
                "coins": total_coins,
                "points": total_points,
                "today_points": today_points,
                "weekly_points": weekly_points,
                "daily_goal": daily_goal,
                "goal_percent": min(100, round(today_points / daily_goal * 100)) if daily_goal else 0,
                "contributions": post_count,
                "missions_completed": mission_count,
                "weekly_reports": weekly_reports,
                "weekly_missions": weekly_missions,
                "level": 1 + total_points // 100,
            },
            "streak": {"days": streak, "week": week_days},
            "achievements": achievements,
            "activities": [dict(row) for row in events],
        }

    @staticmethod
    def today_date() -> str:
        return datetime.now().astimezone().date().isoformat()

    @staticmethod
    def record_event(
        connection: sqlite3.Connection,
        user_id: int,
        event_key: str,
        event_date: str,
        points: int,
        coins: int,
    ) -> bool:
        cursor = connection.execute(
            """INSERT OR IGNORE INTO activity_events
               (user_id, event_key, event_date, points, coins, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, event_key, event_date, points, coins, now_utc().isoformat(timespec="seconds")),
        )
        return cursor.rowcount == 1

    def read_json(self, max_bytes: int = 16_384) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Solicitud no válida.") from error
        if length <= 0 or length > max_bytes:
            raise ValueError("El contenido de la solicitud no es válido.")
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("El contenido de la solicitud no es válido.")
        return data

    @staticmethod
    def text_field(data: dict, field: str, error: str) -> str:
        value = data.get(field)
        if not isinstance(value, str):
            raise ValueError(error)
        return value

    @staticmethod
    def optional_coordinate(value: object, minimum: float, maximum: float) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("La ubicación no es válida.")
        if not minimum <= value <= maximum:
            raise ValueError("La ubicación no es válida.")
        return float(value)

    def current_user(self) -> dict | None:
        token = self.session_token()
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with database() as connection:
            row = connection.execute(
                """SELECT users.id, users.name, users.email, users.business_name, users.role, users.avatar_url
                   FROM sessions JOIN users ON users.id = sessions.user_id
                   WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
                (token_hash, now_utc().isoformat(timespec="seconds")),
            ).fetchone()
        return dict(row) if row else None

    def session_token(self) -> str | None:
        cookies = SimpleCookie()
        cookies.load(self.headers.get("Cookie", ""))
        cookie = cookies.get(SESSION_COOKIE)
        return cookie.value if cookie else None

    @staticmethod
    def store_session(connection: sqlite3.Connection, token: str, user_id: int) -> None:
        now = now_utc()
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (now.isoformat(),))
        connection.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (
                hashlib.sha256(token.encode("utf-8")).hexdigest(),
                user_id,
                (now + timedelta(seconds=SESSION_SECONDS)).isoformat(timespec="seconds"),
            ),
        )

    @staticmethod
    def session_cookie(token: str) -> str:
        return (
            f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; "
            f"Max-Age={SESSION_SECONDS}"
        )

    def serve_static(self, url_path: str) -> None:
        relative_path = unquote(url_path).lstrip("/") or "feed/index.html"
        file_path = (ROOT / relative_path).resolve()
        if ROOT not in file_path.parents or file_path.suffix.lower() not in {
            ".html", ".css", ".js", ".ico", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".woff2"
        }:
            self.send_json({"error": "No se encontró esa página."}, 404)
            return
        if not file_path.is_file():
            self.send_json({"error": "No se encontró esa página."}, 404)
            return

        body = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        charset = "; charset=utf-8" if content_type.startswith("text/") or content_type in {
            "application/javascript", "application/json"
        } else ""
        self.send_header("Content-Type", f"{content_type}{charset}")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, status: int = 200, headers: list[tuple[str, str]] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in headers or []:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"{self.log_date_time_string()} {format_string % args}")


def main() -> None:
    initialize_database()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), CivicMxHandler)
    print(f"HeroesMX disponible en http://localhost:{PORT}")
    print(f"Base de datos local: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()