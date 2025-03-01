from ninja import Schema
from pydantic import EmailStr


class LoginInSchema(Schema):
    email: EmailStr
    password: str


class LoginOutSchema(Schema):
    token: str


class SignupInSchema(Schema):
    email: str
    password: str
    first_name: str
    last_name: str


class SignupOutSchema(Schema):
    token: str
