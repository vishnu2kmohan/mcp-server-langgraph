"""
Unit tests for PII Detection

Tests the PII detection patterns for identifying sensitive information
before it's sent to LLMs. Required for GDPR, HIPAA, and SOC2 compliance.

TDD: RED phase - these tests define expected behavior before implementation.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.pii]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pii_detection_types")
class TestPIIDetectionTypes:
    """Test suite for PII type definitions"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_pii_type_enum_exists(self):
        """GIVEN the privacy module
        WHEN importing PIIType
        THEN it should be an enum with expected values
        """
        from mcp_server_langgraph.privacy.detectors import PIIType

        assert PIIType.EMAIL is not None
        assert PIIType.PHONE is not None
        assert PIIType.SSN is not None
        assert PIIType.CREDIT_CARD is not None
        assert PIIType.NAME is not None
        assert PIIType.ADDRESS is not None
        assert PIIType.IP_ADDRESS is not None
        assert PIIType.DOB is not None

    def test_pii_detection_model_exists(self):
        """GIVEN the privacy module
        WHEN importing PIIDetection
        THEN it should be a Pydantic model
        """
        from mcp_server_langgraph.privacy.detectors import PIIDetection

        detection = PIIDetection(
            pii_type="EMAIL",
            value="test@example.com",
            start=0,
            end=16,
        )
        assert detection.pii_type == "EMAIL"
        assert detection.value == "test@example.com"
        assert detection.start == 0
        assert detection.end == 16


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pii_detection_email")
class TestPIIDetectionEmail:
    """Test suite for email detection"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_email_simple(self):
        """GIVEN text containing a simple email
        WHEN detecting PII
        THEN the email should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Contact me at test@example.com please"
        detections = detect_pii(text)

        email_detections = [d for d in detections if d.pii_type == "EMAIL"]
        assert len(email_detections) == 1
        assert email_detections[0].value == "test@example.com"

    def test_detect_multiple_emails(self):
        """GIVEN text containing multiple emails
        WHEN detecting PII
        THEN all emails should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Contact john@example.com or jane@test.org"
        detections = detect_pii(text)

        email_detections = [d for d in detections if d.pii_type == "EMAIL"]
        assert len(email_detections) == 2

    def test_detect_email_with_subdomain(self):
        """GIVEN text containing email with subdomain
        WHEN detecting PII
        THEN the email should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Email: user@mail.company.co.uk"
        detections = detect_pii(text)

        email_detections = [d for d in detections if d.pii_type == "EMAIL"]
        assert len(email_detections) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pii_detection_phone")
class TestPIIDetectionPhone:
    """Test suite for phone number detection"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_us_phone_number(self):
        """GIVEN text containing US phone number
        WHEN detecting PII
        THEN the phone number should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Call me at 555-123-4567"
        detections = detect_pii(text)

        phone_detections = [d for d in detections if d.pii_type == "PHONE"]
        assert len(phone_detections) == 1

    def test_detect_phone_with_parens(self):
        """GIVEN text containing phone with parentheses
        WHEN detecting PII
        THEN the phone number should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Phone: (555) 123-4567"
        detections = detect_pii(text)

        phone_detections = [d for d in detections if d.pii_type == "PHONE"]
        assert len(phone_detections) == 1

    def test_detect_international_phone(self):
        """GIVEN text containing international phone number
        WHEN detecting PII
        THEN the phone number should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "International: +1-555-123-4567"
        detections = detect_pii(text)

        phone_detections = [d for d in detections if d.pii_type == "PHONE"]
        assert len(phone_detections) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pii_detection_ssn")
class TestPIIDetectionSSN:
    """Test suite for SSN detection"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_ssn_with_dashes(self):
        """GIVEN text containing SSN with dashes
        WHEN detecting PII
        THEN the SSN should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "SSN: 123-45-6789"
        detections = detect_pii(text)

        ssn_detections = [d for d in detections if d.pii_type == "SSN"]
        assert len(ssn_detections) == 1

    def test_detect_ssn_without_dashes(self):
        """GIVEN text containing SSN without dashes
        WHEN detecting PII
        THEN the SSN should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "SSN: 123456789"
        detections = detect_pii(text)

        ssn_detections = [d for d in detections if d.pii_type == "SSN"]
        assert len(ssn_detections) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pii_detection_credit_card")
class TestPIIDetectionCreditCard:
    """Test suite for credit card detection"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_credit_card_with_spaces(self):
        """GIVEN text containing credit card with spaces
        WHEN detecting PII
        THEN the credit card should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Card: 4111 1111 1111 1111"
        detections = detect_pii(text)

        cc_detections = [d for d in detections if d.pii_type == "CREDIT_CARD"]
        assert len(cc_detections) == 1

    def test_detect_credit_card_with_dashes(self):
        """GIVEN text containing credit card with dashes
        WHEN detecting PII
        THEN the credit card should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Card: 4111-1111-1111-1111"
        detections = detect_pii(text)

        cc_detections = [d for d in detections if d.pii_type == "CREDIT_CARD"]
        assert len(cc_detections) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pii_detection_ip")
class TestPIIDetectionIPAddress:
    """Test suite for IP address detection"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_ipv4_address(self):
        """GIVEN text containing IPv4 address
        WHEN detecting PII
        THEN the IP address should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Server IP: 192.168.1.100"
        detections = detect_pii(text)

        ip_detections = [d for d in detections if d.pii_type == "IP_ADDRESS"]
        assert len(ip_detections) == 1

    def test_ignore_localhost(self):
        """GIVEN text containing localhost IP
        WHEN detecting PII
        THEN localhost should not be flagged as PII
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Connect to 127.0.0.1"
        detections = detect_pii(text)

        ip_detections = [d for d in detections if d.pii_type == "IP_ADDRESS"]
        # Localhost is typically not considered sensitive PII
        assert len(ip_detections) == 0


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pii_detection_dob")
class TestPIIDetectionDOB:
    """Test suite for date of birth detection"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_dob_mm_dd_yyyy(self):
        """GIVEN text containing DOB in MM/DD/YYYY format
        WHEN detecting PII
        THEN the DOB should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Birth date: 12/25/1990"
        detections = detect_pii(text)

        dob_detections = [d for d in detections if d.pii_type == "DOB"]
        assert len(dob_detections) == 1

    def test_detect_dob_yyyy_mm_dd(self):
        """GIVEN text containing DOB in YYYY-MM-DD format
        WHEN detecting PII
        THEN the DOB should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "DOB: 1990-12-25"
        detections = detect_pii(text)

        dob_detections = [d for d in detections if d.pii_type == "DOB"]
        assert len(dob_detections) == 1


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pii_detection_combined")
class TestPIIDetectionCombined:
    """Test suite for combined PII detection scenarios"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_detect_multiple_pii_types(self):
        """GIVEN text containing multiple PII types
        WHEN detecting PII
        THEN all PII types should be detected
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Contact john@example.com at 555-123-4567. SSN: 123-45-6789"
        detections = detect_pii(text)

        pii_types = {d.pii_type for d in detections}
        assert "EMAIL" in pii_types
        assert "PHONE" in pii_types
        assert "SSN" in pii_types

    def test_detect_no_pii_in_clean_text(self):
        """GIVEN text containing no PII
        WHEN detecting PII
        THEN no detections should be returned
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "This is a regular sentence with no personal information."
        detections = detect_pii(text)

        assert len(detections) == 0

    def test_detect_pii_returns_positions(self):
        """GIVEN text containing PII
        WHEN detecting PII
        THEN detection should include start and end positions
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Email: test@example.com"
        detections = detect_pii(text)

        assert len(detections) == 1
        assert detections[0].start == 7
        assert detections[0].end == 23

    def test_empty_text_returns_empty_list(self):
        """GIVEN empty text
        WHEN detecting PII
        THEN empty list should be returned
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        detections = detect_pii("")
        assert detections == []

    def test_none_text_returns_empty_list(self):
        """GIVEN None as text
        WHEN detecting PII
        THEN empty list should be returned
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        detections = detect_pii(None)  # type: ignore[arg-type]
        assert detections == []


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_pii_detection_feature_flag")
class TestPIIDetectionFeatureFlag:
    """Test suite for PII detection feature flag integration"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_pii_detection_respects_feature_flag_disabled(self):
        """GIVEN PII detection feature flag is disabled
        WHEN detecting PII
        THEN no detections should occur (skip detection)
        """
        from unittest.mock import patch

        from mcp_server_langgraph.privacy.detectors import detect_pii

        with patch(
            "mcp_server_langgraph.privacy.detectors.is_feature_enabled",
            return_value=False,
        ):
            text = "Contact: test@example.com"
            detections = detect_pii(text)

            # When feature is disabled, detection is skipped
            assert len(detections) == 0
