#!/usr/bin/env python3
"""
Setup script for Infisical secrets management
"""

import os

from mcp_server_langgraph.secrets.manager import SecretsManager


def setup_infisical():  # noqa: C901
    """Setup Infisical and create sample secrets"""
    print("\n" + "=" * 60)
    print("Infisical Setup")
    print("=" * 60)

    # Check for credentials
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")

    if not all([client_id, client_secret, project_id]):
        print("\n⚠️  Infisical credentials not found in environment!")
        print("\nTo use Infisical:")
        print("1. Sign up at https://app.infisical.com")
        print("2. Create a project")
        print("3. Generate Universal Auth credentials:")
        print("   - Go to Project Settings → Access Control → Machine Identities")
        print("   - Create a new Machine Identity")
        print("   - Create Universal Auth credentials")
        print("4. Add to your .env file:")
        print("   INFISICAL_CLIENT_ID=your-client-id")
        print("   INFISICAL_CLIENT_SECRET=your-client-secret")
        print("   INFISICAL_PROJECT_ID=your-project-id")
        print("\n💡 For now, the app will use environment variables as fallback.")
        return

    print("\n1. Connecting to Infisical...")
    print(f"   Site: {os.getenv('INFISICAL_SITE_URL', 'https://app.infisical.com')}")
    print(f"   Project: {project_id}")

    secrets_mgr = SecretsManager(client_id=client_id, client_secret=client_secret, project_id=project_id)

    if not secrets_mgr.client:
        print("   ✗ Failed to connect to Infisical")
        return

    print("   ✓ Connected successfully")

    # Create sample secrets
    print("\n2. Creating sample secrets...")
    sample_secrets = {
        "JWT_SECRET_KEY": "super-secret-jwt-key-change-in-production-12345",
        "ANTHROPIC_API_KEY": "sk-ant-api03-...",  # Placeholder
        "DATABASE_PASSWORD": "secure-db-password-123",
        "API_SECRET": "api-secret-key-xyz",
    }

    for key, value in sample_secrets.items():
        try:
            # Try to create, will fail if exists
            success = secrets_mgr.create_secret(key=key, value=value, secret_comment="Sample secret created by setup script")

            if success:
                print(f"   ✓ Created: {key}")
            else:
                print(f"   ℹ️  Skipped: {key} (may already exist)")

        except Exception:
            # Try to update if creation failed
            try:
                success = secrets_mgr.update_secret(key=key, value=value)
                if success:
                    print(f"   ✓ Updated: {key}")
            except Exception as update_error:
                print(f"   ✗ Failed: {key} - {update_error}")

    # Test retrieval
    print("\n3. Testing secret retrieval...")
    for key in sample_secrets:
        try:
            value = secrets_mgr.get_secret(key, use_cache=False)
            if value:
                print(f"   ✓ Retrieved: {key} = {value[:10]}..." if len(value) > 10 else f"   ✓ Retrieved: {key}")
            else:
                print(f"   ✗ Failed to retrieve: {key}")
        except Exception as e:
            print(f"   ✗ Error retrieving {key}: {e}")

    # List all secrets
    print("\n4. Listing all secrets in project...")
    try:
        all_secrets = secrets_mgr.get_all_secrets()
        print(f"   ✓ Found {len(all_secrets)} secrets:")
        for key in all_secrets.keys():
            print(f"      - {key}")
    except Exception as e:
        print(f"   ✗ Failed to list secrets: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("✓ Infisical setup completed!")
    print("=" * 60)

    print("\n📋 Secrets Management:")
    print(
        """
    The application will now:
    1. Try to load secrets from Infisical first
    2. Fall back to environment variables if Infisical unavailable
    3. Use default values as last resort

    Secrets are cached in memory for performance.
    """
    )

    print("\n🔧 Usage in Code:")
    print(
        """
    from mcp_server_langgraph.secrets.manager import get_secrets_manager

    secrets_mgr = get_secrets_manager()

    # Get a secret
    api_key = secrets_mgr.get_secret("ANTHROPIC_API_KEY")

    # Get with fallback
    jwt_key = secrets_mgr.get_secret("JWT_SECRET_KEY", fallback="default")

    # Create/update secrets
    secrets_mgr.create_secret("NEW_SECRET", "value")
    secrets_mgr.update_secret("EXISTING_SECRET", "new_value")
    """
    )

    print("\n🔐 Best Practices:")
    print("1. Never commit secrets to version control")
    print("2. Use Infisical for production secrets")
    print("3. Rotate secrets regularly")
    print("4. Use different secrets per environment (dev/staging/prod)")
    print("5. Enable secret versioning in Infisical")
    print()


if __name__ == "__main__":
    setup_infisical()
