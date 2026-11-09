import os
import sys
from pathlib import Path

from fastapi import Header, HTTPException

sys.path.append(str(Path(__file__).resolve().parent.parent / "shared"))

from common import supabase

# The auth package was renamed between supabase releases.
try:
    from supabase_auth.errors import AuthError
except ImportError:  # pragma: no cover
    from gotrue.errors import AuthError


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
    verifies it with Supabase, and returns the user's id, role and name.

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
        user_response = supabase().auth.get_user(token)

    except AuthError:
        # Supabase looked at the token and rejected it.
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    except Exception as e:
        # Anything else is a problem reaching Supabase, not a bad token.
        # Answering 401 here would sign a student out over a network blip.
        print("[ORCHESTRATOR] Could not verify token:", type(e).__name__, e)

        raise HTTPException(
            status_code=503,
            detail="Could not reach the sign-in service. Try again in a moment."
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
    role = None
    full_name = None

    try:

        profile = supabase().table("profiles") \
            .select("role,full_name") \
            .eq("id", user_id) \
            .execute()

        if profile.data:
            role = profile.data[0]["role"]
            full_name = profile.data[0].get("full_name")

    except Exception:
        pass


    return {
        "id": user_id,
        "role": role,
        "full_name": full_name
    }
