import re
import json
import logging

logger = logging.getLogger("chronicles-json-utils")


def repair_json(json_str: str) -> str:
    if not json_str:
        return ""

    json_str = json_str.strip()

    def fix_newlines_in_strings(match):
        return match.group(0).replace('\n', '\\n').replace('\r', '')

    json_str = re.sub(
        r'"[^"\\]*(?:\\.[^"\\]*)*"',
        fix_newlines_in_strings,
        json_str,
        flags=re.DOTALL
    )

    json_str = re.sub(r',\s*([\]}])', r'\1', json_str)

    json_str = re.sub(
        r'\[\s*"([^"]+)"\s*:\s*"([^"]*)"',
        r'["\1: \2"',
        json_str
    )
    json_str = re.sub(
        r',\s*"([^"]+)"\s*:\s*"([^"]*)"\s*(?=[,\]])',
        r', "\1: \2"',
        json_str
    )

    json_str = re.sub(
        r'"([a-z][a-z0-9_]*):\s*([^"]+)"(?=\s*[,}])',
        r'"\1": "\2"',
        json_str
    )

    last_brace = json_str.rfind('}')
    if last_brace != -1:
        json_str = json_str[:last_brace + 1]

    return json_str


def extract_and_repair_json(raw: str) -> dict:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    json_str = fenced.group(1) if fenced else None

    if not json_str:
        brace = re.search(r"\{.*\}", raw, re.DOTALL)
        json_str = brace.group(0) if brace else None

    if not json_str:
        raise ValueError(f"No JSON found in model output. Raw: {raw[:300]}")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    repaired = repair_json(json_str)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        logger.error(f"JSON repair FAILED. Raw (500 chars): {json_str[:500]}")
        logger.error(f"Repaired (500 chars): {repaired[:500]}")
        raise ValueError(f"Invalid JSON after repair: {e}")
