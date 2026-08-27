# Data Migration Plan: Synthetic to Live Operational Data

**Date:** 2026-07-26  
**Status:** DRAFT — Pending Phase 5 Completion  
**Scope:** Transitioning Helix Education from synthetic test data to live Helix Prime operational streams.

---

## 1. Migration Strategy

The migration will follow a **Dual-Write / Shadow Mode** approach to ensure zero downtime and data integrity during the transition.

### Phase A: Schema Validation

- Verify that live Helix Prime events (from TMK Loop) match the Avro schemas defined in `api_layer/assessment_event_schema.avsc`.
- Run validation scripts against a 7-day sample of live production data.

### Phase B: Historical Backfill

- Extract historical assessment and competency data from Helix Prime's PostgreSQL database.
- Transform and load into Helix Education's EventStore (`events.jsonl`) using the `state_core` mutators.
- **Target:** 90 days of historical data for ML model retraining.

### Phase C: Live Stream Integration

- Switch the `CognitiveAgent` grounding source from `StubGroundingClient` to `HttpGroundingClient` pointing to the live TMK Loop API.
- Enable dual-write mode: assessments are scored locally but also sent to the Prime Metacognitive Memory for cross-validation.

---

## 2. Data Mapping

| Helix Prime Source | Helix Education Target | Transformation Logic |
| --- | --- | --- |
| `wfm_forecasting_events` | `progress_engine.milestones` | Map FTE variance to "Forecasting Proficiency" |
| `rta_adherence_logs` | `quiz_engine.sessions` | Convert adherence gaps into "RTA Compliance" quiz items |
| `cx_churn_scores` | `analytics_engine.kpis` | Direct mapping for Closed-Loop Analytics correlation |
| `b2b_sop_versions` | `content_engine.lessons` | Parse SOP markdown into lesson sections with citations |

---

## 3. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
| --- | --- | --- | --- |
| **Data Volume Overload** | Medium | High | Implement batch processing for historical backfill; use Kafka for live stream buffering. |
| **Schema Mismatch** | Low | High | Automated schema registry checks in CI/CD pipeline before migration start. |
| **Performance Degradation** | Medium | Medium | Monitor P99 latency via Prometheus; auto-scale Kubernetes pods if CPU > 70%. |

---

## 4. Rollback Plan

If critical errors are detected during Phase C:

1. **Switch Grounding Source:** Revert `CognitiveAgent` to `StubGroundingClient`.
2. **Disable Dual-Write:** Stop sending assessment results to Prime Metacognitive Memory.
3. **Restore Snapshot:** Use the pre-migration backup of `events.jsonl` and `sealed_keys.jsonl`.

---

## 5. Success Criteria

- [ ] 90 days of historical data successfully backfilled with <1% error rate.
- [ ] Live TMK Loop events processed with <100ms latency.
- [ ] Closed-Loop Analytics showing statistically significant correlations (p < 0.05) within 30 days.
