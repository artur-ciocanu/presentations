"""Flight-meal memory demo using real Hindsight and an explicit source review."""

import asyncio
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from hindsight_client import Hindsight
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from config import ROOT, load_config

# Stage path matches the deck (S16, S18, S19) and Config B of demo/experiments/hindsight/REPORT.md.
RETAIN_TAGS = ["task:flight-booking"]
QUESTION = "Does Artur have diabetes?"
SUBJECT_FILTER = {"tags": ["subject:user"], "tags_match": "any_strict"}
GUARDRAILS = {
    "retain_mission": "Record user-declared facts with who each fact is about. Do not promote assistant "
                      "suggestions or statements to facts about the user. Write extracted facts in English.",
    "enable_observations": False,
    "entity_labels": [
        {"key": "subject", "description": "Who the fact is about; distinguish the user from a family member.",
         "type": "value", "optional": True, "tag": True,
         "values": [{"value": "user", "description": "The user speaking"},
                    {"value": "family_member", "description": "A family member of the user"}]},
        {"key": "category", "description": "The category of the fact.", "type": "multi-values", "tag": True,
         "values": [{"value": "health", "description": "Health conditions or health information"},
                    {"value": "food_preference", "description": "Food preferences and restrictions"}]},
    ],
}


class ClaimReview(BaseModel):
    fact_id: str
    claim: str
    subject: Literal["speaker", "mom", "both", "other", "unclear"]
    kind: Literal["diabetes", "cinnamon_avoidance", "cinnamon_allergy", "allergy_not_stated", "flight", "other"]
    provenance: Literal["stated", "inferred", "unsupported", "unclear"]
    health_related: bool
    source_quote: str | None


class MemoryReview(BaseModel):
    claims: list[ClaimReview]


@dataclass
class Session:
    bank_id: str
    conversation_id: str = field(default_factory=lambda: "chat-" + uuid.uuid4().hex)
    transcript: list[dict] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)

    def new_conversation(self):
        self.conversation_id = "chat-" + uuid.uuid4().hex
        self.transcript = []


def review_errors(review: MemoryReview, sources: dict[str, str], facts: list[dict], *, initial_document: str | None):
    """Guard the fixed demo's expected ownership; this is not a general safety classifier."""
    errors = []
    ids = {fact["id"] for fact in facts}
    facts_by_id = {fact["id"]: fact for fact in facts}
    reviewed = {claim.fact_id for claim in review.claims}
    if ids != reviewed:
        errors.append("Review does not cover exactly the returned Hindsight fact IDs")
    for claim in review.claims:
        fact = facts_by_id.get(claim.fact_id, {})
        source = sources.get(fact.get("document_id"), "")
        if claim.provenance == "stated" and (not claim.source_quote or claim.source_quote.casefold() not in source.casefold()):
            errors.append("A claimed direct statement lacks an exact source quote")
        if claim.provenance in ("unsupported", "unclear"):
            errors.append("A returned fact has an unsupported or unclear claim")
        if initial_document and fact.get("document_id") == initial_document:
            if claim.kind == "diabetes" and (claim.subject != "mom" or not claim.health_related):
                errors.append("Diabetes was attributed to someone other than mom or not marked health-related")
            if claim.kind == "diabetes" and claim.provenance == "stated" and "she has diabetes" not in (claim.source_quote or "").casefold():
                errors.append("The diabetes source quote does not establish whose statement it is")
            if claim.kind == "cinnamon_allergy":
                errors.append("A cinnamon allergy was inferred or claimed")
            if claim.kind == "allergy_not_stated" and claim.provenance != "inferred":
                errors.append("A statement about an unmentioned allergy must be shown as inferred")
            if claim.kind == "cinnamon_avoidance" and claim.subject != "speaker":
                errors.append("The cinnamon preference was attributed to someone other than the speaker")
            if claim.kind == "cinnamon_avoidance" and claim.provenance == "stated" and "i want to avoid" not in (claim.source_quote or "").casefold():
                errors.append("The cinnamon source quote does not establish whose preference it is")
            if (claim.kind == "cinnamon_avoidance" and claim.provenance == "stated"
                    and re.search(r"\b(?:food|foods|meal|meals|dish|dishes)\b", claim.claim, re.I)
                    and not re.search(r"\b(?:food|foods|meal|meals|dish|dishes)\b", claim.source_quote or "", re.I)):
                errors.append("A meal-specific cinnamon claim is inferred, not directly stated")
    if initial_document:
        # A conservative extra check on the real text, not a substitute for review.
        for fact in facts:
            if fact.get("document_id") != initial_document:
                continue
            text = fact.get("text", "").lower()
            absence = re.search(r"\bno\s+(?:\w+\s+){0,3}allerg\w*\s+(?:was|is)\s+(?:stated|mentioned|reported)\b", text)
            if absence and not any(c.fact_id == fact["id"] and c.kind == "allergy_not_stated" and c.provenance == "inferred" for c in review.claims):
                errors.append("The review omitted an inferred statement that no allergy was mentioned")
            positive_text = text[:absence.start()] + text[absence.end():] if absence else text
            if re.search(r"\bcinnamon\b.{0,80}\ballerg\w*|\ballerg\w*.{0,80}\bcinnamon\b", positive_text):
                errors.append("A returned fact mentions a cinnamon allergy; inspect it before proceeding")
            if re.search(r"\b(?:speaker|user|traveler|traveller|customer)\s+(?:has|have|is diagnosed with)\s+diabetes\b", text):
                errors.append("A returned fact attributes diabetes to the speaker; inspect it before proceeding")
            if re.search(r"\b(?:speaker|user|traveler|traveller|customer)\s+(?:is|was)\s+diabetic\b", text):
                errors.append("A returned fact describes the speaker as diabetic; inspect it before proceeding")
    return list(dict.fromkeys(errors))


class Demo:
    def __init__(self):
        config = load_config()
        self.memory = Hindsight(base_url=f"http://127.0.0.1:{config['HINDSIGHT_PORT']}", timeout=180)
        self.llm_client = AsyncOpenAI(base_url=config["LLM_BASE_URL"], api_key=config["LLM_API_KEY"],
                                      timeout=25.0, max_retries=0)
        provider = OpenAIProvider(openai_client=self.llm_client)
        model = OpenAIResponsesModel(config["LLM_MODEL"], provider=provider)
        self.phase_times = {}
        self.reviewer = Agent(model, output_type=MemoryReview, instructions=(
            "Review each actual stored or recalled memory against its supplied source document. "
            "Return all atomic claims and qualifiers for every fact ID, including any claim about what "
            "was not stated; do not omit a clause just because it is not a medical diagnosis. "
            "Return no invented fact IDs. "
            "Identify whose fact it is: speaker, mom, both, other, or unclear. "
            "Label each claim stated only if the exact source quote supports that claim and its subject; "
            "otherwise label inferred, unsupported, or unclear. For stated claims source_quote must be an "
            "exact substring of that fact's source document; otherwise use null. Do not equate avoiding cinnamon "
            "with an allergy, and do not assign mom's diabetes to the speaker. If a memory makes either "
            "claim, report the claim as it appears and label its provenance unsupported; do not hide it. "
            "If a memory says no allergy was stated or mentioned, review that separate meta-claim with "
            "kind allergy_not_stated and provenance inferred: it is an inference about the source, not "
            "evidence that the person has or does not have an allergy. Do not equate it with an allergy diagnosis. "
            "When the source says avoid anything with cinnamon, preserve that wording in the stated claim. "
            "A specific link to meals or food is a separate inferred qualifier unless the source says it. "
            "Mark diabetes and allergy claims health-related; a food preference alone is not a diagnosis. "
            "This is an application review, not a Hindsight-provided provenance label."
        ))

    async def phase(self, name, operation, timeout):
        start = time.monotonic()
        try:
            return await asyncio.wait_for(operation, timeout=timeout)
        except TimeoutError:
            raise TimeoutError(f"{name} exceeded {timeout} seconds") from None
        finally:
            self.phase_times[name] = round(time.monotonic() - start, 3)

    async def aclose(self):
        await self.memory.aclose()
        await self.llm_client.close()

    async def create_session(self):
        bank = "artur-" + uuid.uuid4().hex[:8]
        await self.phase("create_bank", self.memory.acreate_bank(bank_id=bank, name="Artur, flight booking"), 15)
        await self.phase("guardrails", self.memory.aupdate_bank_config(bank, **GUARDRAILS), 15)
        return Session(bank_id=bank)

    async def turn(self, session: Session, text: str):
        """Retain one user message, then ask the same question without and with the subject filter."""
        document_id = "source-" + uuid.uuid4().hex[:8]
        retained = await self.phase("retain", self.memory.aretain(
            bank_id=session.bank_id, content="user: " + text, document_id=document_id,
            timestamp=datetime.now(timezone.utc), tags=RETAIN_TAGS, retain_async=False,
        ), 45)
        session.sources[document_id] = text
        stored = (await self.phase("list_stored", self.memory.alist_memories(bank_id=session.bank_id, document_id=document_id), 15)).model_dump(mode="json")
        unfiltered = (await self.phase("recall_unfiltered", self.memory.arecall(bank_id=session.bank_id, query=QUESTION), 15)).model_dump(mode="json")
        filtered = (await self.phase("recall_subject_user", self.memory.arecall(bank_id=session.bank_id, query=QUESTION, **SUBJECT_FILTER), 15)).model_dump(mode="json")
        session.transcript.append({"role": "user", "content": text})
        return {
            "source_text": text, "source_document": document_id, "question": QUESTION,
            "stored_facts": stored, "recall_unfiltered": unfiltered, "recall_subject_user": filtered,
            "checks": stage_checks(stored["items"], unfiltered["results"], filtered["results"]),
            "retained": retained.model_dump(mode="json"),
            "phase_seconds": dict(self.phase_times),
            "bank_id": session.bank_id, "conversation_id": session.conversation_id,
        }


def is_mom_health(fact):
    tags = set(fact.get("tags") or [])
    return "subject:family_member" in tags and "category:health" in tags


def stage_checks(stored, unfiltered, filtered):
    """What the slides claim, checked on the actual results. Labels are model-assigned, so these can fail."""
    return {
        "mom_health_fact_tagged": any(is_mom_health(f) for f in stored),
        "unfiltered_first_is_mom_health": bool(unfiltered) and is_mom_health(unfiltered[0]),
        "filtered_excludes_mom_health": not any(is_mom_health(f) for f in filtered),
        "filtered_returns_something": bool(filtered),
    }
