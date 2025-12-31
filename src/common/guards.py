import re, json
from typing import Dict, Any, Tuple
from pydantic import BaseModel, Field

class SafeOutput(BaseModel):
    answer: str
    citations: list[str] = []
    safety: str = Field(pattern="^(safe|unsafe)$")
    rationale: str

# FILTRES D'ENTRÉE RENFORCÉS (Contre LLM01: Prompt Injection)
DENY_INPUT = [
    r"(?i)ignore (all|previous) instructions",
    r"(?i)you are now", # Bloque "You are now DAN", etc.
    r"(?i)system prompt|instruction set", # Bloque le leak de prompt
    r"(?i)print (the )?admin password",
    r"(?i)run shell|execute .*command|rm -rf",
    r"(?i)base64|hex encode", # Bloque les tentatives d'obfuscation
]

# FILTRES DE SORTIE (Contre LLM06: Sensitive Information Disclosure)
DENY_OUTPUT = [
    r"(?i)secret|password|api[_-]?key|token|private key|ssh-rsa",
    r"(?i)internal server error|traceback|line \d+", # Bloque les fuites d'erreurs techniques
]

def input_guard(text: str) -> Tuple[bool, str]:
    for pat in DENY_INPUT:
        if re.search(pat, text):
            return False, f"blocked by input rule /{pat}/"
    return True, ""

def output_guard(text: str) -> Tuple[bool, str]:
    for pat in DENY_OUTPUT:
        if re.search(pat, text):
            return False, f"blocked by output rule /{pat}/"
    return True, ""

def enforce_json_schema(raw: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Nettoie et valide le JSON retourné par le modèle.
    C'est la défense principale contre LLM02: Insecure Output Handling.
    """
    try:
        # Nettoyage automatique des balises Markdown
        clean_raw = raw.replace("```json", "").replace("```", "").strip()
        
        # Extraction du bloc JSON si l'IA a ajouté du texte avant/après
        match = re.search(r'(\{.*\})', clean_raw, re.DOTALL)
        if match:
            clean_raw = match.group(1)
            
        obj = json.loads(clean_raw)
        SafeOutput(**obj)   # Validation via Pydantic
        return True, "", obj
    except Exception as e:
        return False, f"schema error: {e}", {"raw": raw[:400]}