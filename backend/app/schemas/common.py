from pydantic import BaseModel


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total_pages: int
    total_items: int


class ListResponsePaginated[T](BaseModel):
    data: list[T]
    pagination_meta: PaginationMeta
