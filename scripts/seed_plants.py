#!/usr/bin/env python3
"""Seed initial plant catalog data into Firestore."""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-0682ff5b5b9d"
COLLECTION_NAME = "plants"

SAMPLE_PLANTS = [
    {
        "id": "snake-plant",
        "name": "Snake Plant (Sansevieria)",
        "scientific_name": "Dracaena trifasciata",
        "category": "indoor",
        "hardiness_zone": "Indoor (tolerates cold drafts)",
        "light_level": "low to bright indirect",
        "watering": "Every 2-3 weeks (allow soil to completely dry)",
        "difficulty": "beginner",
        "pet_safe": False,
        "description": "Virtually indestructible indoor plant that thrives in dry Canadian indoor winter conditions.",
        "beginner_tips": [
            "Do not overwater, especially during dim Canadian winter months.",
            "Keep away from curious cats or dogs."
        ],
    },
    {
        "id": "zz-plant",
        "name": "ZZ Plant",
        "scientific_name": "Zamioculcas zamiifolia",
        "category": "indoor",
        "hardiness_zone": "Indoor",
        "light_level": "low to moderate",
        "watering": "Every 3-4 weeks",
        "difficulty": "beginner",
        "pet_safe": False,
        "description": "Tolerates low light and severe neglect. Glossy green foliage handles low humidity heated apartments well.",
        "beginner_tips": [
            "Water sparingly; its underground rhizomes store water efficiently.",
            "Wipe dust off leaves monthly with a damp cloth."
        ],
    },
    {
        "id": "spider-plant",
        "name": "Spider Plant",
        "scientific_name": "Chlorophytum comosum",
        "category": "indoor",
        "hardiness_zone": "Indoor",
        "light_level": "moderate to bright indirect",
        "watering": "Weekly (keep slightly moist but well-drained)",
        "difficulty": "beginner",
        "pet_safe": True,
        "description": "Classic pet-safe houseplant that produces baby 'spiderettes'. Adapts well to Canadian indoor heating.",
        "beginner_tips": [
            "Safe around cats and dogs.",
            "Use filtered or standing tap water if leaf tips turn brown due to chlorine/fluoride."
        ],
    },
    {
        "id": "hosta",
        "name": "Hosta (Plantain Lily)",
        "scientific_name": "Hosta spp.",
        "category": "outdoor",
        "hardiness_zone": "Zone 3-9",
        "light_level": "partial shade to full shade",
        "watering": "Moderate; water deeply during hot summer dry spells",
        "difficulty": "beginner",
        "pet_safe": False,
        "description": "Extremely hardy outdoor perennial for Canadian gardens. Survives freezing Canadian winters easily.",
        "beginner_tips": [
            "Mulch well in late autumn for root protection in colder zones (Zone 3-4).",
            "Watch out for slugs in wet spring months."
        ],
    },
    {
        "id": "coneflower",
        "name": "Purple Coneflower",
        "scientific_name": "Echinacea purpurea",
        "category": "outdoor",
        "hardiness_zone": "Zone 3-9",
        "light_level": "full sun",
        "watering": "Low to moderate once established (drought-tolerant)",
        "difficulty": "beginner",
        "pet_safe": True,
        "description": "Tough native prairie perennial with pollinator-attracting purple blooms that thrive across Canada.",
        "beginner_tips": [
            "Leaves seed heads intact in autumn for winter birds (goldfinches).",
            "Prefers well-draining soil to prevent winter root rot."
        ],
    },
]


def seed():
    print(f"Connecting to Firestore project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)
    col = db.collection(COLLECTION_NAME)

    for plant in SAMPLE_PLANTS:
        doc_id = plant["id"]
        col.document(doc_id).set(plant)
        print(f"  ✓ Seeded plant: {plant['name']} ({doc_id})")

    print(f"Successfully seeded {len(SAMPLE_PLANTS)} plants into Firestore collection '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    seed()
