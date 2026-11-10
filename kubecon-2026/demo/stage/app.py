"""Chainlit surface for the stage demo: retain once, then the same question without and with a subject filter."""

import html

import chainlit as cl

from config import load_config
from offline_chainlit import install_local_template
from runtime import Demo

load_config()
install_local_template()


def actions():
    return [cl.Action(name="new_conversation", label="New conversation · keep memory", payload={})]


def cell(value):
    return html.escape(value).replace("|", "\\|")


def tag_value(tags, prefix):
    value = next((tag[len(prefix):] for tag in tags if tag.startswith(prefix)), None)
    return f"`{cell(value)}`" if value else "—"


def facts_markdown(items):
    if not items:
        return "_No facts returned._"
    lines = ["| # | About whom | Fact | Category |", "|---|---|---|---|"]
    for rank, item in enumerate(items, 1):
        tags = item.get("tags") or []
        text = (item.get("text") or "").split(" | Involving:")[0]
        lines.append(f"| {rank} | {tag_value(tags, 'subject:')} | {cell(text)} | {tag_value(tags, 'category:')} |")
    return "\n".join(lines)


@cl.on_chat_start
async def start():
    demo = Demo()
    session = await demo.create_session()
    cl.user_session.set("demo", demo)
    cl.user_session.set("state", session)
    await cl.Message(
        content="## Flight meals for two\n"
                f"Memory bank: `{session.bank_id}` · subject and category labels on · consolidation off",
        actions=actions(),
    ).send()


@cl.action_callback("new_conversation")
async def new_conversation(action):
    cl.user_session.get("state").new_conversation()
    await cl.Message(content="**Fresh conversation.** App chat context cleared; the same Hindsight bank remains.", actions=actions()).send()


@cl.on_chat_end
async def end():
    demo = cl.user_session.get("demo")
    if demo:
        await demo.aclose()


@cl.on_message
async def message(message):
    try:
        result = await cl.user_session.get("demo").turn(cl.user_session.get("state"), message.content)
        question = html.escape(result["question"])
        await cl.Message(content="### WRITE · retain · tags: `task:flight-booking`\n> " + html.escape(result["source_text"]) +
                         "\n\n**Stored facts, with the labels Hindsight assigned as tags:**\n\n" +
                         facts_markdown(result["stored_facts"]["items"])).send()
        await cl.Message(content=f"### READ · recall · no filter\n> {question}\n\n" +
                         facts_markdown(result["recall_unfiltered"]["results"])).send()
        failed = [name for name, ok in result["checks"].items() if not ok]
        note = ("\n\n**Check failed:** " + ", ".join(failed) + ". The labels are model-assigned; show this result as it is."
                if failed else "")
        await cl.Message(content=f"### READ · recall · tags: `[\"subject:user\"]` · tags_match: `\"any_strict\"`\n> {question}\n\n" +
                         facts_markdown(result["recall_subject_user"]["results"]) + note,
                         actions=actions()).send()
    except Exception as exc:
        await cl.Message(content=f"**Demo blocked: {type(exc).__name__}.** Go to S19; an earlier retain may have completed.", actions=actions()).send()
