"""The i18n negotiator endpoints (topic 27, area ``i18n``).

Both endpoints of the demo router, over the per-test app (a fresh service
per test — no state leaks): the panel's policy (servable locales with
their CLDR plural grammar, the fixed inputs) and catalog table (including
the deliberately untranslated German message), then the negotiate round
against real ``Accept-Language`` headers — the German region fallback,
Polish with its category math, the wildcard, the q-ordering, the
hostile-header case (malformed junk is NOT an error; the round answers
the default locale with the fallback visible), and the absent header.
"""

from fastapi.testclient import TestClient

PANEL_PATH = "/api/demo/i18n"
NEGOTIATE_PATH = "/api/demo/i18n/negotiate"


def negotiate(client: TestClient, accept_language: str | None) -> dict:
    """One negotiation round, sending the header exactly as given."""
    headers = {} if accept_language is None else {"Accept-Language": accept_language}
    response = client.get(NEGOTIATE_PATH, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_panel_serves_policy_catalog_and_tour(client: TestClient) -> None:
    body = client.get(PANEL_PATH).json()
    policy = body["policy"]
    assert policy["defaultLocale"] == "en"
    assert [locale["tag"] for locale in policy["supportedLocales"]] == ["en", "de", "pl"]
    german = policy["supportedLocales"][1]
    assert german["englishName"] == "German"
    assert german["nativeName"] == "Deutsch"
    assert german["pluralCategories"] == ["one", "other"]
    assert policy["supportedLocales"][2]["pluralCategories"] == [
        "one",
        "few",
        "many",
        "other",
    ]
    assert policy["fixedInstant"] == "2026-03-08T07:30:00+00:00"
    assert policy["numberInput"] == 1234567.89
    assert (policy["currencyCode"], policy["currencyAmount"]) == ("EUR", 1234.5)
    assert policy["pluralCounts"] == [0, 1, 2, 5, 22]
    assert len(body["catalog"]) == 10
    assert any("untranslated" in note or "deliberately" in note for note in body["honestyNotes"])
    assert any(entry["path"] == NEGOTIATE_PATH for entry in body["endpoints"])


def test_panel_catalog_flags_the_untranslated_message(client: TestClient) -> None:
    catalog = {
        row["msgid"]: row["translations"] for row in client.get(PANEL_PATH).json()["catalog"]
    }
    language = catalog["Language"]
    assert {"locale": "de", "served": "Language", "translated": False} in language
    assert {"locale": "pl", "served": "Język", "translated": True} in language
    upload = catalog["Upload a file"]
    assert all(cell["translated"] for cell in upload)


def test_negotiate_german_region_fallback_changes_every_layer(client: TestClient) -> None:
    body = negotiate(client, "de-DE,de;q=0.9,en;q=0.5")
    assert body["header"] == "de-DE,de;q=0.9,en;q=0.5"
    assert body["selectedLocale"] == "de"
    assert body["matchedVia"] == "region-fallback"
    assert body["fellBackToDefault"] is False
    assert [(row["tag"], row["quality"], row["matchedVia"]) for row in body["ranges"]] == [
        ("de-de", 1.0, "region-fallback"),
        ("de", 0.9, "exact"),
        ("en", 0.5, "exact"),
    ]
    # UI strings serve through the real catalog (de-DE → de).
    strings = {row["msgid"]: row["value"] for row in body["uiStrings"]}
    assert strings["Upload a file"] == "Datei hochladen"
    assert strings["Language"] == "Language"  # the deliberate fallback
    # Formatting and zones answer in German.
    assert body["formatting"]["number"] == "1.234.567,89"
    assert body["formatting"]["currency"] == "1.234,50 €"
    assert body["formatting"]["date"] == "08.03.2026, 07:30:00"
    zones = {row["zone"]: row for row in body["zones"]}
    assert zones["America/New_York"]["abbreviation"] == "EDT"
    assert zones["America/New_York"]["utcOffset"] == "-04:00"
    assert zones["Asia/Kolkata"]["utcOffset"] == "+05:30"


def test_negotiate_polish_plural_category_math(client: TestClient) -> None:
    body = negotiate(client, "pl-PL,pl;q=0.8,en;q=0.3")
    assert body["selectedLocale"] == "pl"
    plurals = [(row["count"], row["category"], row["sentence"]) for row in body["plurals"]]
    assert plurals == [
        (0, "many", "0 plików zostało wysłanych"),
        (1, "one", "1 plik został wysłany"),
        (2, "few", "2 pliki zostały wysłane"),
        (5, "many", "5 plików zostało wysłanych"),
        (22, "few", "22 pliki zostały wysłane"),
    ]
    assert body["formatting"]["number"] == "1 234 567,89"
    assert body["uiStrings"][0]["value"] == "Witamy w przewodniku dla programistów FastAPI"


def test_negotiate_wildcard_serves_the_default(client: TestClient) -> None:
    body = negotiate(client, "*")
    assert body["selectedLocale"] == "en"
    assert body["matchedVia"] == "wildcard"
    assert body["ranges"] == [
        {"raw": "*", "tag": "*", "quality": 1.0, "matchedLocale": "en", "matchedVia": "wildcard"}
    ]
    assert body["formatting"]["date"] == "Mar 8, 2026, 7:30:00 AM"


def test_negotiate_absent_header_falls_back_visibly(client: TestClient) -> None:
    body = negotiate(client, None)
    assert body["header"] is None
    assert body["selectedLocale"] == "en"
    assert body["fellBackToDefault"] is True
    assert body["ranges"] == []


def test_negotiate_malformed_header_is_not_an_error(client: TestClient) -> None:
    body = negotiate(client, "!!!, 1nvalid, de-!!, de;q=2, pl;q=abc")
    assert body["selectedLocale"] == "de"
    assert [row["tag"] for row in body["ranges"]] == ["de", "pl"]
    strings = {row["msgid"]: row["value"] for row in body["uiStrings"]}
    assert strings["Cancel"] == "Abbrechen"


def test_negotiate_exclusion_and_unknown_locales(client: TestClient) -> None:
    # French is unknown → visible default fallback, no crash.
    french = negotiate(client, "fr-CA,fr;q=0.9")
    assert french["selectedLocale"] == "en"
    assert french["fellBackToDefault"] is True
    assert all(row["matchedVia"] == "none" for row in french["ranges"])

    # q=0 excludes Polish; the wildcard then serves the first survivor.
    excluded = negotiate(client, "pl;q=0, *")
    assert excluded["selectedLocale"] == "en"
    assert excluded["matchedVia"] == "wildcard"
    excluded_rows = [row for row in excluded["ranges"] if row["matchedVia"] == "excluded"]
    assert [row["tag"] for row in excluded_rows] == ["pl"]


def test_negotiate_zones_render_in_the_negotiated_locale(client: TestClient) -> None:
    body = negotiate(client, "pl")
    zones = {row["zone"]: row for row in body["zones"]}
    assert zones["UTC"]["formatted"] == "8 mar 2026, 07:30:00"
    assert zones["America/New_York"]["formatted"] == "8 mar 2026, 03:30:00"
    assert zones["America/New_York"]["wallTime"] == "2026-03-08T03:30:00-04:00"
    assert zones["Asia/Kolkata"]["wallTime"] == "2026-03-08T13:00:00+05:30"
