import jwt
from ninja.security import HttpBearer
from django.contrib.auth import get_user_model
from django.conf import settings

from config.ninja_utils.errors import NinjaError


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")

            if not user_id:
                raise NinjaError(
                    error_name="invalid_token", message="Invalid token", status_code=401
                )

            User = get_user_model()
            user = User.objects.filter(id=user_id).first()

            if not user:
                raise NinjaError(
                    error_name="user_not_found",
                    message="User not found",
                    status_code=404,
                )

            return user
        except jwt.ExpiredSignatureError:
            raise NinjaError(
                error_name="token_expired", message="Token expired", status_code=401
            )
        except jwt.InvalidTokenError:
            raise NinjaError(
                error_name="invalid_token", message="Invalid token", status_code=401
            )


auth_bearer = AuthBearer()
