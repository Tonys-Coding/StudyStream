import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Header, HTTPException
from supabase import create_client


# Load the same root .env the agents use
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# Dev-only escape hatch.
#
# When REQUIRE_AUTH is false, requests without an Authorization header are
# allowed through and the caller falls back to the user_id in the request
# body. This keeps /docs and test_orchestrator.py usable without minting a
# real token.
#
# It also means anyone can claim any user_id, so this must stay true
# anywhere other than a local machine.
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").strip().lower() != "false"


def get_current_user(
        authorization: str | None = Header(default=None)
) -> dict | None:
    """
    Reads the Authorization header (format: 'Bearer <jwt-token>'),
    verifies it with Supabase, and returns the user's id + role.

    Returns None when auth is disabled and no header was sent.
    """

    if not authorization:

        if REQUIRE_AUTH:
            raise HTTPException(
                status_code=401,
                detail="Missing Authorization header"
            )

        return None


    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Malformed Authorization header"
        )


    token = authorization.removeprefix("Bearer ").strip()


    try:
        user_response = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


    if not user_response or not user_response.user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


    user_id = user_response.user.id


    # A user can be authenticated without having a profile row yet, since
    # profile setup happens just after signup. Missing profile is not an
    # error here - it just means the role is not known.
    try:

        profile = supabase.table("profiles") \
            .select("role") \
            .eq("id", user_id) \
            .execute()

        role = profile.data[0]["role"] if profile.data else None

    except Exception:
        role = None


    return {
        "id": user_id,
        "role": role
    }
