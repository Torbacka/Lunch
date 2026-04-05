# Technology Stack

**Analysis Date:** 2026-04-05

## Languages

**Primary:**
- Python 3.x - All application code, cloud functions, and service modules

## Runtime

**Environment:**
- Google Cloud Functions (serverless deployment)

**Package Manager:**
- pip - Python package management
- Lockfile: `requirements.txt` present

## Frameworks

**Core:**
- Flask 1.0.2 - Lightweight web framework for HTTP endpoints and local development server

**HTTP/Networking:**
- requests 2.21.0 - HTTP client library for API calls to external services

## Key Dependencies

**Critical:**
- pymongo 3.7.2 - MongoDB client for database operations, core data persistence
- Flask 1.0.2 - Web framework for routing and request handling
- requests 2.21.0 - HTTP client for Slack API and Google Places API calls

**Infrastructure:**
- Click 7.0 - Command-line interface creation framework (indirect Flask dependency)
- Jinja2 2.10.1 - Template engine (Flask dependency)
- Werkzeug 0.15.3 - WSGI utilities (Flask dependency)
- certifi 2019.3.9 - SSL/TLS certificate verification

**Async & Networking:**
- async-timeout 3.0.1 - Timeout management for async operations
- yarl 1.3.0 - URL parsing and manipulation
- multidict 4.5.2 - Multivalue dictionary implementation
- dnspython 1.16.0 - DNS toolkit
- pycares 3.0.0 - Async DNS resolver
- aiohttp (implied dependency) - Async HTTP client

## Configuration

**Environment:**
- Environment variables required (not hardcoded):
  - `MONGO_PASSWORD` - MongoDB authentication
  - `SLACK_TOKEN` - Slack API token for user operations
  - `BOT_TOKEN` - Slack bot token for messaging
  - `PLACES_PASSWORD` - Google Places API key

**Build:**
- No build configuration detected
- Deployment via Google Cloud Functions CLI (`gcloud`)

## Platform Requirements

**Development:**
- Python 3.x (tested with 3.12.6)
- virtualenv for local environment isolation
- pip for dependency installation

**Production:**
- Google Cloud Functions
- MongoDB Atlas cluster with replica set
- Slack workspace with bot integration
- Google Places API enabled

---

*Stack analysis: 2026-04-05*
