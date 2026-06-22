from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import PracticeScenario, PracticeSkill, VoicePersonality, VoicePreset


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

VOICE_BLUEPRINTS = [
    ("feminina clara", "female", 0.96, True),
    ("feminina lenta", "female", 0.84, False),
    ("masculina clara", "male", 0.96, False),
    ("masculina lenta", "male", 0.84, False),
    ("neutra clara", "neutral", 0.94, False),
]

PERSONALITY_BLUEPRINTS = [
    {
        "suffix": "Marina paciente",
        "gender": "female",
        "age": 32,
        "profession": "professora de idiomas",
        "hobbies": "música, viagens e café",
        "description": "Tutora feminina paciente, acolhedora e encorajadora.",
        "tone": "paciente e gentil",
        "prompt_instructions": "Fale como uma tutora paciente. Corrija com delicadeza, use exemplos curtos e mantenha a conversa leve.",
    },
    {
        "suffix": "Rafael conversacional",
        "gender": "male",
        "age": 35,
        "profession": "mentor de conversação",
        "hobbies": "cinema, tecnologia e esportes",
        "description": "Tutor masculino direto, casual e natural.",
        "tone": "conversacional e objetivo",
        "prompt_instructions": "Fale como um mentor casual. Faça perguntas naturais, corrija sem formalidade excessiva e mantenha fluidez.",
    },
    {
        "suffix": "Lia barista",
        "gender": "female",
        "age": 28,
        "profession": "barista",
        "hobbies": "cafés especiais, livros e fotografia",
        "description": "Personagem de café/restaurante para prática cotidiana.",
        "tone": "simpática e prática",
        "prompt_instructions": "Simule uma conversa de café ou restaurante quando fizer sentido. Seja simpática, breve e contextual.",
    },
    {
        "suffix": "Carlos profissional",
        "gender": "male",
        "age": 41,
        "profession": "recrutador e gerente",
        "hobbies": "negócios, leitura e corrida",
        "description": "Persona profissional para entrevistas e reuniões.",
        "tone": "profissional e respeitoso",
        "prompt_instructions": "Fale como um profissional de trabalho. Ajude com respostas claras, polidas e adequadas a entrevistas ou reuniões.",
    },
    {
        "suffix": "Sofia guia",
        "gender": "female",
        "age": 37,
        "profession": "guia de viagem",
        "hobbies": "história, mapas e gastronomia",
        "description": "Guia de viagem para hotel, aeroporto e direções.",
        "tone": "calma e prestativa",
        "prompt_instructions": "Fale como uma guia de viagem prestativa. Dê respostas práticas e continue o contexto de viagem quando aplicável.",
    },
]


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
        for name_suffix, gender, speed, default_for_language in VOICE_BLUEPRINTS:
            name = f"Tutor {language['label']} {name_suffix}"
            voice = voices_by_name.get(name)
            if not voice:
                voice = VoicePreset(
                    name=name,
                    provider="browser",
                    model="browser-speech-synthesis",
                    voice="",
                    language=language["voice_language"],
                    gender=gender,
                    speed=speed,
                    pitch=1.0,
                    is_default=default_for_language and language_code == "en",
                    is_active=True,
                )
                session.add(voice)

    existing_personalities = await session.execute(select(VoicePersonality))
    personalities_by_name = {personality.name: personality for personality in existing_personalities.scalars().all()}
    for language_code, language in LANGUAGES.items():
        for blueprint in PERSONALITY_BLUEPRINTS:
            name = f"{blueprint['suffix']} em {language['label']}"
            if name not in personalities_by_name:
                session.add(
                    VoicePersonality(
                        name=name,
                        gender=blueprint["gender"],
                        age=blueprint["age"],
                        profession=blueprint["profession"],
                        hobbies=blueprint["hobbies"],
                        description=f"{blueprint['description']} Idioma: {language['label']}.",
                        tone=blueprint["tone"],
                        prompt_instructions=blueprint["prompt_instructions"],
                        target_language=language_code,
                        is_active=True,
                    )
                )

    await session.commit()
