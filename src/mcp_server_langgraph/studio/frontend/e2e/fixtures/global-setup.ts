/**
 * Global Setup for E2E Tests with Backend Integration
 *
 * Runs once before all tests when BACKEND_ENABLED=true.
 * Verifies backend services are available and healthy.
 */

async function globalSetup(): Promise<void> {
  console.log('\n🚀 E2E Global Setup: Verifying backend services...\n');

  const services = [
    { name: 'API Server', url: process.env.API_URL || 'http://localhost:8003/health' },
    { name: 'Keycloak', url: (process.env.KEYCLOAK_URL || 'http://localhost:9082') + '/health/ready' },
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
