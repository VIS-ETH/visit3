from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi_csrf_protect import CsrfProtect

from app.core.csrf import CSRF_COOKIE_KEY, unsign_csrf_token

router = APIRouter()


@router.get("/csrftoken")
async def get_csrf_token(
    request: Request,
    response: Response,
    csrf_protect: Annotated[CsrfProtect, Depends()],
):
    existing_token = unsign_csrf_token(request.cookies.get(CSRF_COOKIE_KEY))
    if existing_token:
        return {"token": existing_token}

    token, signed_token = csrf_protect.generate_csrf_tokens()
    csrf_protect.set_csrf_cookie(signed_token, response)
    return {"token": token}
