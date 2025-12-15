/**
 * Global Setup for E2E Tests with Backend Integration
 *
 * Runs once before all tests when BACKEND_ENABLED=true.
 * Verifies backend services are available and healthy.
 */

async function globalSetup(): Promise<void> {
  console.log('\n🚀 E2E Global Setup: Verifying backend services...\n');

  const services = [
    // API server is on port 8000, with trailing slash to avoid redirect
    { name: 'API Server', url: process.env.API_URL || 'http://localhost:8000/health/' },
    // Keycloak is on port 9082 with /authn prefix
    // Note: /authn/health/ready returns 404; use realm endpoint to verify readiness
    { name: 'Keycloak', url: (process.env.KEYCLOAK_URL || 'http://localhost:9082') + '/authn/realms/default' },
    // Qdrant vector database on port 9333 (test environment)
    { name: 'Qdrant', url: process.env.QDRANT_URL || 'http://localhost:9333/' },
  ];

  for (const service of services) {
    try {
      const response = await fetch(service.url, { method: 'GET' });
      if (response.ok) {
        console.log(`  ✅ ${service.name} is healthy`);
      } else {
        console.warn(`  ⚠️ ${service.name} returned ${response.status}`);
      }
    } catch (error) {
      console.warn(`  ❌ ${service.name} not reachable: ${error}`);
    }
  }

  console.log('\n');
}

export default globalSetup;
