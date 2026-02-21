# Pydantic & ORM Integration Guide

This document explains how to use Pydantic models (specifically `JobResponse`) with database objects in this FastAPI project.

## 1. `BaseModel`

All schemas in `app/schemas/` inherit from Pydantic's `BaseModel`. This provides:

- **Type Safety**: Validation of input and output data.
- **Serialization**: Easy conversion to JSON (`model_dump_json()`) or dictionaries (`model_dump()`).
- **Parsing**: Creation of objects from untrusted sources (like HTTP request bodies).

## 2. `model_config` (Pydantic V2)

Our schemas use `model_config = ConfigDict(from_attributes=True)`. In Pydantic V1, this was `orm_mode = True`.

- **Why it matters**: By default, Pydantic expects data as a dictionary (e.g., `data["id"]`).
- **The Magic**: `from_attributes=True` tells Pydantic it can also read values from object attributes (e.g., `data.id`). This is essential when working with SQLModel or SQLAlchemy ORM objects.

## 3. Usage: ORM -> Response Schema

When you fetch a `Job` object from the database, you can convert it to a `JobResponse` easily.

### Explicit Conversion (Recommended in logic)

```python
from app.models.job import Job
from app.schemas.job import JobResponse

# Fetch from DB (SQLModel/SQLAlchemy)
job_obj = await db.get(Job, some_id)

# Convert ORM object to Pydantic schema
response_data = JobResponse.model_validate(job_obj)
```

### Conversion for Lists

```python
result = await db.execute(select(Job))
jobs = result.scalars().all()

# Modern list comprehension
return [JobResponse.model_validate(j) for j in jobs]
```

### Automatic Conversion in FastAPI

FastAPI handles this automatically if you use the `response_model` decorator.

```python
@router.get("/{id}", response_model=JobResponse)
async def get_job(id: UUID, db: AsyncSession = Depends(get_db)):
    job_obj = ... # fetch from db
    return job_obj # FastAPI calls JobResponse.model_validate(job_obj) internally
```

## 4. Summary Table

| Feature                            | Use Case                                    | Example                                           |
| :--------------------------------- | :------------------------------------------ | :------------------------------------------------ |
| `BaseModel`                        | Core data validation and structure          | `class JobResponse(BaseModel): ...`               |
| `ConfigDict(from_attributes=True)` | Allow reading from ORM objects              | `model_config = ConfigDict(from_attributes=True)` |
| `model_validate()`                 | Manual conversion from DB object to schema  | `JobResponse.model_validate(db_obj)`              |
| `response_model=...`               | automatic FastAPI conversion & OpenAPI docs | `@router.get("/", response_model=JobResponse)`    |
