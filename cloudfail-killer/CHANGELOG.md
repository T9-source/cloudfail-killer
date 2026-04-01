# Changelog

All notable changes to CloudFail-Killer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.6.0] - 2026-04-01

### Added
- GitHub Actions CI/CD pipeline (lint, type-check, security, test, build, Docker)
- PyPI publishing workflow with automated releases
- Multi-arch Docker support (amd64 + arm64) with docker-compose
- Comprehensive README with badges, architecture diagram, CLI reference
- Full CONTRIBUTING guide with source/exporter development instructions
- SECURITY.md with responsible disclosure policy
- CHANGELOG.md for version tracking
- 317 tests covering unit, integration, and benchmark suites

## [0.5.0] - 2026-04-01

### Added
- Full pipeline integration tests (source → enrichment → active → export)
- IPv6 integration tests (SourceResult, EnrichedResult, Cache, Exporters)
- Performance benchmarks (object creation, serialization, filtering, scoring, export)

### Changed
- Updated test framework with conftest.py shared fixtures
- All tests passing (317 total)

## [0.4.0] - 2026-03-31

### Added
- Active HTTP/TCP probing with response comparison
- Host Header Injection probe (10 proxy + 8 origin indicators)
- SQLite cache with campaign history and IP discovery timeline (7-day TTL)
- Webhook notifications (Slack, Discord, Generic with auto-detection)
- PDF export with cover page, summary, tables (ReportLab)
- Nuclei YAML template + target list export
- JSON, CSV, Markdown export modules

### Changed
- Runner pipeline: Collection → Enrichment → Active → Host Header → Cache → Webhook → Export

## [0.3.0] - 2026-03-30

### Added
- 6-stage enrichment pipeline (SSL → ASN → JS → Scoring → FP Filter → Dedup)
- SSL Certificate Checker with wildcard support
- ASN Lookup (15+ hosting providers)
- JS Recon Engine (12 regex patterns)
- Multi-signal confidence scoring (0-100) with profile weights
- False Positive Filter (CDN/WAF/honeypot detection)
- Result deduplication

## [0.2.0] - 2026-03-29

### Added
- 13 passive data source plugins
- Favicon MurmurHash3 computation (Shodan/Censys query builders)
- Dual-stack DNS resolver (A + AAAA)
- Source registry with enable/disable

## [0.1.0] - 2026-03-28

### Added
- Async HTTP engine with httpx (HTTP/2, IPv6, retry, rate limiting)
- SourceRunner with concurrent execution
- Cloudflare IP range checker (v4 + v6)
- Stealth module (UA rotation, delays, Tor)
- 5 scan profiles with scoring weights
- Initial CLI (Typer + Rich)

## [0.0.1] - 2026-03-27

### Added
- Project foundation (pyproject.toml, MIT license, structure)
- Plugin architecture (BaseSource abstract class)
- Configuration system (Pydantic)
- SourceResult and EnrichedResult data models
