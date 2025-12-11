# [Alert Name] Runbook

## Overview

Brief description of what this runbook covers.

---

## [Alert Name]

### Alert Definition
```yaml
alert: AlertName
expr: <prometheus_query>
for: <duration>
severity: <critical|warning|info>
```

### Severity
**[CRITICAL|WARNING|INFO]** - [Response time expectation]

### Impact
- First impact
- Second impact
- Third impact

### Diagnosis

1. **First diagnostic step**
   ```bash
   # Command or query
   ```

2. **Second diagnostic step**
   ```promql
   # Prometheus query
   ```

3. **Third diagnostic step**
   - Check this
   - Verify that

### Resolution

1. **If condition A**
   - Step 1
   - Step 2
   ```bash
   # Command to fix
   ```

2. **If condition B**
   - Step 1
   - Step 2

3. **If condition C**
   - Step 1
   - Step 2

### Escalation
- **On-call SRE**: [Contact channel]
- **Team Owner**: [Contact info]

---

## Template Usage

1. Copy this template to `monitoring/runbooks/`
2. Replace all placeholders in `[]`
3. Add specific diagnostic steps and commands
4. Include relevant Prometheus queries
5. Document escalation paths

### Severity Guidelines

| Severity | Response Time | Examples |
|----------|--------------|----------|
| Critical | Immediate | Service down, SLA breach |
| Warning | 30 minutes | Performance degradation |
| Info | Next business day | Capacity planning |

### Best Practices

- Include specific commands that can be copy-pasted
- Add relevant Grafana dashboard links
- Include rollback procedures where applicable
- Keep runbooks up-to-date after incidents
- Review and update quarterly
