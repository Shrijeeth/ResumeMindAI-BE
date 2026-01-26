from ontology import exceptions


def test_llm_provider_not_configured_error_message():
    err = exceptions.LLMProviderNotConfiguredError("user-123")
    assert "user-123" in str(err)
    assert "No LLM provider configured" in str(err)


def test_ontology_validation_error_message():
    err = exceptions.OntologyValidationError("bad schema")
    assert err.reason == "bad schema"
    assert "bad schema" in str(err)
