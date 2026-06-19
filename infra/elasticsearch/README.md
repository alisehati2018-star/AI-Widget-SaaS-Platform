# Elasticsearch (Phase 0)

Phase 0 stands up a **secure, healthy** single-node Elasticsearch 9.2+ cluster
on the free tier (REQ-M1-001/003/008). That is the entire Phase-0 scope for the
search spine.

**Explicitly NOT in Phase 0** (these are Phase 1 / M2, and live under
`infra/elasticsearch/` when built):
- the custom Persian analyzer (`fa_text` / `fa_search`, ZWNJ, normalization)
- the catalogue index template + mappings (`dense_vector` `bbq_disk`, etc.)
- index aliases and the zero-downtime reindex flow

See Appendix A of the blueprint for the reference analyzer/mapping that Phase 1
will implement.

## Bring-up

```bash
cp .env.example .env            # then set ES_PASSWORD etc. (never commit .env)
docker compose -f infra/docker-compose.yml up -d elasticsearch kibana
python infra/scripts/verify_cluster.py
```

## Production hardening (documented now, enforced in M12/Phase 3)

- CA-verified TLS on transport + HTTP (REQ-M1-003) — dev uses the bundled
  single-node security; production mounts real certs.
- Snapshots/backups with tested restore + DR objectives (REQ-M12-005).
- Cluster + model servers kept off the public network (REQ-M1-009).
