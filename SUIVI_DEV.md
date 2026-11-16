# SUIVI_DEV — ADITUS (Portail GNC-PASS)

## 2026-11-16 — OTP par Brevo + contournement RLS (service_role)

### Objectif
Remplacer l'envoi du code OTP par le SMTP de Supabase (défaillant : « Error sending magic link email »)
par un envoi via Brevo, et corriger les blocages RLS (code 42501) apparus quand l'app n'ouvre plus
de session Supabase authentifiée.

### Décisions prises
- OTP généré localement (6 chiffres) ; seul le hash SHA-256 est stocké en session,
  validité 10 minutes, 5 tentatives max (`services/otp.py`).
- Envoi du code par Brevo (`envoyer_email_otp` dans `services/mailer.py`).
- Toutes les requêtes métier (lectures + écritures) passent par le client `supabase_admin`
  (clé `service_role`) : la RLS est contournée côté serveur uniquement ; l'accès reste protégé
  par l'OTP et les rôles vérifiés en session.
- Le cache des clients Supabase est indexé sur une empreinte de la clé (invalidation auto si la clé change).
- La validation d'une demande vérifie désormais que la ligne a bien été modifiée (évite les faux succès).

### Fichiers modifiés
- `services/otp.py` (nouveau)
- `services/mailer.py` : `envoyer_email_otp`, robustesse de `_get_brevo_api_instance`
- `services/auth.py` : connexion OTP Brevo, vérification locale du code
- `services/db.py` : empreinte de clé dans le cache, avertissement si clé service absente
- `views/*.py` : requêtes sur `supabase_admin`
- `config.py` : version v1.1.1

### Tests exécutés
- `py_compile` sur app / services / views : OK
- Tests unitaires `services/otp.py` (format 6 chiffres, hash, expiration, 5 tentatives, mauvais code) : OK
- `envoyer_email_otp` sans clé API : retour propre `False` (pas de crash)
- PATCH manuel `statut = Validé` via API REST (service_role) : OK, confirmé en base

### Tests non réalisés
- Parcours complet Streamlit en conditions réelles après redémarrage du process
  (à refaire : nouvelle demande → validation depuis l'Espace Valideur → statut « Validé » en base)

### Problèmes connus
- `SUPABASE_SERVICE_KEY` (clé `sb_secret_...`, service_role) doit être présente dans
  `.streamlit/secrets.toml` ; sinon le client admin retombe sur la clé anon (avertissement affiché).
- Toute valeur de secret exposée dans une conversation doit être révoquée
  (clé API Brevo, mot de passe d'application Gmail, etc.).

### Prochaine action
- Valider le flux complet en local, puis merger la branche `fix/otp-brevo-service-role` via PR.
