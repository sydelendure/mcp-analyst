import asyncio
import os
import sys
import time
import re
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.mcp_client import CustomMCPClient

# Load .env file
load_dotenv()


def sanitize_schema(schema):
    if not isinstance(schema, dict):
        return schema
    cleaned = {}
    forbidden = {"additionalProperties", "additional_properties", "$schema"}
    for k, v in schema.items():
        if k in forbidden:
            continue
        if isinstance(v, dict):
            cleaned[k] = sanitize_schema(v)
        elif isinstance(v, list):
            cleaned[k] = [sanitize_schema(item) if isinstance(item, dict) else item for item in v]
        else:
            cleaned[k] = v
    return cleaned


def send_message_safely(chat, message):
    retries = 0
    max_retries = 10
    while True:
        try:
            return chat.send_message(message)
        except Exception as e:
            err_str = str(e)
            retries += 1
            if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and retries <= max_retries:
                match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str) or re.search(r"retryDelay': '(\d+)s'", err_str)
                delay = int(float(match.group(1))) + 2 if match else 20
                print(f"\nRate limit reached. Waiting {delay}s for quota window to reset (Attempt {retries}/{max_retries})...", flush=True)
                time.sleep(delay)
            elif ("503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str.lower() or "overloaded" in err_str.lower() or "500" in err_str or "502" in err_str or "504" in err_str) and retries <= max_retries:
                backoff = min(2 ** retries + 2, 20)
                print(f"\nGemini model is experiencing temporary high demand (503). Retrying in {backoff}s (Attempt {retries}/{max_retries})...", flush=True)
                time.sleep(backoff)
            elif ("Connection reset" in err_str or "ReadError" in err_str or "RemoteProtocolError" in err_str or "BrokenResourceError" in err_str) and retries <= max_retries:
                print(f"\nTransient network interruption. Retrying ({retries}/{max_retries}) in 3s...", flush=True)
                time.sleep(3)
            else:
                raise e


async def run_copilot(prompt: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set. Please set it in your .env file.")
        sys.exit(1)

    gemini_client = genai.Client(api_key=api_key)

    # CONNECT OVER THE NETWORK TO THE CUSTOM MCP SERVER
    server_url = "http://127.0.0.1:8000/sse"
    print(f"Connecting to standalone Custom MCP Server at {server_url}...")

    async with CustomMCPClient(server_url) as session:
        tools_list = await session.list_tools()
        print(f"Connected! Discovered {len(tools_list)} tools from the remote server via MCP 2024-11-05 protocol.")

        gemini_declarations = []
        for t in tools_list:
            raw_schema = t.input_schema if hasattr(t, "input_schema") else getattr(t, "inputSchema", {})
            gemini_declarations.append(
                types.FunctionDeclaration(
                    name=t.name,
                    description=t.description or "",
                    parameters=sanitize_schema(raw_schema),
                )
            )

        system_instruction = (
            "You are an autonomous enterprise data analyst copilot. "
            "When given an audit request, you must execute the complete end-to-end audit pipeline by calling all relevant tools in sequence:\n"
            "1. Call `preview_dataset` to inspect columns and dimensions.\n"
            "2. Call `fetch_live_fx_rates` for currency conversion rates.\n"
            "3. Call `generate_segment_matrix` to generate cohort aggregation data.\n"
            "4. Call `detect_anomalies` to identify business rule violations and statistical spikes.\n"
            "5. Call `dispatch_slack_alert` with a clean, concise, highly readable summary.\n"
            "6. Call `export_audit_summary` to save the full audit report to disk.\n"
            "Execute each tool call until all required steps are completed, then provide a final concise executive briefing.\n\n"
            "SLACK ALERT FORMATTING RULES:\n"
            "- When calling dispatch_slack_alert, format the message cleanly and simply as follows:\n"
            "  AUDIT SUMMARY: <dataset name>\n"
            "  Status: <Clean | Action Required>\n"
            "  Records Scanned: <number>\n\n"
            "  Key Findings:\n"
            "  - Anomalies: <list order violations concisely or 'None'>\n"
            "  - Top Market Segment: <Country> - <Category> (<Revenue>)\n"
            "  - Live FX Benchmark: <from/to rate>\n\n"
            "  Next Steps: Executive report exported to disk.\n"
            "- Keep spacing clean and easy for an executive to read in seconds.\n"
            "- CRITICAL: Do NOT use ANY emojis or emoji shortcodes (no :rotating_light:, no icons) anywhere in your tool calls, Slack messages, findings, or executive reports."
        )

        model_name = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        chat = gemini_client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[types.Tool(function_declarations=gemini_declarations)]
            ),
        )

        print(f"\nUser Query: {prompt}\n" + "=" * 60)
        response = send_message_safely(chat, prompt)

        while response.function_calls:
            response_parts = []
            for call in response.function_calls:
                call_args = dict(call.args)
                tool_title = call.name.replace("_", " ").title()
                print(f"[Executing Tool on Custom MCP Server]: {tool_title}")

                # The tool is executed on the separate MCP server over SSE/HTTP!
                result = await session.call_tool(call.name, call_args)
                result_text = str(result.data if hasattr(result, "data") else result)

                response_parts.append(
                    types.Part.from_function_response(
                        name=call.name, response={"result": result_text}
                    )
                )

            time.sleep(1)
            response = send_message_safely(chat, response_parts)

        print("=" * 60 + "\nAI Copilot Final Analysis:\n")
        print(response.text)


if __name__ == "__main__":
    query = (
        "Inspect data/global_sales.csv. Check the live EUR to USD exchange rate, "
        "scan for revenue anomalies, alert the team of findings, and save an audit report."
    )
    asyncio.run(run_copilot(query))
