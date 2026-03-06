"""
HIPAA PHI Protection Compliance Tests

Tests verifying HIPAA (Health Insurance Portability and Accountability Act)
compliance for PHI (Protected Health Information) detection and tokenization.

HIPAA Rules Covered:
- Privacy Rule (45 CFR 164.502-164.514): Use and disclosure of PHI
- Security Rule (45 CFR 164.308-164.312): Administrative/Technical safeguards
- Minimum Necessary Rule (45 CFR 164.502(b)): Limit PHI exposure

PHI Identifiers (18 HIPAA Identifiers):
This module tests detection of common PHI identifiers including:
- Names, Dates, Phone/Fax, Email, SSN, Medical Record Numbers
- IP Addresses, Account Numbers, Certificate/License Numbers

TDD: RED phase - these tests define expected HIPAA compliance behavior.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.compliance, pytest.mark.pii, pytest.mark.hipaa]


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_hipaa_privacy_rule")
class TestHIPAAPrivacyRule:
    """HIPAA Privacy Rule (45 CFR 164.502-164.514): Use and Disclosure of PHI.

    PHI may only be used or disclosed as permitted by HIPAA.
    Tokenization ensures PHI is protected during AI processing.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_patient_email_is_protected(self):
        """GIVEN patient record containing email
        WHEN processing with AI/LLM
        THEN email must be tokenized (not exposed)

        Requirement: 45 CFR 164.502 - Uses and disclosures of PHI
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        patient_note = "Patient contact: patient@hospital.org"

        tokenized, lookup = tokenizer.tokenize(patient_note)

        # PHI (email) must not be exposed to AI
        assert "patient@hospital.org" not in tokenized
        # But can be restored for authorized use
        restored = tokenizer.untokenize(tokenized, lookup)
        assert restored == patient_note

    def test_patient_phone_is_protected(self):
        """GIVEN patient record containing phone number
        WHEN processing with AI/LLM
        THEN phone must be tokenized

        Requirement: 45 CFR 164.502 - PHI protection
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        patient_note = "Emergency contact: 555-867-5309"

        tokenized, lookup = tokenizer.tokenize(patient_note)

        assert "555-867-5309" not in tokenized

    def test_patient_ssn_is_protected(self):
        """GIVEN patient record containing SSN
        WHEN processing with AI/LLM
        THEN SSN must be tokenized

        Requirement: 45 CFR 164.514(b)(2)(i) - SSN is a HIPAA identifier
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        patient_record = "Patient SSN: 123-45-6789"

        tokenized, _ = tokenizer.tokenize(patient_record)

        assert "123-45-6789" not in tokenized

    def test_patient_dob_is_protected(self):
        """GIVEN patient record containing date of birth
        WHEN processing with AI/LLM
        THEN DOB must be tokenized (ages over 89 are PHI)

        Requirement: 45 CFR 164.514(b)(2)(i) - Dates are HIPAA identifiers
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        patient_record = "Patient DOB: 1935-05-15"

        tokenized, _ = tokenizer.tokenize(patient_record)

        assert "1935-05-15" not in tokenized


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_hipaa_minimum_necessary")
class TestHIPAAMinimumNecessaryRule:
    """HIPAA Minimum Necessary Rule (45 CFR 164.502(b)).

    Covered entities must make reasonable efforts to limit PHI
    to the minimum necessary to accomplish the intended purpose.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_only_phi_is_tokenized_not_entire_record(self):
        """GIVEN medical record with mixed content
        WHEN tokenizing for AI processing
        THEN only PHI should be replaced, clinical info preserved

        Requirement: 45 CFR 164.502(b) - Minimum necessary principle
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        medical_note = """
        Patient: John Doe
        Email: john.doe@example.com
        Phone: 555-123-4567

        Chief Complaint: Persistent headache for 3 days
        Diagnosis: Tension-type headache
        Treatment: Ibuprofen 400mg as needed
        """

        tokenized, _ = tokenizer.tokenize(medical_note)

        # PHI should be tokenized
        assert "john.doe@example.com" not in tokenized
        assert "555-123-4567" not in tokenized

        # Clinical information should be preserved for AI analysis
        assert "Persistent headache" in tokenized
        assert "Tension-type headache" in tokenized
        assert "Ibuprofen" in tokenized

    def test_phi_detection_is_comprehensive(self):
        """GIVEN text with multiple PHI types
        WHEN detecting PHI
        THEN all PHI types should be identified

        Requirement: 45 CFR 164.502(b) - Complete PHI identification
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = """
        Patient: Jane Smith
        DOB: 1980-06-20
        SSN: 987-65-4321
        Email: jane.smith@health.org
        Phone: (555) 999-8888
        IP: 10.0.0.50
        """

        detections = detect_pii(text)
        detected_types = {d.pii_type for d in detections}

        # All common PHI identifiers should be detected
        assert "EMAIL" in detected_types
        assert "PHONE" in detected_types
        assert "SSN" in detected_types
        assert "DOB" in detected_types
        assert "IP_ADDRESS" in detected_types


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_hipaa_security_rule_administrative")
class TestHIPAASecurityRuleAdministrative:
    """HIPAA Security Rule - Administrative Safeguards (45 CFR 164.308).

    Covered entities must implement administrative actions, policies,
    and procedures to protect ePHI.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_phi_access_requires_lookup_table(self):
        """GIVEN tokenized PHI
        WHEN attempting to access original values
        THEN lookup table (authorization) is required

        Requirement: 45 CFR 164.308(a)(4) - Access management
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        phi = "Patient SSN: 123-45-6789"

        tokenized, lookup = tokenizer.tokenize(phi)

        # Without lookup table, PHI cannot be recovered
        empty_lookup: dict[str, str] = {}
        result = tokenizer.untokenize(tokenized, empty_lookup)
        assert "123-45-6789" not in result

        # With lookup table (authorization), PHI can be recovered
        result_authorized = tokenizer.untokenize(tokenized, lookup)
        assert "123-45-6789" in result_authorized

    def test_phi_lookup_can_be_audited(self):
        """GIVEN PHI tokenization
        WHEN examining lookup table
        THEN all PHI mappings should be visible for audit

        Requirement: 45 CFR 164.308(a)(1)(ii)(D) - Audit controls
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        record = "Contact: patient@example.com, Phone: 555-111-2222"

        _, lookup = tokenizer.tokenize(record)

        # Lookup table provides auditable record of all PHI
        assert len(lookup) >= 2  # At least email and phone
        phi_values = list(lookup.values())
        assert "patient@example.com" in phi_values
        assert "555-111-2222" in phi_values


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_hipaa_security_rule_technical")
class TestHIPAASecurityRuleTechnical:
    """HIPAA Security Rule - Technical Safeguards (45 CFR 164.312).

    Technical measures to protect ePHI including encryption,
    access controls, and transmission security.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_phi_lookup_supports_encryption(self):
        """GIVEN PHI lookup table
        WHEN storing or transmitting
        THEN encryption must be available

        Requirement: 45 CFR 164.312(a)(2)(iv) - Encryption
        """
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()
        table.store("token1", "patient@hospital.org")
        table.store("token2", "123-45-6789")

        # Encryption available for transmission
        encrypted = table.export_encrypted()
        assert encrypted is not None
        assert isinstance(encrypted, (str, bytes, dict))

        # Can be decrypted on authorized receiver
        restored = EncryptedLookupTable.from_encrypted(encrypted)
        assert restored.retrieve("token1") == "patient@hospital.org"

    def test_tokenized_phi_safe_for_transmission(self):
        """GIVEN PHI that needs AI processing
        WHEN tokenizing before transmission
        THEN no PHI should be in transmitted data

        Requirement: 45 CFR 164.312(e)(1) - Transmission security
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        sensitive_record = """
        Name: John Patient
        SSN: 111-22-3333
        Email: john.patient@clinic.org
        Phone: 555-444-3333
        Medical Record: MR-12345
        """

        tokenized, _ = tokenizer.tokenize(sensitive_record)

        # Data transmitted to AI has no PHI
        assert "111-22-3333" not in tokenized
        assert "john.patient@clinic.org" not in tokenized
        assert "555-444-3333" not in tokenized

    def test_phi_integrity_preserved_through_tokenization(self):
        """GIVEN PHI that is tokenized and untokenized
        WHEN completing the round-trip
        THEN data integrity must be maintained

        Requirement: 45 CFR 164.312(c)(1) - Integrity controls
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original_record = """
        Patient: Jane Doe
        Contact: jane.doe@hospital.org
        SSN: 999-88-7777
        Emergency Phone: 555-999-8888
        """

        tokenized, lookup = tokenizer.tokenize(original_record)
        restored = tokenizer.untokenize(tokenized, lookup)

        # Perfect integrity - no data loss or corruption
        assert restored == original_record


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_hipaa_18_identifiers")
class TestHIPAA18Identifiers:
    """HIPAA 18 PHI Identifiers (45 CFR 164.514(b)(2)).

    HIPAA defines 18 categories of identifiers that must be protected.
    This test suite verifies detection of commonly digitally-transmitted ones.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_identifier_email_detected(self):
        """HIPAA Identifier: Electronic mail addresses"""
        from mcp_server_langgraph.privacy.detectors import detect_pii

        detections = detect_pii("Email: patient@example.org")
        assert any(d.pii_type == "EMAIL" for d in detections)

    def test_identifier_phone_detected(self):
        """HIPAA Identifier: Telephone numbers"""
        from mcp_server_langgraph.privacy.detectors import detect_pii

        detections = detect_pii("Phone: 555-123-4567")
        assert any(d.pii_type == "PHONE" for d in detections)

    def test_identifier_ssn_detected(self):
        """HIPAA Identifier: Social Security numbers"""
        from mcp_server_langgraph.privacy.detectors import detect_pii

        detections = detect_pii("SSN: 123-45-6789")
        assert any(d.pii_type == "SSN" for d in detections)

    def test_identifier_dob_detected(self):
        """HIPAA Identifier: All elements of dates related to an individual"""
        from mcp_server_langgraph.privacy.detectors import detect_pii

        detections = detect_pii("DOB: 1990-05-15")
        assert any(d.pii_type == "DOB" for d in detections)

    def test_identifier_ip_address_detected(self):
        """HIPAA Identifier: IP addresses"""
        from mcp_server_langgraph.privacy.detectors import detect_pii

        detections = detect_pii("IP: 192.168.10.50")
        assert any(d.pii_type == "IP_ADDRESS" for d in detections)


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_hipaa_breach_prevention")
class TestHIPAABreachPrevention:
    """HIPAA Breach Notification Rule (45 CFR 164.400-164.414).

    Tokenization helps prevent breaches by ensuring PHI is not
    exposed even if AI system logs are compromised.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_tokenized_phi_not_breach_if_exposed(self):
        """GIVEN properly tokenized PHI
        WHEN the tokenized text is exposed
        THEN it should not constitute a PHI breach

        Requirement: 45 CFR 164.402 - Breach definition
        Note: Properly de-identified data is not a breach
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        phi = "Patient SSN: 123-45-6789, Email: patient@hospital.org"

        tokenized, _ = tokenizer.tokenize(phi)

        # Tokenized text contains no actual PHI
        assert "123-45-6789" not in tokenized
        assert "patient@hospital.org" not in tokenized
        # Only tokens visible, no usable PHI
        assert "<<" in tokenized

    def test_phi_values_centralized_for_protection(self):
        """GIVEN multiple PHI elements across a record
        WHEN tokenizing
        THEN all PHI should be centralized in lookup table

        Requirement: 45 CFR 164.308(a)(1) - Risk management
        Centralized PHI storage reduces attack surface
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        record = """
        Email 1: patient1@clinic.org
        Email 2: patient2@clinic.org
        Phone 1: 555-111-1111
        Phone 2: 555-222-2222
        SSN: 111-22-3333
        """

        tokenized, lookup = tokenizer.tokenize(record)

        # All PHI centralized in lookup table
        phi_values = list(lookup.values())
        assert "patient1@clinic.org" in phi_values
        assert "patient2@clinic.org" in phi_values
        assert "555-111-1111" in phi_values
        assert "555-222-2222" in phi_values
        assert "111-22-3333" in phi_values

        # Tokenized text has no PHI
        for phi in phi_values:
            assert phi not in tokenized


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_hipaa_business_associate")
class TestHIPAABusinessAssociate:
    """HIPAA Business Associate Requirements (45 CFR 164.502(e)).

    When using third-party AI services, covered entities must
    ensure PHI protection through tokenization.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_phi_protected_before_third_party_ai(self):
        """GIVEN PHI that needs AI processing
        WHEN sending to third-party AI service
        THEN PHI must be tokenized first

        Requirement: 45 CFR 164.502(e) - Business associate contracts
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()

        # Simulated patient record
        patient_data = """
        Patient: John Smith
        SSN: 555-12-3456
        Email: john.smith@patient.org
        DOB: 1985-03-20
        Chief Complaint: Lower back pain
        """

        # Tokenize before sending to third-party AI
        data_for_ai, lookup_kept_internal = tokenizer.tokenize(patient_data)

        # Data sent to AI has no PHI
        assert "555-12-3456" not in data_for_ai
        assert "john.smith@patient.org" not in data_for_ai
        assert "1985-03-20" not in data_for_ai

        # Clinical data preserved for AI analysis
        assert "Lower back pain" in data_for_ai

        # Lookup table stays internal (not shared with BA)
        assert "john.smith@patient.org" in lookup_kept_internal.values()
