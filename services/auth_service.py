import os
import sqlite3
import hashlib
import hmac
import secrets
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from contextlib import contextmanager

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "users.db")


class AuthService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        """Initialise la table des utilisateurs avec support des abonnements futurs."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    is_approved INTEGER NOT NULL DEFAULT 0,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    subscription_plan TEXT NOT NULL DEFAULT 'gratuit',
                    subscription_status TEXT NOT NULL DEFAULT 'pending',
                    subscription_expires_at TIMESTAMP,
                    stripe_customer_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            conn.commit()

    @staticmethod
    def _hash_password(password: str, salt_hex: str) -> str:
        """Hachage cryptographique robuste PBKDF2-SHA256 (600 000 itérations, OWASP)."""
        salt_bytes = bytes.fromhex(salt_hex)
        hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 600_000)
        return hash_bytes.hex()

    @staticmethod
    def _verify_password(password: str, salt_hex: str, expected_hash_hex: str) -> bool:
        """Comparaison en temps constant pour contrer les attaques temporelles."""
        computed_hash = AuthService._hash_password(password, salt_hex)
        return hmac.compare_digest(computed_hash, expected_hash_hex)

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Vérifie le format standard d'une adresse email."""
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return bool(re.match(pattern, email.strip()))

    def get_user_count(self) -> int:
        """Retourne le nombre total d'utilisateurs inscrits."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]

    def register_user(self, email: str, password: str, name: str = "") -> dict:
        """Inscrit un nouvel utilisateur avec hachage fort."""
        clean_email = email.strip().lower()
        clean_name = name.strip() or clean_email.split('@')[0].capitalize()

        if not self.is_valid_email(clean_email):
            return {"success": False, "error": "Format d'adresse email invalide."}

        if len(password) < 6:
            return {"success": False, "error": "Le mot de passe doit contenir au moins 6 caractères."}

        salt = secrets.token_hex(32)
        pwd_hash = self._hash_password(password, salt)

        # Si c'est le tout premier compte créé sur l'application, ou si l'email correspond à ADMIN_EMAIL
        admin_env_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        is_first_user = (self.get_user_count() == 0)
        is_admin_candidate = is_first_user or (admin_env_email and clean_email == admin_env_email)

        is_approved = 1 if is_admin_candidate else 0
        is_admin = 1 if is_admin_candidate else 0
        sub_plan = "fondateur_admin" if is_admin_candidate else "decouverte"
        sub_status = "active" if is_admin_candidate else "pending"

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (
                        email, name, password_hash, salt, 
                        is_approved, is_admin, subscription_plan, subscription_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clean_email, clean_name, pwd_hash, salt, 
                    is_approved, is_admin, sub_plan, sub_status, datetime.now().isoformat()
                ))
                conn.commit()
                user_id = cursor.lastrowid

            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "email": clean_email,
                    "name": clean_name,
                    "is_approved": bool(is_approved),
                    "is_admin": bool(is_admin),
                    "subscription_plan": sub_plan,
                    "subscription_status": sub_status
                }
            }
        except sqlite3.IntegrityError:
            return {"success": False, "error": "Un compte existe déjà avec cette adresse email."}
        except Exception as e:
            return {"success": False, "error": f"Erreur lors de l'enregistrement : {str(e)}"}

    def authenticate_user(self, email: str, password: str) -> dict:
        """Vérifie les identifiants d'un utilisateur et retourne son statut complet."""
        clean_email = email.strip().lower()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, password_hash, salt, is_approved, is_admin, 
                       subscription_plan, subscription_status, subscription_expires_at
                FROM users WHERE email = ?
            """, (clean_email,))
            row = cursor.fetchone()

        if not row:
            return {"success": False, "error": "Adresse email ou mot de passe incorrect."}

        if not self._verify_password(password, row["salt"], row["password_hash"]):
            return {"success": False, "error": "Adresse email ou mot de passe incorrect."}

        # Mise à jour de la dernière connexion
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now().isoformat(), row["id"]))
            conn.commit()

        user_data = {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "is_approved": bool(row["is_approved"]),
            "is_admin": bool(row["is_admin"]),
            "subscription_plan": row["subscription_plan"],
            "subscription_status": row["subscription_status"],
            "subscription_expires_at": row["subscription_expires_at"]
        }

        return {"success": True, "user": user_data}

    # --- MÉTHODES D'ADMINISTRATION ---

    def get_pending_users(self) -> list[dict]:
        """Récupère tous les utilisateurs en attente d'approbation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, subscription_plan, subscription_status, created_at 
                FROM users 
                WHERE is_approved = 0 
                ORDER BY created_at DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def get_all_users(self) -> list[dict]:
        """Récupère l'ensemble des utilisateurs enregistrés."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, is_approved, is_admin, subscription_plan, 
                       subscription_status, created_at, last_login 
                FROM users 
                ORDER BY created_at DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def approve_user(self, user_id: int, plan: str = "gratuit") -> bool:
        """Approuve un utilisateur en attente et active son accès."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET is_approved = 1, subscription_status = 'active', subscription_plan = ? 
                WHERE id = ?
            """, (plan, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def reject_or_delete_user(self, user_id: int) -> bool:
        """Supprime une demande d'inscription ou un compte utilisateur."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def toggle_user_access(self, user_id: int, new_status: int) -> bool:
        """Active ou suspend l'accès d'un compte utilisateur."""
        sub_status = "active" if new_status == 1 else "suspended"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET is_approved = ?, subscription_status = ? 
                WHERE id = ?
            """, (new_status, sub_status, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_user_plan(self, user_id: int, new_plan: str) -> bool:
        """Met à jour la formule d'abonnement d'un utilisateur."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET subscription_plan = ? WHERE id = ?", (new_plan, user_id))
            conn.commit()
            return cursor.rowcount > 0
