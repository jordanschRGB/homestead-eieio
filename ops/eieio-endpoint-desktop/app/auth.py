from fastapi import Header, HTTPException, status


def auth_dependency(expected_token: str):
    def _auth(authorization: str | None = Header(default=None)) -> None:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "missing_bearer_token"},
            )

        token = authorization.removeprefix("Bearer ").strip()
        if token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "invalid_bearer_token"},
            )

    return _auth
