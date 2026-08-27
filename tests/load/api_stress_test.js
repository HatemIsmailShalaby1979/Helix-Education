/**
 * Helix Education API Load Test
 * 
 * Simulates 1000 concurrent users interacting with the Education Center API.
 * Targets: Quiz submission, Metrics retrieval, and Content generation.
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency_ms');

// Performance Thresholds (Phase 4 Acceptance Criteria)
export const options = {
  stages: [
    { duration: '30s', target: 200 },  // Ramp up to 200 users
    { duration: '1m', target: 500 },   // Stay at 500 users
    { duration: '30s', target: 1000 }, // Spike to 1000 users
    { duration: '1m', target: 1000 },  // Sustained load
    { duration: '30s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests must complete below 500ms
    http_req_failed: ['rate<0.01'],   // Error rate must be less than 1%
    errors: ['rate<0.05'],            // Custom error rate < 5%
    api_latency_ms: ['avg<200'],      // Average custom latency < 200ms
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // 1. Get Metrics (Read-heavy operation)
  let res = http.get(`${BASE_URL}/metrics`);
  const checkRes = check(res, {
    'metrics endpoint is up': (r) => r.status === 200,
    'metrics response time < 100ms': (r) => r.timings.duration < 100,
  });
  errorRate.add(!checkRes);
  apiLatency.add(res.timings.duration);

  sleep(1);

  // 2. Simulate Quiz Submission (Write-heavy operation)
  // Note: In a real test, we would use dynamic session IDs from a setup phase
  const payload = JSON.stringify({
    session_id: `test-session-${Math.floor(Math.random() * 1000)}`,
    quiz_item_id: 'item-001',
    raw_answer: 'The primary purpose of event sourcing is auditability and determinism.',
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  res = http.post(`${BASE_URL}/api/v1/quiz/submit`, payload, params);
  check(res, {
    'quiz submission successful': (r) => r.status === 200 || r.status === 201,
  });
  errorRate.add(res.status !== 200 && res.status !== 201);
  apiLatency.add(res.timings.duration);

  sleep(2);
}
