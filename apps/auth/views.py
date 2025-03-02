from ninja import NinjaAPI
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from django.utils import timezone

from config.ninja_utils.errors import NinjaError
from apps.auth.schemas import (
    LoginInSchema,
    LoginOutSchema,
    SignupInSchema,
    SignupOutSchema,
)
from apps.auth.utils import create_jwt_token


auth_api = NinjaAPI(urls_namespace="auth")


# Set custom exception handler
@auth_api.exception_handler(NinjaError)
def handle_elham_error(request, exc: NinjaError):
    return auth_api.create_response(
        request,
        {"error_name": exc.error_name, "message": exc.message},
        status=exc.status_code,
    )


@auth_api.post("login/", response=LoginOutSchema)
def login(request, data: LoginInSchema):
    user = authenticate(request, username=data.email, password=data.password)

    if not user:
        raise NinjaError(
            error_name="invalid_credentials",
            message="Invalid email or password",
            status_code=401,
        )

    token = create_jwt_token(user.id)
    user.last_login = timezone.now()
    user.save()

    return {"token": token}


@auth_api.post("signup/", response=SignupOutSchema)
def signup(request, data: SignupInSchema):
    User = get_user_model()

    if User.objects.filter(email=data.email).exists():
        raise NinjaError(
            error_name="email_in_use",
            message="Email is already in use",
            status_code=400,
        )

    user = User.objects.create(
        email=data.email,
        username=data.email,
        password=make_password(data.password),  # Hash the password before saving
        first_name=data.first_name,
        last_name=data.last_name,
    )

    token = create_jwt_token(user.id)
    user.last_login = timezone.now()
    user.save()

    return {"token": token}
