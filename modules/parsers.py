import json
import re

def clean_json_string(s: str) -> str:
    """
    清理一個可能不符合 JSON 標準的字串，主要是將結構性的單引號替換為雙引號。
    這個函式只會替換不在雙引號字串內的單引號。
    """
    res = []
    in_string = False
    escaped = False

    for char in s:
        if char == '"' and not escaped:
            in_string = not in_string
        
        if char == "'" and not in_string:
            res.append('"')
        else:
            res.append(char)
        
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
            
    return "".join(res)

def extract_outermost_json(text: str) -> str | None:
    """
    從字串中提取最外層的 JSON 物件。
    """
    if not isinstance(text, str):
        return None
        
    start_index = text.find('{')
    end_index = text.rfind('}')

    if start_index == -1 or end_index == -1 or end_index < start_index:
        return None

    potential_json = text[start_index : end_index + 1]

    try:
        json.loads(potential_json)
        return potential_json
    except json.JSONDecodeError:
        return None

def extract_from_string(text: str, *keys: str):
    """
    從字串中提取指定鍵的值。
    優先嘗試將字串解析為 JSON，如果失敗或找不到鍵，則使用正規表示式作為備案。
    """
    if not text or not keys:
        return None if len(keys) == 1 else (None,) * len(keys)

    try:
        normalized_text = text
        for key in keys:
            normalized_text = normalized_text.replace(f'"{key.capitalize()}"', f'"{key.lower()}"')
        
        cleaned_text = clean_json_string(normalized_text)
        data = json.loads(cleaned_text)
        
        if isinstance(data, dict):
            values = [data.get(key.lower()) for key in keys]
            if all(v is not None for v in values):
                return values[0] if len(values) == 1 else tuple(values)
    except (json.JSONDecodeError, AttributeError):
        pass

    results = []
    for key in keys:
        
        pattern = rf'["\']?{key}["\']?\s*:\s*["\']([^"\']+)["\']'
        
        try:
            match = re.search(pattern, text, re.IGNORECASE)
            results.append(match.group(1).strip() if match else None)
        except (re.error, IndexError):
            results.append(None)

    return results[0] if len(results) == 1 else tuple(results)