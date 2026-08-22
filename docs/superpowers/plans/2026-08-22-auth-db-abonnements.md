# Comptes, DB & abonnements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un mode compte optionnel (auth par lien magique, profils natals persistés, statut d'abonnement) activé uniquement si `DATABASE_URL` est configuré, sans changer le comportement stateless actuel quand elle est absente.

**Architecture:** `db.py` détecte `DATABASE_URL` et expose `DB_ENABLED`. `models.py` définit le schéma SQLAlchemy (6 tables). `auth.py` porte la logique pure (lien magique, session signée). Le routeur `comptes.py` n'est monté dans `main.py` que si `DB_ENABLED` est vrai — sinon les routes `/auth/*`, `/profils/*`, `/moi` n'existent simplement pas (404 naturel de FastAPI, pas de code de garde à écrire). `/portrait` gagne un incrément best-effort du compteur global.

**Tech Stack:** FastAPI (existant), SQLAlchemy 2.x + psycopg (driver Postgres), Alembic (migrations), itsdangerous (cookie de session signé), PostgreSQL 16.

## Global Constraints

- `DATABASE_URL` absent → comportement identique à aujourd'hui : `/portrait`, `/theme`, `/lecture-approfondie` inchangés, aucune tentative de connexion DB, aucun crash au démarrage.
- Pas de mot de passe stocké nulle part : authentification par lien magique uniquement.
- Aucun SDK Stripe dans ce sprint. `scripts/toggle_abonnement.py` simule ce qu'un futur webhook écrirait.
- Création de `profils_natals` illimitée et gratuite ; seule l'activation de `suivi_actif` est plafonnée à 4 par compte ET nécessite `abonnements.statut == "actif"`.
- Tests Python lancés depuis `engine/` : `cd engine && python -m pytest -q`. Les tests touchant la DB utilisent une Postgres de test dédiée et sont **skip** proprement si `DATABASE_URL_TEST` n'est pas configuré (jamais d'échec bruyant faute de service).
- Repli honnête sur l'envoi d'email : si aucun service n'est configuré, le lien de connexion est loggé côté serveur (warning explicite), jamais une erreur utilisateur.

---

## File Structure

- **Create** `db.py` — connexion SQLAlchemy optionnelle, `DB_ENABLED`, `get_db()` (dépendance FastAPI).
- **Create** `models.py` — 6 modèles SQLAlchemy (`Compte`, `LienMagique`, `Session`, `ProfilNatal`, `Abonnement`, `CompteurPortraits`) + `MAX_SUIVIS_ACTIFS`.
- **Create** `auth.py` — `demander_lien()`, `verifier_lien()`, `compte_depuis_cookie()`, `deconnecter()`, envoi d'email avec repli honnête.
- **Create** `comptes.py` — routeur FastAPI (`/auth/demande-lien`, `/auth/verifier`, `/auth/deconnexion`, `/moi`, `/profils`, `/profils/{id}`, `/profils/import-local`, `/stats`).
- **Modify** `main.py` — montage conditionnel du routeur, incrément du compteur dans `/portrait`.
- **Create** `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_initial.py` — migration initiale (les 6 tables).
- **Create** `scripts/toggle_abonnement.py` — CLI dev/admin pour simuler un changement d'abonnement.
- **Modify** `requirements.txt` — ajoute `sqlalchemy`, `psycopg[binary]`, `alembic`, `itsdangerous`.
- **Modify** `docker-compose.yml` — service `postgres-test` (profil `test`, disposable).
- **Modify** `.env.example` — documente `DATABASE_URL`, `DATABASE_URL_TEST`, `SESSION_SECRET`, `BASE_URL`, `EMAIL_SMTP_URL`.
- **Modify** `Dockerfile` — copie les nouveaux fichiers (`db.py`, `models.py`, `auth.py`, `comptes.py`).
- **Create** `engine/conftest.py` — fixture `db_session` (skip si `DATABASE_URL_TEST` absent).
- **Create** `engine/test_db_flag.py` — comportement du feature-flag (DB absente).
- **Create** `engine/test_auth.py` — logique lien magique / session.
- **Create** `engine/test_comptes_api.py` — endpoints `/auth/*`, `/moi`, `/profils/*`, `/stats`.

---

### Task 1: Dépendances + Postgres de test

**Files:**
- Modify: `requirements.txt`
- Modify: `docker-compose.yml`
- Modify: `.env.example`

**Interfaces:**
- Produces: service Docker `postgres-test` (profil `test`), variables d'env documentées, consommées par toutes les tâches suivantes.

- [ ] **Step 1: Ajouter les dépendances**

Dans `requirements.txt`, ajouter après `httpx==0.28.1` :

```
sqlalchemy==2.0.36
psycopg[binary]==3.2.3
alembic==1.14.0
itsdangerous==2.2.0
```

- [ ] **Step 2: Installer et vérifier**

Run: `pip install -r requirements.txt`
Expected: installation sans erreur.

- [ ] **Step 3: Ajouter le service Postgres de test**

Dans `docker-compose.yml`, ajouter un service (fichier complet après modification) :

```yaml
services:
  portrait-cosmique:
    build: .
    image: portrait-cosmique
    ports: ["8410:8410"]
    environment:
      - CORS_ORIGINS=${CORS_ORIGINS:-*}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
      - OPENROUTER_MODEL=${OPENROUTER_MODEL:-google/gemma-3-27b-it:free}
      - DATABASE_URL=${DATABASE_URL:-}
      - SESSION_SECRET=${SESSION_SECRET:-}
      - BASE_URL=${BASE_URL:-http://localhost:8410}
      - EMAIL_SMTP_URL=${EMAIL_SMTP_URL:-}

  postgres-test:
    image: postgres:16-alpine
    profiles: ["test"]
    environment:
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
      - POSTGRES_DB=portrait_cosmique_test
    ports: ["5433:5432"]
```

Note : `postgres-test` n'est **jamais** démarré par un simple `docker compose up` (grâce à `profiles: ["test"]`) — il faut explicitement `docker compose --profile test up -d postgres-test`. Un self-hoster qui lance l'app normalement ne voit rien changer.

- [ ] **Step 4: Démarrer la DB de test et vérifier**

Run: `docker compose --profile test up -d postgres-test`
Run: `sleep 2 && docker compose exec postgres-test pg_isready -U test`
Expected: `accepting connections`.

- [ ] **Step 5: Documenter les variables d'environnement**

Ajouter à la fin de `.env.example` :

```
# ── Mode compte (optionnel — sous-projet 3/5, préparation Free/Paid) ──────
# Absent par défaut : l'app reste 100% stateless, comme aujourd'hui. Renseigner
# ces variables active les routes /auth/*, /profils/*, /moi.

# URL de connexion PostgreSQL (ex. postgresql+psycopg://user:pass@host:5432/db).
# Laisser vide pour rester en mode stateless (aucun compte, aucune DB).
DATABASE_URL=

# Secret de signature des cookies de session (générer avec `openssl rand -hex 32`).
# Requis dès que DATABASE_URL est renseigné.
SESSION_SECRET=

# URL publique de cette instance, utilisée pour construire le lien de connexion
# envoyé par email (ex. https://portrait-cosmique.example.com).
BASE_URL=http://localhost:8410

# Service d'envoi d'email pour le lien de connexion. Laisser vide : le lien est
# affiché dans les logs serveur (repli honnête, pratique en dev/self-hébergement).
EMAIL_SMTP_URL=
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt docker-compose.yml .env.example
git commit -m "chore: dépendances + Postgres de test pour le mode compte"
```

---

### Task 2: `db.py` — connexion optionnelle

**Files:**
- Create: `db.py`
- Test: `engine/test_db_flag.py`

**Interfaces:**
- Produces: `db.DATABASE_URL: str`, `db.DB_ENABLED: bool`, `db.Base` (declarative base), `db.engine`, `db.SessionLocal`, `db.get_db()` (générateur, dépendance FastAPI).

- [ ] **Step 1: Write failing test**

Create `engine/test_db_flag.py` :

```python
"""Comportement du feature-flag DB (DATABASE_URL absent/présent)."""
import importlib
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def test_db_disabled_sans_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import db
    importlib.reload(db)
    assert db.DB_ENABLED is False
    assert db.engine is None
    assert db.SessionLocal is None


def test_db_enabled_avec_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/x")
    import db
    importlib.reload(db)
    assert db.DB_ENABLED is True
    assert db.engine is not None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd engine && python -m pytest test_db_flag.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'db'`).

- [ ] **Step 3: Implement `db.py`**

Create `/db.py` (racine du projet) :

```python
"""Connexion DB optionnelle — activée uniquement si DATABASE_URL est configuré.

Sans DATABASE_URL (self-hébergement par défaut), DB_ENABLED est False : aucune
connexion n'est tentée, aucune table n'est créée, et main.py ne monte pas les
routes compte (voir comptes.py). Le reste de l'app (/portrait, /theme,
/lecture-approfondie) est indépendant de ce module."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_ENABLED = bool(DATABASE_URL)

Base = declarative_base()

if DB_ENABLED:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
else:
    engine = None
    SessionLocal = None


def get_db():
    """Dépendance FastAPI : une session par requête, fermée après usage.

    N'est appelée que par des routes montées uniquement quand DB_ENABLED est
    vrai (voir comptes.py + main.py) — pas de garde nécessaire ici."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd engine && python -m pytest test_db_flag.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add db.py engine/test_db_flag.py
git commit -m "feat: connexion DB optionnelle (DB_ENABLED via DATABASE_URL)"
```

---

### Task 3: `models.py` + migration Alembic initiale

**Files:**
- Create: `models.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/0001_initial.py`
- Create: `engine/conftest.py`

**Interfaces:**
- Consumes: `db.Base`, `db.DATABASE_URL` (Task 2).
- Produces: `models.Compte`, `models.LienMagique`, `models.Session`, `models.ProfilNatal`, `models.Abonnement`, `models.CompteurPortraits`, `models.MAX_SUIVIS_ACTIFS = 4`. Fixture pytest `db_session` (skip si `DATABASE_URL_TEST` absent), consommée par les Tasks 4-7.

- [ ] **Step 1: Implement `models.py`**

Create `/models.py` :

```python
"""Modèles SQLAlchemy — comptes, profils natals, abonnements.

Voir docs/superpowers/specs/2026-08-22-auth-db-abonnements-design.md pour le
schéma complet et les règles métier. Actifs uniquement si DATABASE_URL est
configuré (db.DB_ENABLED)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from db import Base

MAX_SUIVIS_ACTIFS = 4


def _uuid() -> str:
    return str(uuid.uuid4())


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


class Compte(Base):
    __tablename__ = "comptes"
    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    cree_le = Column(DateTime(timezone=True), default=_maintenant)

    profils = relationship("ProfilNatal", back_populates="compte",
                            cascade="all, delete-orphan")
    abonnement = relationship("Abonnement", back_populates="compte",
                               uselist=False, cascade="all, delete-orphan")


class LienMagique(Base):
    __tablename__ = "liens_magiques"
    id = Column(String, primary_key=True, default=_uuid)
    compte_id = Column(String, ForeignKey("comptes.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expire_le = Column(DateTime(timezone=True), nullable=False)
    utilise_le = Column(DateTime(timezone=True), nullable=True)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=_uuid)
    compte_id = Column(String, ForeignKey("comptes.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expire_le = Column(DateTime(timezone=True), nullable=False)


class ProfilNatal(Base):
    __tablename__ = "profils_natals"
    id = Column(String, primary_key=True, default=_uuid)
    compte_id = Column(String, ForeignKey("comptes.id"), nullable=False)
    label = Column(String, nullable=False, default="")
    prenoms = Column(String, nullable=False, default="")
    nom = Column(String, nullable=False, default="")
    date_naissance = Column(String, nullable=False, default="")
    heure_naissance = Column(String, nullable=True)
    ville = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    utc_offset = Column(Float, nullable=True)
    systeme_numerologie = Column(String, nullable=False, default="classique")
    suivi_actif = Column(Boolean, nullable=False, default=False)
    cree_le = Column(DateTime(timezone=True), default=_maintenant)

    compte = relationship("Compte", back_populates="profils")


class Abonnement(Base):
    __tablename__ = "abonnements"
    id = Column(String, primary_key=True, default=_uuid)
    compte_id = Column(String, ForeignKey("comptes.id"), unique=True, nullable=False)
    statut = Column(String, nullable=False, default="inactif")
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    plan = Column(String, nullable=True)
    debut_le = Column(DateTime(timezone=True), nullable=True)
    fin_le = Column(DateTime(timezone=True), nullable=True)
    maj_le = Column(DateTime(timezone=True), default=_maintenant, onupdate=_maintenant)

    compte = relationship("Compte", back_populates="abonnement")


class CompteurPortraits(Base):
    __tablename__ = "compteur_portraits"
    id = Column(Integer, primary_key=True)
    total = Column(Integer, nullable=False, default=0)
    maj_le = Column(DateTime(timezone=True), default=_maintenant, onupdate=_maintenant)
```

- [ ] **Step 2: Initialiser Alembic**

Run: `alembic init alembic`
Expected: crée `alembic.ini` et `alembic/` à la racine.

- [ ] **Step 3: Configurer `alembic/env.py`**

Remplacer le contenu de `alembic/env.py` par :

```python
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).parent.parent))

from db import Base, DATABASE_URL
import models  # noqa: F401 — enregistre les modèles sur Base.metadata

config = context.config
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Générer la migration initiale**

Run: `export DATABASE_URL="postgresql+psycopg://test:test@localhost:5433/portrait_cosmique_test"` (Postgres de test de la Task 1, déjà démarrée)
Run: `alembic revision --autogenerate -m "initial"`
Expected: crée `alembic/versions/<hash>_initial.py` avec les 6 tables détectées.

Renommer ce fichier en `alembic/versions/0001_initial.py` pour un nom stable et lisible.

- [ ] **Step 5: Appliquer et vérifier**

Run: `alembic upgrade head`
Run: `docker compose exec postgres-test psql -U test -d portrait_cosmique_test -c "\dt"`
Expected : liste les 6 tables (`comptes`, `liens_magiques`, `sessions`, `profils_natals`, `abonnements`, `compteur_portraits`) + `alembic_version`.

- [ ] **Step 6: Créer la fixture pytest partagée**

Create `engine/conftest.py` :

```python
"""Fixtures partagées pour les tests touchant la DB (comptes/profils/abonnements).

Nécessite DATABASE_URL_TEST (Postgres de test, voir docker-compose.yml service
`postgres-test`). Les tests qui en dépendent sont skip proprement si absent —
jamais d'échec bruyant faute de service démarré."""
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

DATABASE_URL_TEST = os.getenv("DATABASE_URL_TEST", "")


@pytest.fixture
def db_session():
    if not DATABASE_URL_TEST:
        pytest.skip("DATABASE_URL_TEST non configuré — tests DB ignorés.")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import db as db_module
    db_module.DATABASE_URL = DATABASE_URL_TEST
    db_module.DB_ENABLED = True
    db_module.engine = create_engine(DATABASE_URL_TEST)
    db_module.SessionLocal = sessionmaker(bind=db_module.engine, autoflush=False,
                                          autocommit=False)

    import models
    models.Base.metadata.create_all(db_module.engine)
    session = db_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()
        models.Base.metadata.drop_all(db_module.engine)
```

- [ ] **Step 7: Vérifier la fixture**

Run: `export DATABASE_URL_TEST="postgresql+psycopg://test:test@localhost:5433/portrait_cosmique_test"`
Run: `cd engine && python -m pytest test_db_flag.py -v` (ne doit pas être affecté)
Expected: toujours 2 passed (la fixture n'est pas encore utilisée par ce fichier).

- [ ] **Step 8: Commit**

```bash
git add models.py alembic.ini alembic/ engine/conftest.py
git commit -m "feat: modèles SQLAlchemy + migration initiale + fixture de test DB"
```

---

### Task 4: `auth.py` — lien magique + session

**Files:**
- Create: `auth.py`
- Test: `engine/test_auth.py`

**Interfaces:**
- Consumes: `models.Compte`, `models.LienMagique`, `models.Session` (Task 3), fixture `db_session` (Task 3).
- Produces: `auth.demander_lien(db, email) -> None`, `auth.verifier_lien(db, token) -> str | None` (renvoie le cookie signé ou None), `auth.compte_depuis_cookie(db, cookie) -> models.Compte | None`, `auth.deconnecter(db, cookie) -> None`, `auth.DUREE_SESSION_JOURS = 30`.

- [ ] **Step 1: Write failing tests**

Create `engine/test_auth.py` :

```python
"""Logique d'authentification par lien magique (pure, contre Postgres de test)."""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def test_demander_lien_cree_le_compte(db_session, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import auth
    import models
    auth.demander_lien(db_session, "test@example.com")
    compte = db_session.query(models.Compte).filter_by(email="test@example.com").first()
    assert compte is not None
    lien = db_session.query(models.LienMagique).filter_by(compte_id=compte.id).first()
    assert lien is not None
    assert lien.utilise_le is None


def test_verifier_lien_valide_cree_une_session(db_session, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import auth
    import models
    auth.demander_lien(db_session, "test2@example.com")
    lien = db_session.query(models.LienMagique).first()
    cookie = auth.verifier_lien(db_session, lien.token)
    assert cookie is not None
    compte = auth.compte_depuis_cookie(db_session, cookie)
    assert compte is not None
    assert compte.email == "test2@example.com"


def test_verifier_lien_deja_utilise_echoue(db_session, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import auth
    auth.demander_lien(db_session, "test3@example.com")
    import models
    lien = db_session.query(models.LienMagique).first()
    premier = auth.verifier_lien(db_session, lien.token)
    assert premier is not None
    second = auth.verifier_lien(db_session, lien.token)
    assert second is None


def test_verifier_lien_inconnu_echoue(db_session, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import auth
    assert auth.verifier_lien(db_session, "token-inexistant") is None


def test_compte_depuis_cookie_invalide_renvoie_none(db_session, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import auth
    assert auth.compte_depuis_cookie(db_session, "cookie-invalide") is None
    assert auth.compte_depuis_cookie(db_session, None) is None


def test_deconnecter_invalide_la_session(db_session, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import auth
    auth.demander_lien(db_session, "test4@example.com")
    import models
    lien = db_session.query(models.LienMagique).first()
    cookie = auth.verifier_lien(db_session, lien.token)
    auth.deconnecter(db_session, cookie)
    assert auth.compte_depuis_cookie(db_session, cookie) is None


def test_email_non_configure_logue_le_lien(db_session, monkeypatch, caplog):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    monkeypatch.delenv("EMAIL_SMTP_URL", raising=False)
    import importlib
    import auth
    importlib.reload(auth)
    with caplog.at_level("WARNING"):
        auth.demander_lien(db_session, "test5@example.com")
    assert any("test5@example.com" in r.message for r in caplog.records)
```

- [ ] **Step 2: Run to verify it fails**

Run: `export DATABASE_URL_TEST="postgresql+psycopg://test:test@localhost:5433/portrait_cosmique_test"`
Run: `cd engine && python -m pytest test_auth.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'auth'`).

- [ ] **Step 3: Implement `auth.py`**

Create `/auth.py` :

```python
"""Authentification par lien magique — création/vérification de tokens, sessions
signées, envoi d'email avec repli honnête (log si aucun service configuré)."""
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

import models

logger = logging.getLogger("portrait-cosmique.auth")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8410")
EMAIL_SMTP_URL = os.getenv("EMAIL_SMTP_URL", "")

DUREE_LIEN_MINUTES = 15
DUREE_SESSION_JOURS = 30


def _serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("SESSION_SECRET", "")
    if not secret:
        raise RuntimeError("SESSION_SECRET manquant (requis quand DATABASE_URL est configuré).")
    return URLSafeTimedSerializer(secret, salt="portrait-cosmique-session")


def demander_lien(db, email: str) -> None:
    """Crée le compte si besoin, génère un lien magique, l'envoie (ou le logue).

    Ne lève jamais pour un email invalide/inconnu (anti-énumération : l'appelant
    HTTP répond toujours 200 générique, voir comptes.py)."""
    email = (email or "").strip().lower()
    compte = db.query(models.Compte).filter_by(email=email).first()
    if compte is None:
        compte = models.Compte(email=email)
        db.add(compte)
        db.flush()
    token = secrets.token_urlsafe(32)
    lien = models.LienMagique(
        compte_id=compte.id, token=token,
        expire_le=datetime.now(timezone.utc) + timedelta(minutes=DUREE_LIEN_MINUTES))
    db.add(lien)
    db.commit()
    url = f"{BASE_URL}/auth/verifier?token={token}"
    _envoyer_lien(email, url)


def _envoyer_lien(email: str, url: str) -> None:
    """Envoie le lien par email si un service est configuré ; repli honnête sinon :
    le lien est loggé au lieu d'être envoyé (jamais un plantage ni un blocage)."""
    if not EMAIL_SMTP_URL:
        logger.warning(
            "EMAIL_SMTP_URL non configuré — lien de connexion pour %s : %s", email, url)
        return
    logger.warning(
        "EMAIL_SMTP_URL configuré mais l'envoi réel n'est pas câblé dans ce sprint "
        "— lien pour %s : %s", email, url)


def verifier_lien(db, token: str) -> str | None:
    """Consomme un lien magique valide, crée une session, renvoie le cookie signé
    (ou None si le lien est invalide, expiré ou déjà utilisé)."""
    lien = db.query(models.LienMagique).filter_by(token=token).first()
    maintenant = datetime.now(timezone.utc)
    if lien is None or lien.utilise_le is not None:
        return None
    expire_le = lien.expire_le
    if expire_le.tzinfo is None:
        expire_le = expire_le.replace(tzinfo=timezone.utc)
    if expire_le < maintenant:
        return None
    lien.utilise_le = maintenant
    session_token = secrets.token_urlsafe(32)
    session = models.Session(
        compte_id=lien.compte_id, token=session_token,
        expire_le=maintenant + timedelta(days=DUREE_SESSION_JOURS))
    db.add(session)
    db.commit()
    return _serializer().dumps(session_token)


def compte_depuis_cookie(db, cookie: str | None):
    """Résout le compte courant depuis le cookie de session, ou None si absent/invalide/expiré."""
    if not cookie:
        return None
    try:
        session_token = _serializer().loads(cookie, max_age=DUREE_SESSION_JOURS * 86400)
    except (BadSignature, SignatureExpired):
        return None
    session = db.query(models.Session).filter_by(token=session_token).first()
    if session is None:
        return None
    expire_le = session.expire_le
    if expire_le.tzinfo is None:
        expire_le = expire_le.replace(tzinfo=timezone.utc)
    if expire_le < datetime.now(timezone.utc):
        return None
    return db.query(models.Compte).filter_by(id=session.compte_id).first()


def deconnecter(db, cookie: str | None) -> None:
    """Invalide la session correspondant au cookie (no-op si absent/invalide)."""
    if not cookie:
        return
    try:
        session_token = _serializer().loads(cookie)
    except (BadSignature, SignatureExpired):
        return
    db.query(models.Session).filter_by(token=session_token).delete()
    db.commit()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd engine && python -m pytest test_auth.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add auth.py engine/test_auth.py
git commit -m "feat: authentification par lien magique (lien, session, repli email)"
```

---

### Task 5: Routeur `comptes.py` — auth endpoints + montage conditionnel

**Files:**
- Create: `comptes.py`
- Modify: `main.py`
- Test: `engine/test_comptes_api.py`

**Interfaces:**
- Consumes: `auth.*` (Task 4), `db.get_db`, `db.DB_ENABLED` (Task 2), `models.*` (Task 3).
- Produces: routeur FastAPI monté sur `app` uniquement si `db.DB_ENABLED`. Consommé par Task 6/7 (mêmes fichier `comptes.py`, endpoints ajoutés dans ces tâches).

- [ ] **Step 1: Write failing tests**

Create `engine/test_comptes_api.py` :

```python
"""Tests API du mode compte (/auth/*, /moi) — nécessite Postgres de test."""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _client_avec_db(db_session, monkeypatch):
    """App FastAPI reconstruite avec le mode compte actif (DB de test)."""
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import importlib

    import db as db_module
    importlib.reload(db_module)
    import main
    importlib.reload(main)
    from fastapi.testclient import TestClient
    return TestClient(main.app)


def test_demande_lien_repond_200_generique(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    r = client.post("/auth/demande-lien", json={"email": "a@example.com"})
    assert r.status_code == 200
    r2 = client.post("/auth/demande-lien", json={"email": "inconnu-jamais-vu@example.com"})
    assert r2.status_code == 200
    assert r.json() == r2.json()


def test_verifier_puis_moi(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    client.post("/auth/demande-lien", json={"email": "b@example.com"})
    import models
    lien = db_session.query(models.LienMagique).first()
    r = client.get(f"/auth/verifier?token={lien.token}")
    assert r.status_code == 200
    r_moi = client.get("/moi")
    assert r_moi.status_code == 200
    assert r_moi.json()["email"] == "b@example.com"
    assert r_moi.json()["abonnement_statut"] == "inactif"


def test_moi_sans_session_401(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    r = client.get("/moi")
    assert r.status_code == 401


def test_deconnexion_invalide_la_session(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    client.post("/auth/demande-lien", json={"email": "c@example.com"})
    import models
    lien = db_session.query(models.LienMagique).first()
    client.get(f"/auth/verifier?token={lien.token}")
    client.post("/auth/deconnexion")
    r = client.get("/moi")
    assert r.status_code == 401
```

- [ ] **Step 2: Run to verify it fails**

Run: `export DATABASE_URL_TEST="postgresql+psycopg://test:test@localhost:5433/portrait_cosmique_test"`
Run: `cd engine && python -m pytest test_comptes_api.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'comptes'`).

- [ ] **Step 3: Implement `comptes.py` (partie auth)**

Create `/comptes.py` :

```python
"""Routes compte — montées dans main.py uniquement si db.DB_ENABLED."""
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

import auth
import db
import models

router = APIRouter()

COOKIE_NOM = "pc_session"


class DemandeLienBody(BaseModel):
    email: str


def compte_courant(pc_session: str | None = Cookie(None),
                    bd: DbSession = Depends(db.get_db)) -> models.Compte:
    compte = auth.compte_depuis_cookie(bd, pc_session)
    if compte is None:
        raise HTTPException(401, "Non connecté.")
    return compte


@router.post("/auth/demande-lien")
def demande_lien(body: DemandeLienBody, bd: DbSession = Depends(db.get_db)):
    email = (body.email or "").strip()
    if email:
        auth.demander_lien(bd, email)
    return {"statut": "ok"}


@router.get("/auth/verifier")
def verifier(token: str, response: Response, bd: DbSession = Depends(db.get_db)):
    cookie = auth.verifier_lien(bd, token)
    if cookie is None:
        raise HTTPException(400, "Lien invalide, expiré ou déjà utilisé.")
    response.set_cookie(COOKIE_NOM, cookie, httponly=True, samesite="lax",
                         max_age=auth.DUREE_SESSION_JOURS * 86400)
    return {"statut": "connecté"}


@router.post("/auth/deconnexion")
def deconnexion(response: Response, pc_session: str | None = Cookie(None),
                 bd: DbSession = Depends(db.get_db)):
    auth.deconnecter(bd, pc_session)
    response.delete_cookie(COOKIE_NOM)
    return {"statut": "déconnecté"}


@router.get("/moi")
def moi(compte: models.Compte = Depends(compte_courant), bd: DbSession = Depends(db.get_db)):
    ab = bd.query(models.Abonnement).filter_by(compte_id=compte.id).first()
    return {"email": compte.email, "abonnement_statut": ab.statut if ab else "inactif"}
```

- [ ] **Step 4: Monter le routeur dans `main.py`**

Dans `main.py`, après `import llm` (ligne 32), ajouter :

```python
import db

if db.DB_ENABLED:
    import comptes
```

Après la ligne `app.add_middleware(CORSMiddleware, ...)` (ligne 37), ajouter :

```python
if db.DB_ENABLED:
    app.include_router(comptes.router)
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd engine && python -m pytest test_comptes_api.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add comptes.py main.py engine/test_comptes_api.py
git commit -m "feat: routes /auth/* + /moi, montage conditionnel sur DB_ENABLED"
```

---

### Task 6: Endpoints `/profils` — CRUD + règle des 4 suivis actifs

**Files:**
- Modify: `comptes.py`
- Modify: `engine/test_comptes_api.py`

**Interfaces:**
- Consumes: `compte_courant`, `db.get_db`, `models.ProfilNatal`, `models.Abonnement`, `models.MAX_SUIVIS_ACTIFS` (Tasks 3/5).
- Produces: `GET/POST /profils`, `PATCH/DELETE /profils/{id}`, `POST /profils/import-local`.

- [ ] **Step 1: Write failing tests**

Append à `engine/test_comptes_api.py` :

```python
def _connecte(client, db_session, email):
    import models
    client.post("/auth/demande-lien", json={"email": email})
    lien = db_session.query(models.LienMagique).filter(
        models.LienMagique.compte_id == db_session.query(models.Compte)
        .filter_by(email=email).first().id).order_by(models.LienMagique.expire_le.desc()).first()
    client.get(f"/auth/verifier?token={lien.token}")


_PROFIL = {"label": "Moi", "prenoms": "Jean", "nom": "Dupont",
           "date_naissance": "1990-01-15", "heure_naissance": "14:30",
           "ville": "Toulouse", "latitude": 43.6, "longitude": 1.44,
           "utc_offset": 1.0, "systeme_numerologie": "classique"}


def test_creer_et_lister_profils(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    _connecte(client, db_session, "d@example.com")
    r = client.post("/profils", json=_PROFIL)
    assert r.status_code == 200
    assert r.json()["suivi_actif"] is False
    r_liste = client.get("/profils")
    assert len(r_liste.json()) == 1


def test_creation_profils_illimitee(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    _connecte(client, db_session, "e@example.com")
    for i in range(6):
        r = client.post("/profils", json={**_PROFIL, "label": f"Profil {i}"})
        assert r.status_code == 200
    assert len(client.get("/profils").json()) == 6


def test_activer_suivi_sans_abonnement_402(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    _connecte(client, db_session, "f@example.com")
    profil = client.post("/profils", json=_PROFIL).json()
    r = client.patch(f"/profils/{profil['id']}", json={"suivi_actif": True})
    assert r.status_code == 402


def test_limite_4_suivis_actifs(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    _connecte(client, db_session, "g@example.com")
    import models
    compte = db_session.query(models.Compte).filter_by(email="g@example.com").first()
    db_session.add(models.Abonnement(compte_id=compte.id, statut="actif"))
    db_session.commit()
    ids = []
    for i in range(5):
        p = client.post("/profils", json={**_PROFIL, "label": f"P{i}"}).json()
        ids.append(p["id"])
    for pid in ids[:4]:
        r = client.patch(f"/profils/{pid}", json={"suivi_actif": True})
        assert r.status_code == 200
    r5 = client.patch(f"/profils/{ids[4]}", json={"suivi_actif": True})
    assert r5.status_code == 402


def test_supprimer_profil(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    _connecte(client, db_session, "h@example.com")
    p = client.post("/profils", json=_PROFIL).json()
    r = client.delete(f"/profils/{p['id']}")
    assert r.status_code == 200
    assert client.get("/profils").json() == []


def test_import_local(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    _connecte(client, db_session, "i@example.com")
    r = client.post("/profils/import-local", json=[_PROFIL, {**_PROFIL, "label": "Autre"}])
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert len(client.get("/profils").json()) == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd engine && python -m pytest test_comptes_api.py -v`
Expected: FAIL (404 sur `/profils`, routes pas encore définies).

- [ ] **Step 3: Ajouter les endpoints dans `comptes.py`**

Ajouter à la fin de `comptes.py` :

```python
class ProfilBody(BaseModel):
    label: str = ""
    prenoms: str = ""
    nom: str = ""
    date_naissance: str = ""
    heure_naissance: str | None = None
    ville: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    utc_offset: float | None = None
    systeme_numerologie: str = "classique"


class ProfilPatchBody(BaseModel):
    label: str | None = None
    prenoms: str | None = None
    nom: str | None = None
    date_naissance: str | None = None
    heure_naissance: str | None = None
    ville: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    utc_offset: float | None = None
    systeme_numerologie: str | None = None
    suivi_actif: bool | None = None


def _profil_json(p: "models.ProfilNatal") -> dict:
    return {"id": p.id, "label": p.label, "prenoms": p.prenoms, "nom": p.nom,
            "date_naissance": p.date_naissance, "heure_naissance": p.heure_naissance,
            "ville": p.ville, "latitude": p.latitude, "longitude": p.longitude,
            "utc_offset": p.utc_offset, "systeme_numerologie": p.systeme_numerologie,
            "suivi_actif": p.suivi_actif}


@router.get("/profils")
def lister_profils(compte: models.Compte = Depends(compte_courant),
                    bd: DbSession = Depends(db.get_db)):
    profils = bd.query(models.ProfilNatal).filter_by(compte_id=compte.id).all()
    return [_profil_json(p) for p in profils]


@router.post("/profils")
def creer_profil(body: ProfilBody, compte: models.Compte = Depends(compte_courant),
                  bd: DbSession = Depends(db.get_db)):
    p = models.ProfilNatal(compte_id=compte.id, **body.model_dump())
    bd.add(p)
    bd.commit()
    return _profil_json(p)


@router.patch("/profils/{profil_id}")
def modifier_profil(profil_id: str, body: ProfilPatchBody,
                     compte: models.Compte = Depends(compte_courant),
                     bd: DbSession = Depends(db.get_db)):
    p = bd.query(models.ProfilNatal).filter_by(id=profil_id, compte_id=compte.id).first()
    if p is None:
        raise HTTPException(404, "Profil introuvable.")
    donnees = body.model_dump(exclude_unset=True)
    if donnees.get("suivi_actif") is True and not p.suivi_actif:
        ab = bd.query(models.Abonnement).filter_by(compte_id=compte.id).first()
        if ab is None or ab.statut != "actif":
            raise HTTPException(402, "Abonnement requis pour activer le suivi quotidien.")
        nb_actifs = bd.query(models.ProfilNatal).filter_by(
            compte_id=compte.id, suivi_actif=True).count()
        if nb_actifs >= models.MAX_SUIVIS_ACTIFS:
            raise HTTPException(402, f"Limite de {models.MAX_SUIVIS_ACTIFS} suivis actifs atteinte.")
    for cle, val in donnees.items():
        setattr(p, cle, val)
    bd.commit()
    return _profil_json(p)


@router.delete("/profils/{profil_id}")
def supprimer_profil(profil_id: str, compte: models.Compte = Depends(compte_courant),
                      bd: DbSession = Depends(db.get_db)):
    p = bd.query(models.ProfilNatal).filter_by(id=profil_id, compte_id=compte.id).first()
    if p is None:
        raise HTTPException(404, "Profil introuvable.")
    bd.delete(p)
    bd.commit()
    return {"statut": "supprimé"}


@router.post("/profils/import-local")
def importer_profils(profils: list[ProfilBody],
                      compte: models.Compte = Depends(compte_courant),
                      bd: DbSession = Depends(db.get_db)):
    crees = []
    for body in profils:
        p = models.ProfilNatal(compte_id=compte.id, **body.model_dump())
        bd.add(p)
        crees.append(p)
    bd.commit()
    return [_profil_json(p) for p in crees]
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd engine && python -m pytest test_comptes_api.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add comptes.py engine/test_comptes_api.py
git commit -m "feat: CRUD /profils + règle des 4 suivis actifs + import localStorage"
```

---

### Task 7: `/stats` + incrément du compteur dans `/portrait`

**Files:**
- Modify: `comptes.py`
- Modify: `main.py`
- Test: `engine/test_comptes_api.py`, `engine/test_api_theme.py`

**Interfaces:**
- Consumes: `models.CompteurPortraits`, `db.SessionLocal`, `db.DB_ENABLED`.
- Produces: `GET /stats` (public), incrément best-effort appelé depuis `/portrait`.

- [ ] **Step 1: Write failing tests**

Append à `engine/test_comptes_api.py` :

```python
def test_stats_public_sans_session(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    r = client.get("/stats")
    assert r.status_code == 200
    assert r.json() == {"portraits_calcules": 0}


def test_stats_incremente_par_portrait(db_session, monkeypatch):
    client = _client_avec_db(db_session, monkeypatch)
    fiche = {"prenoms": "T", "nom": "U", "date_naissance": "2000-01-01"}
    client.post("/portrait", json=fiche)
    client.post("/portrait", json=fiche)
    r = client.get("/stats")
    assert r.json()["portraits_calcules"] == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd engine && python -m pytest test_comptes_api.py -v -k stats`
Expected: FAIL (404 sur `/stats`, ou `portraits_calcules` reste à 0).

- [ ] **Step 3: Ajouter `/stats` dans `comptes.py`**

Ajouter à la fin de `comptes.py` :

```python
@router.get("/stats")
def stats(bd: DbSession = Depends(db.get_db)):
    c = bd.query(models.CompteurPortraits).filter_by(id=1).first()
    return {"portraits_calcules": c.total if c else 0}
```

- [ ] **Step 4: Ajouter l'incrément dans `main.py`**

Dans `main.py`, après le bloc `if db.DB_ENABLED: import comptes` (ajouté en Task 5), ajouter la fonction d'incrément :

```python
def _incrementer_compteur_portraits() -> None:
    """Best-effort : n'échoue jamais le calcul du portrait si la DB est indisponible."""
    if not db.DB_ENABLED:
        return
    import comptes as _c  # noqa: F401 — s'assure que les modèles sont importés
    import models
    try:
        with db.SessionLocal() as s:
            c = s.query(models.CompteurPortraits).filter_by(id=1).first()
            if c is None:
                c = models.CompteurPortraits(id=1, total=0)
                s.add(c)
            c.total += 1
            s.commit()
    except Exception:  # noqa: BLE001 — repli honnête, jamais bloquant
        import logging
        logging.getLogger("portrait-cosmique").warning(
            "compteur_portraits : incrément échoué (non bloquant)")
```

Dans la fonction `portrait(body: Fiche)` (ligne ~126), ajouter en première ligne du corps :

```python
def portrait(body: Fiche):
    """Fiche → traditions calculées → portrait (stats/archétype/forces/faiblesse/pierre/
    récit) → empreinte lisible. Étendu : inclut désormais `theme_complet` intégré
    pour que le récit déterministe et l'empreinte exploitent les nouvelles données."""
    _incrementer_compteur_portraits()
    trad = traditions.calculer(body.model_dump())
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd engine && python -m pytest test_comptes_api.py test_api_theme.py -v`
Expected: tous passent (les tests existants de `test_api_theme.py` ne sont pas affectés : `DATABASE_URL` absent dans leur contexte d'exécution normal → `_incrementer_compteur_portraits()` est un no-op immédiat).

- [ ] **Step 6: Commit**

```bash
git add comptes.py main.py engine/test_comptes_api.py
git commit -m "feat: /stats public + compteur de portraits calculés (best-effort)"
```

---

### Task 8: `scripts/toggle_abonnement.py`

**Files:**
- Create: `scripts/toggle_abonnement.py`
- Test: `engine/test_toggle_abonnement.py`

**Interfaces:**
- Consumes: `db.DB_ENABLED`, `db.SessionLocal`, `models.Compte`, `models.Abonnement`.
- Produces: `toggle_abonnement.toggle(email: str, statut: str) -> None` (importable et testable directement, en plus de l'usage CLI).

- [ ] **Step 1: Write failing test**

Create `engine/test_toggle_abonnement.py` :

```python
"""CLI dev/admin de bascule d'abonnement (simule un futur webhook Stripe)."""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def test_toggle_active_un_abonnement(db_session, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import auth
    import models
    auth.demander_lien(db_session, "j@example.com")

    import toggle_abonnement
    toggle_abonnement.toggle("j@example.com", "actif")

    ab = db_session.query(models.Abonnement).join(models.Compte).filter(
        models.Compte.email == "j@example.com").first()
    assert ab is not None
    assert ab.statut == "actif"


def test_toggle_compte_inconnu_leve(db_session, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import toggle_abonnement
    try:
        toggle_abonnement.toggle("jamais-vu@example.com", "actif")
        assert False, "devrait lever SystemExit"
    except SystemExit:
        pass


def test_toggle_statut_invalide_leve(db_session, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    import auth
    auth.demander_lien(db_session, "k@example.com")
    import toggle_abonnement
    try:
        toggle_abonnement.toggle("k@example.com", "gold-vip")
        assert False, "devrait lever SystemExit"
    except SystemExit:
        pass
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd engine && python -m pytest test_toggle_abonnement.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'toggle_abonnement'`).

- [ ] **Step 3: Implement `scripts/toggle_abonnement.py`**

Create `/scripts/toggle_abonnement.py` :

```python
#!/usr/bin/env python3
"""CLI dev/admin : simule ce qu'un futur webhook Stripe écrirait dans `abonnements`.

Usage : python scripts/toggle_abonnement.py --email x@y.com --statut actif

Aucun SDK Stripe ici — ce script existe uniquement pour tester la logique métier
(règle des 4 suivis actifs, blocage 402) sans attendre l'intégration Stripe réelle."""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import models

STATUTS_VALIDES = {"inactif", "actif", "essai", "annule"}


def toggle(email: str, statut: str) -> None:
    if not db.DB_ENABLED:
        raise SystemExit("DATABASE_URL non configuré — ce script nécessite une DB.")
    if statut not in STATUTS_VALIDES:
        raise SystemExit(
            f"Statut invalide : {statut} (attendu : {', '.join(sorted(STATUTS_VALIDES))})")
    with db.SessionLocal() as s:
        compte = s.query(models.Compte).filter_by(email=email).first()
        if compte is None:
            raise SystemExit(f"Aucun compte pour {email}.")
        ab = s.query(models.Abonnement).filter_by(compte_id=compte.id).first()
        if ab is None:
            ab = models.Abonnement(compte_id=compte.id)
            s.add(ab)
        ab.statut = statut
        ab.maj_le = datetime.now(timezone.utc)
        s.commit()
    print(f"Abonnement de {email} → {statut}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--statut", required=True, choices=sorted(STATUTS_VALIDES))
    args = parser.parse_args()
    toggle(args.email, args.statut)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd engine && python -m pytest test_toggle_abonnement.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/toggle_abonnement.py engine/test_toggle_abonnement.py
git commit -m "feat: script CLI toggle_abonnement (prêt pour un futur webhook Stripe)"
```

---

### Task 9: Feature-flag OFF, Dockerfile, README

**Files:**
- Modify: `Dockerfile`
- Modify: `README.md`, `README.en.md`
- Test: `engine/test_db_flag.py`

**Interfaces:**
- Consumes: tout ce qui précède.
- Produces: comportement final vérifié quand `DATABASE_URL` est absent (cas par défaut, self-hébergement).

- [ ] **Step 1: Write failing test**

Append à `engine/test_db_flag.py` :

```python
def test_routes_compte_absentes_sans_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import importlib
    import db
    importlib.reload(db)
    import main
    importlib.reload(main)
    from fastapi.testclient import TestClient
    client = TestClient(main.app)

    assert client.get("/moi").status_code == 404
    assert client.post("/auth/demande-lien", json={"email": "x@y.com"}).status_code == 404
    assert client.get("/profils").status_code == 404

    r = client.post("/portrait", json={"prenoms": "T", "nom": "U",
                                        "date_naissance": "2000-01-01"})
    assert r.status_code == 200
    assert "portrait" in r.json()
```

- [ ] **Step 2: Run to verify it fails or passes**

Run: `unset DATABASE_URL_TEST; cd engine && python -m pytest test_db_flag.py -v`
Expected: si les tâches précédentes sont correctement implémentées, ce test **passe déjà** (le montage conditionnel de Task 5 garantit ce comportement). C'est un test de non-régression explicite, pas une nouvelle fonctionnalité — s'il échoue, corriger le montage conditionnel dans `main.py` (Task 5, Step 4) avant de continuer.

- [ ] **Step 3: Mettre à jour le `Dockerfile`**

Remplacer la ligne `COPY main.py llm.py ./` par :

```dockerfile
COPY main.py llm.py db.py models.py auth.py comptes.py ./
```

- [ ] **Step 4: Vérifier l'image Docker**

Run: `docker compose build`
Run: `docker compose up -d`
Run: `curl http://localhost:8410/sante`
Expected: `{"statut":"ok",...}` — inchangé, aucune variable DB configurée dans `docker-compose.yml` par défaut.
Run: `docker compose down`

- [ ] **Step 5: Documenter le mode compte dans le README**

Ajouter dans `README.md`, après la section « Ce que tu obtiens » :

```markdown
## Mode compte (optionnel)

Par défaut, cette instance reste 100 % stateless : aucune donnée n'est conservée,
comme décrit plus haut. Un mode compte optionnel existe pour qui veut sauvegarder
ses profils natals côté serveur (lien magique par email, pas de mot de passe) : il
s'active en renseignant `DATABASE_URL` (PostgreSQL) — voir `.env.example`. Sans
cette variable, rien ne change : pas de DB, pas de compte, pas de route `/auth/*`.
```

Ajouter l'équivalent anglais dans `README.en.md`.

- [ ] **Step 6: Run full test suite**

Run: `export DATABASE_URL_TEST="postgresql+psycopg://test:test@localhost:5433/portrait_cosmique_test"`
Run: `cd engine && python -m pytest -q`
Expected: tous les tests passent (existants + nouveaux).

- [ ] **Step 7: Commit**

```bash
git add Dockerfile README.md README.en.md engine/test_db_flag.py
git commit -m "feat: mode compte prêt en Docker + doc README + non-régression flag OFF"
```

---

## Self-Review

**Spec coverage :**
- DB optionnelle par `DATABASE_URL` → Task 2, vérifié end-to-end Task 9.
- 6 tables du modèle de données → Task 3.
- Règle des 4 suivis actifs + abonnement requis → Task 6.
- Flux lien magique (demande, vérification, repli email) → Task 4, exposé en API Task 5.
- Endpoints `/auth/*`, `/moi`, `/profils/*`, `/stats` → Tasks 5-7.
- Prêt pour Stripe sans Stripe (script CLI) → Task 8.
- Import localStorage → Task 6 (`/profils/import-local`).
- Cas aux limites (DB absente, lien expiré/utilisé, email non configuré, 402, import vide) → couverts respectivement Tasks 9/2, 4, 4, 6, 6 (liste vide → boucle no-op, déjà correct sans code supplémentaire).
- Tests contre Postgres de test, jamais de mock ORM → fixture `db_session` (Task 3), utilisée partout.

**Placeholder scan :** aucun TBD/TODO ; chaque étape de code contient l'implémentation complète, pas de renvoi à « voir Task N ».

**Type consistency :** `_profil_json()` (Task 6) et le schéma `ProfilBody`/`ProfilPatchBody` utilisent les mêmes noms de champs que `models.ProfilNatal` (Task 3) et que la structure `portrait-cosmique-profils` du localStorage existant (`prenoms, nom, date_naissance, heure_naissance, ville, latitude, longitude, utc_offset, systeme_numerologie`) — cohérent avec le format d'import (Task 6, `/profils/import-local`). `MAX_SUIVIS_ACTIFS` défini une fois dans `models.py` (Task 3), réutilisé tel quel dans `comptes.py` (Task 6) sans redéfinition locale.

No gaps found. Plan complete.
