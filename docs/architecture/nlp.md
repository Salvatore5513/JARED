# `nlp/` package

## NLP responsibilities

`nlp/` converts text → structured intent.

Key rule: **NLP never executes anything.** It returns:

- intent name
- confidence
- slots (entities)

Routing/orchestration happens in `nlp/intents/router.py`, but “routing” here means *building ActionRequests and calling DeviceManager* — not bypassing policy or touching drivers.


Intent schema, parsing/classification, routing, and recovery/repair of transcripts.

## `nlp/`

### `nlp/__init__.py`

## `nlp/__pycache__/`

### `nlp/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

## `nlp/dialogue/`

### `nlp/dialogue/__init__.py`

### `nlp/dialogue/disambiguation.py`

### `nlp/dialogue/planner.py`

### `nlp/dialogue/response_templates.py`

## `nlp/dialogue/__pycache__/`

### `nlp/dialogue/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `nlp/dialogue/__pycache__/disambiguation.cpython-313.pyc`

**Type:** `pyc`

### `nlp/dialogue/__pycache__/planner.cpython-313.pyc`

**Type:** `pyc`

### `nlp/dialogue/__pycache__/response_templates.cpython-313.pyc`

**Type:** `pyc`

## `nlp/intents/`

### `nlp/intents/__init__.py`

### `nlp/intents/classifier.py`

**Functions:** `_norm`, `classify`

**Used by:** `nlp.intents.parser`

### `nlp/intents/parser.py`

**Functions:** `parse`

**Used by:** `app.main`

### `nlp/intents/repair.py`

### `nlp/intents/router.py`

**Classes:** `IntentRouter`

**Used by:** `app.main`

### `nlp/intents/schema.py`

**Classes:** `IntentMatch`

**Used by:** `nlp.intents.classifier`, `nlp.intents.parser`

## `nlp/intents/__pycache__/`

### `nlp/intents/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `nlp/intents/__pycache__/classifier.cpython-313.pyc`

**Type:** `pyc`

### `nlp/intents/__pycache__/parser.cpython-313.pyc`

**Type:** `pyc`

### `nlp/intents/__pycache__/repair.cpython-313.pyc`

**Type:** `pyc`

### `nlp/intents/__pycache__/router.cpython-313.pyc`

**Type:** `pyc`

### `nlp/intents/__pycache__/schema.cpython-313.pyc`

**Type:** `pyc`

## `nlp/memory/`

### `nlp/memory/__init__.py`

### `nlp/memory/decision_capture.py`

### `nlp/memory/memory_router.py`

### `nlp/memory/troubleshooting_capture.py`

### `nlp/memory/working_memory.py`

## `nlp/memory/__pycache__/`

### `nlp/memory/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `nlp/memory/__pycache__/decision_capture.cpython-313.pyc`

**Type:** `pyc`

### `nlp/memory/__pycache__/memory_router.cpython-313.pyc`

**Type:** `pyc`

### `nlp/memory/__pycache__/troubleshooting_capture.cpython-313.pyc`

**Type:** `pyc`

### `nlp/memory/__pycache__/working_memory.cpython-313.pyc`

**Type:** `pyc`

## `nlp/memory/models/`

### `nlp/memory/models/__init__.py`

### `nlp/memory/models/decision.py`

### `nlp/memory/models/note.py`

### `nlp/memory/models/troubleshooting.py`

## `nlp/memory/models/__pycache__/`

### `nlp/memory/models/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `nlp/memory/models/__pycache__/decision.cpython-313.pyc`

**Type:** `pyc`

### `nlp/memory/models/__pycache__/note.cpython-313.pyc`

**Type:** `pyc`

### `nlp/memory/models/__pycache__/troubleshooting.cpython-313.pyc`

**Type:** `pyc`

## `nlp/memory/stores/`

### `nlp/memory/stores/__init__.py`

### `nlp/memory/stores/sqlite_store.py`

### `nlp/memory/stores/vector_store.py`

## `nlp/memory/stores/__pycache__/`

### `nlp/memory/stores/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `nlp/memory/stores/__pycache__/sqlite_store.cpython-313.pyc`

**Type:** `pyc`

### `nlp/memory/stores/__pycache__/vector_store.cpython-313.pyc`

**Type:** `pyc`