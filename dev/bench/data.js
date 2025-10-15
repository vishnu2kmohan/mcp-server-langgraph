window.BENCHMARK_DATA = {
  "lastUpdate": 1760564861526,
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
      }
    ]
  }
}