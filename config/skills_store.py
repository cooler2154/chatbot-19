import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

SKILLS_PATH = Path("config/skills.json")
_LOCK = threading.Lock()

def _ensure_file():
    SKILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SKILLS_PATH.exists():
        SKILLS_PATH.write_text("[]")

def load_skills() -> List[Dict[str, Any]]:
    _ensure_file()
    with _LOCK:
        try:
            return json.loads(SKILLS_PATH.read_text())
        except Exception:
            return []

def save_skills(skills: List[Dict[str, Any]]):
    _ensure_file()
    with _LOCK:
        SKILLS_PATH.write_text(json.dumps(skills, indent=2))

def get_all() -> List[Dict[str, Any]]:
    return load_skills()

def get(name: str) -> Optional[Dict[str, Any]]:
    for s in load_skills():
        if s.get("name") == name:
            return s
    return None

def upsert(skill: Dict[str, Any]):
    skills = load_skills()
    for i, s in enumerate(skills):
        if s.get("name") == skill.get("name"):
            skills[i] = skill
            save_skills(skills)
            return
    skills.append(skill)
    save_skills(skills)

def delete(name: str) -> bool:
    skills = load_skills()
    new = [s for s in skills if s.get("name") != name]
    if len(new) == len(skills):
        return False
    save_skills(new)
    return True
