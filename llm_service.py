import os
import json
from openai import OpenAI
from maps_service import search_places

def get_llm_response(user_message: str):
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    model = os.getenv("OLLAMA_MODEL", "llama3.1")
    
    # We use OpenAI client pointing to Ollama's local endpoint
    client = OpenAI(
        base_url=base_url,
        api_key="ollama" # api key is ignored by ollama but required by client
    )
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_google_maps_places",
                "description": "Find places to eat, visit, or go to using Google Maps Places API. Call this whenever a user asks for recommendations on places or locations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query, e.g., 'Japanese restaurant in Jakarta', 'parks near me', 'coffee shops'"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    
    messages = [
        {
            "role": "system", 
            "content": "You are a helpful AI assistant connected to Google Maps. "
                       "If a user asks for places, ALWAYS use the 'search_google_maps_places' tool to fetch real data. "
                       "When you provide the final answer, format it nicely. Provide the name, address, rating, and provide BOTH the 'Google Maps Link' (which you return as a markdown link) AND output the 'embed_map_url' inside an HTML iframe so the user can see it right away. "
                       "Example iframe format:\n"
                       """<iframe width=\"600\" height=\"450\" style=\"border:0\" allowfullscreen src=\"EMBED_URL_HERE\"></iframe>"""
                       "\nAlways make sure to output the link and the iframe."
        },
        {"role": "user", "content": user_message}
    ]
    
    # 1. First completion request to let the model decide if it wants to use a tool
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools
        )
    except Exception as e:
        return f"Error connecting to local LLM: {str(e)}. Please assure Ollama is running (`ollama serve`)."

    message = response.choices[0].message
    
    # 2. Check if the model wants to call a tool
    if message.tool_calls:
        # Append the assistant's tool-call message to the history
        messages.append(message)
        
        for tool_call in message.tool_calls:
            if tool_call.function.name == "search_google_maps_places":
                args = json.loads(tool_call.function.arguments)
                query = args.get("query")
                
                # 3. Call our actual function
                places_data = search_places(query)
                
                # 4. Append the tool response
                messages.append({
                    "role": "tool",
                    "content": json.dumps(places_data),
                    "tool_call_id": tool_call.id
                })
        
        # 5. Second completion request to get the final grounded answer
        final_response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        return final_response.choices[0].message.content
        
    return message.content
