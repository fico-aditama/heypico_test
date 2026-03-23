import os
import json
from openai import OpenAI
from maps_service import search_places


SYSTEM_PROMPT = (
    "You are a friendly and helpful AI assistant integrated with Google Maps. "
    "Your job is to help users find places to eat, visit, or explore. "
    "When a user asks about any place, food, or location, ALWAYS call the 'search_google_maps_places' tool. "
    "After receiving tool results, format your response beautifully in Markdown:\n"
    "- Show each place with its name (bold), address, and star rating.\n"
    "- Include a clickable [View on Google Maps](URL) link.\n"
    "- Embed the map using an HTML iframe exactly like this (use the embed_map_url from results):\n"
    "  <iframe width='100%' height='350' style='border:0;border-radius:12px;' allowfullscreen loading='lazy' "
    "  referrerpolicy='no-referrer-when-downgrade' src='EMBED_URL_HERE'></iframe>\n"
    "- Repeat the iframe for each place found.\n"
    "- Be conversational and warm. Add a short helpful comment about each place if possible.\n"
    "If the user is making general conversation (not asking about places), respond normally without using any tool."
)

# Keywords that indicate a location-based search query
LOCATION_KEYWORDS = [
    "cari", "cariin", "find", "where", "tempat", "lokasi", "makan", "minum",
    "restoran", "cafe", "kafe", "hotel", "wisata", "restaurant", "place",
    "near", "nearby", "around", "dekat", "recommend", "rekomendasi", "suggest",
    "best", "good", "enak", "coffee", "shop", "toko", "mall", "park", "pantai",
    "beach", "bar", "visit", "kunjungi", "jalan", "explore", "di ", "in ",
    "jakarta", "batam", "bali", "jogja", "yogyakarta", "surabaya", "bandung",
    "medan", "makassar", "singapore", "singapura", "sushi", "pizza", "bakso",
    "warung", "rumah makan", "spa", "museum", "taman", "alun"
]


def _is_location_query(message: str) -> bool:
    """Heuristic check: does this message ask about a place/location?"""
    return any(kw in message.lower() for kw in LOCATION_KEYWORDS)


def _format_places_fallback(query: str, places_data: dict) -> str:
    """Manually format a places result as Markdown+iframes (used when LLM skips tool call)."""
    if places_data.get("status") != "success":
        return f"⚠️ Could not fetch places: {places_data.get('message', 'Unknown error')}"

    places = places_data.get("places", [])
    if not places:
        return f"Sorry, I couldn't find any places matching **\"{query}\"**. Try a different search!"

    lines = [f"Here are some places I found for **\"{query}\"**:\n"]
    for p in places:
        lines.append(f"### 📍 {p['name']}")
        lines.append(f"**Address:** {p['address']}")
        lines.append(f"**Rating:** ⭐ {p['rating']} ({p.get('user_ratings_total', 0)} reviews)")
        lines.append(f"[Get Directions]({p['search_link']})\n")
        lines.append(
            f"<iframe width='100%' height='450' style='border:0;border-radius:12px;margin-top:8px;box-shadow: 0 4px 20px rgba(0,0,0,0.3);'"
            f" allowfullscreen loading='lazy' referrerpolicy='no-referrer-when-downgrade'"
            f" src='{p['embed_map_url']}'></iframe>\n"
        )
    return "\n".join(lines)


from vector_memory import get_semantic_memory

def get_llm_response(user_message: str) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("OLLAMA_MODEL", "llama3.1")

    client = OpenAI(base_url=base_url, api_key="ollama")

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_google_maps_places",
                "description": (
                    "Search for real-world places using Google Maps. "
                    "Call this whenever a user asks for place recommendations or wants to find a location."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The full search query, e.g. 'best sushi restaurant in Jakarta'"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    # --- RAG: Fetch semantic memories from Vector DB ---
    past_memory = get_semantic_memory(user_message, limit=3)
    
    dynamic_system_prompt = SYSTEM_PROMPT
    if past_memory:
        dynamic_system_prompt += (
            "\n\n--- PAST MEMORY CONTEXT FROM VECTOR DB ---\n"
            "Here is relevant context from your previous conversations with this user. "
            "Use it to personalize your response if applicable:\n"
            f"{past_memory}\n"
            "------------------------------------------\n"
        )

    # Build messages with the RAG-enhanced system prompt
    messages = [{"role": "system", "content": dynamic_system_prompt}]
    messages.append({"role": "user", "content": user_message})

    location_query = _is_location_query(user_message)

    # ⚡ FAST PATH: For location queries, skip LLM entirely → go direct to Maps API
    # This avoids the slow 2-round-trip LLM overhead (can save 30-60 seconds on CPU)
    if location_query:
        places_data = search_places(user_message)
        return _format_places_fallback(user_message, places_data)

    # --- For non-location queries: use LLM as normal ---
    tool_choice = "auto"

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice
        )
    except Exception as e:
        return (
            f"⚠️ **Error connecting to local LLM.**\n\n"
            f"Make sure Ollama is running: `ollama serve`\n\n_Details: {str(e)}_"
        )

    message = response.choices[0].message

    # --- Round 2: If LLM wants to call a tool, execute it ---
    if message.tool_calls:
        messages.append(message)

        for tool_call in message.tool_calls:
            if tool_call.function.name == "search_google_maps_places":
                try:
                    args = json.loads(tool_call.function.arguments)
                    query = args.get("query", user_message)
                except (json.JSONDecodeError, AttributeError):
                    query = user_message

                places_data = search_places(query)

                messages.append({
                    "role": "tool",
                    "content": json.dumps(places_data, ensure_ascii=False),
                    "tool_call_id": tool_call.id
                })

        try:
            final_response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            return final_response.choices[0].message.content or "Sorry, I couldn't generate a response."
        except Exception as e:
            return f"⚠️ **Error generating final response:** {str(e)}"

    # --- Fallback: Location query but LLM still skipped tool → call Maps directly ---
    if location_query:
        places_data = search_places(user_message)
        return _format_places_fallback(user_message, places_data)

    # --- Non-location: Direct LLM reply ---
    return message.content or "Sorry, I couldn't generate a response."
