import pytest
from app.agent import list_plants, get_plant_details, get_beginner_gardener_checklist, lookup_canadian_climate_zone, search_botanical_species_info, FIRESTORE_PROJECT_ID

def test_hardcoded_project_id():
    assert FIRESTORE_PROJECT_ID == "qwiklabs-gcp-04-0682ff5b5b9d"

def test_get_beginner_gardener_checklist():
    checklist = get_beginner_gardener_checklist()
    assert "guidelines" in checklist
    assert len(checklist["guidelines"]) > 0

def test_firestore_list_and_details():
    plants = list_plants()
    assert len(plants) >= 5
    snake_plant = get_plant_details("snake-plant")
    assert snake_plant.get("id") == "snake-plant"
    assert "Snake Plant" in snake_plant.get("name", "")

def test_lookup_canadian_climate_zone():
    res = lookup_canadian_climate_zone("Toronto")
    assert "Zone 6" in res["hardiness_zone"]
    assert "sure_shot_success_item" in res
    assert "flowering_annuals_for_budding_gardeners" in res
    assert len(res["flowering_annuals_for_budding_gardeners"]) > 0

    calgary = lookup_canadian_climate_zone("Calgary")
    assert "Zone 3" in calgary["hardiness_zone"] or "Zone 4" in calgary["hardiness_zone"]
    assert "Pansies" in calgary["sure_shot_success_item"]["name"]

def test_search_botanical_species_info():
    res = search_botanical_species_info("Monstera deliciosa")
    assert res.get("total_matches", 0) > 0
    first = res["species"][0]
    assert "Monstera" in first["scientific_name"]
    assert first["photo_url"] is not None
