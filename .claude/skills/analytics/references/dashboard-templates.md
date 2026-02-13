# Dashboard Templates & Command Insights Reference

Command-specific insight templates, full dashboard layout, and success criteria for the `/analytics` skill.

---

## Full Dashboard Template

Use this box-drawn format for the comprehensive dashboard output:

```
+==================================================================+
|              WORKFLOW ANALYTICS DASHBOARD                         |
|              Last 30 Days | Auto-Generated                       |
+==================================================================+
|  COMMAND USAGE STATISTICS                                        |
+==================================================================+
|  Total Commands Used:      {total}                               |
|  Unique Commands:          {unique}                              |
|  Most Used:                {most_used}                           |
|  Highest Value:            {highest_value}                       |
|  Total Time Saved:         {total_saved}                         |
+==================================================================+
|  TOP 10 COMMANDS BY VALUE                                        |
+==================================================================+
|  1. {cmd}  {uses} uses | {saved} saved | {per_use} min/use      |
|  ...                                                             |
+==================================================================+
|  RETURN ON INVESTMENT (ROI)                                      |
+==================================================================+
|  Investment:               {investment} (one-time)               |
|  Return (30 days):         {return}                              |
|  ROI:                      {roi_ratio}                           |
|  Break-Even:               {status}                              |
|                                                                  |
|  Projected Annual:         {annual_saved}                        |
|  Work Weeks Saved:         {weeks_saved}                         |
|  Annualized ROI:           {annual_roi}                          |
+==================================================================+
|  DEVELOPMENT VELOCITY                                            |
+==================================================================+
|  Commits (30d):            {commits}                             |
|  Contributors:             {contributors}                        |
|  Files Changed:            {files}                               |
|  Lines Added:              {added}                               |
|  Lines Removed:            {removed}                             |
|  Net Change:               {net}                                 |
|  Avg Commits/Day:          {avg}                                 |
+==================================================================+
|  QUALITY METRICS                                                 |
+==================================================================+
|  Test Pass Rate:           {pass_rate}                           |
|  Test Coverage:            {coverage}                            |
|  Mypy Strict Modules:      {mypy}                               |
|  Open TODOs:               {todos}                               |
|  Documentation:            {docs}                                |
+==================================================================+
|  EFFICIENCY GAINS (vs baseline)                                  |
+==================================================================+
|  Sprint Setup:             {sprint_gain}                         |
|  Context Loading:          {context_gain}                        |
|  Test Analysis:            {test_gain}                           |
|  ADR Creation:             {adr_gain}                            |
|  Coverage Analysis:        {coverage_gain}                       |
|  Debugging:                {debug_gain}                          |
|  Deployment:               {deploy_gain}                         |
|  Overall:                  {overall_gain}                        |
+==================================================================+
|  RECOMMENDATIONS                                                 |
+==================================================================+
|  High Impact:                                                    |
|    - {rec_1}                                                     |
|    - {rec_2}                                                     |
|    - {rec_3}                                                     |
|                                                                  |
|  Watch:                                                          |
|    - {watch_1}                                                   |
|    - {watch_2}                                                   |
|                                                                  |
|  Celebrate:                                                      |
|    - {celebrate_1}                                               |
|    - {celebrate_2}                                               |
|    - {celebrate_3}                                               |
+==================================================================+
```

---

## Step 6: Command-Specific Insights

For top commands, provide insights:

```
-------------------------------------------------------------------
  COMMAND INSIGHTS
-------------------------------------------------------------------

  /test-summary (Most Used)
  -----------------------------------------------------------------
  Uses: 45 times (16% of all commands)
  Pattern: Used before commits and PRs (good practice!)
  Value: 3.8 hours saved
  Recommendation: Continue using before every commit

  /create-adr (Highest Value)
  -----------------------------------------------------------------
  Uses: 12 times (saves 40 min each!)
  Pattern: Used for major decisions
  Value: 8.0 hours saved
  Opportunity: Use for all architectural decisions
  Potential: Could use 2-3x more often

  /quick-debug (Best ROI)
  -----------------------------------------------------------------
  Uses: 38 times
  Pattern: First response to errors (excellent!)
  Value: 7.6 hours saved (12 min per use)
  Recommendation: Keep as primary debugging tool

-------------------------------------------------------------------
```

### Insight Template

For each top command, generate an insight block:

```
  /{command_name} ({label})
  -----------------------------------------------------------------
  Uses: {count} times ({percentage}% of all commands)
  Pattern: {usage_pattern}
  Value: {hours_saved} hours saved
  Recommendation: {recommendation}
```

Labels to assign based on ranking:
- **Most Used**: Highest usage count
- **Highest Value**: Highest time saved per use
- **Best ROI**: Best ratio of total savings to usage frequency
- **Rising Star**: Fastest growing usage trend
- **Underused**: High per-use value but low usage count

---

## Success Criteria

The analytics dashboard is complete when:

- Usage statistics displayed (total commands, unique commands, most used, highest value)
- ROI calculated from actual data (investment, return, ratio, break-even status)
- Trends visualized (weekly usage chart, weekly time saved chart)
- Actionable recommendations provided (quick wins, optimization opportunities, metrics to track)
- Data-driven insights generated (per-command analysis with patterns and recommendations)
- Export options available (JSON and CSV export commands)
