from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


COMMON_PASSWORDS = [
    "password",
    "password123",
    "password1",
    "qwerty",
    "qwerty123",
    "123456",
    "12345678",
    "123456789",
    "1234567890",
    "abc123",
    "monkey",
    "master",
    "dragon",
    "letmein",
    "login",
    "admin",
    "welcome",
    "hello",
    "shadow",
    "sunshine",
    "princess",
    "football",
    "iloveyou",
    "trustno1",
    "пароль",
    "пароль123",
    "йцукен",
    "йцукен123",
    "inostatus",
    "innostatus123",
    "signature",
    "поиск",
]


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Пароль должен быть не менее 8 символов, содержать заглавную букву, строчную букву и цифру",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль должен содержать не менее 8 символов")
        if not any(c.isupper() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(c.islower() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not any(c.isdigit() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")

        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("Пароль слишком простой. Используйте более сложный пароль")

        import re

        if re.search(r"(.)\1{2,}", v):
            raise ValueError("Пароль не должен содержать повторяющиеся символы")

        return v


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    organization: Optional[str] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    kpp: Optional[str] = None
    media_outlets: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Пароль должен быть не менее 8 символов, содержать заглавную букву, строчную букву и цифру",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль должен содержать не менее 8 символов")
        if not any(c.isupper() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(c.islower() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not any(c.isdigit() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")

        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("Пароль слишком простой. Используйте более сложный пароль")

        import re

        if re.search(r"(.)\1{2,}", v):
            raise ValueError("Пароль не должен содержать повторяющиеся символы")

        return v


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    organization: Optional[str] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    kpp: Optional[str] = None
    media_outlets: Optional[str] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    exp: Optional[datetime] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Пароль должен быть не менее 8 символов",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Пароль должен содержать не менее 8 символов")
        if not any(c.isupper() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(c.islower() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not any(c.isdigit() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")

        if v.lower() in COMMON_PASSWORDS:
            raise ValueError("Пароль слишком простой. Используйте более сложный пароль")

        import re

        if re.search(r"(.)\1{2,}", v):
            raise ValueError("Пароль не должен содержать повторяющиеся символы")

        return v


class APIKeyCreate(BaseModel):
    name: Optional[str] = None
    key_type: Optional[str] = "free"
    max_uses: Optional[int] = 2


class APIKeyResponse(BaseModel):
    id: int
    key: str
    name: Optional[str]
    key_type: str
    max_uses: int
    used_count: int
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    @property
    def remaining(self) -> int:
        return max(0, self.max_uses - self.used_count)

    class Config:
        from_attributes = True


class CheckRequest(BaseModel):
    text: str = Field(
        ..., min_length=1, max_length=20000, description="Текст до 20000 символов"
    )
    filename: Optional[str] = None
    api_key_id: Optional[int] = None
    api_key: Optional[str] = None


class CheckResponse(BaseModel):
    id: int
    text: str
    filename: Optional[str]
    result: Optional[str]
    similarity_score: float
    created_at: datetime

    class Config:
        from_attributes = True


class CheckHistoryResponse(BaseModel):
    id: int
    filename: Optional[str] = None
    similarity_score: float
    created_at: datetime
    result: Optional[str] = (
        None
    )

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    id: str
    status: str
    input_filename: str
    output_filename: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    api_key: str


class TaskStatusResponse(BaseModel):
    id: str
    status: str
    input_filename: str
    output_filename: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    api_key: str


class CheckResultFind(BaseModel):
    id: str
    des_date: str
    exclu_date: str
    agent: str
    found_text: str
    text: str
    duplicate: list = []


class CheckResultSection(BaseModel):
    finds: Optional[dict | list] = None


DatabaseInfo = dict


class CheckResultResponse(BaseModel):
    discalimer: Optional[str] = None
    filename: str
    check_time: str
    standart_check: Optional[CheckResultSection] = None
    translit_check: Optional[CheckResultSection] = None
    database_info: Optional[dict] = None
    UUID_FILE: Optional[str] = None
    UUID_TASK: Optional[str] = None
    task_id: Optional[str] = None
    input_filename: Optional[str] = None
    similarity_score: Optional[float] = None


class FileCheckRequest(BaseModel):
    filename: str
    content_type: str


class CheckWebsiteRequest(BaseModel):
    url: AnyHttpUrl
    filename: Optional[str] = None
