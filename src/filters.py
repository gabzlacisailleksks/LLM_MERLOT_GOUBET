import re

def basic_input_filter(s: str) -> str:
    s = s.strip()
    s = re.sub(r'(?i)ignore (all|previous|latest) instructions', '[REDACTED_INJECTION_ATTEMPT]', s)
    s = re.sub(r'(?i)you are (now|a|an) (system|admin|developer|jailbroken|dan)', '[ROLE_PLAY_BLOCKED]', s)
    s = re.sub(r'(?i)(reveal|show|output|print) (the|your) (system prompt|policy|instructions)', '[LEAK_ATTEMPT_BLOCKED]', s)
    s = re.sub(r'(?i)(system|user|assistant|developer):', '[TAG_REMOVED]', s)
    return s