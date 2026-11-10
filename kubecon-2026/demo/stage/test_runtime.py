import asyncio

import pytest

from runtime import ClaimReview, Demo, MemoryReview, Session, review_errors, stage_checks

SOURCE = "I'm booking a long flight for me and my mom. She has diabetes. I want to avoid anything with cinnamon."


def claim(**changes):
    values = {"fact_id": "fact-1", "claim": "Mom has diabetes", "subject": "mom", "kind": "diabetes",
              "provenance": "stated", "health_related": True, "source_quote": "She has diabetes."}
    values.update(changes)
    return ClaimReview(**values)


def errors(review, text="Mom has diabetes."):
    return review_errors(review, {"doc-1": SOURCE}, [{"id": "fact-1", "document_id": "doc-1", "text": text}], initial_document="doc-1")


def test_new_conversation_keeps_bank_and_sources_but_clears_context():
    session = Session(bank_id="demo")
    before = session.conversation_id
    session.transcript = [{"role": "user", "content": "old context"}]
    session.sources = {"doc-1": SOURCE}
    session.new_conversation()
    assert session.bank_id == "demo"
    assert session.conversation_id != before
    assert session.transcript == []
    assert session.sources == {"doc-1": SOURCE}


def test_direct_mom_diabetes_is_accepted():
    assert errors(MemoryReview(claims=[claim()])) == []


def test_diabetes_attributed_to_speaker_is_rejected():
    found = errors(MemoryReview(claims=[claim(subject="speaker")]), "The user has diabetes.")
    assert any("other than mom" in item for item in found)
    assert any("attributes diabetes to the speaker" in item for item in found)


def test_invented_cinnamon_allergy_is_rejected():
    found = errors(MemoryReview(claims=[claim(subject="speaker", kind="cinnamon_allergy", provenance="inferred", source_quote=None)]), "The user is allergic to cinnamon.")
    assert any("cinnamon allergy" in item for item in found)


def test_absence_of_allergy_statement_is_reviewed_as_inferred_not_diagnosed():
    preference = claim(subject="speaker", kind="cinnamon_avoidance", health_related=False,
                       source_quote="I want to avoid anything with cinnamon.")
    absence = claim(subject="speaker", kind="allergy_not_stated", provenance="inferred",
                    health_related=False, source_quote=None, claim="No allergy was stated")
    text = "The user wants to avoid cinnamon; no allergy was stated."
    assert errors(MemoryReview(claims=[preference, absence]), text) == []
    assert any("omitted" in item for item in errors(MemoryReview(claims=[preference]), text))


def test_direct_claim_requires_a_verbatim_and_subject_specific_quote():
    found = errors(MemoryReview(claims=[claim(source_quote="I want to avoid anything with cinnamon.")]))
    assert any("whose statement" in item for item in found)
    found = errors(MemoryReview(claims=[claim(source_quote="This was never said")]))
    assert any("exact source quote" in item for item in found)


def test_meal_specific_qualifier_is_not_labeled_directly_stated():
    review = MemoryReview(claims=[claim(subject="speaker", kind="cinnamon_avoidance", health_related=False,
                                         claim="Avoid cinnamon in meals", source_quote="I want to avoid anything with cinnamon.")])
    assert any("meal-specific" in item for item in errors(review, "The user avoids cinnamon in meals."))


def test_incomplete_or_invented_review_is_rejected():
    assert any("exactly" in item for item in errors(MemoryReview(claims=[])))
    assert any("exactly" in item for item in errors(MemoryReview(claims=[claim(fact_id="invented")])))


def test_uncertain_claim_is_not_silently_treated_as_stated():
    found = errors(MemoryReview(claims=[claim(provenance="unclear", source_quote=None)]))
    assert any("unsupported or unclear" in item for item in found)


def test_slow_phase_is_bounded_and_timed():
    demo = Demo.__new__(Demo)
    demo.phase_times = {}

    async def blocked():
        await asyncio.Event().wait()

    async def exercise():
        with pytest.raises(TimeoutError, match="test_phase exceeded"):
            await demo.phase("test_phase", blocked(), 0.01)

    asyncio.run(exercise())
    assert "test_phase" in demo.phase_times


MOM = {"text": "User's mother has diabetes.", "tags": ["task:flight-booking", "subject:family_member", "category:health"]}
ME = {"text": "User wants to avoid cinnamon.", "tags": ["task:flight-booking", "subject:user", "category:food_preference"]}


def test_stage_checks_pass_when_filter_excludes_mom_health():
    assert all(stage_checks([MOM, ME], [MOM, ME], [ME]).values())


def test_stage_checks_fail_when_filter_leaks_mom_health_or_labels_are_missing():
    assert not stage_checks([MOM, ME], [MOM, ME], [MOM, ME])["filtered_excludes_mom_health"]
    untagged = {"text": MOM["text"], "tags": ["task:flight-booking"]}
    checks = stage_checks([untagged, ME], [untagged, ME], [ME])
    assert not checks["mom_health_fact_tagged"] and not checks["unfiltered_first_is_mom_health"]
