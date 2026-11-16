"""
Gestion de l'OTP (code de vérification) côté application ADITUS.
Module pur (sans Streamlit) : génération, stockage sécurisé (hash) et vérification.
Le code en clair n'est jamais conservé : seul son hash SHA-256 est stocké en session.
"""

import hashlib
import secrets
import time

OTP_LONGUEUR = 6
OTP_VALIDITE_SECONDES = 600  # 10 minutes
OTP_MAX_TENTATIVES = 5


def generer_code_otp() -> str:
    """Génère un code numérique de OTP_LONGUEUR chiffres (zéros initiaux possibles)."""
    return f"{secrets.randbelow(10 ** OTP_LONGUEUR):0{OTP_LONGUEUR}d}"


def hacher_code(code: str) -> str:
    """Retourne le hash SHA-256 du code saisi (normalisé)."""
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def generer_otp() -> tuple[str, dict]:
    """
    Génère un nouvel OTP.
    Retourne (code_en_clair, record) : le code en clair est destiné à l'envoi par e-mail,
    le record (hash + expiration + tentatives) est celui stocké en session.
    """
    code = generer_code_otp()
    record = {
        "hash": hacher_code(code),
        "expire_le": time.time() + OTP_VALIDITE_SECONDES,
        "tentatives": 0,
    }
    return code, record


def verifier_otp(saisie: str, record: dict) -> tuple[bool, str]:
    """
    Vérifie un code saisi contre le record stocké.
    Retourne (succès, raison) avec raison parmi : "ok", "expired", "too_many", "wrong", "missing".
    Incrémente le compteur de tentatives à chaque essai.
    """
    if not record:
        return False, "missing"
    if time.time() > record.get("expire_le", 0):
        return False, "expired"
    if record.get("tentatives", 0) >= OTP_MAX_TENTATIVES:
        return False, "too_many"
    record["tentatives"] = record.get("tentatives", 0) + 1
    if hacher_code(saisie) == record.get("hash"):
        return True, "ok"
    return False, "wrong"
