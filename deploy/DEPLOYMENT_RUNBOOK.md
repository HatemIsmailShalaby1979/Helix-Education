# Helix Education L&D Engine — Production Deployment Runbook

**Version:** 1.0.0  
**Last Updated:** 2026-07-26  
**Owner:** DevOps / SRE Team  
**Risk Level:** HIGH — Requires coordination with Helix Prime operational engines.

---

## 1. Pre-Deployment Checklist

Before initiating the deployment, ensure the following conditions are met:

- [ ] **Security Audit:** Formal penetration test completed with zero critical/high vulnerabilities.
- [ ] **Secrets Management:** `helix-secrets` Kubernetes secret created with `kms-master-key`.
- [ ] **Infrastructure:** Kubernetes cluster (3+ nodes) and PostgreSQL database are online and healthy.
- [ ] **Data Backup:** Full backup of current synthetic data in `events.jsonl` and `sealed_keys.jsonl`.
- [ ] **Governance Approval:** DEC-2026-XXX (Production Deployment) approved in `DECISION_LOG.md`.

---

## 2. Deployment Sequence

### Step 1: Apply Persistent Volume Claim

Ensure the event store has durable storage before launching pods.

```bash
kubectl apply -f deploy/k8s/pvc.yaml -n helix-prime
```

### Step 2: Deploy Core Engine

Apply the main deployment and service manifests.

```bash
kubectl apply -f deploy/k8s/deployment.yaml -n helix-prime
```

### Step 3: Verify Pod Health

Wait for all 3 replicas to reach `Running` state.

```bash
kubectl get pods -l app=helix-education -n helix-prime -w
```

### Step 4: Validate Observability

Check that the `/metrics` endpoint is responding and Prometheus is scraping data.

```bash
kubectl port-forward svc/helix-education-service 8000:80 -n helix-prime
curl http://localhost:8000/metrics
```

---

## 3. Data Migration Execution

Follow the `DATA_MIGRATION_PLAN.md` to transition to live data.

1. **Schema Validation:** Run `python scripts/validate_live_schema.py` against the TMK Loop API.
2. **Historical Backfill:** Execute `python scripts/backfill_historical_data.py --days 90`.
3. **Live Stream Switch:** Update the `CognitiveAgent` configuration to point to the production TMK endpoint.

---

## 4. Post-Deployment Validation

Perform these checks within 1 hour of deployment:

- [ ] **Latency Check:** P99 API latency is < 500ms under normal load.
- [ ] **Encryption Check:** Verify new answer keys in `sealed_keys.jsonl` are ciphertext.
- [ ] **Integration Check:** Confirm WILI Dashboard is receiving real-time gap patterns from Helix Prime.
- [ ] **Analytics Check:** Verify Closed-Loop Analytics engine is ingesting operational KPIs.

---

## 5. Rollback Procedure

If critical failures occur during or after deployment:

1. **Stop Live Stream:** Revert `CognitiveAgent` to `StubGroundingClient` via ConfigMap update.
2. **Scale Down:** Reduce Helix Education replicas to 0 to stop processing.

   ```bash
   kubectl scale deployment helix-education-engine --replicas=0 -n helix-prime
   ```

3. **Restore Data:** Replace `events.jsonl` with the pre-deployment backup.
4. **Revert Manifests:** Apply the previous stable version of `deployment.yaml`.

---

## 6. Emergency Contacts

| Role | Name | Contact |
| --- | --- | --- |
| **SRE Lead** | [Name] | [Slack/Phone] |
| **Tech Lead** | [Name] | [Slack/Phone] |
| **Security Officer** | [Name] | [Slack/Phone] |

---

## End of Runbook
