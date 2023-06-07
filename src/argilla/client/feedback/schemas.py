#  Copyright 2021-present, the Recognai S.L. team.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import warnings
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from pydantic import (
    BaseModel,
    Extra,
    Field,
    PositiveInt,
    StrictInt,
    StrictStr,
    root_validator,
    validator,
)

FETCHING_BATCH_SIZE = 250
PUSHING_BATCH_SIZE = 32


class ValueSchema(BaseModel):
    value: Union[StrictStr, StrictInt, List[str]]


class ResponseSchema(BaseModel):
    user_id: Optional[UUID] = None
    values: Dict[str, ValueSchema]
    status: Literal["submitted", "discarded"] = "submitted"

    @validator("user_id", always=True)
    def user_id_must_have_value(cls, v):
        if not v:
            warnings.warn(
                "`user_id` not provided, so it will be set to `None`. Which is not an"
                " issue, unless you're planning to log the response in Argilla, as "
                " it will be automatically set to the active `user_id`.",
                stacklevel=2,
            )
        return v


class FeedbackRecord(BaseModel):
    fields: Dict[str, str]
    responses: Optional[Union[ResponseSchema, List[ResponseSchema]]] = None
    external_id: Optional[str] = None

    @validator("responses", always=True)
    def responses_must_be_a_list(cls, v: Optional[Union[ResponseSchema, List[ResponseSchema]]]) -> List[ResponseSchema]:
        if not v:
            return []
        if isinstance(v, ResponseSchema):
            return [v]
        return v

    class Config:
        extra = Extra.ignore


class FieldSchema(BaseModel):
    name: str
    title: Optional[str] = None
    required: bool = True
    settings: Dict[str, Any]

    @validator("title", always=True)
    def title_must_have_value(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            return values["name"].capitalize()
        return v

    class Config:
        validate_assignment = True
        extra = Extra.forbid


class TextField(FieldSchema):
    settings: Dict[str, Any] = Field({"type": "text"})
    use_markdown: bool = False

    @root_validator
    def update_settings(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["settings"]["use_markdown"] = values.get("use_markdown", False)
        return values


FIELD_TYPE_TO_PYTHON_TYPE = {"text": str}


class QuestionSchema(BaseModel):
    name: str
    title: Optional[str] = None
    description: Optional[str] = None
    required: bool = True
    settings: Dict[str, Any]

    @validator("title", always=True)
    def title_must_have_value(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if not v:
            return values["name"].capitalize()
        return v

    class Config:
        validate_assignment = True
        extra = Extra.forbid


# TODO(alvarobartt): add `TextResponse` and `RatingResponse` classes
class TextQuestion(QuestionSchema):
    settings: Dict[str, Any] = Field({"type": "text", "use_markdown": False})
    use_markdown: bool = False

    @root_validator
    def update_settings(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["settings"]["use_markdown"] = values.get("use_markdown", False)
        return values


class RatingQuestion(QuestionSchema):
    settings: Dict[str, Any] = Field({"type": "rating"})
    values: List[int] = Field(unique_items=True)

    @root_validator
    def update_settings(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["settings"]["options"] = [{"value": value} for value in values.get("values", [])]
        return values


class _LabelQuestion(QuestionSchema):
    settings: Dict[str, Any] = Field({})
    labels: List[str] = Field(unique_items=True)
    visible_labels: Optional[PositiveInt] = 20

    @root_validator
    def update_settings(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        values["settings"]["options"] = [{"value": label, "text": label} for label in values.get("labels", [])]
        values["settings"]["visible_options"] = values.get("visible_labels", 20)
        return values


class SingleLabelQuestion(_LabelQuestion):
    settings: Dict[str, Any] = Field({"type": "label_selection"})


class MultiLabelQuestion(_LabelQuestion):
    settings: Dict[str, Any] = Field({"type": "multi_label_selection"})


AllowedFieldTypes = TextField
AllowedQuestionTypes = Union[TextQuestion, RatingQuestion, SingleLabelQuestion, MultiLabelQuestion]


class FeedbackDatasetConfig(BaseModel):
    fields: List[AllowedFieldTypes]
    questions: List[AllowedQuestionTypes]
    guidelines: Optional[str] = None

    class Config:
        smart_union = True
