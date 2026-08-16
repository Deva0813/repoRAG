from beanie.odm.documents import Document, DocumentWithSoftDelete
from beanie.odm.fields import PydanticObjectId
from pydantic.fields import Field


class BaseDocument(Document):
    id: PydanticObjectId | None = Field(
        default=None,
        alias="_id",
        serialization_alias="id",
    )

class BaseDocumentWithSoftDelete(DocumentWithSoftDelete):
    id: PydanticObjectId | None = Field(
        default=None,
        alias="_id",
        serialization_alias="id",
    )
