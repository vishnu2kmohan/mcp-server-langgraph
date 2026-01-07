# Prompt Quality Alert Runbook

This runbook provides troubleshooting guidance for prompt validation and quality alerts in the MCP Server LangGraph system.

## Overview

Prompt quality alerts monitor LLM output validation, parse errors, and usage patterns. These alerts help detect prompt drift, LLM provider issues, and output format problems.

## Symptoms

When these alerts fire, you may observe:
- High prompt validation failure rates
- JSON parse errors in LLM responses
- Missing or invalid fields in structured outputs
- Sudden drops in prompt usage

---

## PromptValidationFailureRateHigh

### Description
Prompt validation failure rate exceeds 10% over 5 minutes.

### Impact
**Warning** - LLM outputs may not meet quality standards.

### Resolution
1. Check `prompt_validation_failure_total` by failure_type label
2. Review recent prompt changes in configuration
3. Check LLM provider status and response quality
4. Verify prompt templates are correctly formatted

### Escalation
Notify AI/ML team during business hours.

---

## PromptValidationFailureRateCritical

### Description
Prompt validation failure rate exceeds 25% over 5 minutes.

### Impact
**Critical** - Significant portion of LLM outputs are failing validation.

### Resolution
1. Check if LLM provider is returning valid responses
2. Consider enabling fallback responses
3. Review recent deployments for prompt changes
4. Check LLM model version and configuration

### Escalation
Page on-call immediately. This is a P1 incident.

---

## PromptSpecificValidationFailing

### Description
A specific prompt has validation failure rate above 20%.

### Impact
**Warning** - Individual prompt quality is degraded.

### Resolution
1. Identify the failing prompt from `prompt_name` label
2. Review the prompt's output format instructions
3. Check for schema changes affecting this prompt
4. Test the prompt in isolation

### Escalation
Notify prompt owner or AI team.

---

## PromptParseErrorRateHigh

### Description
JSON parse errors occurring at high rate in prompt responses.

### Impact
**Warning** - LLM may be returning malformed JSON or markdown-wrapped responses.

### Resolution
1. Check LLM response format in logs
2. Verify markdown code block stripping in validation
3. Review LLM temperature and output format settings
4. Check for model changes affecting JSON output

### Escalation
Create ticket for AI team investigation.

---

## PromptSpecificParseErrors

### Description
A specific prompt is experiencing parse errors.

### Impact
**Warning** - Individual prompt has formatting issues.

### Resolution
1. Review the prompt's output format instructions
2. Add explicit JSON format requirements to prompt
3. Increase output format constraints in prompt template
4. Consider adding response sanitization

### Escalation
Notify prompt owner.

---

## PromptUsageAbsent

### Description
No prompt usage metrics received for 10 minutes.

### Impact
**Warning** - Service may not be processing any prompts.

### Resolution
1. Check service health and pod status: `kubectl get pods -l app=mcp-server-langgraph`
2. Verify Prometheus scrape configuration
3. Check metrics endpoint availability: `curl localhost:8000/metrics`
4. Review application logs for errors

### Escalation
Page on-call if service is down.

---

## PromptUsageDrop

### Description
Prompt usage dropped by more than 50% compared to hourly baseline.

### Impact
**Warning** - May indicate service degradation or traffic shift.

### Resolution
1. Check for upstream traffic changes
2. Verify load balancer health
3. Review recent deployments
4. Check for circuit breaker activations

### Escalation
Notify on-call for investigation.

---

## PromptConstraintViolationsHigh

### Description
High rate of constraint violations in prompt outputs (e.g., confidence > 1.0).

### Impact
**Warning** - LLM outputs violating schema constraints.

### Resolution
1. Review prompt instructions for value range clarity
2. Add explicit constraints to prompt template
3. Check if LLM model change affected output quality
4. Consider adding post-processing validation

### Escalation
Notify AI team for prompt improvement.

---

## PromptMissingFieldsHigh

### Description
High rate of missing fields in prompt outputs.

### Impact
**Warning** - LLM outputs are incomplete.

### Resolution
1. Review prompt output format instructions
2. Add explicit required field list to prompt
3. Check for prompt template corruption
4. Verify LLM model is following instructions

### Escalation
Create ticket for prompt review.

---

## PromptInvalidEnumValuesHigh

### Description
High rate of invalid enum values in prompt outputs.

### Impact
**Warning** - LLM producing values outside allowed sets.

### Resolution
1. Ensure prompts list all valid enum values explicitly
2. Add examples of valid values to prompt
3. Consider adding enum validation post-processing
4. Review if new enum values need to be added

### Escalation
Notify prompt owner for template update.
