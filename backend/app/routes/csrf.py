from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi_csrf_protect import CsrfProtect

router = APIRouter()


@router.get("/csrftoken")
async def get_csrf_token(
    response: Response, csrf_protect: Annotated[CsrfProtect, Depends()]
):
    token, signed_token = csrf_protect.generate_csrf_tokens()
    csrf_protect.set_csrf_cookie(signed_token, response)
    return {"token": token}
