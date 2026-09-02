# Dailymobile

Plateforme de vente et réparation d'appareils électroniques (Douala).

## Stack

- Python 3.12
- Django 6.1
- PostgreSQL 18
- Django REST Framework

## Prérequis

- Python 3.12+
- PostgreSQL avec la base `dailymobile_test` et le rôle `dailymobile_app`
- Schéma SQL chargé (`schema_v1_3.sql`)

## Installation

```bash
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt