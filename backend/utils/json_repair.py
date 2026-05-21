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
    clean = raw

    # Strip markdown code fences
    if "```" in clean:
        idx = clean.find("```")
        next_line = clean.find("\n", idx)
        if next_line > 0:
            clean = clean[next_line + 1:]
        else:
            clean = clean[idx + 3:]
        closing = clean.rfind("```")
        if closing > 0:
            clean = clean[:closing]

    # Strip leading/trailing whitespace and markdown
    clean = clean.strip()

    # Find JSON object by brace matching
    json_str = None
    first_brace = clean.find("{")
    if first_brace >= 0:
        depth = 0
        in_string = False
        escape = False
        json_start = first_brace
        for i in range(first_brace, len(clean)):
            c = clean[i]
            if escape:
                escape = False
                continue
            if c == '"' and not escape:
                in_string = not in_string
            elif c == '\\' and in_string:
                escape = True
            elif not in_string:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = clean[json_start:i + 1]
                        break

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
