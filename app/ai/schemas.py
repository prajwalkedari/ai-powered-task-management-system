"""Shape of the JSON we require the model to return. Anything else is rejected."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

GeneratedText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class GeneratedDescription(BaseModel):
    description: GeneratedText


class GeneratedSummary(BaseModel):
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
