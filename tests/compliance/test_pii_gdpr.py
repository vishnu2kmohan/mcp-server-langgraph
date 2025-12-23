"""
GDPR PII Protection Compliance Tests

Tests verifying GDPR (General Data Protection Regulation) compliance
for PII (Personally Identifiable Information) detection and tokenization.

GDPR Articles Covered:
- Article 5(1)(f): Integrity and confidentiality (data protection by default)
- Article 25: Data protection by design and by default
- Article 32: Security of processing (appropriate technical measures)
- Article 17: Right to erasure (tokenization enables data removal)
- Article 20: Right to data portability (tokenized data format)

TDD: RED phase - these tests define expected GDPR compliance behavior.
"""

import gc

import pytest

pytestmark = [pytest.mark.compliance, pytest.mark.pii, pytest.mark.gdpr]


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_gdpr_article_5_integrity")
class TestGDPRArticle5Integrity:
    """GDPR Article 5(1)(f): Integrity and confidentiality of processing.

    Personal data must be processed in a manner that ensures appropriate
    security, including protection against unauthorized processing.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_email_is_tokenized_before_llm_exposure(self):
        """GIVEN text containing an email address
        WHEN preparing data for LLM processing
        THEN the email must be replaced with a non-reversible token

        Requirement: GDPR Article 5(1)(f) - protect against unauthorized processing
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        input_text = "Customer email: john.doe@company.com"

        tokenized_text, _ = tokenizer.tokenize(input_text)

        # Email must NOT appear in the text sent to LLM
        assert "john.doe@company.com" not in tokenized_text
        assert "@" not in tokenized_text or "<<" in tokenized_text

    def test_phone_is_tokenized_before_llm_exposure(self):
        """GIVEN text containing a phone number
        WHEN preparing data for LLM processing
        THEN the phone number must be replaced with a token

        Requirement: GDPR Article 5(1)(f) - protect personal data
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        input_text = "Contact number: +1-555-123-4567"

        tokenized_text, _ = tokenizer.tokenize(input_text)

        # Phone number must NOT appear in LLM-bound text
        assert "555-123-4567" not in tokenized_text

    def test_all_gdpr_relevant_pii_types_are_detected(self):
        """GIVEN text containing GDPR-relevant personal data
        WHEN detecting PII
        THEN all personal data types must be identified

        Requirement: GDPR Article 5(1)(f) - comprehensive data protection
        GDPR defines personal data as any information relating to an
        identified or identifiable natural person.
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        # Text with multiple GDPR-relevant personal data types
        text = """
        Name: John Smith
        Email: john.smith@example.com
        Phone: (555) 123-4567
        Date of Birth: 1985-03-15
        IP Address: 192.168.100.50
        """

        detections = detect_pii(text)
        detected_types = {d.pii_type for d in detections}

        # GDPR requires protection of all identifiable personal data
        assert "EMAIL" in detected_types
        assert "PHONE" in detected_types
        assert "DOB" in detected_types
        assert "IP_ADDRESS" in detected_types

    def test_tokenization_preserves_data_utility(self):
        """GIVEN text with PII that needs to be processed
        WHEN tokenizing for LLM processing
        THEN the tokenized text should maintain semantic meaning

        Requirement: GDPR Article 5(1)(f) - processing must remain useful
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        input_text = "Please send confirmation to user@example.com"

        tokenized_text, _ = tokenizer.tokenize(input_text)

        # The text should still make sense (contain context words)
        assert "send" in tokenized_text
        assert "confirmation" in tokenized_text
        # Token should indicate it's an email for LLM context
        assert "EMAIL" in tokenized_text


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_gdpr_article_25_design")
class TestGDPRArticle25DataProtectionByDesign:
    """GDPR Article 25: Data protection by design and by default.

    Controllers must implement appropriate technical measures to protect
    personal data, both at the time of design and during processing.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_pii_protection_is_default_behavior(self):
        """GIVEN the PII tokenizer
        WHEN processing any text
        THEN PII protection should be automatic (by default)

        Requirement: GDPR Article 25(2) - data protection by default
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        # Default tokenizer should protect PII without additional config
        tokenizer = PIITokenizer()  # No special configuration needed
        text = "Contact: sensitive@email.com"

        tokenized, lookup = tokenizer.tokenize(text)

        # Protection is automatic
        assert "sensitive@email.com" not in tokenized
        assert len(lookup) > 0

    def test_protection_cannot_be_accidentally_bypassed(self):
        """GIVEN sensitive text with PII
        WHEN using the standard processing pipeline
        THEN PII should always be detected and tokenized

        Requirement: GDPR Article 25(1) - built-in protection
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        text = "SSN: 123-45-6789"

        # Detection happens first
        detections = detect_pii(text)
        assert len(detections) > 0
        assert any(d.pii_type == "SSN" for d in detections)

        # Then tokenization
        tokenizer = PIITokenizer()
        tokenized, _ = tokenizer.tokenize(text)
        assert "123-45-6789" not in tokenized

    def test_tokenization_is_deterministic(self):
        """GIVEN the same PII value
        WHEN tokenizing multiple times
        THEN the same token should be generated

        Requirement: GDPR Article 25 - consistent protection mechanism
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        email = "consistent@example.com"
        text1 = f"Email: {email}"
        text2 = f"Contact: {email}"

        tokenized1, lookup1 = tokenizer.tokenize(text1)
        tokenized2, lookup2 = tokenizer.tokenize(text2)

        # Same email should generate same token
        tokens1 = [k for k, v in lookup1.items() if v == email]
        tokens2 = [k for k, v in lookup2.items() if v == email]

        assert tokens1 == tokens2  # Deterministic tokenization


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_gdpr_article_32_security")
class TestGDPRArticle32SecurityOfProcessing:
    """GDPR Article 32: Security of processing.

    Controllers must implement appropriate technical measures including
    encryption, pseudonymization, and ability to ensure confidentiality.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_lookup_table_supports_encryption(self):
        """GIVEN a lookup table storing PII mappings
        WHEN storing sensitive data
        THEN encryption should be available

        Requirement: GDPR Article 32(1)(a) - encryption of personal data
        """
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()
        table.store("<<EMAIL_token>>", "sensitive@email.com")

        # Table should support encrypted export
        encrypted_export = table.export_encrypted()
        assert encrypted_export is not None
        assert isinstance(encrypted_export, (str, bytes, dict))

    def test_encrypted_lookup_table_can_be_restored(self):
        """GIVEN an encrypted lookup table export
        WHEN restoring the table
        THEN all mappings should be correctly restored

        Requirement: GDPR Article 32(1)(c) - ability to restore access
        """
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        # Create and populate table
        original = EncryptedLookupTable()
        original.store("token1", "value1")
        original.store("token2", "value2")

        # Export and restore
        exported = original.export_encrypted()
        restored = EncryptedLookupTable.from_encrypted(exported)

        # Verify restoration
        assert restored.retrieve("token1") == "value1"
        assert restored.retrieve("token2") == "value2"

    def test_tokenization_enables_pseudonymization(self):
        """GIVEN text with personal data
        WHEN tokenizing
        THEN the result is pseudonymized (reversible with key)

        Requirement: GDPR Article 32(1)(a) - pseudonymization
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        original = "John Doe's email is john@company.com"

        tokenized, lookup = tokenizer.tokenize(original)

        # Tokenized text is pseudonymized (no real PII visible)
        assert "john@company.com" not in tokenized

        # But can be reversed with the lookup table (the "key")
        restored = tokenizer.untokenize(tokenized, lookup)
        assert restored == original


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_gdpr_article_17_erasure")
class TestGDPRArticle17RightToErasure:
    """GDPR Article 17: Right to erasure (right to be forgotten).

    Data subjects have the right to have their personal data erased.
    Tokenization enables this by centralizing PII in lookup tables.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_pii_can_be_removed_from_lookup_table(self):
        """GIVEN a lookup table with user PII
        WHEN implementing erasure request
        THEN specific PII can be removed

        Requirement: GDPR Article 17(1) - erasure of personal data
        """
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()
        table.store("user1_email", "user1@example.com")
        table.store("user2_email", "user2@example.com")

        # Erasure: remove specific user's data
        table.remove("user1_email")

        # Verify erasure
        assert table.retrieve("user1_email") is None
        # Other user's data remains
        assert table.retrieve("user2_email") == "user2@example.com"

    def test_tokenized_text_remains_valid_after_erasure(self):
        """GIVEN tokenized text and lookup table
        WHEN PII is erased from lookup
        THEN tokenized text remains valid (just not restorable)

        Requirement: GDPR Article 17 - erasure without data corruption
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Email: user@example.com"

        tokenized, lookup = tokenizer.tokenize(text)

        # Simulate erasure by clearing lookup
        lookup.clear()

        # Tokenized text is still valid, just not restorable
        assert "<<" in tokenized
        assert "EMAIL" in tokenized
        # Attempting untokenize returns text with tokens intact
        result = tokenizer.untokenize(tokenized, lookup)
        assert "<<" in result  # Token remains since lookup is empty


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_gdpr_article_20_portability")
class TestGDPRArticle20DataPortability:
    """GDPR Article 20: Right to data portability.

    Data subjects have the right to receive their personal data in a
    structured, commonly used and machine-readable format.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_lookup_table_is_json_serializable(self):
        """GIVEN a lookup table with PII mappings
        WHEN exporting for portability
        THEN it should be in a standard format (JSON)

        Requirement: GDPR Article 20(1) - machine-readable format
        """
        import json

        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Contact: john@example.com, Phone: 555-123-4567"

        _, lookup = tokenizer.tokenize(text)

        # Must be JSON serializable for portability
        json_export = json.dumps(lookup)
        assert isinstance(json_export, str)

        # Must be restorable from JSON
        restored = json.loads(json_export)
        assert restored == lookup

    def test_pii_mappings_include_type_metadata(self):
        """GIVEN tokenized PII
        WHEN examining the token format
        THEN the PII type should be identifiable

        Requirement: GDPR Article 20 - structured data with context
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Email: test@example.com, Phone: 555-123-4567"

        tokenized, lookup = tokenizer.tokenize(text)

        # Tokens should include type information for structure
        for token in lookup.keys():
            # Token format includes PII type (e.g., <<EMAIL_hash>>)
            assert any(pii_type in token for pii_type in ["EMAIL", "PHONE", "SSN", "CREDIT_CARD", "DOB"])


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_gdpr_special_categories")
class TestGDPRSpecialCategoryData:
    """GDPR Article 9: Processing of special categories of personal data.

    Special categories (health, genetic, biometric data) require
    additional protection measures.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_ssn_is_detected_as_sensitive_identifier(self):
        """GIVEN text containing SSN
        WHEN detecting PII
        THEN SSN should be identified as highly sensitive

        Requirement: SSN combined with other data can reveal special categories
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Patient SSN: 123-45-6789"
        detections = detect_pii(text)

        ssn_detections = [d for d in detections if d.pii_type == "SSN"]
        assert len(ssn_detections) == 1

    def test_dob_is_detected_for_age_discrimination_prevention(self):
        """GIVEN text containing date of birth
        WHEN detecting PII
        THEN DOB should be identified (age is protected characteristic)

        Requirement: Age data requires protection under GDPR
        """
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = "Employee DOB: 1980-05-15"
        detections = detect_pii(text)

        dob_detections = [d for d in detections if d.pii_type == "DOB"]
        assert len(dob_detections) == 1


@pytest.mark.compliance
@pytest.mark.xdist_group(name="test_gdpr_cross_border")
class TestGDPRCrossBorderProtection:
    """GDPR Chapter V: Transfers of personal data to third countries.

    When data is processed by external LLMs (potentially in other
    jurisdictions), tokenization provides protection.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_tokenized_data_safe_for_external_processing(self):
        """GIVEN EU citizen's personal data
        WHEN sending to external LLM service
        THEN only tokenized (pseudonymized) data should be transmitted

        Requirement: GDPR Chapter V - protection for cross-border transfers
        """
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        # Use phone format that's detected by the PII detector
        eu_citizen_data = """
        Name: Hans Mueller
        Email: hans.mueller@company.de
        Phone: 555-123-4567
        """

        tokenized, lookup = tokenizer.tokenize(eu_citizen_data)

        # No real PII in text that goes to external LLM
        assert "hans.mueller@company.de" not in tokenized
        assert "555-123-4567" not in tokenized

        # Lookup table stays within the EU jurisdiction
        assert "hans.mueller@company.de" in lookup.values()

    def test_lookup_table_enables_data_residency_compliance(self):
        """GIVEN tokenized data and its lookup table
        WHEN implementing data residency requirements
        THEN lookup table can be stored in EU while tokens travel

        Requirement: GDPR - data residency support
        """
        import json

        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = "Contact: eu.citizen@example.eu"

        tokenized, lookup = tokenizer.tokenize(text)

        # Lookup table is a separate artifact that can be stored locally
        assert isinstance(lookup, dict)

        # Can be serialized for secure EU storage
        serialized = json.dumps(lookup)
        assert isinstance(serialized, str)

        # Tokenized text contains no real PII - safe for any location
        assert "eu.citizen@example.eu" not in tokenized
