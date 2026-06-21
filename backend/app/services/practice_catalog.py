from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import PracticeScenario, PracticeSkill, VoicePreset


DEFAULT_SKILLS = [
    {"name": "Fluência", "description": "Responder com mais naturalidade e menos pausas.", "level": "all"},
    {"name": "Pronúncia", "description": "Treinar sons, ritmo e clareza na fala.", "level": "all"},
    {"name": "Vocabulário natural", "description": "Usar expressões comuns em situações reais.", "level": "beginner"},
    {"name": "Correção gramatical", "description": "Receber correções leves e aplicáveis durante a conversa.", "level": "all"},
    {"name": "Escuta ativa", "description": "Entender perguntas curtas e responder com confiança.", "level": "beginner"},
    {"name": "Fala profissional", "description": "Praticar linguagem de trabalho, reuniões e entrevistas.", "level": "intermediate"},
]

SCENARIO_BLUEPRINTS = [
    ("Apresentação pessoal", "Practice introductions, origin, routine and interests.", "beginner", ["Fluência", "Vocabulário natural"]),
    ("Pedir café e restaurante", "Practice ordering food, asking preferences and paying politely.", "beginner", ["Fluência", "Pronúncia", "Vocabulário natural"]),
    ("Viagem, hotel e aeroporto", "Practice check-in, reservations, directions and travel questions.", "beginner", ["Escuta ativa", "Vocabulário natural"]),
    ("Entrevista de emprego", "Practice short answers about experience, goals and strengths.", "intermediate", ["Fala profissional", "Correção gramatical"]),
    ("Reunião de trabalho", "Practice opinions, status updates and polite interruptions.", "intermediate", ["Fala profissional", "Fluência"]),
    ("Conversa casual", "Practice small talk, hobbies, weekend plans and follow-up questions.", "beginner", ["Fluência", "Escuta ativa"]),
    ("Compras e atendimento", "Practice sizes, prices, returns and asking for help in stores.", "beginner", ["Vocabulário natural", "Escuta ativa"]),
    ("Emergência e ajuda", "Practice asking for help, describing problems and urgent needs.", "beginner", ["Escuta ativa", "Pronúncia"]),
    ("Pronúncia guiada", "Practice short sentences with rhythm, clarity and repetition.", "all", ["Pronúncia"]),
    ("Revisão gramatical", "Practice correcting mistakes gently while keeping conversation natural.", "all", ["Correção gramatical"]),
]

LANGUAGES = {
    "en": {"label": "Inglês", "voice_language": "en-US"},
    "es": {"label": "Espanhol", "voice_language": "es-ES"},
    "fr": {"label": "Francês", "voice_language": "fr-FR"},
    "pt": {"label": "Português", "voice_language": "pt-BR"},
}


def _scenario_title(base_title: str, language_label: str) -> str:
    return f"{base_title} em {language_label}"


async def bootstrap_practice_catalog(session: AsyncSession) -> None:
    existing_skills = await session.execute(select(PracticeSkill))
    skills_by_name = {skill.name: skill for skill in existing_skills.scalars().all()}

    for item in DEFAULT_SKILLS:
        skill = skills_by_name.get(item["name"])
        if not skill:
            skill = PracticeSkill(**item)
            session.add(skill)
            skills_by_name[skill.name] = skill
        else:
            skill.description = item["description"]
            skill.level = item["level"]
            skill.is_active = True

    await session.flush()

    existing_scenarios = await session.execute(select(PracticeScenario).options(selectinload(PracticeScenario.skills)))
    scenarios_by_title = {scenario.title: scenario for scenario in existing_scenarios.scalars().all()}

    for language_code, language in LANGUAGES.items():
        for base_title, prompt, level, skill_names in SCENARIO_BLUEPRINTS:
            title = _scenario_title(base_title, language["label"])
            scenario = scenarios_by_title.get(title)
            if not scenario:
                scenario = PracticeScenario(
                    title=title,
                    description=f"{base_title} para praticar {language['label']} em contexto real.",
                    prompt_template=prompt,
                    target_language=language_code,
                    level=level,
                    is_active=True,
                )
                session.add(scenario)
            else:
                scenario.description = f"{base_title} para praticar {language['label']} em contexto real."
                scenario.prompt_template = prompt
                scenario.target_language = language_code
                scenario.level = level
                scenario.is_active = True
            scenario.skills = [skills_by_name[name] for name in skill_names if name in skills_by_name]

    existing_voices = await session.execute(select(VoicePreset))
    voices_by_name = {voice.name: voice for voice in existing_voices.scalars().all()}
    for language_code, language in LANGUAGES.items():
        for name_suffix, speed, default_for_language in [("claro", 0.96, True), ("lento", 0.82, False)]:
            name = f"Tutor {language['label']} {name_suffix}"
            voice = voices_by_name.get(name)
            if not voice:
                voice = VoicePreset(name=name)
                session.add(voice)
            voice.provider = "browser"
            voice.model = "browser-speech-synthesis"
            voice.voice = ""
            voice.language = language["voice_language"]
            voice.speed = speed
            voice.pitch = 1.0
            voice.is_default = default_for_language and language_code == "en"
            voice.is_active = True

    await session.commit()
