#!/usr/bin/env python3
"""Fetch website announcements from the GSGW Discord announcement channel."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

API_BASE = "https://discord.com/api/v10"
GUILD_ID = "1502484309460647976"
CHANNEL_ID = "1502485142520729660"
REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "website" / "src" / "lib" / "announcements.json"


def discord_get(path: str, params: dict[str, str] | None = None) -> Any:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set.")

    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "GSGW-Reader announcement sync",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Discord API: {exc.reason}") from exc


def fetch_messages() -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    before: str | None = None

    while True:
        params = {"limit": "100"}
        if before:
            params["before"] = before

        batch = discord_get(f"/channels/{CHANNEL_ID}/messages", params)
        if not isinstance(batch, list):
            raise RuntimeError("Discord returned an unexpected message response.")

        messages.extend(batch)
        if len(batch) < 100:
            break

        before = batch[-1]["id"]

    return messages


def clean_inline_markdown(value: str) -> str:
    value = value.strip()
    bold = re.fullmatch(r"\*\*(.+?)\*\*", value)
    heading = re.fullmatch(r"#{1,6}\s+(.+)", value)
    if bold:
        return bold.group(1).strip()
    if heading:
        return heading.group(1).strip()
    return value


def split_announcement(content: str) -> tuple[str, str, str]:
    content = content.strip()
    if not content:
        return "", "", ""

    lines = content.splitlines()
    first_line = lines[0].strip()
    explicit_title = bool(
        re.fullmatch(r"\\*\\*(.+?)\\*\\*", first_line)
        or re.fullmatch(r"#{1,6}\\s+(.+)", first_line)
    )

    if explicit_title:
        title = clean_inline_markdown(first_line)
        body = "\n".join(lines[1:]).strip()
    else:
        title = clean_inline_markdown(first_line)
        body = content

    # Keep ordinary Discord messages useful without requiring special title syntax.
    if len(title) > 80:
        title = title[:77].rstrip() + "..."

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    short = paragraphs[0] if paragraphs else body
    long = "\n\n".join(paragraphs[1:])

    return title, short, long


def parse_message(
    message: dict[str, Any],
    role_names: dict[str, str],
    member_names: dict[str, str],
    channel_names: dict[str, str],
) -> dict[str, Any] | None:
    content = (message.get("content") or "").strip()
    attachments = message.get("attachments") or []
    embeds = message.get("embeds") or []

    # Skip Discord system messages and truly empty messages.
    if message.get("type", 0) != 0:
        return None
    if not content and not attachments and not embeds:
        return None

    title, _, _ = split_announcement(content)
    if not title:
        embed_title = next((item.get("title") for item in embeds if item.get("title")), None)
        title = embed_title or "Discord announcement"

    # Preserve the complete Discord message as the body. Announcements is a
    # category marker and is removed, while release roles double as visible
    # titles and stay in the body using their readable role names.
    release_roles = {"gsgw releases", "dod releases"}

    def replace_role_mention(match: re.Match[str]) -> str:
        role_name = role_names.get(match.group(1), "")
        return f"@{role_name}" if role_name.casefold() in release_roles else ""

    short = re.sub(r"<@&(\d+)>", replace_role_mention, content)
    short = re.sub(
        r"<@!?(\d+)>",
        lambda match: member_names.get(match.group(1), "Unknown user"),
        short,
    )
    short = re.sub(
        r"<#(\d+)>",
        lambda match: f"#{channel_names.get(match.group(1), 'unknown-channel')}",
        short,
    )
    short = re.sub(r"<a?:[A-Za-z0-9_~]+:\d+>", "", short)
    short = re.sub(r"[ \t]+\n", "\n", short)
    short = re.sub(r"\n{3,}", "\n\n", short).strip()
    long = ""
    if not short:
        embed_description = next(
            (item.get("description") for item in embeds if item.get("description")),
            None,
        )
        short = embed_description or ""

    timestamp = datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00"))
    author = message.get("author") or {}

    normalized_attachments = [
        {
            "url": item.get("url", ""),
            "filename": item.get("filename", ""),
            "contentType": item.get("content_type"),
            "width": item.get("width"),
            "height": item.get("height"),
        }
        for item in attachments
        if item.get("url")
    ]

    normalized_embeds = [
        {
            "title": item.get("title"),
            "description": item.get("description"),
            "url": item.get("url"),
            "image": (item.get("image") or {}).get("url"),
            "thumbnail": (item.get("thumbnail") or {}).get("url"),
        }
        for item in embeds
        if any(
            [
                item.get("title"),
                item.get("description"),
                item.get("url"),
                item.get("image"),
                item.get("thumbnail"),
            ]
        )
    ]

    supported_roles = {"announcements", "gsgw releases", "dod releases"}
    tags = [
        role_names[role_id]
        for role_id in message.get("mention_roles", [])
        if role_id in role_names and role_names[role_id].casefold() in supported_roles
    ]
    if not tags:
        return None

    message_id = str(message["id"])
    return {
        "title": title,
        "date": timestamp.date().isoformat(),
        "short": short,
        "long": long,
        "author": author.get("global_name") or author.get("username") or "",
        "tags": tags,
        "messageId": message_id,
        "discordUrl": f"https://discord.com/channels/{GUILD_ID}/{CHANNEL_ID}/{message_id}",
        "attachments": normalized_attachments,
        "embeds": normalized_embeds,
    }


def main() -> None:
    roles = discord_get(f"/guilds/{GUILD_ID}/roles")
    role_names = {
        str(role["id"]): role["name"]
        for role in roles
        if role.get("id") and role.get("name")
    }

    messages = fetch_messages()

    mentioned_user_ids = {
        str(mention["id"])
        for message in messages
        for mention in message.get("mentions", [])
        if mention.get("id")
    }
    member_names: dict[str, str] = {}
    for user_id in mentioned_user_ids:
        member = discord_get(f"/guilds/{GUILD_ID}/members/{user_id}")
        user = member.get("user") or {}
        member_names[user_id] = (
            member.get("nick")
            or user.get("global_name")
            or user.get("username")
            or "Unknown user"
        )

    mentioned_channel_ids = set(
        re.findall(r"<#(\d+)>", "\n".join(message.get("content") or "" for message in messages))
    )
    channel_names: dict[str, str] = {}
    for channel_id in mentioned_channel_ids:
        channel = discord_get(f"/channels/{channel_id}")
        channel_names[channel_id] = channel.get("name") or "unknown-channel"

    announcements = [
        parsed
        for message in messages
        if (
            parsed := parse_message(
                message,
                role_names,
                member_names,
                channel_names,
            )
        )
        is not None
    ]

    # Discord snowflakes increase over time, so this puts newest messages first.
    announcements.sort(key=lambda item: int(item["messageId"]), reverse=True)
    announcements = announcements[:15]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps({"announcements": announcements}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {len(announcements)} announcements to {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
