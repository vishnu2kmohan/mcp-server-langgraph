❌ Found unconfigured AsyncMock instances:

  tests/builder/test_builder_server_integration.py:211 - AsyncMock 'mock_openfga' created but not configured
  tests/builder/test_builder_server_integration.py:223 - AsyncMock 'mock_openfga' created but not configured
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
  tests/playground/test_mcp_client.py:57 - AsyncMock 'mock_client' created but not configured
  tests/playground/test_mcp_client.py:90 - AsyncMock 'mock_client' created but not configured
  tests/playground/test_mcp_client.py:118 - AsyncMock 'mock_client' created but not configured
  tests/playground/test_mcp_client.py:160 - AsyncMock 'mock_client' created but not configured
  tests/playground/test_mcp_client.py:195 - AsyncMock 'mock_client' created but not configured
  tests/playground/test_mcp_client.py:214 - AsyncMock 'mock_client' created but not configured
  tests/playground/test_mcp_client.py:244 - AsyncMock 'mock_response' created but not configured
  tests/playground/test_mcp_client.py:250 - AsyncMock 'mock_client' created but not configured
  tests/playground/test_mcp_client.py:276 - AsyncMock 'mock_response' created but not configured
  tests/playground/test_mcp_client.py:283 - AsyncMock 'mock_client' created but not configured
  tests/playground/test_mcp_client.py:312 - AsyncMock 'mock_mcp_client' created but not configured
  tests/playground/test_mcp_client.py:346 - AsyncMock 'mock_streaming_client' created but not configured
  tests/playground/test_mcp_client.py:378 - AsyncMock 'mock_mcp_client' created but not configured
  tests/playground/test_mcp_client.py:404 - AsyncMock 'mock_mcp_client' created but not configured
  tests/playground/test_playground_api.py:403 - AsyncMock 'mock_openfga' created but not configured
  tests/playground/test_playground_api.py:418 - AsyncMock 'mock_openfga' created but not configured
  tests/playground/test_playground_session.py:42 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:60 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:88 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:103 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:121 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:140 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:171 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:207 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:312 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:329 - AsyncMock 'mock_pool' created but not configured
  tests/playground/test_playground_session.py:345 - AsyncMock 'mock_redis' created but not configured
  tests/playground/test_playground_session.py:346 - AsyncMock 'mock_redis.close' created but not configured
  tests/security/test_permission_inheritance.py:22 - AsyncMock 'client' created but not configured
  tests/smoke/test_ci_startup_smoke.py:168 - AsyncMock 'mock_keycloak' created but not configured
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

