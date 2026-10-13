"""Persistent random crew skill; equipment and physical performance stay vehicle-specific."""
import random

def assign(unit):
    if isinstance(unit,dict):
        if 'skill' not in unit:unit['skill']=random.random()
        return max(0.,min(1.,unit['skill']))
    if not hasattr(unit,'ai_skill'):unit.ai_skill=random.random()
    return max(0.,min(1.,unit.ai_skill))

def label(skill):
    return '新手' if skill<.33 else '熟练' if skill<.72 else '精锐'

def reaction(skill):return 1.35-.95*skill

def dispersion(skill):return 2.3-2.0*skill
