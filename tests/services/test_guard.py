# tests/test_guard.py

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from src.services.guard import SafetyGuard


class TestSafetyGuard:
    """Test suite for SafetyGuard functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch('src.services.guard.settings') as mock_settings:
            mock_settings.SAFETY_GUARD_TIMEOUT = 30
            mock_settings.SAFETY_GUARD_ENABLED = True
            mock_settings.SAFETY_GUARD_FAIL_OPEN = True
            yield mock_settings

    @pytest.fixture
    def mock_rotator(self):
        """Mock NVIDIA rotator for testing."""
        mock_rotator = Mock()
        mock_rotator.get_key.return_value = "test_api_key"
        mock_rotator.rotate.return_value = "test_api_key_2"
        return mock_rotator

    @pytest.fixture
    def safety_guard(self, mock_settings, mock_rotator):
        """Create SafetyGuard instance for testing."""
        return SafetyGuard(mock_rotator)

    def test_init_with_valid_config(self, mock_settings, mock_rotator):
        """Test SafetyGuard initialization with valid configuration."""
        guard = SafetyGuard(mock_rotator)
        assert guard.nvidia_rotator == mock_rotator
        assert guard.timeout_s == 30
        assert guard.enabled is True
        assert guard.fail_open is True

    def test_init_without_api_key(self, mock_settings):
        """Test SafetyGuard initialization without API key."""
        mock_rotator = Mock()
        mock_rotator.get_key.return_value = None
        with pytest.raises(ValueError, match="No NVIDIA API keys found"):
            SafetyGuard(mock_rotator)

    def test_chunk_text_empty(self, safety_guard):
        """Test text chunking with empty text."""
        result = safety_guard._chunk_text("")
        assert result == [""]

    def test_chunk_text_short(self, safety_guard):
        """Test text chunking with short text."""
        text = "Short text"
        result = safety_guard._chunk_text(text)
        assert result == [text]

    def test_chunk_text_long(self, safety_guard):
        """Test text chunking with long text."""
        text = "a" * 5000  # Longer than default chunk size
        result = safety_guard._chunk_text(text)
        assert len(result) > 1
        assert all(len(chunk) <= 2800 for chunk in result)

    def test_parse_guard_reply_safe(self, safety_guard):
        """Test parsing safe guard reply."""
        is_safe, reason = safety_guard._parse_guard_reply("SAFE")
        assert is_safe is True
        assert reason == ""

    def test_parse_guard_reply_unsafe(self, safety_guard):
        """Test parsing unsafe guard reply."""
        is_safe, reason = safety_guard._parse_guard_reply("UNSAFE: contains harmful content")
        assert is_safe is False
        assert reason == "contains harmful content"

    def test_parse_guard_reply_empty(self, safety_guard):
        """Test parsing empty guard reply."""
        is_safe, reason = safety_guard._parse_guard_reply("")
        assert is_safe is True
        assert reason == "guard_unavailable"

    def test_parse_guard_reply_unknown(self, safety_guard):
        """Test parsing unknown guard reply."""
        is_safe, reason = safety_guard._parse_guard_reply("UNKNOWN_RESPONSE")
        assert is_safe is False
        assert len(reason) <= 180

    def test_is_medical_query_symptoms(self, safety_guard):
        """Test medical query detection for symptoms."""
        queries = [
            "I have a headache",
            "My chest hurts",
            "I'm experiencing nausea",
            "I have a fever"
        ]
        for query in queries:
            assert safety_guard._is_medical_query(query) is True

    def test_is_medical_query_conditions(self, safety_guard):
        """Test medical query detection for conditions."""
        queries = [
            "What is diabetes?",
            "How to treat hypertension",
            "Symptoms of depression",
            "Cancer treatment options"
        ]
        for query in queries:
            assert safety_guard._is_medical_query(query) is True

    def test_is_medical_query_treatments(self, safety_guard):
        """Test medical query detection for treatments."""
        queries = [
            "What medication should I take?",
            "Physical therapy exercises",
            "Surgery options",
            "Vaccination schedule"
        ]
        for query in queries:
            assert safety_guard._is_medical_query(query) is True

    def test_is_medical_query_non_medical(self, safety_guard):
        """Test medical query detection for non-medical content."""
        queries = [
            "What's the weather like?",
            "How to cook pasta",
            "Best restaurants in town",
            "Python programming tutorial"
        ]
        for query in queries:
            assert safety_guard._is_medical_query(query) is False

    def test_detect_harmful_content_safe_medical(self, safety_guard):
        """Test harmful content detection for safe medical content."""
        text = "I have a headache and need advice on pain management"
        is_safe, reason = safety_guard._detect_harmful_content(text)
        assert is_safe is True
        assert reason == "medical_content"

    def test_detect_harmful_content_dangerous_medical(self, safety_guard):
        """Test harmful content detection for dangerous medical content."""
        text = "You should overdose on your medication"
        is_safe, reason = safety_guard._detect_harmful_content(text)
        assert is_safe is False
        assert "dangerous_medical_advice" in reason

    def test_detect_harmful_content_suicide(self, safety_guard):
        """Test harmful content detection for suicide-related content."""
        text = "How to kill yourself"
        is_safe, reason = safety_guard._detect_harmful_content(text)
        assert is_safe is False
        assert "suicide_self_harm" in reason

    def test_detect_harmful_content_violence(self, safety_guard):
        """Test harmful content detection for violent content."""
        text = "How to harm others with weapons"
        is_safe, reason = safety_guard._detect_harmful_content(text)
        assert is_safe is False
        assert "violence" in reason

    def test_assess_risk_level_medical_low(self, safety_guard):
        """Test risk assessment for low-risk medical content."""
        text = "I have a mild headache"
        risk_level, risk_score = safety_guard._assess_risk_level(text)
        assert risk_level == "low"
        assert 0.0 <= risk_score <= 1.0

    def test_assess_risk_level_medical_high(self, safety_guard):
        """Test risk assessment for high-risk medical content."""
        text = "You should commit suicide and overdose on drugs"
        risk_level, risk_score = safety_guard._assess_risk_level(text)
        assert risk_level == "high"
        assert risk_score > 0.6

    def test_assess_risk_level_non_medical(self, safety_guard):
        """Test risk assessment for non-medical content."""
        text = "This is just a normal conversation"
        risk_level, risk_score = safety_guard._assess_risk_level(text)
        assert risk_level == "low"
        assert 0.0 <= risk_score <= 1.0

    @patch('src.services.guard.requests.post')
    def test_call_guard_success(self, mock_post, safety_guard):
        """Test successful guard API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "SAFE"}}]
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "test message"}]
        result = safety_guard._call_guard(messages)
        assert result == "SAFE"

    @patch('src.services.guard.requests.post')
    def test_call_guard_failure(self, mock_post, safety_guard):
        """Test guard API call failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "test message"}]
        result = safety_guard._call_guard(messages)
        assert result == ""

    def test_check_user_query_disabled(self, mock_settings):
        """Test user query check when guard is disabled."""
        mock_settings.SAFETY_GUARD_ENABLED = False
        guard = SafetyGuard()
        
        is_safe, reason = guard.check_user_query("any query")
        assert is_safe is True
        assert reason == "guard_disabled"

    def test_check_user_query_medical(self, safety_guard):
        """Test user query check for medical content."""
        with patch.object(safety_guard, '_call_guard') as mock_call:
            is_safe, reason = safety_guard.check_user_query("I have a headache")
            assert is_safe is True
            assert reason == "medical_query"
            mock_call.assert_not_called()

    def test_check_user_query_non_medical_safe(self, safety_guard):
        """Test user query check for safe non-medical content."""
        with patch.object(safety_guard, '_call_guard') as mock_call, \
             patch.object(safety_guard, '_parse_guard_reply') as mock_parse:
            mock_call.return_value = "SAFE"
            mock_parse.return_value = (True, "")
            
            is_safe, reason = safety_guard.check_user_query("What's the weather?")
            assert is_safe is True
            assert reason == ""

    def test_check_user_query_non_medical_unsafe(self, safety_guard):
        """Test user query check for unsafe non-medical content."""
        with patch.object(safety_guard, '_call_guard') as mock_call, \
             patch.object(safety_guard, '_parse_guard_reply') as mock_parse:
            mock_call.return_value = "UNSAFE: harmful content"
            mock_parse.return_value = (False, "harmful content")
            
            is_safe, reason = safety_guard.check_user_query("How to harm others")
            assert is_safe is False
            assert reason == "harmful content"

    def test_check_model_answer_disabled(self, mock_settings):
        """Test model answer check when guard is disabled."""
        mock_settings.SAFETY_GUARD_ENABLED = False
        guard = SafetyGuard()
        
        is_safe, reason = guard.check_model_answer("query", "answer")
        assert is_safe is True
        assert reason == "guard_disabled"

    def test_check_model_answer_medical_safe(self, safety_guard):
        """Test model answer check for safe medical content."""
        is_safe, reason = safety_guard.check_model_answer(
            "I have a headache", 
            "You should rest and drink water"
        )
        assert is_safe is True
        assert reason == "medical_content"

    def test_check_model_answer_medical_unsafe(self, safety_guard):
        """Test model answer check for unsafe medical content."""
        is_safe, reason = safety_guard.check_model_answer(
            "I have a headache", 
            "You should overdose on medication"
        )
        assert is_safe is False
        assert "dangerous medical advice" in reason

    def test_check_model_answer_high_risk(self, safety_guard):
        """Test model answer check for high-risk content."""
        with patch.object(safety_guard, '_call_guard') as mock_call, \
             patch.object(safety_guard, '_parse_guard_reply') as mock_parse:
            mock_call.return_value = "SAFE"
            mock_parse.return_value = (True, "")
            
            is_safe, reason = safety_guard.check_model_answer(
                "How to harm others", 
                "You should use weapons to attack people"
            )
            assert is_safe is True
            assert reason == "high_risk_validated"

    def test_enhance_messages_with_context_medical(self, safety_guard):
        """Test message enhancement for medical content."""
        messages = [{"role": "user", "content": "I have a headache"}]
        enhanced = safety_guard._enhance_messages_with_context(messages)
        
        assert len(enhanced) == 1
        assert "MEDICAL CONTEXT" in enhanced[0]["content"]
        assert "I have a headache" in enhanced[0]["content"]

    def test_enhance_messages_with_context_non_medical(self, safety_guard):
        """Test message enhancement for non-medical content."""
        messages = [{"role": "user", "content": "What's the weather?"}]
        enhanced = safety_guard._enhance_messages_with_context(messages)
        
        assert enhanced == messages  # Should remain unchanged

    def test_global_safety_guard_instance(self):
        """Test that global safety guard instance is None by default."""
        from src.services.guard import safety_guard
        assert safety_guard is None


if __name__ == "__main__":
    pytest.main([__file__])
