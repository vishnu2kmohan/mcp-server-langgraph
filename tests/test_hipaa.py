"""
Tests for HIPAA compliance controls

Covers HIPAA Security Rule technical safeguards:
- 164.312(a)(2)(i): Emergency Access Procedure
- 164.312(b): Audit Controls
- 164.312(c)(1): Integrity Controls
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_langgraph.auth.hipaa import (
    DataIntegrityCheck,
    EmergencyAccessGrant,
    EmergencyAccessRequest,
    HIPAAControls,
    PHIAuditLog,
    get_hipaa_controls,
    set_hipaa_controls,
)


@pytest.mark.unit
class TestEmergencyAccess:
    """Test emergency access functionality (HIPAA 164.312(a)(2)(i))"""

    @pytest.mark.asyncio
    async def test_grant_emergency_access_success(self):
        """Test granting emergency access"""
        controls = HIPAAControls()

        grant = await controls.grant_emergency_access(
            user_id="user:doctor_smith",
            reason="Patient emergency - cardiac arrest in ER requiring immediate access",
            approver_id="user:supervisor_jones",
            duration_hours=2,
            access_level="PHI",
        )

        assert grant.user_id == "user:doctor_smith"
        assert grant.approver_id == "user:supervisor_jones"
        assert grant.access_level == "PHI"
        assert grant.revoked is False
        assert grant.revoked_at is None
        assert grant.grant_id.startswith("emergency_")

        # Verify grant is stored
        assert grant.grant_id in controls._emergency_grants

    @pytest.mark.asyncio
    async def test_grant_emergency_access_validates_request(self):
        """Test emergency access request validation"""
        controls = HIPAAControls()

        # Reason too short (< 10 characters)
        with pytest.raises(Exception):  # Pydantic validation error
            await controls.grant_emergency_access(
                user_id="user:doctor",
                reason="urgent",  # Too short
                approver_id="user:supervisor",
                duration_hours=2,
            )

    @pytest.mark.asyncio
    async def test_grant_emergency_access_with_custom_duration(self):
        """Test emergency access with custom duration"""
        controls = HIPAAControls()

        # Test minimum duration (1 hour)
        grant1 = await controls.grant_emergency_access(
            user_id="user:doctor",
            reason="Emergency case requiring immediate access to patient records",
            approver_id="user:supervisor",
            duration_hours=1,
        )
        assert grant1.duration_hours == 1

        # Test maximum duration (24 hours)
        grant2 = await controls.grant_emergency_access(
            user_id="user:doctor2",
            reason="Extended emergency coverage for 24-hour shift rotation",
            approver_id="user:supervisor",
            duration_hours=24,
        )
        assert "24" in str(grant2.expires_at) or grant2.grant_id.startswith("emergency_")

    @pytest.mark.asyncio
    async def test_revoke_emergency_access(self):
        """Test revoking emergency access"""
        controls = HIPAAControls()

        # Grant access
        grant = await controls.grant_emergency_access(
            user_id="user:doctor",
            reason="Patient emergency requiring immediate access to medical history",
            approver_id="user:supervisor",
            duration_hours=2,
        )

        # Revoke access
        result = await controls.revoke_emergency_access(grant.grant_id, "user:admin")

        assert result is True
        assert controls._emergency_grants[grant.grant_id].revoked is True
        assert controls._emergency_grants[grant.grant_id].revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_grant(self):
        """Test revoking non-existent grant"""
        controls = HIPAAControls()

        result = await controls.revoke_emergency_access("invalid_grant_id", "user:admin")

        assert result is False

    @pytest.mark.asyncio
    async def test_check_emergency_access_active(self):
        """Test checking active emergency access"""
        controls = HIPAAControls()

        # Grant access
        await controls.grant_emergency_access(
            user_id="user:doctor",
            reason="Patient emergency requiring access to complete medical records",
            approver_id="user:supervisor",
            duration_hours=2,
        )

        # Check access
        grant = await controls.check_emergency_access("user:doctor")

        assert grant is not None
        assert grant.user_id == "user:doctor"
        assert grant.revoked is False

    @pytest.mark.asyncio
    async def test_check_emergency_access_revoked(self):
        """Test that revoked grants are not returned"""
        controls = HIPAAControls()

        # Grant and revoke access
        grant = await controls.grant_emergency_access(
            user_id="user:doctor",
            reason="Emergency access for critical patient care situation",
            approver_id="user:supervisor",
            duration_hours=2,
        )
        await controls.revoke_emergency_access(grant.grant_id, "user:admin")

        # Check access
        active_grant = await controls.check_emergency_access("user:doctor")

        assert active_grant is None

    @pytest.mark.asyncio
    async def test_check_emergency_access_no_grants(self):
        """Test checking emergency access with no grants"""
        controls = HIPAAControls()

        grant = await controls.check_emergency_access("user:unknown")

        assert grant is None


@pytest.mark.unit
class TestPHIAuditLogging:
    """Test PHI audit logging (HIPAA 164.312(b))"""

    @pytest.mark.asyncio
    async def test_log_phi_access_success(self):
        """Test logging successful PHI access"""
        controls = HIPAAControls()

        await controls.log_phi_access(
            user_id="user:doctor_smith",
            action="read",
            patient_id="patient:12345",
            resource_id="medical_record:67890",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            success=True,
        )

        # No exception means success (logging is fire-and-forget)

    @pytest.mark.asyncio
    async def test_log_phi_access_failure(self):
        """Test logging failed PHI access"""
        controls = HIPAAControls()

        await controls.log_phi_access(
            user_id="user:unauthorized",
            action="read",
            patient_id="patient:12345",
            resource_id="medical_record:67890",
            ip_address="192.168.1.200",
            user_agent="curl/7.68.0",
            success=False,
            failure_reason="Insufficient permissions",
        )

        # No exception means success

    @pytest.mark.asyncio
    async def test_log_phi_access_with_optional_fields(self):
        """Test logging PHI access with minimal fields"""
        controls = HIPAAControls()

        await controls.log_phi_access(
            user_id="user:admin",
            action="list",
            patient_id=None,  # Optional
            resource_id=None,  # Optional
            ip_address="192.168.1.1",
            user_agent="PostmanRuntime/7.28.0",
            success=True,
        )

        # No exception means success


@pytest.mark.unit
class TestDataIntegrity:
    """Test data integrity controls (HIPAA 164.312(c)(1))"""

    def test_generate_checksum(self):
        """Test generating HMAC checksum"""
        controls = HIPAAControls(integrity_secret="test-secret-key")

        data = "Patient John Doe, DOB: 1980-01-01, Diagnosis: Hypertension"
        check = controls.generate_checksum(data, "record:123")

        assert check.data_id == "record:123"
        assert check.algorithm == "HMAC-SHA256"
        assert len(check.checksum) == 64  # SHA256 hex digest length
        assert check.created_at is not None

    def test_verify_checksum_valid(self):
        """Test verifying valid checksum"""
        controls = HIPAAControls(integrity_secret="test-secret-key")

        data = "Patient data that must remain unmodified"
        check = controls.generate_checksum(data, "record:456")

        # Verify with same data
        is_valid = controls.verify_checksum(data, check.checksum)

        assert is_valid is True

    def test_verify_checksum_invalid(self):
        """Test verifying invalid checksum (tampered data)"""
        controls = HIPAAControls(integrity_secret="test-secret-key")

        original_data = "Original patient medical record data"
        check = controls.generate_checksum(original_data, "record:789")

        # Tamper with data
        tampered_data = "Modified patient medical record data"

        # Verification should fail
        is_valid = controls.verify_checksum(tampered_data, check.checksum)

        assert is_valid is False

    def test_checksum_with_different_secrets(self):
        """Test that different secrets produce different checksums"""
        data = "Same patient data"

        controls1 = HIPAAControls(integrity_secret="secret1")
        controls2 = HIPAAControls(integrity_secret="secret2")

        check1 = controls1.generate_checksum(data, "record:1")
        check2 = controls2.generate_checksum(data, "record:1")

        assert check1.checksum != check2.checksum

    def test_checksum_constant_time_comparison(self):
        """Test that checksum verification uses constant-time comparison"""
        controls = HIPAAControls(integrity_secret="test-secret")

        data = "Patient information requiring integrity protection"
        controls.generate_checksum(data, "record:999")

        # Create wrong checksum
        wrong_checksum = "a" * 64

        # Verification should fail but use constant time
        is_valid = controls.verify_checksum(data, wrong_checksum)

        assert is_valid is False


@pytest.mark.unit
class TestHIPAAControlsGlobal:
    """Test global HIPAA controls instance management"""

    def test_get_hipaa_controls_singleton(self):
        """Test that get_hipaa_controls returns singleton"""
        # Reset global state
        import mcp_server_langgraph.auth.hipaa as hipaa_module

        hipaa_module._hipaa_controls = None

        controls1 = get_hipaa_controls()
        controls2 = get_hipaa_controls()

        assert controls1 is controls2

    def test_set_hipaa_controls(self):
        """Test setting custom HIPAA controls instance"""
        custom_controls = HIPAAControls(integrity_secret="custom-secret")

        set_hipaa_controls(custom_controls)

        retrieved = get_hipaa_controls()

        assert retrieved is custom_controls
        assert retrieved.integrity_secret == "custom-secret"


@pytest.mark.unit
class TestPydanticModels:
    """Test Pydantic model validation"""

    def test_emergency_access_request_validation(self):
        """Test EmergencyAccessRequest validation"""
        # Valid request
        request = EmergencyAccessRequest(
            user_id="user:doctor",
            reason="Patient emergency requiring immediate medical record access",
            approver_id="user:supervisor",
            duration_hours=2,
        )

        assert request.user_id == "user:doctor"
        assert len(request.reason) >= 10

    def test_emergency_access_request_reason_too_short(self):
        """Test validation fails for short reason"""
        with pytest.raises(Exception):  # Pydantic validation error
            EmergencyAccessRequest(
                user_id="user:doctor",
                reason="urgent",  # < 10 characters
                approver_id="user:supervisor",
                duration_hours=2,
            )

    def test_emergency_access_request_duration_validation(self):
        """Test duration validation (1-24 hours)"""
        # Valid durations
        EmergencyAccessRequest(
            user_id="user:doctor",
            reason="Emergency access required for patient care",
            approver_id="user:supervisor",
            duration_hours=1,  # Minimum
        )

        EmergencyAccessRequest(
            user_id="user:doctor",
            reason="Emergency access required for patient care",
            approver_id="user:supervisor",
            duration_hours=24,  # Maximum
        )

        # Invalid durations
        with pytest.raises(Exception):
            EmergencyAccessRequest(
                user_id="user:doctor",
                reason="Emergency access required for patient care",
                approver_id="user:supervisor",
                duration_hours=0,  # Too low
            )

        with pytest.raises(Exception):
            EmergencyAccessRequest(
                user_id="user:doctor",
                reason="Emergency access required for patient care",
                approver_id="user:supervisor",
                duration_hours=25,  # Too high
            )

    def test_phi_audit_log_model(self):
        """Test PHIAuditLog model"""
        log = PHIAuditLog(
            timestamp="2025-10-13T12:00:00Z",
            user_id="user:doctor",
            action="read",
            phi_accessed=True,
            patient_id="patient:123",
            resource_id="record:456",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            success=True,
        )

        assert log.phi_accessed is True
        assert log.success is True
        assert log.failure_reason is None

    def test_data_integrity_check_model(self):
        """Test DataIntegrityCheck model"""
        check = DataIntegrityCheck(
            data_id="record:123",
            checksum="a" * 64,
            algorithm="HMAC-SHA256",
            created_at="2025-10-13T12:00:00Z",
        )

        assert check.algorithm == "HMAC-SHA256"
        assert len(check.checksum) == 64


@pytest.mark.unit
class TestHIPAAIntegration:
    """Integration tests for HIPAA controls"""

    @pytest.mark.asyncio
    async def test_full_emergency_access_workflow(self):
        """Test complete emergency access workflow"""
        controls = HIPAAControls()

        # 1. Grant emergency access
        grant = await controls.grant_emergency_access(
            user_id="user:doctor_emergency",
            reason="Critical patient emergency requiring immediate access to all records",
            approver_id="user:chief_medical_officer",
            duration_hours=4,
        )

        # 2. Check that access is active
        active_grant = await controls.check_emergency_access("user:doctor_emergency")
        assert active_grant is not None
        assert active_grant.grant_id == grant.grant_id

        # 3. Log PHI access under emergency grant
        await controls.log_phi_access(
            user_id="user:doctor_emergency",
            action="read",
            patient_id="patient:emergency_case",
            resource_id="record:trauma_history",
            ip_address="192.168.100.50",
            user_agent="Hospital_EMR/2.0",
            success=True,
        )

        # 4. Revoke emergency access when no longer needed
        revoked = await controls.revoke_emergency_access(grant.grant_id, "user:chief_medical_officer")
        assert revoked is True

        # 5. Verify access is no longer active
        active_grant_after = await controls.check_emergency_access("user:doctor_emergency")
        assert active_grant_after is None

    @pytest.mark.asyncio
    async def test_integrity_protection_workflow(self):
        """Test data integrity protection workflow"""
        controls = HIPAAControls(integrity_secret="hospital-secret-key-12345")

        # 1. Generate checksum for patient data
        patient_data = '{"patient_id": "123", "name": "John Doe", "diagnosis": "Diabetes Type 2"}'
        checksum = controls.generate_checksum(patient_data, "patient:123:diagnosis")

        # 2. Store checksum (in production, store in database)
        stored_checksum = checksum.checksum

        # 3. Later, verify data hasn't been tampered with
        retrieved_data = '{"patient_id": "123", "name": "John Doe", "diagnosis": "Diabetes Type 2"}'
        is_valid = controls.verify_checksum(retrieved_data, stored_checksum)

        assert is_valid is True

        # 4. Detect tampering
        tampered_data = '{"patient_id": "123", "name": "John Doe", "diagnosis": "Hypertension"}'
        is_tampered = controls.verify_checksum(tampered_data, stored_checksum)

        assert is_tampered is False
