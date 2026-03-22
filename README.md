# 🔍 NetWatch — Surveillance Réseau

Application de surveillance réseau en temps réel.

![Docker](https://img.shields.io/badge/Docker-✓-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)

## 🚀 Démarrage rapide

```bash
docker-compose up --build
```

Ouvre `http://localhost:5000` → `admin / Admin@2024!`

## 📦 Stack

- **Flask 3.0** · **PostgreSQL 15** · **Redis 7**
- **Flask-SocketIO** — alertes temps réel
- **ping3** — ICMP natif + fallback TCP
- **Docker Compose** — réseau bridge `netwatch_network`

## 🐳 Docker Hub

```bash
docker pull sudoman2/netwatch:latest
```

## ✨ Fonctionnalités

- Surveillance ICMP/TCP de tous les équipements
- Alertes en temps réel (panne, rétablissement, latence élevée)
- Historique et graphe de latence par équipement
- Centre d'alertes avec niveaux de sévérité
- Gestion des utilisateurs (admin / opérateur)
- Pipeline CI/CD GitHub Actions → Docker Hub
