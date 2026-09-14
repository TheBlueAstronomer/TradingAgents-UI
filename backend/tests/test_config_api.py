def test_provider_configuration_is_derived_from_upstream_catalog(app_client):
    client, _, _ = app_client
    response = client.get("/api/config/providers")
    assert response.status_code == 200
    providers = {item["id"]: item for item in response.json()}
    assert providers["openai"]["quick_models"][0]["value"] == "gpt-5.6-luna"
    assert providers["openai_compatible"]["requires_backend_url"] is True
    assert providers["openai_compatible"]["allows_custom_model"] is True


def test_analyst_configuration_has_all_selectable_agents(app_client):
    client, _, _ = app_client
    response = client.get("/api/config/analysts")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["market", "social", "news", "fundamentals"]
    assert all(item["selected_by_default"] for item in response.json())
