# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import uuid
from typing import Any, Dict, List, Optional
from .a2ui_prompt import A2UI_INSTRUCTION
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

from .a2ui_utils import a2ui_callback

MODEL = "gemini-3.8-flash"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"
GCP_PROJECT_ID = "qwiklabs-gcp-04-0682ff5b5b9d"
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-04-0682ff5b5b9d"
MEMORY_BANK_ID = "3839203233612431360"
STORAGE_BUCKET_NAME = "sprout-and-bloom-media-qwiklabs-04"
PLANTS_COLLECTION = "plants"


def memory_bank_service_builder():
    """Builds VertexAiMemoryBankService for deployed container runtime."""
    return VertexAiMemoryBankService(
        project=GCP_PROJECT_ID,
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session events to Memory Bank for extraction."""
    await callback_context.add_session_to_memory()
    return None


def _get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with hardcoded project ID."""
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def list_plants(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    pet_safe_only: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """Lists plant varieties from the catalog with optional filters.

    Args:
        category: Filter by plant type: 'indoor' or 'outdoor'.
        difficulty: Filter by difficulty level, e.g. 'beginner', 'intermediate'.
        pet_safe_only: If true, returns only non-toxic / pet-friendly varieties.

    Returns:
        A list of plant documents matching the filters.
    """
    db = _get_firestore_client()
    query = db.collection(PLANTS_COLLECTION)

    if category:
        query = query.where("category", "==", category.lower())
    if difficulty:
        query = query.where("difficulty", "==", difficulty.lower())
    if pet_safe_only is not None and pet_safe_only:
        query = query.where("pet_safe", "==", True)

    docs = query.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


def get_plant_details(plant_id_or_name: str) -> Dict[str, Any]:
    """Retrieves full plant details and beginner care instructions for a specific plant.

    Args:
        plant_id_or_name: The plant document ID or common name (e.g. 'snake-plant', 'Snake Plant', 'zz-plant').

    Returns:
        Plant details dictionary or an error message if not found.
    """
    db = _get_firestore_client()
    col = db.collection(PLANTS_COLLECTION)

    doc = col.document(plant_id_or_name.lower().strip().replace(" ", "-")).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    # Search by matching name case-insensitively
    search_term = plant_id_or_name.lower().strip()
    for item in col.stream():
        data = item.to_dict()
        data["id"] = item.id
        name = data.get("name", "").lower()
        scientific = data.get("scientific_name", "").lower()
        if search_term in name or search_term in scientific or item.id == search_term:
            return data

    return {"error": f"Plant '{plant_id_or_name}' not found in the catalog."}


def add_plant(
    name: str,
    category: str,
    difficulty: str = "beginner",
    hardiness_zone: str = "Indoor",
    light_level: str = "medium indirect",
    watering: str = "Weekly",
    pet_safe: bool = True,
    description: str = "",
    beginner_tips: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Adds a new plant variety to the nursery catalog in Firestore.

    Args:
        name: Common name of the plant (e.g., 'Cast Iron Plant').
        category: 'indoor' or 'outdoor'.
        difficulty: 'beginner', 'intermediate', or 'expert'.
        hardiness_zone: Suitable Canadian hardiness zone or 'Indoor' (e.g. 'Zone 4-8', 'Indoor').
        light_level: Sunlight requirements (e.g., 'low to medium indirect', 'full sun').
        watering: Frequency and guidance (e.g., 'Every 2-3 weeks').
        pet_safe: True if non-toxic to pets, False if toxic.
        description: Summary description of the plant.
        beginner_tips: Helpful beginner tips for growing in Canadian climates.

    Returns:
        Confirmation dictionary with the newly created plant ID and data.
    """
    db = _get_firestore_client()
    doc_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    plant_data = {
        "id": doc_id,
        "name": name,
        "category": category.lower(),
        "difficulty": difficulty.lower(),
        "hardiness_zone": hardiness_zone,
        "light_level": light_level,
        "watering": watering,
        "pet_safe": pet_safe,
        "description": description,
        "beginner_tips": beginner_tips or [],
    }
    db.collection(PLANTS_COLLECTION).document(doc_id).set(plant_data)
    return {"status": "success", "message": f"Added plant '{name}' with ID '{doc_id}'", "plant": plant_data}


def lookup_canadian_climate_zone(location: str) -> Dict[str, Any]:
    """Looks up the Canadian Plant Hardiness Zone, frost calendar dates, and foolproof flowering annuals for budding gardeners.

    Args:
        location: Canadian city, town, province, or postal code prefix (e.g. 'Toronto', 'Calgary', 'Vancouver', 'Montreal', 'Ottawa', 'Halifax', 'Edmonton', 'Winnipeg', 'M5V').

    Returns:
        A dictionary with hardiness zone, last spring frost, first fall frost, safe outdoor planting window,
        top flowering annuals for beginner/budding gardeners, and the #1 'sure shot success' item.
    """
    loc = location.upper().strip()

    # Regional climate database mapping
    climate_db = [
        {
            "match": ["VANCOUVER", "VICTORIA", "BC", "BRITISH COLUMBIA", "V6", "V8", "V5", "V7"],
            "city": "Coastal British Columbia (Vancouver / Victoria area)",
            "zone": "Zone 8b",
            "last_spring_frost": "March 25 - April 10",
            "first_fall_frost": "November 5 - November 20",
            "growing_season_days": 220,
            "flowering_annuals": [
                {"name": "Sweet Alyssum", "exposure": "Full sun to partial shade", "perks": "Delicate honey scent, blooms non-stop from April through November."},
                {"name": "Fuchsia", "exposure": "Partial shade", "perks": "Thrives in mild, humid coastal summers; attracts hummingbirds."},
                {"name": "Begonia (Wax Begonia)", "exposure": "Part shade to shade", "perks": "Weather-resistant, self-cleaning, blooms continuously."}
            ],
            "sure_shot_success": {
                "name": "French Marigold (Tagetes patula)",
                "why": "Virtually bulletproof! Tolerates cool spring starts, resists coastal pests, and blooms vibrant orange and yellow with minimal maintenance."
            }
        },
        {
            "match": ["TORONTO", "GTA", "HAMILTON", "NIAGARA", "M4", "M5", "M6", "L5", "L6", "L8"],
            "city": "Southern Ontario (Greater Toronto & Niagara area)",
            "zone": "Zone 6a / 6b",
            "last_spring_frost": "May 5 - May 15",
            "first_fall_frost": "October 15 - October 25",
            "growing_season_days": 165,
            "flowering_annuals": [
                {"name": "Zinnias (Profusion or Zahara series)", "exposure": "Full sun", "perks": "Loves hot humid Ontario summers, highly disease-resistant, vibrant daisy blooms."},
                {"name": "Petunias (Wave series)", "exposure": "Full sun", "perks": "Vigorous trailing flower power perfect for balcony planters and hanging baskets."},
                {"name": "Cosmos", "exposure": "Full sun", "perks": "Easy to sow from seed, attracts pollinators, thrives even in average soil."}
            ],
            "sure_shot_success": {
                "name": "Zinnia (Profusion Series)",
                "why": "The ultimate beginner champion for Ontario summers! Fast-growing, shrugs off summer heat and humidity, needs no deadheading, and produces cut flowers until October."
            }
        },
        {
            "match": ["OTTAWA", "MONTREAL", "GATINEAU", "QUEBEC", "K1", "K2", "H2", "H3", "H4", "G1"],
            "city": "St. Lawrence Valley / National Capital (Ottawa / Montreal area)",
            "zone": "Zone 5a / 5b",
            "last_spring_frost": "May 10 - May 20",
            "first_fall_frost": "October 1 - October 10",
            "growing_season_days": 145,
            "flowering_annuals": [
                {"name": "Pansies & Violas", "exposure": "Sun to part shade", "perks": "Can be planted early in April; withstands late spring surprise snow flurries."},
                {"name": "Geraniums (Zonal Pelargonium)", "exposure": "Full sun", "perks": "Classic container choice, drought-tolerant, bright red/pink clusters all summer."},
                {"name": "Sunflowers (Dwarf Teddy Bear or Sunspot)", "exposure": "Full sun", "perks": "Fast to sprout from seed, thrilling for kids and budding gardeners."}
            ],
            "sure_shot_success": {
                "name": "Zonal Geranium (Pelargonium)",
                "why": "Tough as nails in containers. Forgiving of missed waterings, thrives in warm sunny spots, and provides instant color from May long weekend until first frost."
            }
        },
        {
            "match": ["CALGARY", "EDMONTON", "ALBERTA", "T2", "T3", "T5", "T6"],
            "city": "Alberta Foothills & Parkland (Calgary / Edmonton area)",
            "zone": "Zone 3b / 4a",
            "last_spring_frost": "May 25 - June 5 (Beware Victoria Day snow!)",
            "first_fall_frost": "September 10 - September 20",
            "growing_season_days": 110,
            "flowering_annuals": [
                {"name": "Pansies", "exposure": "Sun to light shade", "perks": "Survives sudden Alberta cold snaps and freezing spring nights without batting an eye."},
                {"name": "Calendula (Pot Marigold)", "exposure": "Full sun", "perks": "Cool-season annual that blooms quickly from seed in short Prairie summers."},
                {"name": "Nasturtium", "exposure": "Full sun", "perks": "Edible blossoms and leaves; thrives in poor soil with very little feeding."}
            ],
            "sure_shot_success": {
                "name": "Pansies & Violas",
                "why": "The undisputed frost-hardy champion of Alberta! You can plant them weeks before other annuals; even if caught under a surprise May snowfall, they bounce back smiling."
            }
        },
        {
            "match": ["WINNIPEG", "REGINA", "SASKATOON", "PRAIRIES", "MANITOBA", "SASKATCHEWAN", "R2", "R3", "S7", "S4"],
            "city": "Canadian Prairies (Winnipeg / Regina / Saskatoon)",
            "zone": "Zone 3a / 3b",
            "last_spring_frost": "May 20 - May 30",
            "first_fall_frost": "September 15 - September 22",
            "growing_season_days": 120,
            "flowering_annuals": [
                {"name": "French Marigolds", "exposure": "Full sun", "perks": "Shrugs off prairie heat and drying winds."},
                {"name": "Snapdragons", "exposure": "Full sun", "perks": "Light-frost tolerant, stunning spikes that bloom well into crisp autumn."},
                {"name": "Sweet Pea", "exposure": "Full sun (cool roots)", "perks": "Loves cool Prairie spring starts, climbing fragrant blooms."}
            ],
            "sure_shot_success": {
                "name": "French Marigolds",
                "why": "Extreme durability against prairie winds, blazing sun, and sporadic rain. An instant confidence booster for any new gardener."
            }
        },
        {
            "match": ["HALIFAX", "MONCTON", "ST. JOHN", "NOVA SCOTIA", "NEW BRUNSWICK", "PEI", "NEWFOUNDLAND", "B3", "E1", "C1", "A1"],
            "city": "Atlantic Canada (Halifax / Maritimes / Coastal)",
            "zone": "Zone 5b / 6a",
            "last_spring_frost": "May 15 - May 25",
            "first_fall_frost": "October 10 - October 20",
            "growing_season_days": 150,
            "flowering_annuals": [
                {"name": "Begonias (Tuberous or Wax)", "exposure": "Partial shade", "perks": "Loves humid maritime coastal air, no deadheading needed."},
                {"name": "Lobelia", "exposure": "Morning sun / afternoon shade", "perks": "Deep electric blue cascades, perfect for cool coastal summers."},
                {"name": "Impatiens", "exposure": "Shade to part shade", "perks": "Bright nonstop color in shaded maritime yards and porches."}
            ],
            "sure_shot_success": {
                "name": "Wax Begonia (Semperflorens)",
                "why": "Handles damp, foggy maritime conditions with ease without rotting or mildewing. Sets flowers constantly with zero fuss."
            }
        }
    ]

    # Search match
    selected = None
    for entry in climate_db:
        if any(token in loc for token in entry["match"]):
            selected = entry
            break

    # Fallback to general Canadian national average if location not explicitly listed
    if not selected:
        selected = {
            "city": f"Canadian Location ({location})",
            "zone": "Zone 4b / 5a (Canadian Average)",
            "last_spring_frost": "May 15 - May 25 (Victoria Day Rule)",
            "first_fall_frost": "September 25 - October 5",
            "growing_season_days": 135,
            "flowering_annuals": [
                {"name": "French Marigolds", "exposure": "Full sun", "perks": "Pest-repellent, heat-tolerant, continuous golden blooms."},
                {"name": "Zinnias", "exposure": "Full sun", "perks": "Fast germination, bright jewel colors, perfect for cutting."},
                {"name": "Pansies", "exposure": "Sun to light shade", "perks": "Tolerates spring chills and light frost."}
            ],
            "sure_shot_success": {
                "name": "French Marigold",
                "why": "Universally recognized as the most reliable, forgiving, and cheerful flowering annual across all Canadian growing conditions."
            }
        }

    return {
        "location_queried": location,
        "region_matched": selected["city"],
        "hardiness_zone": selected["zone"],
        "frost_dates": {
            "last_spring_frost": selected["last_spring_frost"],
            "first_fall_frost": selected["first_fall_frost"],
            "average_frost_free_days": selected["growing_season_days"],
            "safe_outdoor_planting_advice": "The golden Canadian rule: wait until after the Victoria Day long weekend (late May) before moving warm-season flowering annuals outdoors."
        },
        "flowering_annuals_for_budding_gardeners": selected["flowering_annuals"],
        "sure_shot_success_item": selected["sure_shot_success"]
    }


def get_beginner_gardener_checklist() -> Dict[str, Any]:
    """Provides a foundational beginner gardening checklist tailored to Canadian seasons and indoor conditions.

    Returns:
        A structured checklist covering seasonal transitions, lighting, soil/drainage, and watering rules.
    """
    return {
        "title": "Beginner Canadian Gardener & Houseplant Checklist",
        "guidelines": [
            "Check Hardiness Zone: Before planting outdoors, know your Canadian hardiness zone (e.g., Zone 3 in Prairies, Zone 5/6 in Southern Ontario/Quebec, Zone 8 in Coastal BC).",
            "Indoor Winter Light & Heating: In Canadian winters, days are shorter and radiators/furnaces dry the air. Place tropicals closer to windows and avoid cold drafts from leaky sills.",
            "Drainage First: Always use pots with drainage holes. Overwatering in winter is the #1 houseplant killer.",
            "Watering Rule of Thumb: Insert your finger 2 inches into soil. Only water if dry, and scale back watering frequency in November through March.",
            "Outdoor Planting Window: Wait until after the last expected spring frost date (often mid-to-late May in most Canadian zones) before moving tender plants outdoors.",
            "Pet Safety Check: Always verify plant toxicity if you have cats or dogs at home."
        ]
    }


import os
import urllib.parse
import urllib.request
import json


def search_botanical_species_info(query: str) -> Dict[str, Any]:
    """Searches the open botanical database (iNaturalist public API from public-apis directory) for real scientific taxonomy, photos, and descriptions for indoor or outdoor plants (flowering and non-flowering).

    Args:
        query: Common or scientific plant name to look up (e.g., 'Monstera deliciosa', 'Echinacea purpurea', 'Hosta', 'Fern', 'Peony').

    Returns:
        Real botanical data including scientific name, preferred common name, rank, photo URL, and Wikipedia reference summary.
    """
    # Optional API key or user token from environment variable if provided
    api_token = os.getenv("INATURALIST_API_TOKEN") or os.getenv("PLANT_API_KEY")

    encoded_query = urllib.parse.quote(query.strip())
    # iconic_taxa=Plantae ensures results only return plant species (flowering & non-flowering)
    url = f"https://api.inaturalist.org/v1/taxa?q={encoded_query}&iconic_taxa=Plantae&per_page=5"

    headers = {
        "User-Agent": "SproutAndBloomAgent/1.0 (Educational/Workshop bot)"
    }
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results = []
        for item in payload.get("results", []):
            photo = item.get("default_photo") or {}
            photo_url = photo.get("medium_url") or photo.get("url")
            results.append({
                "scientific_name": item.get("name"),
                "common_name": item.get("preferred_common_name", ""),
                "rank": item.get("rank"),
                "wikipedia_url": item.get("wikipedia_url"),
                "photo_url": photo_url,
                "attribution": photo.get("attribution"),
                "wikipedia_summary": (item.get("wikipedia_summary") or "").strip()
            })

        return {
            "query": query,
            "total_matches": len(results),
            "species": results
        }
    except Exception as e:
        return {
            "query": query,
            "error": f"Failed to retrieve botanical species info: {str(e)}"
        }


async def generate_plant_scene_image(
    prompt_description: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """Generates an image of a botanical scene or plant arrangement using gemini-3.1-flash-lite-image in the global region.

    Saves the image as an ADK artifact (available in the Playground Artifacts panel) and uploads it to the public Cloud Storage bucket.

    Args:
        prompt_description: Description of the scene to generate (e.g. 'beautiful supertunias in different colours, hostas, and indoor plants together, showing indoor and outdoor representation in Canadian terrain with wisteria').

    Returns:
        A dictionary with the public image URL, bucket details, and artifact filename.
    """
    client = genai.Client(
        vertexai=True,
        project=GCP_PROJECT_ID,
        location="global",
    )

    response = await client.aio.models.generate_content(
        model=IMAGE_MODEL,
        contents=prompt_description,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    image_bytes = None
    mime_type = "image/jpeg"
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            image_bytes = part.inline_data.data
            mime_type = part.inline_data.mime_type or "image/jpeg"
            break

    if not image_bytes:
        return {"error": "Failed to extract image bytes from model response."}

    # 1. Save with tool_context.save_artifact so it appears in the Playground Artifacts panel
    extension = "jpg" if "jpeg" in mime_type or "jpg" in mime_type else "png"
    artifact_id = str(uuid.uuid4())[:8]
    filename = f"plant_scene_{artifact_id}.{extension}"
    artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    try:
        await tool_context.save_artifact(filename=filename, artifact=artifact_part)
    except Exception as e:
        # Gracefully handle when runner/test doesn't have artifact service initialized
        pass

    # 2. Upload the same image bytes to the public Cloud Storage bucket
    storage_client = storage.Client(project=GCP_PROJECT_ID)
    bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
    blob_name = f"generated/{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{blob_name}"

    return {
        "status": "success",
        "prompt": prompt_description,
        "artifact_filename": filename,
        "public_url": public_url,
        "bucket": STORAGE_BUCKET_NAME,
        "message": f"Generated image saved as artifact '{filename}' and published at {public_url}",
    }


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are Sprout & Bloom, a lightweight, friendly plant care and gardening concierge tailored to Canada. "
        "You help both beginner and experienced gardeners with plant care advice, indoor houseplants, "
        "outdoor gardening, hardiness zones, frost dates, easy-care varieties, and troubleshooting care issues. "
        "Answer questions conversationally, concisely, and accurately without needing external tool calls."
    ),
    tools=[],
)

app = App(
    root_agent=root_agent,
    name="app",
)
