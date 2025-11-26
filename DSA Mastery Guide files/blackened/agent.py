# ======================================================
# 💼 DAY 5: AI SALES DEVELOPMENT REP (SDR)
# 🧑‍🏫 "Om Store" - Auto-Lead Capture Agent
# 🚀 Features: FAQ Retrieval, Lead Qualification, JSON Database
# ======================================================

import logging
import json
import os
import asyncio
from datetime import datetime
from typing import Annotated, Literal, Optional, List
from dataclasses import dataclass, asdict

print("\n" + "💼" * 50)
print("🚀 AI SDR AGENT - DAY 5 TUTORIAL")
print("📚 SELLING: Om's DSA & LeetCode Mastery Courses")
print("💡 agent.py LOADED SUCCESSFULLY!")
print("💼" * 50 + "\n")

from dotenv import load_dotenv
from pydantic import Field
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)

# 🔌 PLUGINS
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")
load_dotenv(".env.local")

# ======================================================
# 📂 1. KNOWLEDGE BASE (FAQ)
# ======================================================

FAQ_FILE = "store_faq.json"
LEADS_FILE = "leads_db.json"

# Default FAQ data for "Om Store"
DEFAULT_FAQ = [
    {
        "question": "What courses do you offer?",
        "answer": "We offer premium courses on Data Structures, Algorithms, LeetCode Mastery, and System Design. We also have a complete DSA Bootcamp for FAANG interviews."
    },
    {
        "question": "How much does the LeetCode Mastery course cost?",
        "answer": "Our 'Complete LeetCode Mastery' course is priced at $249. It includes 200+ solved problems, patterns, and mock interviews."
    },
    {
        "question": "Do you offer free content?",
        "answer": "Yes! Om uploads weekly free DSA tutorials on YouTube. Premium courses offer structured learning, advanced problems, and interview preparation."
    },
    {
        "question": "Do you provide 1:1 mock interviews?",
        "answer": "Yes. We offer personalized mock interviews for DSA, System Design, and behavioral rounds. Pricing depends on the session type."
    }
]

def load_knowledge_base():
    """Generates FAQ file if missing, then loads it."""
    try:
        path = os.path.join(os.path.dirname(__file__), FAQ_FILE)
        if not os.path.exists(path):
            with open(path, "w", encoding='utf-8') as f:
                json.dump(DEFAULT_FAQ, f, indent=4)
        with open(path, "r", encoding='utf-8') as f:
            return json.dumps(json.load(f))  # Return as string for the Prompt
    except Exception as e:
        print(f"⚠️ Error loading FAQ: {e}")
        return ""

STORE_FAQ_TEXT = load_knowledge_base()

# ======================================================
# 💾 2. LEAD DATA STRUCTURE
# ======================================================

@dataclass
class LeadProfile:
    name: str | None = None
    company: str | None = None
    email: str | None = None
    role: str | None = None
    use_case: str | None = None
    team_size: str | None = None
    timeline: str | None = None

    def is_qualified(self):
        """Returns True if we have the minimum info (Name + Email + Use Case)"""
        return all([self.name, self.email, self.use_case])

@dataclass
class Userdata:
    lead_profile: LeadProfile

# ======================================================
# 🛠️ 3. SDR TOOLS
# ======================================================

@function_tool
async def update_lead_profile(
    ctx: RunContext[Userdata],
    name: Annotated[Optional[str], Field(description="Customer's name")] = None,
    company: Annotated[Optional[str], Field(description="Customer's company name")] = None,
    email: Annotated[Optional[str], Field(description="Customer's email address")] = None,
    role: Annotated[Optional[str], Field(description="Customer's job title")] = None,
    use_case: Annotated[Optional[str], Field(description="What they want to learn (e.g., DSA, LeetCode prep)")] = None,
    team_size: Annotated[Optional[str], Field(description="Number of people in their team")] = None,
    timeline: Annotated[Optional[str], Field(description="When they want to start (e.g., Now, next month)")] = None,
) -> str:

    profile = ctx.userdata.lead_profile

    if name: profile.name = name
    if company: profile.company = company
    if email: profile.email = email
    if role: profile.role = role
    if use_case: profile.use_case = use_case
    if team_size: profile.team_size = team_size
    if timeline: profile.timeline = timeline

    print(f"📝 UPDATING LEAD: {profile}")
    return "Lead profile updated. Continue the conversation."

@function_tool
async def submit_lead_and_end(
    ctx: RunContext[Userdata],
) -> str:

    profile = ctx.userdata.lead_profile

    db_path = os.path.join(os.path.dirname(__file__), LEADS_FILE)

    entry = asdict(profile)
    entry["timestamp"] = datetime.now().isoformat()

    existing_data = []
    if os.path.exists(db_path):
        try:
            with open(db_path, "r") as f:
                existing_data = json.load(f)
        except:
            pass

    existing_data.append(entry)

    with open(db_path, "w") as f:
        json.dump(existing_data, f, indent=4)

    print(f"✅ LEAD SAVED TO {LEADS_FILE}")
    return (
        f"Lead saved. Summarize the call for the user: "
        f"'Thanks {profile.name}, I have your info regarding {profile.use_case}. "
        f"We will email you at {profile.email}. Goodbye!'"
    )

# ======================================================
# 🧠 4. AGENT DEFINITION
# ======================================================

class SDRAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=f"""
            You are 'Sarah', a friendly and professional Sales Development Rep (SDR) for 'Om Store'.

            📘 **YOUR KNOWLEDGE BASE (FAQ):**
            {STORE_FAQ_TEXT}

            🎯 **YOUR GOAL:**
            1. Answer questions about our DSA / LeetCode / System Design courses.
            2. **QUALIFY THE LEAD:** Gradually ask for:
               - Name
               - Company / Role
               - Email
               - What they want to learn (e.g., LeetCode prep, DSA from basics)
               - Timeline to start

            ⚙️ **BEHAVIOR:**
            - Friendly and conversational.
            - Answer → then ask for a detail.
            - Use `update_lead_profile` whenever user provides info.
            - Use `submit_lead_and_end` when user says “bye”, “thanks”, “that’s all”.

            🚫 **RESTRICTIONS:**
            - If unsure, say: “I'll check with Om and email you.”
            """
        ,
            tools=[update_lead_profile, submit_lead_and_end],
        )

# ======================================================
# 🎬 ENTRYPOINT
# ======================================================

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}

    print("\n" + "💼" * 25)
    print("🚀 STARTING SDR SESSION")

    userdata = Userdata(lead_profile=LeadProfile())

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-natalie",
            style="Promo",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        userdata=userdata,
    )

    await session.start(
        agent=SDRAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC()
        ),
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
