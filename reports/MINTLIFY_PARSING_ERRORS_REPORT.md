# Mintlify Documentation Parsing Error Report

Generated: comprehensive_mintlify_check.py

```
====================================================================================================
MINTLIFY DOCUMENTATION PARSING ERROR REPORT
====================================================================================================

SUMMARY STATISTICS
----------------------------------------------------------------------------------------------------
Files scanned:       279
Files with issues:   47
Total issues found:  97
Read errors:         0

ISSUES BY SEVERITY
----------------------------------------------------------------------------------------------------
CRITICAL       10 issues
HIGH           18 issues
MEDIUM         69 issues

ISSUES BY TYPE
----------------------------------------------------------------------------------------------------
placeholder_tag                  69 issues
unclosed_html_tag                18 issues
unclosed_jsx_component           10 issues

DETAILED ISSUES BY FILE
====================================================================================================


.github/COMPLIANCE_PHASE1_SUMMARY.md
----------------------------------------------------------------------------------------------------
  🟡 Line   31 [placeholder_tag          ] Placeholder tag <token> should be escaped or use backticks: `<token>`
       Fix: Escape as `<token>`


.github/CONTRIBUTING.md
----------------------------------------------------------------------------------------------------
  🟡 Line  274 [placeholder_tag          ] Placeholder tag <type> should be escaped or use backticks: `<type>`
       Fix: Escape as `<type>`
  🟡 Line  274 [placeholder_tag          ] Placeholder tag <scope> should be escaped or use backticks: `<scope>`
       Fix: Escape as `<scope>`
  🟡 Line  274 [placeholder_tag          ] Placeholder tag <subject> should be escaped or use backticks: `<subject>`
       Fix: Escape as `<subject>`
  🟡 Line  276 [placeholder_tag          ] Placeholder tag <body> should be escaped or use backticks: `<body>`
       Fix: Escape as `<body>`
  🟡 Line  278 [placeholder_tag          ] Placeholder tag <footer> should be escaped or use backticks: `<footer>`
       Fix: Escape as `<footer>`


.venv/lib/python3.12/site-packages/litellm/anthropic_interface/readme.md
----------------------------------------------------------------------------------------------------
  🟡 Line   80 [placeholder_tag          ] Placeholder tag <Tabs> should be escaped or use backticks: `<Tabs>`
       Fix: Escape as `<Tabs>`
  🔴 Line   80 [unclosed_jsx_component   ] JSX component <Tabs> opened 1 times but closed 0 times
       Fix: Add closing tag </Tabs>
  🟠 Line   81 [unclosed_html_tag        ] Tag <TabItem> opened 2 times but closed 1 times


.venv/lib/python3.12/site-packages/litellm/integrations/bitbucket/README.md
----------------------------------------------------------------------------------------------------
  🟡 Line  259 [placeholder_tag          ] Placeholder tag <base_model> should be escaped or use backticks: `<base_model>`
       Fix: Escape as `<base_model>`


.venv/lib/python3.12/site-packages/litellm/integrations/gitlab/README.md
----------------------------------------------------------------------------------------------------
  🟡 Line   60 [placeholder_tag          ] Placeholder tag <repo_name> should be escaped or use backticks: `<repo_name>`
       Fix: Escape as `<repo_name>`
  🟡 Line  259 [placeholder_tag          ] Placeholder tag <base_model> should be escaped or use backticks: `<base_model>`
       Fix: Escape as `<base_model>`


.venv/lib/python3.12/site-packages/litellm/proxy/client/cli/README.md
----------------------------------------------------------------------------------------------------
  🟡 Line  137 [placeholder_tag          ] Placeholder tag <regex> should be escaped or use backticks: `<regex>`
       Fix: Escape as `<regex>`
  🟡 Line  362 [placeholder_tag          ] Placeholder tag <model> should be escaped or use backticks: `<model>`
       Fix: Escape as `<model>`
  🟡 Line  412 [placeholder_tag          ] Placeholder tag <method> should be escaped or use backticks: `<method>`
       Fix: Escape as `<method>`
  🟡 Line  412 [placeholder_tag          ] Placeholder tag <uri> should be escaped or use backticks: `<uri>`
       Fix: Escape as `<uri>`


.venv/lib/python3.12/site-packages/temporalio/bridge/sdk-core/AGENTS.md
----------------------------------------------------------------------------------------------------
  🟡 Line   77 [placeholder_tag          ] Placeholder tag <workflow_id> should be escaped or use backticks: `<workflow_id>`
       Fix: Escape as `<workflow_id>`


CHANGELOG.md
----------------------------------------------------------------------------------------------------
  🟠 Line  417 [unclosed_html_tag        ] Tag <500ms> opened 1 times but closed 0 times


docs/DEPENDENCY_MANAGEMENT.md
----------------------------------------------------------------------------------------------------
  🟡 Line  140 [placeholder_tag          ] Placeholder tag <package> should be escaped or use backticks: `<package>`
       Fix: Escape as `<package>`
  🟡 Line  140 [placeholder_tag          ] Placeholder tag <version> should be escaped or use backticks: `<version>`
       Fix: Escape as `<version>`
  🟡 Line  297 [placeholder_tag          ] Placeholder tag <issue> should be escaped or use backticks: `<issue>`
       Fix: Escape as `<issue>`


docs/PYDANTIC_AI_INTEGRATION.md
----------------------------------------------------------------------------------------------------
  🟠 Line  401 [unclosed_html_tag        ] Tag <5ms> opened 1 times but closed 0 times


docs/SLA_OPERATIONS_RUNBOOK.md
----------------------------------------------------------------------------------------------------
  🟠 Line   44 [unclosed_html_tag        ] Tag <500ms> opened 1 times but closed 0 times
  🟠 Line  216 [unclosed_html_tag        ] Tag <EOF> opened 1 times but closed 0 times
       Fix: Remove <<EOF or escape heredoc syntax
  🟡 Line  469 [placeholder_tag          ] Placeholder tag <dependency> should be escaped or use backticks: `<dependency>`
       Fix: Escape as `<dependency>`
  🟡 Line  469 [placeholder_tag          ] Placeholder tag <port> should be escaped or use backticks: `<port>`
       Fix: Escape as `<port>`


docs/adr/0007-authentication-provider-pattern.md
----------------------------------------------------------------------------------------------------
  🟡 Line   64 [placeholder_tag          ] Placeholder tag <secret> should be escaped or use backticks: `<secret>`
       Fix: Escape as `<secret>`


docs/advanced/contributing.mdx
----------------------------------------------------------------------------------------------------
  🟡 Line  362 [placeholder_tag          ] Placeholder tag <type> should be escaped or use backticks: `<type>`
       Fix: Escape as `<type>`
  🟡 Line  362 [placeholder_tag          ] Placeholder tag <description> should be escaped or use backticks: `<description>`
       Fix: Escape as `<description>`


docs/advanced/testing.mdx
----------------------------------------------------------------------------------------------------
  🟡 Line  680 [placeholder_tag          ] Placeholder tag <script> should be escaped or use backticks: `<script>`
       Fix: Escape as `<script>`


docs/advanced/troubleshooting.mdx
----------------------------------------------------------------------------------------------------
  🟡 Line  455 [placeholder_tag          ] Placeholder tag <blocking_pid> should be escaped or use backticks: `<blocking_pid>`
       Fix: Escape as `<blocking_pid>`
  🟡 Line  887 [placeholder_tag          ] Placeholder tag <username> should be escaped or use backticks: `<username>`
       Fix: Escape as `<username>`
  🟡 Line  888 [placeholder_tag          ] Placeholder tag <password> should be escaped or use backticks: `<password>`
       Fix: Escape as `<password>`
  🟡 Line  889 [placeholder_tag          ] Placeholder tag <email> should be escaped or use backticks: `<email>`
       Fix: Escape as `<email>`


docs/architecture/adr-0007-authentication-provider-pattern.mdx
----------------------------------------------------------------------------------------------------
  🟡 Line   69 [placeholder_tag          ] Placeholder tag <secret> should be escaped or use backticks: `<secret>`
       Fix: Escape as `<secret>`


docs/deployment/kong-gateway.mdx
----------------------------------------------------------------------------------------------------
  🟠 Line  243 [unclosed_html_tag        ] Tag <EOF> opened 4 times but closed 0 times
       Fix: Remove <<EOF or escape heredoc syntax


docs/deployment/kubernetes.md
----------------------------------------------------------------------------------------------------
  🟠 Line  331 [unclosed_html_tag        ] Tag <EOF> opened 2 times but closed 0 times
       Fix: Remove <<EOF or escape heredoc syntax


docs/deployment/kubernetes.mdx
----------------------------------------------------------------------------------------------------
  🟠 Line  190 [unclosed_html_tag        ] Tag <EOF> opened 2 times but closed 0 times
       Fix: Remove <<EOF or escape heredoc syntax


docs/deployment/kubernetes/aks.mdx
----------------------------------------------------------------------------------------------------
  🟠 Line  369 [unclosed_html_tag        ] Tag <EOF> opened 1 times but closed 0 times
       Fix: Remove <<EOF or escape heredoc syntax


docs/deployment/kubernetes/eks.mdx
----------------------------------------------------------------------------------------------------
  🟠 Line  147 [unclosed_html_tag        ] Tag <EOF> opened 1 times but closed 0 times
       Fix: Remove <<EOF or escape heredoc syntax


docs/deployment/kubernetes/gke.mdx
----------------------------------------------------------------------------------------------------
  🟠 Line  313 [unclosed_html_tag        ] Tag <EOF> opened 1 times but closed 0 times
       Fix: Remove <<EOF or escape heredoc syntax


docs/deployment/monitoring.mdx
----------------------------------------------------------------------------------------------------
  🟠 Line  302 [unclosed_html_tag        ] Tag <EOF> opened 1 times but closed 0 times
       Fix: Remove <<EOF or escape heredoc syntax


docs/development/ci-cd.md
----------------------------------------------------------------------------------------------------
  🟡 Line  594 [placeholder_tag          ] Placeholder tag <key> should be escaped or use backticks: `<key>`
       Fix: Escape as `<key>`
  🟡 Line  595 [placeholder_tag          ] Placeholder tag <secret> should be escaped or use backticks: `<secret>`
       Fix: Escape as `<secret>`
  🟡 Line  596 [placeholder_tag          ] Placeholder tag <password> should be escaped or use backticks: `<password>`
       Fix: Escape as `<password>`
  🟡 Line  600 [placeholder_tag          ] Placeholder tag <id> should be escaped or use backticks: `<id>`
       Fix: Escape as `<id>`


docs/integrations/litellm.md
----------------------------------------------------------------------------------------------------
  🟡 Line  203 [placeholder_tag          ] Placeholder tag <tag> should be escaped or use backticks: `<tag>`
       Fix: Escape as `<tag>`


docs/reference/pydantic-ai.md
----------------------------------------------------------------------------------------------------
  🟠 Line  261 [unclosed_html_tag        ] Tag <5ms> opened 1 times but closed 0 times


docs/reports/archive/2025-10/CI_STATUS_UPDATE.md
----------------------------------------------------------------------------------------------------
  🟡 Line  106 [placeholder_tag          ] Placeholder tag <RUN_ID> should be escaped or use backticks: `<RUN_ID>`
       Fix: Escape as `<RUN_ID>`


docs/reports/archive/2025-10/DEPENDABOT_REBASE_STATUS.md
----------------------------------------------------------------------------------------------------
  🟡 Line  282 [placeholder_tag          ] Placeholder tag <RUN_ID> should be escaped or use backticks: `<RUN_ID>`
       Fix: Escape as `<RUN_ID>`


docs/reports/archive/2025-10/DEPENDABOT_SESSION_2025-10-13.md
----------------------------------------------------------------------------------------------------
  🟡 Line  258 [placeholder_tag          ] Placeholder tag <number> should be escaped or use backticks: `<number>`
       Fix: Escape as `<number>`


docs/reports/archive/2025-10/DEPENDENCY_AUDIT_REPORT_20251013.md
----------------------------------------------------------------------------------------------------
  🟡 Line  229 [placeholder_tag          ] Placeholder tag <package> should be escaped or use backticks: `<package>`
       Fix: Escape as `<package>`
  🟡 Line  229 [placeholder_tag          ] Placeholder tag <version> should be escaped or use backticks: `<version>`
       Fix: Escape as `<version>`


docs/reports/archive/2025-10/FINAL_SESSION_STATUS.md
----------------------------------------------------------------------------------------------------
  🟡 Line  321 [placeholder_tag          ] Placeholder tag <ID> should be escaped or use backticks: `<ID>`
       Fix: Escape as `<ID>`


docs/reports/archive/2025-10/LANGGRAPH_UPGRADE_ASSESSMENT.md
----------------------------------------------------------------------------------------------------
  🟠 Line   55 [unclosed_html_tag        ] Tag <class> opened 1 times but closed 0 times


docs/reports/archive/2025-10/MINTLIFY_QUICKSTART_20251013.md
----------------------------------------------------------------------------------------------------
  🟡 Line  167 [placeholder_tag          ] Placeholder tag <CardGroup> should be escaped or use backticks: `<CardGroup>`
       Fix: Escape as `<CardGroup>`
  🟡 Line  167 [placeholder_tag          ] Placeholder tag <Card> should be escaped or use backticks: `<Card>`
       Fix: Escape as `<Card>`
  🔴 Line  167 [unclosed_jsx_component   ] JSX component <Card> opened 1 times but closed 0 times
       Fix: Add closing tag </Card>
  🔴 Line  167 [unclosed_jsx_component   ] JSX component <CardGroup> opened 1 times but closed 0 times
       Fix: Add closing tag </CardGroup>
  🟡 Line  168 [placeholder_tag          ] Placeholder tag <Accordion> should be escaped or use backticks: `<Accordion>`
       Fix: Escape as `<Accordion>`
  🟡 Line  168 [placeholder_tag          ] Placeholder tag <AccordionGroup> should be escaped or use backticks: `<AccordionGroup>`
       Fix: Escape as `<AccordionGroup>`
  🔴 Line  168 [unclosed_jsx_component   ] JSX component <Accordion> opened 1 times but closed 0 times
       Fix: Add closing tag </Accordion>
  🔴 Line  168 [unclosed_jsx_component   ] JSX component <AccordionGroup> opened 1 times but closed 0 times
       Fix: Add closing tag </AccordionGroup>
  🟡 Line  169 [placeholder_tag          ] Placeholder tag <Tabs> should be escaped or use backticks: `<Tabs>`
       Fix: Escape as `<Tabs>`
  🟡 Line  169 [placeholder_tag          ] Placeholder tag <Tab> should be escaped or use backticks: `<Tab>`
       Fix: Escape as `<Tab>`
  🔴 Line  169 [unclosed_jsx_component   ] JSX component <Tabs> opened 1 times but closed 0 times
       Fix: Add closing tag </Tabs>
  🔴 Line  169 [unclosed_jsx_component   ] JSX component <Tab> opened 1 times but closed 0 times
       Fix: Add closing tag </Tab>
  🟡 Line  170 [placeholder_tag          ] Placeholder tag <Steps> should be escaped or use backticks: `<Steps>`
       Fix: Escape as `<Steps>`
  🟡 Line  170 [placeholder_tag          ] Placeholder tag <Step> should be escaped or use backticks: `<Step>`
       Fix: Escape as `<Step>`
  🔴 Line  170 [unclosed_jsx_component   ] JSX component <Steps> opened 1 times but closed 0 times
       Fix: Add closing tag </Steps>
  🔴 Line  170 [unclosed_jsx_component   ] JSX component <Step> opened 1 times but closed 0 times
       Fix: Add closing tag </Step>
  🟡 Line  171 [placeholder_tag          ] Placeholder tag <CodeGroup> should be escaped or use backticks: `<CodeGroup>`
       Fix: Escape as `<CodeGroup>`
  🔴 Line  171 [unclosed_jsx_component   ] JSX component <CodeGroup> opened 1 times but closed 0 times
       Fix: Add closing tag </CodeGroup>


docs/reports/archive/2025-10/NEXT_STEPS.md
----------------------------------------------------------------------------------------------------
  🟠 Line  265 [unclosed_html_tag        ] Tag <2> opened 1 times but closed 0 times


docs/reports/archive/2025-10/REBASE_COMPLETION_TRACKER.md
----------------------------------------------------------------------------------------------------
  🟡 Line  106 [placeholder_tag          ] Placeholder tag <NEW_RUN_ID> should be escaped or use backticks: `<NEW_RUN_ID>`
       Fix: Escape as `<NEW_RUN_ID>`
  🟡 Line  142 [placeholder_tag          ] Placeholder tag <module> should be escaped or use backticks: `<module>`
       Fix: Escape as `<module>`


docs/reports/archive/2025-10/TEST_FAILURE_ROOT_CAUSE.md
----------------------------------------------------------------------------------------------------
  🟡 Line   56 [placeholder_tag          ] Placeholder tag <module> should be escaped or use backticks: `<module>`
       Fix: Escape as `<module>`
  🟡 Line  484 [placeholder_tag          ] Placeholder tag <RUN_ID> should be escaped or use backticks: `<RUN_ID>`
       Fix: Escape as `<RUN_ID>`


docs/reports/archive/DEPENDABOT_MERGE_STATUS.md
----------------------------------------------------------------------------------------------------
  🟡 Line  267 [placeholder_tag          ] Placeholder tag <package> should be escaped or use backticks: `<package>`
       Fix: Escape as `<package>`
  🟡 Line  267 [placeholder_tag          ] Placeholder tag <version> should be escaped or use backticks: `<version>`
       Fix: Escape as `<version>`
  🟡 Line  267 [placeholder_tag          ] Placeholder tag <issue> should be escaped or use backticks: `<issue>`
       Fix: Escape as `<issue>`


docs/runbooks/README.md
----------------------------------------------------------------------------------------------------
  🟡 Line   49 [placeholder_tag          ] Placeholder tag <component> should be escaped or use backticks: `<component>`
       Fix: Escape as `<component>`
  🟡 Line   55 [placeholder_tag          ] Placeholder tag <command> should be escaped or use backticks: `<command>`
       Fix: Escape as `<command>`
  🟡 Line   58 [placeholder_tag          ] Placeholder tag <service> should be escaped or use backticks: `<service>`
       Fix: Escape as `<service>`
  🟡 Line   77 [placeholder_tag          ] Placeholder tag <key> should be escaped or use backticks: `<key>`
       Fix: Escape as `<key>`
  🟡 Line   96 [placeholder_tag          ] Placeholder tag <promql> should be escaped or use backticks: `<promql>`
       Fix: Escape as `<promql>`


docs/runbooks/keycloak-slow.md
----------------------------------------------------------------------------------------------------
  🟡 Line  189 [placeholder_tag          ] Placeholder tag <secret> should be escaped or use backticks: `<secret>`
       Fix: Escape as `<secret>`


docs/runbooks/keycloak-token-refresh.md
----------------------------------------------------------------------------------------------------
  🟡 Line  214 [placeholder_tag          ] Placeholder tag <token> should be escaped or use backticks: `<token>`
       Fix: Escape as `<token>`
  🟡 Line  220 [placeholder_tag          ] Placeholder tag <secret> should be escaped or use backticks: `<secret>`
       Fix: Escape as `<secret>`


docs/runbooks/redis-down.md
----------------------------------------------------------------------------------------------------
  🟡 Line  149 [placeholder_tag          ] Placeholder tag <password> should be escaped or use backticks: `<password>`
       Fix: Escape as `<password>`


docs/runbooks/session-errors.md
----------------------------------------------------------------------------------------------------
  🟡 Line   93 [placeholder_tag          ] Placeholder tag <token> should be escaped or use backticks: `<token>`
       Fix: Escape as `<token>`
  🟡 Line  175 [placeholder_tag          ] Placeholder tag <password> should be escaped or use backticks: `<password>`
       Fix: Escape as `<password>`


docs/runbooks/session-ttl.md
----------------------------------------------------------------------------------------------------
  🟡 Line   98 [placeholder_tag          ] Placeholder tag <token> should be escaped or use backticks: `<token>`
       Fix: Escape as `<token>`


docs/security/compliance.mdx
----------------------------------------------------------------------------------------------------
  🟡 Line  617 [placeholder_tag          ] Placeholder tag <script> should be escaped or use backticks: `<script>`
       Fix: Escape as `<script>`


monitoring/grafana/dashboards/README.md
----------------------------------------------------------------------------------------------------
  🟠 Line   80 [unclosed_html_tag        ] Tag <500ms> opened 1 times but closed 0 times


monitoring/prometheus/alerts/README.md
----------------------------------------------------------------------------------------------------
  🟠 Line   25 [unclosed_html_tag        ] Tag <2> opened 1 times but closed 0 times


tests/README.md
----------------------------------------------------------------------------------------------------
  🟠 Line   28 [unclosed_html_tag        ] Tag <5> opened 1 times but closed 0 times

```
