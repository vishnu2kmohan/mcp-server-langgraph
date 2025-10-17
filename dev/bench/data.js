window.BENCHMARK_DATA = {
  "lastUpdate": 1760726173623,
  "repoUrl": "https://github.com/vishnu2kmohan/mcp-server-langgraph",
  "entries": {
    "Benchmark": [
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "9bbc99fd26427d691e7848c33ce9bad63f990807",
          "message": "fix: add contents:write permission to benchmark-tests job for gh-pages push\n\nThe benchmark-action/github-action-benchmark requires write permissions\nto push benchmark results to the gh-pages branch. Without this permission,\nthe action fails with a 403 error when attempting to push.\n\nError resolved:\n- Command 'git' failed with args '... push ... gh-pages:gh-pages ...'\n- remote: Permission to vishnu2kmohan/mcp-server-langgraph.git denied to github-actions[bot]\n- fatal: unable to access: The requested URL returned error: 403\n\nThis change grants the benchmark-tests job the necessary permissions\nto automatically publish benchmark results to gh-pages.\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
          "timestamp": "2025-10-15T17:46:03-04:00",
          "tree_id": "50545188bb703a8e399051b40f26a40596c2cd5e",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/9bbc99fd26427d691e7848c33ce9bad63f990807"
        },
        "date": 1760564861045,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 37103.5630150263,
            "unit": "iter/sec",
            "range": "stddev: 0.0000028389862647852885",
            "extra": "mean: 26.9515895170234 usec\nrounds: 4865"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 32658.81497674621,
            "unit": "iter/sec",
            "range": "stddev: 0.000004915138498806017",
            "extra": "mean: 30.61960456042333 usec\nrounds: 6666"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 31454.264692142333,
            "unit": "iter/sec",
            "range": "stddev: 0.00000320352060712866",
            "extra": "mean: 31.79219129067139 usec\nrounds: 13916"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 424404.2905366903,
            "unit": "iter/sec",
            "range": "stddev: 4.610670724194107e-7",
            "extra": "mean: 2.356243851200059 usec\nrounds: 37609"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 424360.79737073014,
            "unit": "iter/sec",
            "range": "stddev: 4.756082702752129e-7",
            "extra": "mean: 2.3564853450079175 usec\nrounds: 49983"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 422722.3146354282,
            "unit": "iter/sec",
            "range": "stddev: 4.3912503135372124e-7",
            "extra": "mean: 2.365619143769209 usec\nrounds: 52508"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 2001879.6287218663,
            "unit": "iter/sec",
            "range": "stddev: 2.0864647928492782e-7",
            "extra": "mean: 499.5305340303936 nsec\nrounds: 97953"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 423335.4467037903,
            "unit": "iter/sec",
            "range": "stddev: 4.941240261063585e-7",
            "extra": "mean: 2.3621929318375847 usec\nrounds: 46773"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2947.3244192978964,
            "unit": "iter/sec",
            "range": "stddev: 0.000010735926969378306",
            "extra": "mean: 339.29077961435183 usec\nrounds: 2178"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2800.025131463889,
            "unit": "iter/sec",
            "range": "stddev: 0.00004679623473227242",
            "extra": "mean: 357.1396516277649 usec\nrounds: 1751"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 35559.679896901864,
            "unit": "iter/sec",
            "range": "stddev: 0.000010805240250514037",
            "extra": "mean: 28.121737959939427 usec\nrounds: 7392"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 11207.85283399465,
            "unit": "iter/sec",
            "range": "stddev: 0.000029229988269691703",
            "extra": "mean: 89.2231558364944 usec\nrounds: 3401"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "b8937e7b8d2f8a65b1f93780684a1739ea472943",
          "message": "fix: resolve Kustomize CI/CD failures and restore project README\n\n## CI/CD Deployment Fixes\n\n**Issue**: Kustomize deployment failures in GitHub Actions CI/CD pipeline\n\n**Root Causes**:\n1. Kustomize security constraint: Cannot reference files outside kustomization directory\n2. Deprecated Kustomize fields in overlay configurations (bases, commonLabels, patchesStrategicMerge)\n3. ConfigMap merge conflicts in dev/staging overlays\n\n## Changes Made\n\n### Kustomize Configuration Updates (4 files)\n\n1. **deployments/kustomize/base/kustomization.yaml**:\n   - Updated resources to reference local files instead of ../../kubernetes/base/\n   - Added explanatory comment about security constraint\n   - Modern labels syntax with pairs\n\n2. **deployments/kustomize/overlays/dev/kustomization.yaml**:\n   - Fixed: bases → resources\n   - Fixed: commonLabels → labels with pairs\n   - Fixed: patchesStrategicMerge → patches with target selectors\n   - Removed problematic configMapGenerator with merge behavior\n   - Image tag: dev-latest, replicas: 1\n\n3. **deployments/kustomize/overlays/staging/kustomization.yaml**:\n   - Same deprecation fixes as dev\n   - Image tag: staging-2.5.0, replicas: 2\n\n4. **deployments/kustomize/overlays/production/kustomization.yaml**:\n   - Same deprecation fixes as dev/staging\n   - Added HPA patch for production scaling\n   - Image tag: v2.5.0, replicas: 5\n\n### Kubernetes Manifests Copied (19 files)\n\nCopied all base manifests from deployments/kubernetes/base/ to deployments/kustomize/base/:\n- Core: namespace.yaml, deployment.yaml, service.yaml, configmap.yaml, secret.yaml\n- RBAC/Scaling: serviceaccount.yaml, hpa.yaml, pdb.yaml, networkpolicy.yaml\n- PostgreSQL: postgres-statefulset.yaml, postgres-service.yaml\n- OpenFGA: openfga-deployment.yaml, openfga-service.yaml\n- Keycloak: keycloak-deployment.yaml, keycloak-service.yaml\n- Redis: redis-session-deployment.yaml, redis-session-service.yaml\n- Observability: otel-collector-deployment.yaml\n- Ingress: ingress-http.yaml\n\n## Repository Structure Fix\n\n**Issue**: Root README.md was accidentally replaced with documentation index during repository reorganization (commit a78880d)\n\n**Fix**:\n- Restored proper project README at repository root with:\n  - Project overview and description\n  - CI/CD status badges (CI Pipeline, PR Checks, Quality Tests, Security Scan)\n  - Quality badges (Code Coverage, Property Tests, Contract Tests)\n  - Complete feature list and quick start guide\n  - Comprehensive documentation links\n- Verified docs/README.md remains as documentation guide for Mintlify\n\n## Validation\n\n✅ All three Kustomize overlays build successfully:\n- kubectl kustomize deployments/kustomize/overlays/dev\n- kubectl kustomize deployments/kustomize/overlays/staging\n- kubectl kustomize deployments/kustomize/overlays/production\n\n✅ No deprecation warnings\n✅ No security constraint violations\n✅ README structure restored correctly\n\n## Files Modified\n- CHANGELOG.md (documented all CI/CD fixes)\n- README.md (restored project README)\n- deployments/kustomize/base/kustomization.yaml\n- deployments/kustomize/overlays/dev/kustomization.yaml\n- deployments/kustomize/overlays/staging/kustomization.yaml\n- deployments/kustomize/overlays/production/kustomization.yaml\n\n## Files Added (19 Kubernetes manifests)\n- deployments/kustomize/base/*.yaml (all base resources)\n\nRelated: GitHub Actions CI/CD pipeline workflows\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
          "timestamp": "2025-10-15T18:08:30-04:00",
          "tree_id": "8f3344f24ba6731f536bcfdb070a5d026a1fa426",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/b8937e7b8d2f8a65b1f93780684a1739ea472943"
        },
        "date": 1760566202280,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 34699.315664603375,
            "unit": "iter/sec",
            "range": "stddev: 0.000002973959627461222",
            "extra": "mean: 28.81901215764021 usec\nrounds: 5840"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 31124.00370237896,
            "unit": "iter/sec",
            "range": "stddev: 0.0000029736469002679924",
            "extra": "mean: 32.12954250881178 usec\nrounds: 6975"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 30413.574410460114,
            "unit": "iter/sec",
            "range": "stddev: 0.000004675731419957961",
            "extra": "mean: 32.88005502096034 usec\nrounds: 15176"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 428562.1565407436,
            "unit": "iter/sec",
            "range": "stddev: 4.826695589947132e-7",
            "extra": "mean: 2.333383815481453 usec\nrounds: 39235"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 429855.6144107261,
            "unit": "iter/sec",
            "range": "stddev: 5.043029519019228e-7",
            "extra": "mean: 2.326362542387319 usec\nrounds: 69556"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 422977.2732590837,
            "unit": "iter/sec",
            "range": "stddev: 5.254969912646766e-7",
            "extra": "mean: 2.3641932160914854 usec\nrounds: 71552"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1944754.026755489,
            "unit": "iter/sec",
            "range": "stddev: 1.954226774673131e-7",
            "extra": "mean: 514.2038459580106 nsec\nrounds: 98922"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 419737.0079488817,
            "unit": "iter/sec",
            "range": "stddev: 4.7015384299561134e-7",
            "extra": "mean: 2.3824441997303856 usec\nrounds: 57661"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2927.9388092764343,
            "unit": "iter/sec",
            "range": "stddev: 0.000010295750408699967",
            "extra": "mean: 341.5371922499721 usec\nrounds: 2658"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2897.2383132967025,
            "unit": "iter/sec",
            "range": "stddev: 0.00005069405836160677",
            "extra": "mean: 345.1562805208531 usec\nrounds: 1843"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 36308.79121291742,
            "unit": "iter/sec",
            "range": "stddev: 0.000006578035632097731",
            "extra": "mean: 27.541539296528114 usec\nrounds: 8016"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 8225.852787012042,
            "unit": "iter/sec",
            "range": "stddev: 0.0023033327692230676",
            "extra": "mean: 121.56794266716264 usec\nrounds: 4064"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "460844adb65d8e912709fadc52752e739b2202ee",
          "message": "fix: disable staging deployment until Kubernetes cluster is provisioned\n\nTemporarily disable the deploy-staging job in CI/CD workflow as the staging\nKubernetes cluster is not yet available. This prevents deployment failures\nand allows other CI/CD jobs to complete successfully.\n\nChanges:\n- Comment out deploy-staging job in .github/workflows/ci.yaml:296-321\n- Add TODO note to re-enable when staging cluster is ready\n- Dev and production deployments remain unaffected\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
          "timestamp": "2025-10-15T18:11:38-04:00",
          "tree_id": "ab7c96d1737591ecdf13f9ccd978dd1b065f35f6",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/460844adb65d8e912709fadc52752e739b2202ee"
        },
        "date": 1760566401646,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 37548.63148041209,
            "unit": "iter/sec",
            "range": "stddev: 0.000002941302435490542",
            "extra": "mean: 26.63212907031426 usec\nrounds: 5098"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 33172.24557884542,
            "unit": "iter/sec",
            "range": "stddev: 0.00000347927964120589",
            "extra": "mean: 30.145683011514887 usec\nrounds: 5975"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 32316.24299475616,
            "unit": "iter/sec",
            "range": "stddev: 0.0000030282854986112325",
            "extra": "mean: 30.944191135159688 usec\nrounds: 15026"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 428369.1690123165,
            "unit": "iter/sec",
            "range": "stddev: 4.850137848881095e-7",
            "extra": "mean: 2.3344350442065727 usec\nrounds: 39704"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 434461.146934167,
            "unit": "iter/sec",
            "range": "stddev: 4.805741642871036e-7",
            "extra": "mean: 2.3017017909579103 usec\nrounds: 47128"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 427244.31842975214,
            "unit": "iter/sec",
            "range": "stddev: 4.5990985903084323e-7",
            "extra": "mean: 2.3405811543036843 usec\nrounds: 61882"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1370072.4623305022,
            "unit": "iter/sec",
            "range": "stddev: 2.667568696092647e-7",
            "extra": "mean: 729.888401887148 nsec\nrounds: 157431"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 421992.2779438149,
            "unit": "iter/sec",
            "range": "stddev: 5.288872110186255e-7",
            "extra": "mean: 2.36971160911419 usec\nrounds: 51718"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2932.153471612923,
            "unit": "iter/sec",
            "range": "stddev: 0.000009587154114853886",
            "extra": "mean: 341.0462684444408 usec\nrounds: 2250"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2839.569127975015,
            "unit": "iter/sec",
            "range": "stddev: 0.00007008747240690885",
            "extra": "mean: 352.16610511367656 usec\nrounds: 1760"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 36375.638701624375,
            "unit": "iter/sec",
            "range": "stddev: 0.000006608057500288797",
            "extra": "mean: 27.49092622682511 usec\nrounds: 7374"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 8464.70037594269,
            "unit": "iter/sec",
            "range": "stddev: 0.002342498185360839",
            "extra": "mean: 118.13767240268476 usec\nrounds: 4939"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "c25a468caddbd811dc6a22fc46aa0a4afdb53058",
          "message": "docs: update documentation to reflect v2.5.0 state\n\n- Add ADR 0022 (Distributed Conversation Checkpointing) to Mintlify navigation\n- Update ADR index in adr/README.md to include ADR 0022\n- Align documentation package version from 2.2.0 to 2.5.0\n\nThis ensures 100% documentation coverage with all 22 ADRs accessible\nin the Mintlify site and properly indexed.\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
          "timestamp": "2025-10-15T18:18:04-04:00",
          "tree_id": "97fd8d9dc3d4d5490930a18260c847ee81638fa7",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/c25a468caddbd811dc6a22fc46aa0a4afdb53058"
        },
        "date": 1760566787649,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 37096.77308359924,
            "unit": "iter/sec",
            "range": "stddev: 0.000002513678402872457",
            "extra": "mean: 26.95652254567952 usec\nrounds: 4635"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 33569.199635119345,
            "unit": "iter/sec",
            "range": "stddev: 0.0000031339057252169477",
            "extra": "mean: 29.789211862943027 usec\nrounds: 6339"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 32548.644300789823,
            "unit": "iter/sec",
            "range": "stddev: 0.000003114443106743381",
            "extra": "mean: 30.72324582120104 usec\nrounds: 15495"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 433418.8036804105,
            "unit": "iter/sec",
            "range": "stddev: 4.650483612603519e-7",
            "extra": "mean: 2.307237229922698 usec\nrounds: 37314"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 437228.61152010347,
            "unit": "iter/sec",
            "range": "stddev: 4.809372860718844e-7",
            "extra": "mean: 2.2871330321300825 usec\nrounds: 65067"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 437846.8102388288,
            "unit": "iter/sec",
            "range": "stddev: 4.295494193885604e-7",
            "extra": "mean: 2.283903814337571 usec\nrounds: 60456"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1983826.320039791,
            "unit": "iter/sec",
            "range": "stddev: 1.054612798728367e-7",
            "extra": "mean: 504.07638506376014 nsec\nrounds: 87866"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 433160.24267525005,
            "unit": "iter/sec",
            "range": "stddev: 5.004198938441426e-7",
            "extra": "mean: 2.308614460606724 usec\nrounds: 39127"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2914.5805890173724,
            "unit": "iter/sec",
            "range": "stddev: 0.00002061402117787711",
            "extra": "mean: 343.10253892727053 usec\nrounds: 2312"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2623.1242310428347,
            "unit": "iter/sec",
            "range": "stddev: 0.00008120864838419392",
            "extra": "mean: 381.22479605262373 usec\nrounds: 1520"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 36044.01558148424,
            "unit": "iter/sec",
            "range": "stddev: 0.000006627072975654011",
            "extra": "mean: 27.74385661162844 usec\nrounds: 6723"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 7691.098374195219,
            "unit": "iter/sec",
            "range": "stddev: 0.002904228835315235",
            "extra": "mean: 130.02044068960933 usec\nrounds: 4350"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "db60f3a637faef4a448051ae8dbe101113f6a348",
          "message": "chore: prepare release v2.6.0\n\n- Update CHANGELOG.md with v2.6.0 release notes\n- Bump version to 2.6.0 in pyproject.toml and config.py\n- Document all changes since v2.5.0:\n  - Fixed Kustomize CI/CD deployment issues\n  - Resolved pytest-asyncio compatibility\n  - Enhanced deployment validation\n  - Updated documentation\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
          "timestamp": "2025-10-15T18:21:14-04:00",
          "tree_id": "c96b8f5dd7515a26761c2f2217982cf36411fa80",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/db60f3a637faef4a448051ae8dbe101113f6a348"
        },
        "date": 1760566975350,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 35674.493895658066,
            "unit": "iter/sec",
            "range": "stddev: 0.0000027268032217235783",
            "extra": "mean: 28.03123158312583 usec\nrounds: 5104"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 31115.43841184404,
            "unit": "iter/sec",
            "range": "stddev: 0.0000031638254130446753",
            "extra": "mean: 32.13838695646826 usec\nrounds: 6670"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 30157.995858661445,
            "unit": "iter/sec",
            "range": "stddev: 0.0000031152874977524",
            "extra": "mean: 33.1587020797603 usec\nrounds: 15098"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 419421.25166606973,
            "unit": "iter/sec",
            "range": "stddev: 4.2837439924097996e-7",
            "extra": "mean: 2.3842377944076354 usec\nrounds: 37524"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 431739.8400371076,
            "unit": "iter/sec",
            "range": "stddev: 4.866044970119916e-7",
            "extra": "mean: 2.3162096875610345 usec\nrounds: 52149"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 428162.2285726644,
            "unit": "iter/sec",
            "range": "stddev: 4.55387828961779e-7",
            "extra": "mean: 2.335563329193312 usec\nrounds: 54043"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1938119.372429835,
            "unit": "iter/sec",
            "range": "stddev: 2.0866112272221874e-7",
            "extra": "mean: 515.9640908734597 nsec\nrounds: 99128"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 426201.61171052384,
            "unit": "iter/sec",
            "range": "stddev: 5.336685915625664e-7",
            "extra": "mean: 2.34630741067962 usec\nrounds: 42061"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2936.496107396717,
            "unit": "iter/sec",
            "range": "stddev: 0.000007539419200684984",
            "extra": "mean: 340.54191234277744 usec\nrounds: 2544"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2802.448490637568,
            "unit": "iter/sec",
            "range": "stddev: 0.00005274045125340143",
            "extra": "mean: 356.83082252566084 usec\nrounds: 1758"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 35218.63811960171,
            "unit": "iter/sec",
            "range": "stddev: 0.000006656158533085955",
            "extra": "mean: 28.394056482366587 usec\nrounds: 7312"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 7741.03267671259,
            "unit": "iter/sec",
            "range": "stddev: 0.0027705355298139195",
            "extra": "mean: 129.18173088305232 usec\nrounds: 4054"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "a3232361947701d6c013bd9ca28893770dc50827",
          "message": "feat: enhance version bump automation to include all version files\n\n- Update bump-versions.sh to include:\n  - package.json (npm package version)\n  - src/mcp_server_langgraph/core/config.py (service_version)\n  - .mcp/manifest.json (MCP manifest version)\n\n- Update bump-deployment-versions.yaml workflow:\n  - Include new files in commit message\n  - Include new files in release comment\n  - Include new files in workflow summary\n\n- Update RELEASE_PROCESS.md documentation:\n  - List all 9 files updated by automation\n\nNow all version-related files are automatically updated when a release is triggered,\nensuring complete version consistency across the entire project.\n\nFiles updated by automation (9 total):\n1. pyproject.toml\n2. package.json\n3. src/mcp_server_langgraph/core/config.py\n4. .mcp/manifest.json\n5. docker-compose.yml\n6. deployments/kubernetes/base/deployment.yaml\n7. deployments/helm/mcp-server-langgraph/Chart.yaml\n8. deployments/helm/mcp-server-langgraph/values.yaml\n9. deployments/kustomize/base/kustomization.yaml\n\nTested with: DRY_RUN=1 bash scripts/deployment/bump-versions.sh 2.7.0\n✅ All 9 files show correct version updates\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
          "timestamp": "2025-10-15T18:27:27-04:00",
          "tree_id": "e31d77e9b3641763629afc1879de69a9b374be79",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/a3232361947701d6c013bd9ca28893770dc50827"
        },
        "date": 1760567344245,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 36744.744729140744,
            "unit": "iter/sec",
            "range": "stddev: 0.0000027549769120313415",
            "extra": "mean: 27.214776082168317 usec\nrounds: 6422"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 33228.77616630423,
            "unit": "iter/sec",
            "range": "stddev: 0.0000028230074960245364",
            "extra": "mean: 30.094397548533667 usec\nrounds: 6935"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 30927.21465074824,
            "unit": "iter/sec",
            "range": "stddev: 0.0000035433445077081507",
            "extra": "mean: 32.33398194091192 usec\nrounds: 15394"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 436650.6632239841,
            "unit": "iter/sec",
            "range": "stddev: 4.6587734627534007e-7",
            "extra": "mean: 2.2901602682028686 usec\nrounds: 41468"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 441367.984465275,
            "unit": "iter/sec",
            "range": "stddev: 4.951265782001973e-7",
            "extra": "mean: 2.2656831378730775 usec\nrounds: 67714"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 438157.69970846793,
            "unit": "iter/sec",
            "range": "stddev: 4.656378692144625e-7",
            "extra": "mean: 2.2822832981489514 usec\nrounds: 71603"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1999449.6907182464,
            "unit": "iter/sec",
            "range": "stddev: 8.577120982933352e-8",
            "extra": "mean: 500.1376151858955 nsec\nrounds: 96909"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 412412.6077288209,
            "unit": "iter/sec",
            "range": "stddev: 7.757434876304276e-7",
            "extra": "mean: 2.4247561332012997 usec\nrounds: 58167"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2940.571021006104,
            "unit": "iter/sec",
            "range": "stddev: 0.000008035116167085134",
            "extra": "mean: 340.07000438229653 usec\nrounds: 2510"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2897.0026569431075,
            "unit": "iter/sec",
            "range": "stddev: 0.00004947526350439048",
            "extra": "mean: 345.18435721946884 usec\nrounds: 1856"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 37158.03753456902,
            "unit": "iter/sec",
            "range": "stddev: 0.000006645375548683509",
            "extra": "mean: 26.912077880046166 usec\nrounds: 8359"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 8662.203590382684,
            "unit": "iter/sec",
            "range": "stddev: 0.0021859543782287265",
            "extra": "mean: 115.44406565440948 usec\nrounds: 4874"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "f85e91396110efebc1327529cdb0614523cba707",
          "message": "feat: automate release notes from CHANGELOG.md and enhance documentation\n\nImplements automatic extraction of release notes from CHANGELOG.md when creating\nGitHub releases, ensuring comprehensive descriptions like v2.5.0.\n\nChanges:\n- Enhanced .github/workflows/release.yaml with CHANGELOG extraction (lines 30-134)\n  - Extracts version-specific section from CHANGELOG.md\n  - Adds deployment instructions (Docker, Helm, Kubernetes)\n  - Falls back to commit log if CHANGELOG section not found\n  - Properly escapes version numbers in sed patterns\n- Updated docs/deployment/RELEASE_PROCESS.md (lines 206-237)\n  - Added comprehensive CHANGELOG checklist to \"Before Release\" section\n  - Emphasized importance of updating CHANGELOG.md before releases\n  - Added detailed sub-tasks for creating comprehensive release notes\n  - Noted that release descriptions are auto-generated from CHANGELOG.md\n\nBenefits:\n- ✅ Future releases will automatically have comprehensive descriptions\n- ✅ Consistent release notes format across all releases\n- ✅ Reduced manual effort when creating releases\n- ✅ Fallback mechanism prevents empty release descriptions\n\nContext:\n- Fixed v2.6.0 release (previously had minimal description)\n- Ensures all future releases match quality of v2.5.0\n- Part of release process improvement initiative\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
          "timestamp": "2025-10-15T18:37:11-04:00",
          "tree_id": "0ff7ba932670b114e026c0fd9ee12e35f10591ec",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/f85e91396110efebc1327529cdb0614523cba707"
        },
        "date": 1760567926431,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 37512.83517911035,
            "unit": "iter/sec",
            "range": "stddev: 0.0000034475824999198515",
            "extra": "mean: 26.657542551112392 usec\nrounds: 5135"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 33855.43695020822,
            "unit": "iter/sec",
            "range": "stddev: 0.0000030832830054566467",
            "extra": "mean: 29.537353231350032 usec\nrounds: 6081"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 31794.58195159443,
            "unit": "iter/sec",
            "range": "stddev: 0.0000045051496814048635",
            "extra": "mean: 31.451899619955597 usec\nrounds: 15262"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 435734.8268239903,
            "unit": "iter/sec",
            "range": "stddev: 4.838488226862867e-7",
            "extra": "mean: 2.2949737740470715 usec\nrounds: 39846"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 439041.93818029686,
            "unit": "iter/sec",
            "range": "stddev: 4.6087734249443047e-7",
            "extra": "mean: 2.2776867379565466 usec\nrounds: 65450"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 437201.5093419034,
            "unit": "iter/sec",
            "range": "stddev: 5.278230090234014e-7",
            "extra": "mean: 2.2872748118030235 usec\nrounds: 66944"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 2008419.38666033,
            "unit": "iter/sec",
            "range": "stddev: 1.9060335854815494e-7",
            "extra": "mean: 497.90397694917436 nsec\nrounds: 98040"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 434880.4281886252,
            "unit": "iter/sec",
            "range": "stddev: 4.894723059437234e-7",
            "extra": "mean: 2.2994826512777893 usec\nrounds: 52367"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2966.9620315162315,
            "unit": "iter/sec",
            "range": "stddev: 0.00000926908229831717",
            "extra": "mean: 337.04509507624596 usec\nrounds: 2356"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2830.767160719663,
            "unit": "iter/sec",
            "range": "stddev: 0.00005534440791975149",
            "extra": "mean: 353.26112789360286 usec\nrounds: 1728"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 36324.352431205276,
            "unit": "iter/sec",
            "range": "stddev: 0.000006385325642921244",
            "extra": "mean: 27.529740602916483 usec\nrounds: 7795"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 8586.972484248095,
            "unit": "iter/sec",
            "range": "stddev: 0.0022194189710520403",
            "extra": "mean: 116.45547972051799 usec\nrounds: 5153"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "9064266c489e48735ab1481976b6ffcdd40d5817",
          "message": "fix: resolve YAML syntax error in release workflow\n\n**Issue**: GitHub Actions workflow validation failing with YAML syntax error\n\n**Root Cause**:\n- Backticks (`) in heredoc were being parsed as YAML tokens\n- Error on line 55: 'found character `` that cannot start any token'\n- Caused workflow to fail immediately (0s duration) on push events\n\n**Changes Made**:\n\n1. **release.yaml** - Replaced heredoc with echo commands\n   - Lines 50-79: Deployment info section (Docker images, Helm)\n   - Lines 93-109: Fallback section (generated from commits)\n   - Used command grouping {...} instead of heredoc <<EOF\n   - Eliminated all backtick characters from YAML\n\n2. **Validation**:\n   - Confirmed YAML is valid with yaml.safe_load()\n   - Workflow triggers correctly on tag pushes only (v*.*.*)\n   - No longer triggers on regular push events\n\n**Impact**:\n- ✅ release.yaml will ONLY trigger on tag pushes (v*.*.*)\n- ✅ security-scan.yaml will ONLY trigger on schedule/PR/manual\n- ✅ Regular pushes to main will not trigger these workflows\n- ✅ Only CI/CD Pipeline and Quality Tests run on push\n\n**Testing**:\n- YAML syntax validation: PASSED\n- Workflow triggers: tags (v*.*.*), workflow_dispatch\n- Expected behavior: No execution on regular push events\n\nRelated workflows: .github/workflows/security-scan.yaml (already valid)\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
          "timestamp": "2025-10-15T18:47:05-04:00",
          "tree_id": "83eac83ab406f07ffc90eccf83e44ffbb5691333",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/9064266c489e48735ab1481976b6ffcdd40d5817"
        },
        "date": 1760568525502,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 36855.570671791116,
            "unit": "iter/sec",
            "range": "stddev: 0.0000030628807080338778",
            "extra": "mean: 27.13294033364107 usec\nrounds: 5095"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 33173.08503165777,
            "unit": "iter/sec",
            "range": "stddev: 0.0000031218886549429622",
            "extra": "mean: 30.14492016783121 usec\nrounds: 6664"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 31534.182212722466,
            "unit": "iter/sec",
            "range": "stddev: 0.0000035432575759830008",
            "extra": "mean: 31.711619894063723 usec\nrounds: 14788"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 433995.4359239842,
            "unit": "iter/sec",
            "range": "stddev: 4.745589108048966e-7",
            "extra": "mean: 2.3041716968082437 usec\nrounds: 30618"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 439271.4336917402,
            "unit": "iter/sec",
            "range": "stddev: 4.554974746273551e-7",
            "extra": "mean: 2.2764967701080976 usec\nrounds: 56042"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 438684.54917186324,
            "unit": "iter/sec",
            "range": "stddev: 4.899285926441264e-7",
            "extra": "mean: 2.279542331472063 usec\nrounds: 56648"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 2015041.4380739988,
            "unit": "iter/sec",
            "range": "stddev: 4.7078590303749505e-8",
            "extra": "mean: 496.26770998605974 nsec\nrounds: 100929"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 432391.0393977189,
            "unit": "iter/sec",
            "range": "stddev: 0.000002092153643101964",
            "extra": "mean: 2.3127213769112984 usec\nrounds: 50667"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2896.168417169914,
            "unit": "iter/sec",
            "range": "stddev: 0.00004497306893644697",
            "extra": "mean: 345.28378739009344 usec\nrounds: 2427"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2844.388107035371,
            "unit": "iter/sec",
            "range": "stddev: 0.00005662128136153431",
            "extra": "mean: 351.5694632271097 usec\nrounds: 1822"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 36499.11490715696,
            "unit": "iter/sec",
            "range": "stddev: 0.000007978019471989327",
            "extra": "mean: 27.397924649507438 usec\nrounds: 7923"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 7856.073304455398,
            "unit": "iter/sec",
            "range": "stddev: 0.002619801458046737",
            "extra": "mean: 127.29005461709124 usec\nrounds: 4138"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "01d60a5eba1d894415ddbc735dbce8ea29f85c99",
          "message": "fix: prevent workflow failures on incorrect trigger events\n\nFixed GitHub Actions workflow failures by adding conditional execution\nguards and fixing YAML syntax errors.\n\n## Changes Made\n\n### release.yaml\n1. Fixed YAML syntax error (line 55): Replaced heredoc with backticks\n   - Replaced `cat >> file << EOF` with command grouping `{...} >> file`\n   - Eliminated backticks from YAML token parsing scope\n   - Lines 50-79: Deployment info section\n   - Lines 93-109: Fallback section\n\n2. Added conditional execution guard\n   - Line 21: `if: startsWith(github.ref, 'refs/tags/v')`\n   - Ensures create-release job only runs on tag pushes (v*.*.*)\n   - Prevents workflow from appearing as \"failed\" on regular pushes\n\n### security-scan.yaml\nAdded conditional execution guards to prevent execution on push events:\n- Line 23: trivy-scan job\n- Line 47: dependency-check job\n- Line 84: codeql job\n- Line 105: secrets-scan job\n- Line 123: license-check job\n\nAll jobs now only run on: schedule, pull_request, workflow_dispatch\n\n## Validation\n- ✅ release.yaml YAML validation passed\n- ✅ security-scan.yaml YAML validation passed\n\n## Impact\n- Workflows will no longer show as \"failed\" on regular push events\n- Release workflow only triggers on version tags\n- Security scans only run on schedule/PR/manual trigger\n\nFixes: Workflow failures on every push to main branch",
          "timestamp": "2025-10-15T18:51:51-04:00",
          "tree_id": "ad0b93772c9431009a3d783ae1d3f4176f6c2353",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/01d60a5eba1d894415ddbc735dbce8ea29f85c99"
        },
        "date": 1760568808939,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 37737.75994918889,
            "unit": "iter/sec",
            "range": "stddev: 0.0000027196331581891886",
            "extra": "mean: 26.4986581436319 usec\nrounds: 5280"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 32950.57913484495,
            "unit": "iter/sec",
            "range": "stddev: 0.000004033814871496518",
            "extra": "mean: 30.348480246968062 usec\nrounds: 6505"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 31588.283262048415,
            "unit": "iter/sec",
            "range": "stddev: 0.000003750605662801132",
            "extra": "mean: 31.657307606882362 usec\nrounds: 15354"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 434697.29961730394,
            "unit": "iter/sec",
            "range": "stddev: 4.870793680729364e-7",
            "extra": "mean: 2.300451373588871 usec\nrounds: 33305"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 428617.72240649525,
            "unit": "iter/sec",
            "range": "stddev: 4.654812942779281e-7",
            "extra": "mean: 2.333081316342803 usec\nrounds: 72224"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 433984.5469447156,
            "unit": "iter/sec",
            "range": "stddev: 4.554933927560504e-7",
            "extra": "mean: 2.3042295101060084 usec\nrounds: 68790"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 2002445.9780313582,
            "unit": "iter/sec",
            "range": "stddev: 4.5246260116495224e-8",
            "extra": "mean: 499.3892524297302 nsec\nrounds: 97571"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 424910.12636119814,
            "unit": "iter/sec",
            "range": "stddev: 6.530088398329549e-7",
            "extra": "mean: 2.353438852031364 usec\nrounds: 51343"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2970.7364424239468,
            "unit": "iter/sec",
            "range": "stddev: 0.000010419983123743797",
            "extra": "mean: 336.616869042768 usec\nrounds: 2581"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2882.302976188796,
            "unit": "iter/sec",
            "range": "stddev: 0.00004773619383316273",
            "extra": "mean: 346.94478972584534 usec\nrounds: 1869"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 36577.16247966606,
            "unit": "iter/sec",
            "range": "stddev: 0.000007502984764895448",
            "extra": "mean: 27.33946353974065 usec\nrounds: 8187"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 8510.213235955507,
            "unit": "iter/sec",
            "range": "stddev: 0.0022413111449958723",
            "extra": "mean: 117.50586880420538 usec\nrounds: 5084"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "90d5159ca79c02a6d5d5976ab85d0089443a5b39",
          "message": "feat: update model configuration to gemini-2.5-flash and Claude 4.5 fallbacks\n\n- Replace gemini-2.5-flash-002 with gemini-2.5-flash for all model references\n- Update fallback models to use Claude 4.5 family (claude-haiku-4-5-20251001, claude-sonnet-4-5-20250929)\n- Add dedicated model configuration for summarization and verification tasks\n- Enhance embedding configuration with provider support (Google/local)\n- Add HIPAA compliance and data security settings\n- Implement fail-closed security pattern for secrets management\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
          "timestamp": "2025-10-17T13:53:32-04:00",
          "tree_id": "12de44b72eb7f90ab18b7081a941684861509be7",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/90d5159ca79c02a6d5d5976ab85d0089443a5b39"
        },
        "date": 1760724071104,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 36334.84534967014,
            "unit": "iter/sec",
            "range": "stddev: 0.0000034136928863930612",
            "extra": "mean: 27.521790456969107 usec\nrounds: 5030"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 33520.625667627886,
            "unit": "iter/sec",
            "range": "stddev: 0.000003434878499070777",
            "extra": "mean: 29.83237872453369 usec\nrounds: 6411"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 29996.690033140276,
            "unit": "iter/sec",
            "range": "stddev: 0.000007994415370928042",
            "extra": "mean: 33.33701148010671 usec\nrounds: 14373"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 427607.18513496907,
            "unit": "iter/sec",
            "range": "stddev: 6.220672900804138e-7",
            "extra": "mean: 2.3385949412528277 usec\nrounds: 33963"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 426114.6302382814,
            "unit": "iter/sec",
            "range": "stddev: 6.394273723999407e-7",
            "extra": "mean: 2.3467863552133954 usec\nrounds: 50158"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 426412.9267355214,
            "unit": "iter/sec",
            "range": "stddev: 5.395280287602627e-7",
            "extra": "mean: 2.3451446644820892 usec\nrounds: 49003"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1988743.4889205943,
            "unit": "iter/sec",
            "range": "stddev: 4.7749426172559415e-8",
            "extra": "mean: 502.830056048484 nsec\nrounds: 95979"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 428565.279025681,
            "unit": "iter/sec",
            "range": "stddev: 8.9925181585058e-7",
            "extra": "mean: 2.333366814673936 usec\nrounds: 46105"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2996.450584979329,
            "unit": "iter/sec",
            "range": "stddev: 0.000011405230117700526",
            "extra": "mean: 333.72817993823134 usec\nrounds: 2562"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 3006.133482819691,
            "unit": "iter/sec",
            "range": "stddev: 0.00003979856786703138",
            "extra": "mean: 332.65322571838055 usec\nrounds: 1843"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 35070.063881218506,
            "unit": "iter/sec",
            "range": "stddev: 0.000010171283798112382",
            "extra": "mean: 28.514347832013563 usec\nrounds: 7449"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 11237.002752641903,
            "unit": "iter/sec",
            "range": "stddev: 0.000026913303855235452",
            "extra": "mean: 88.99170197007315 usec\nrounds: 4060"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "b49ea329946c331ca6b80a9855f0f088f8461a1a",
          "message": "docs: prepare CHANGELOG for v2.7.0 release",
          "timestamp": "2025-10-17T14:04:06-04:00",
          "tree_id": "f4e93c750e1d5d726dc5b5b9eb243e618f0ec179",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/b49ea329946c331ca6b80a9855f0f088f8461a1a"
        },
        "date": 1760724385582,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 36215.718180784286,
            "unit": "iter/sec",
            "range": "stddev: 0.0000028095515470592125",
            "extra": "mean: 27.612320015528244 usec\nrounds: 5131"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 32338.053292683737,
            "unit": "iter/sec",
            "range": "stddev: 0.000003400770973473444",
            "extra": "mean: 30.92332092316278 usec\nrounds: 6500"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 30963.29551485116,
            "unit": "iter/sec",
            "range": "stddev: 0.000003244559525451254",
            "extra": "mean: 32.29630384531784 usec\nrounds: 14537"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 429198.86618665577,
            "unit": "iter/sec",
            "range": "stddev: 4.5894986453559857e-7",
            "extra": "mean: 2.329922277951933 usec\nrounds: 36682"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 435727.574279354,
            "unit": "iter/sec",
            "range": "stddev: 4.7085238215204757e-7",
            "extra": "mean: 2.2950119731437497 usec\nrounds: 64227"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 432787.3799017309,
            "unit": "iter/sec",
            "range": "stddev: 4.6867123173964044e-7",
            "extra": "mean: 2.3106034196908904 usec\nrounds: 62696"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 2005008.383653474,
            "unit": "iter/sec",
            "range": "stddev: 4.912266047037735e-8",
            "extra": "mean: 498.75103174273323 nsec\nrounds: 98232"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 432526.83605535066,
            "unit": "iter/sec",
            "range": "stddev: 4.698467061223991e-7",
            "extra": "mean: 2.311995272062216 usec\nrounds: 51608"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2998.877233546222,
            "unit": "iter/sec",
            "range": "stddev: 0.00001320332623365973",
            "extra": "mean: 333.45813186806697 usec\nrounds: 2639"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2803.518754186059,
            "unit": "iter/sec",
            "range": "stddev: 0.000052652855763415795",
            "extra": "mean: 356.694599779957 usec\nrounds: 1819"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 40497.617180903835,
            "unit": "iter/sec",
            "range": "stddev: 0.0000024364011650620447",
            "extra": "mean: 24.692810827189557 usec\nrounds: 8257"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 12633.425675760564,
            "unit": "iter/sec",
            "range": "stddev: 0.00002131348857360456",
            "extra": "mean: 79.15509424483929 usec\nrounds: 5369"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "55c2c1e5a9ef1c5af6c96429cfcaed15e126a2e2",
          "message": "fix: remove unused asyncio import in agent.py\n\n- Removed unused asyncio import causing flake8 F401 error\n- Fixes CI/CD lint failures\n- Required for v2.7.0 release",
          "timestamp": "2025-10-17T14:14:04-04:00",
          "tree_id": "a82814594b9115fe474d6ff3ebf2238695bd4c39",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/55c2c1e5a9ef1c5af6c96429cfcaed15e126a2e2"
        },
        "date": 1760725033967,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 40857.51813864487,
            "unit": "iter/sec",
            "range": "stddev: 0.0000013293480477338124",
            "extra": "mean: 24.47529966471838 usec\nrounds: 5366"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 34483.55229284472,
            "unit": "iter/sec",
            "range": "stddev: 0.0000021464924325384836",
            "extra": "mean: 28.99933253708025 usec\nrounds: 5861"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 33459.76683604434,
            "unit": "iter/sec",
            "range": "stddev: 0.0000014041823761540449",
            "extra": "mean: 29.886639823286384 usec\nrounds: 9959"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 448884.4362679534,
            "unit": "iter/sec",
            "range": "stddev: 3.368180486921767e-7",
            "extra": "mean: 2.227744869735399 usec\nrounds: 37279"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 445675.30480876734,
            "unit": "iter/sec",
            "range": "stddev: 4.150594357397491e-7",
            "extra": "mean: 2.243785978738681 usec\nrounds: 55658"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 449195.77572993503,
            "unit": "iter/sec",
            "range": "stddev: 3.0015673029597306e-7",
            "extra": "mean: 2.2262008104929705 usec\nrounds: 57248"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1967631.1680637244,
            "unit": "iter/sec",
            "range": "stddev: 4.899610243938586e-8",
            "extra": "mean: 508.2253301486702 nsec\nrounds: 97305"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 448112.9388490426,
            "unit": "iter/sec",
            "range": "stddev: 3.6306366362320277e-7",
            "extra": "mean: 2.231580285471011 usec\nrounds: 48695"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2936.513873997553,
            "unit": "iter/sec",
            "range": "stddev: 0.0000347670308869823",
            "extra": "mean: 340.53985198396964 usec\nrounds: 2520"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 3209.3117678909684,
            "unit": "iter/sec",
            "range": "stddev: 0.00005714811849513686",
            "extra": "mean: 311.5932861384671 usec\nrounds: 2020"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 44392.99311102514,
            "unit": "iter/sec",
            "range": "stddev: 0.0000016891726800807958",
            "extra": "mean: 22.526077426206406 usec\nrounds: 8408"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 15086.347931486169,
            "unit": "iter/sec",
            "range": "stddev: 0.000019028124900901956",
            "extra": "mean: 66.28509461278806 usec\nrounds: 5179"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "088542d6f49df2ad3816b53f2014f78bba39cb8f",
          "message": "fix: correct import sorting in validate_documentation_links.py\n\n- Reordered imports to match isort requirements (alphabetical)\n- Fixed typing imports order: Dict, List, Set, Tuple\n- Resolves CI lint failure in isort check\n\nFixes: CI/CD lint failures blocking v2.7.0 release",
          "timestamp": "2025-10-17T14:19:40-04:00",
          "tree_id": "d1806884a394b49e25caa57aa85706d9737ef7f7",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/088542d6f49df2ad3816b53f2014f78bba39cb8f"
        },
        "date": 1760725342048,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 36847.04559166979,
            "unit": "iter/sec",
            "range": "stddev: 0.0000025640144554594382",
            "extra": "mean: 27.1392179194436 usec\nrounds: 5268"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 32563.188001389975,
            "unit": "iter/sec",
            "range": "stddev: 0.0000029544552749934587",
            "extra": "mean: 30.709523894199624 usec\nrounds: 6696"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 30743.352844919922,
            "unit": "iter/sec",
            "range": "stddev: 0.0000037493070754786077",
            "extra": "mean: 32.527356565314946 usec\nrounds: 15108"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 436114.3862494671,
            "unit": "iter/sec",
            "range": "stddev: 4.475416229974946e-7",
            "extra": "mean: 2.2929764106153057 usec\nrounds: 40103"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 431785.27885846695,
            "unit": "iter/sec",
            "range": "stddev: 4.931055749836626e-7",
            "extra": "mean: 2.3159659417841936 usec\nrounds: 65622"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 436941.5442846481,
            "unit": "iter/sec",
            "range": "stddev: 7.883266376458538e-7",
            "extra": "mean: 2.2886356609490632 usec\nrounds: 58956"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1833935.0399927963,
            "unit": "iter/sec",
            "range": "stddev: 7.4960190338553e-8",
            "extra": "mean: 545.27558402719 nsec\nrounds: 92507"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 437778.27107525134,
            "unit": "iter/sec",
            "range": "stddev: 5.012649007334877e-7",
            "extra": "mean: 2.2842613854357023 usec\nrounds: 52505"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2979.3570499177445,
            "unit": "iter/sec",
            "range": "stddev: 0.000010249623876054262",
            "extra": "mean: 335.64288645015154 usec\nrounds: 2686"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2976.296380654636,
            "unit": "iter/sec",
            "range": "stddev: 0.00004628399361274149",
            "extra": "mean: 335.98804423504697 usec\nrounds: 1786"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 40500.53540607587,
            "unit": "iter/sec",
            "range": "stddev: 0.0000026119230443784764",
            "extra": "mean: 24.69103161164582 usec\nrounds: 8351"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 12547.671137817812,
            "unit": "iter/sec",
            "range": "stddev: 0.000018216287033876535",
            "extra": "mean: 79.69606383658471 usec\nrounds: 5467"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "e0c8af35f81c3b711a904171dc80e26fbd142b33",
          "message": "fix: correct AsyncMock side_effect in integration test\n\n- Fixed test_compaction_then_extraction to use actual response objects\n- Changed from async functions to MagicMock response objects in side_effect\n- Resolves test failure in CI integration tests\n\nFixes: Integration test failures blocking v2.7.0 release",
          "timestamp": "2025-10-17T14:29:05-04:00",
          "tree_id": "6123dc9f3c73635fecdf10abec82656b6e66508f",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/e0c8af35f81c3b711a904171dc80e26fbd142b33"
        },
        "date": 1760725900144,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 37405.948798173304,
            "unit": "iter/sec",
            "range": "stddev: 0.0000026121437215553707",
            "extra": "mean: 26.733715682379223 usec\nrounds: 5012"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 33442.721483895715,
            "unit": "iter/sec",
            "range": "stddev: 0.0000028955511990328657",
            "extra": "mean: 29.90187268346412 usec\nrounds: 6637"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 31929.341023541157,
            "unit": "iter/sec",
            "range": "stddev: 0.0000030505365052077683",
            "extra": "mean: 31.319155608714595 usec\nrounds: 15012"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 439570.1244668404,
            "unit": "iter/sec",
            "range": "stddev: 5.033112859037116e-7",
            "extra": "mean: 2.2749498756607065 usec\nrounds: 36589"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 441165.4884938994,
            "unit": "iter/sec",
            "range": "stddev: 4.979916562439919e-7",
            "extra": "mean: 2.2667230916314716 usec\nrounds: 62815"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 439160.0389169648,
            "unit": "iter/sec",
            "range": "stddev: 6.106246262298544e-7",
            "extra": "mean: 2.2770742130047887 usec\nrounds: 43173"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1961463.5523244718,
            "unit": "iter/sec",
            "range": "stddev: 1.0428700155918107e-7",
            "extra": "mean: 509.82339121975014 nsec\nrounds: 98242"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 439078.4348225807,
            "unit": "iter/sec",
            "range": "stddev: 4.876826553006135e-7",
            "extra": "mean: 2.2774974143379914 usec\nrounds: 50083"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2998.4072908386624,
            "unit": "iter/sec",
            "range": "stddev: 0.000024568411706283644",
            "extra": "mean: 333.5103950205168 usec\nrounds: 2691"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 2974.1942500885893,
            "unit": "iter/sec",
            "range": "stddev: 0.000044185749792634133",
            "extra": "mean: 336.2255172035969 usec\nrounds: 1831"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 41890.3347643337,
            "unit": "iter/sec",
            "range": "stddev: 0.000002684008335657922",
            "extra": "mean: 23.87185506217107 usec\nrounds: 8376"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 12563.535507300448,
            "unit": "iter/sec",
            "range": "stddev: 0.00001816707517084745",
            "extra": "mean: 79.59542912255213 usec\nrounds: 5185"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "committer": {
            "email": "vmohan@emergence.ai",
            "name": "Vishnu Mohan",
            "username": "vishnu2kmohan"
          },
          "distinct": true,
          "id": "645f749ef928a62070cbffb01fcd00565fc77292",
          "message": "docs: add v2.7.0 release summary and fix reports",
          "timestamp": "2025-10-17T14:33:48-04:00",
          "tree_id": "25a51ebe7154b3c47a0fa41405e867a163c29fce",
          "url": "https://github.com/vishnu2kmohan/mcp-server-langgraph/commit/645f749ef928a62070cbffb01fcd00565fc77292"
        },
        "date": 1760726172640,
        "tool": "pytest",
        "benches": [
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_encoding_performance",
            "value": 39993.90751004573,
            "unit": "iter/sec",
            "range": "stddev: 0.0000018194756022586694",
            "extra": "mean: 25.0038083862853 usec\nrounds: 5652"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_decoding_performance",
            "value": 34820.98688992971,
            "unit": "iter/sec",
            "range": "stddev: 0.000001652199092386774",
            "extra": "mean: 28.718312986390448 usec\nrounds: 6553"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestJWTBenchmarks::test_jwt_validation_performance",
            "value": 33751.018925499586,
            "unit": "iter/sec",
            "range": "stddev: 0.0000017773186041086613",
            "extra": "mean: 29.62873512670397 usec\nrounds: 14052"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_authorization_check_performance",
            "value": 441727.81400590896,
            "unit": "iter/sec",
            "range": "stddev: 3.456141643695854e-7",
            "extra": "mean: 2.263837522322339 usec\nrounds: 38116"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestOpenFGABenchmarks::test_batch_authorization_performance",
            "value": 445204.9823943796,
            "unit": "iter/sec",
            "range": "stddev: 3.8742904218725314e-7",
            "extra": "mean: 2.2461563539155582 usec\nrounds: 61073"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestLLMBenchmarks::test_llm_request_performance",
            "value": 444970.3931287681,
            "unit": "iter/sec",
            "range": "stddev: 3.165980601441773e-7",
            "extra": "mean: 2.2473405319589754 usec\nrounds: 53807"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_agent_initialization_performance",
            "value": 1982099.928702203,
            "unit": "iter/sec",
            "range": "stddev: 3.9113383815469886e-8",
            "extra": "mean: 504.51543109370806 nsec\nrounds: 99050"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestAgentBenchmarks::test_message_processing_performance",
            "value": 444009.79273777624,
            "unit": "iter/sec",
            "range": "stddev: 3.272015200385866e-7",
            "extra": "mean: 2.252202578312459 usec\nrounds: 47394"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_serialization_performance",
            "value": 2931.4784973933,
            "unit": "iter/sec",
            "range": "stddev: 0.000007793643528943948",
            "extra": "mean: 341.12479449847916 usec\nrounds: 2472"
          },
          {
            "name": "tests/performance/test_benchmarks.py::TestResourceBenchmarks::test_state_deserialization_performance",
            "value": 3195.6445373832325,
            "unit": "iter/sec",
            "range": "stddev: 0.000054299920912796856",
            "extra": "mean: 312.9259178553239 usec\nrounds: 2033"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_performance",
            "value": 43847.59290704967,
            "unit": "iter/sec",
            "range": "stddev: 0.000001645932713535405",
            "extra": "mean: 22.806269026440066 usec\nrounds: 8278"
          },
          {
            "name": "tests/test_json_logger.py::TestPerformance::test_formatting_with_trace_performance",
            "value": 15091.287124922006,
            "unit": "iter/sec",
            "range": "stddev: 0.00001952356420494118",
            "extra": "mean: 66.26340031319019 usec\nrounds: 5111"
          }
        ]
      }
    ]
  }
}