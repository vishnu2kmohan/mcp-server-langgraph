❌ Found unconfigured AsyncMock instances:

  tests/e2e/test_real_clients.py:52 - AsyncMock 'mock_instance' created but not configured
  tests/e2e/test_real_clients.py:81 - AsyncMock 'mock_instance' created but not configured
  tests/e2e/test_real_clients.py:126 - AsyncMock 'mock_instance' created but not configured
  tests/e2e/test_real_clients.py:169 - AsyncMock 'mock_instance' created but not configured
  tests/e2e/test_real_clients.py:195 - AsyncMock 'mock_instance' created but not configured
  tests/helpers/test_verifier.py:39 - AsyncMock 'verifier.llm' created but not configured
  tests/integration/test_agentic_loop_integration.py:54 - AsyncMock 'llm' created but not configured
  tests/integration/test_conversation_state_persistence.py:39 - AsyncMock 'llm' created but not configured
  tests/integration/test_mcp_startup_validation.py:141 - AsyncMock 'mock_keycloak.create_client' created but not configured
  tests/integration/test_pydantic_ai.py:43 - AsyncMock 'mock.run' created but not configured
  tests/security/test_permission_inheritance.py:22 - AsyncMock 'client' created but not configured
  tests/smoke/test_ci_startup_smoke.py:168 - AsyncMock 'mock_keycloak' created but not configured
  tests/unit/test_cache_redis_config.py:135 - AsyncMock 'mock_client' created but not configured
  tests/unit/test_cache_redis_config.py:291 - AsyncMock 'mock_client' created but not configured
  tests/unit/test_cache_redis_config.py:395 - AsyncMock 'mock_redis_client' created but not configured
  tests/unit/test_search_tools.py:203 - AsyncMock 'mock_client_instance' created but not configured
  tests/unit/test_search_tools.py:248 - AsyncMock 'mock_client_instance' created but not configured
  tests/utils/mock_factories.py:104 - AsyncMock 'mock_client' created but not configured
  tests/utils/mock_factories.py:429 - AsyncMock 'checkpointer' created but not configured
  tests/utils/mock_factories.py:476 - AsyncMock 'mock' created but not configured
  tests/utils/mock_factories.py:476 - AsyncMock 'mock' created but not configured
  tests/utils/mock_factories.py:538 - AsyncMock 'mock.aput' created but not configured

📖 Fix: Add explicit return_value or side_effect configuration:
   Option 1 - Constructor kwargs: mock = AsyncMock(return_value=value)
   Option 2 - Post-creation: mock.method.return_value = expected_value
   Option 3 - Spec: mock = AsyncMock(spec=SomeClass)
   Option 4 - Suppress: mock = AsyncMock()  # noqa: async-mock-config

See: tests/ASYNC_MOCK_GUIDELINES.md for best practices
