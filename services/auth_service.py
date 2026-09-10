import os
import sqlite3
import hashlib
import hmac
import secrets
import re
from datetime import datetime
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "users.db")


class AuthService:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.use_firestore = False
        self.firestore_db = None

        # Détection automatique de l'environnement Cloud Run ou activation explicite
        force_firestore = os.getenv("USE_FIRESTORE", "").lower() in ("true", "1", "yes")
        is_cloud = bool(os.getenv("K_SERVICE") or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT"))

        if force_firestore or is_cloud:
            try:
                from google.cloud import firestore
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or None
                self.firestore_db = firestore.Client(project=project_id)
                self.use_firestore = True
                print("[AuthService] Mode persistant activé : Google Cloud Firestore")
            except Exception as e:
                print(f"[AuthService] Firestore non disponible ({e}), bascule automatique sur SQLite.")
                self.use_firestore = False
                self.firestore_db = None

        if not self.use_firestore:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._init_sqlite()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_sqlite(self):
        """Initialise la table SQLite des utilisateurs pour le développement local."""
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
        if self.use_firestore:
            try:
                count_query = self.firestore_db.collection("users").count()
                results = count_query.get()
                return results[0][0].value
            except Exception:
                docs = list(self.firestore_db.collection("users").select([]).stream())
                return len(docs)

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

        # Premier utilisateur inscrit devient Admin
        admin_env_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        is_first_user = (self.get_user_count() == 0)
        is_admin_candidate = is_first_user or (admin_env_email and clean_email == admin_env_email)

        is_approved = 1 if is_admin_candidate else 0
        is_admin = 1 if is_admin_candidate else 0
        sub_plan = "fondateur_admin" if is_admin_candidate else "decouverte"
        sub_status = "active" if is_admin_candidate else "pending"
        now_iso = datetime.now().isoformat()

        if self.use_firestore:
            try:
                doc_ref = self.firestore_db.collection("users").document(clean_email)
                if doc_ref.get().exists:
                    return {"success": False, "error": "Un compte existe déjà avec cette adresse email."}

                user_data = {
                    "id": clean_email,
                    "email": clean_email,
                    "name": clean_name,
                    "password_hash": pwd_hash,
                    "salt": salt,
                    "is_approved": bool(is_approved),
                    "is_admin": bool(is_admin),
                    "subscription_plan": sub_plan,
                    "subscription_status": sub_status,
                    "subscription_expires_at": None,
                    "stripe_customer_id": None,
                    "created_at": now_iso,
                    "last_login": None
                }
                doc_ref.set(user_data)
                return {"success": True, "user": user_data}
            except Exception as e:
                return {"success": False, "error": f"Erreur Firestore : {str(e)}"}

        # Branche SQLite locale
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
                    is_approved, is_admin, sub_plan, sub_status, now_iso
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

        if self.use_firestore:
            try:
                doc_ref = self.firestore_db.collection("users").document(clean_email)
                doc = doc_ref.get()
                if not doc.exists:
                    return {"success": False, "error": "Adresse email ou mot de passe incorrect."}

                data = doc.to_dict()
                if not self._verify_password(password, data["salt"], data["password_hash"]):
                    return {"success": False, "error": "Adresse email ou mot de passe incorrect."}

                now_iso = datetime.now().isoformat()
                doc_ref.update({"last_login": now_iso})
                data["last_login"] = now_iso
                data["id"] = data.get("id") or clean_email
                data["is_approved"] = bool(data.get("is_approved", False))
                data["is_admin"] = bool(data.get("is_admin", False))
                return {"success": True, "user": data}
            except Exception as e:
                return {"success": False, "error": f"Erreur d'authentification : {str(e)}"}

        # Branche SQLite locale
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
        if self.use_firestore:
            docs = self.firestore_db.collection("users").where("is_approved", "==", False).stream()
            pending = []
            for d in docs:
                data = d.to_dict()
                data["id"] = data.get("id") or d.id
                pending.append(data)
            pending.sort(key=lambda x: x.get("created_at") or "", reverse=True)
            return pending

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
        if self.use_firestore:
            docs = self.firestore_db.collection("users").stream()
            users = []
            for d in docs:
                data = d.to_dict()
                data["id"] = data.get("id") or d.id
                data["is_approved"] = bool(data.get("is_approved", False))
                data["is_admin"] = bool(data.get("is_admin", False))
                users.append(data)
            users.sort(key=lambda x: x.get("created_at") or "", reverse=True)
            return users

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, is_approved, is_admin, subscription_plan, 
                       subscription_status, created_at, last_login 
                FROM users 
                ORDER BY created_at DESC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def approve_user(self, user_id, plan: str = "gratuit") -> bool:
        """Approuve un utilisateur en attente et active son accès."""
        if self.use_firestore:
            doc_ref = self.firestore_db.collection("users").document(str(user_id))
            doc_ref.update({
                "is_approved": True,
                "subscription_status": "active",
                "subscription_plan": plan
            })
            return True

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET is_approved = 1, subscription_status = 'active', subscription_plan = ? 
                WHERE id = ?
            """, (plan, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def reject_or_delete_user(self, user_id) -> bool:
        """Supprime une demande d'inscription ou un compte utilisateur."""
        if self.use_firestore:
            self.firestore_db.collection("users").document(str(user_id)).delete()
            return True

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def toggle_user_access(self, user_id, new_status: int) -> bool:
        """Active ou suspend l'accès d'un compte utilisateur."""
        sub_status = "active" if new_status == 1 else "suspended"
        if self.use_firestore:
            self.firestore_db.collection("users").document(str(user_id)).update({
                "is_approved": bool(new_status),
                "subscription_status": sub_status
            })
            return True

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET is_approved = ?, subscription_status = ? 
                WHERE id = ?
            """, (new_status, sub_status, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def update_user_plan(self, user_id, new_plan: str) -> bool:
        """Met à jour la formule d'abonnement d'un utilisateur."""
        if self.use_firestore:
            self.firestore_db.collection("users").document(str(user_id)).update({
                "subscription_plan": new_plan
            })
            return True

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET subscription_plan = ? WHERE id = ?", (new_plan, user_id))
            conn.commit()
            return cursor.rowcount > 0
