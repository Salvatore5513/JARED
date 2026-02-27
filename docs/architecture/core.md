# `core/` package

## What lives here (core rules)

`core/` is the "constitutional layer" of JARED — the small set of primitives that everything else must obey:

- **EventBus is the observability spine**: components emit events; they do not secretly call each other.
- **NetPolicy is the only network gate**: any outbound network access must be explicitly allowed.
- **PolicyEngine is the only safety authority**: allow/deny, auth level, verification requirement, and rate limits are decided here.
- **Config Manager is the single source of truth**: runtime behavior comes from config + environment variables, not scattered globals.

If you’re ever unsure where a rule belongs, it likely belongs in `core/` (or it doesn’t exist yet).


Shared foundations: config, event bus, networking policy, security, scheduling, observability.

## `core/`

### `core/__init__.py`

### `core/clock.py`

### `core/errors.py`

### `core/event_bus.py`

**Classes:** `Event`, `EventBus`

**Used by:** `app.main`, `devices.execution.device_manager`, `speech.pipeline`, `tests.test_device_manager`, `tools.guardrails_smoke`

### `core/ids.py`

### `core/scheduler.py`

## `core/__pycache__/`

### `core/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `core/__pycache__/clock.cpython-313.pyc`

**Type:** `pyc`

### `core/__pycache__/errors.cpython-313.pyc`

**Type:** `pyc`

### `core/__pycache__/event_bus.cpython-313.pyc`

**Type:** `pyc`

### `core/__pycache__/ids.cpython-313.pyc`

**Type:** `pyc`

### `core/__pycache__/scheduler.cpython-313.pyc`

**Type:** `pyc`

## `core/config/`

### `core/config/__init__.py`

### `core/config/manager.py`

**Classes:** `Config`, `ConfigManager`

**Functions:** `_default_data_dir`, `load_config`

**Used by:** `app.main`, `core.net.policy`, `core.security.policies`, `tools.cli`

### `core/config/schema.py`

## `core/config/__pycache__/`

### `core/config/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `core/config/__pycache__/manager.cpython-313.pyc`

**Type:** `pyc`

### `core/config/__pycache__/schema.cpython-313.pyc`

**Type:** `pyc`

## `core/net/`

### `core/net/__init__.py`

### `core/net/dns.py`

### `core/net/http_client.py`

**Functions:** `configure`, `_get_policy`, `get`, `post`

### `core/net/policy.py`

**Classes:** `NetPolicy`

**Used by:** `app.main`, `core.net.http_client`, `core.security.policies`

## `core/net/__pycache__/`

### `core/net/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `core/net/__pycache__/dns.cpython-313.pyc`

**Type:** `pyc`

### `core/net/__pycache__/http_client.cpython-313.pyc`

**Type:** `pyc`

### `core/net/__pycache__/policy.cpython-313.pyc`

**Type:** `pyc`

## `core/observability/`

### `core/observability/__init__.py`

### `core/observability/crash_recovery.py`

### `core/observability/diagnostics_bundle.py`

### `core/observability/healthcheck.py`

**Functions:** `run_healthcheck`

**Used by:** `app.main`

### `core/observability/logger.py`

**Functions:** `get_logger`

**Key constants:** `LOG_DIR`, `LOG_FILE`

**Used by:** `app.main`, `nlp.intents.router`

### `core/observability/metrics.py`

### `core/observability/traces.py`

## `core/observability/__pycache__/`

### `core/observability/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `core/observability/__pycache__/crash_recovery.cpython-313.pyc`

**Type:** `pyc`

### `core/observability/__pycache__/diagnostics_bundle.cpython-313.pyc`

**Type:** `pyc`

### `core/observability/__pycache__/healthcheck.cpython-313.pyc`

**Type:** `pyc`

### `core/observability/__pycache__/logger.cpython-313.pyc`

**Type:** `pyc`

### `core/observability/__pycache__/metrics.cpython-313.pyc`

**Type:** `pyc`

### `core/observability/__pycache__/traces.cpython-313.pyc`

**Type:** `pyc`

## `core/security/`

### `core/security/__init__.py`

### `core/security/audit_log.py`

**Classes:** `AuditLog`

**Functions:** `_now_ms`, `_to_jsonable`

**Used by:** `app.main`, `devices.execution.device_manager`, `tests.test_device_manager`

### `core/security/confirmations.py`

### `core/security/policies.py`

**Classes:** `Policies`

### `core/security/policy_engine.py`

**Classes:** `PolicyConfig`, `PolicyEngine`

**Used by:** `app.main`, `core.security.policies`, `devices.execution.device_manager`, `tests.test_class2_policy`, `tests.test_device_manager`, `tools.guardrails_smoke`

### `core/security/rate_limits.py`

**Classes:** `RateLimitResult`, `RateLimiter`

**Functions:** `_now_ms`

**Used by:** `app.main`, `devices.execution.device_manager`, `tests.test_device_manager`

### `core/security/roles.py`

## `core/security/__pycache__/`

### `core/security/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `core/security/__pycache__/audit_log.cpython-313.pyc`

**Type:** `pyc`

### `core/security/__pycache__/confirmations.cpython-313.pyc`

**Type:** `pyc`

### `core/security/__pycache__/policy_engine.cpython-313.pyc`

**Type:** `pyc`

### `core/security/__pycache__/rate_limits.cpython-313.pyc`

**Type:** `pyc`

### `core/security/__pycache__/roles.cpython-313.pyc`

**Type:** `pyc`

## `core/security/auth/`

### `core/security/auth/__init__.py`

### `core/security/auth/auth_window.py`

**Classes:** `AuthState`, `AuthWindow`

**Functions:** `_now_ms`

**Used by:** `app.main`, `devices.execution.device_manager`, `tests.test_device_manager`

### `core/security/auth/pin_phrase.py`

**Classes:** `PinConfig`, `PinVerifier`

### `core/security/auth/ptt.py`

**Classes:** `PTTState`, `PTTManager`

## `core/security/auth/__pycache__/`

### `core/security/auth/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `core/security/auth/__pycache__/auth_window.cpython-313.pyc`

**Type:** `pyc`

### `core/security/auth/__pycache__/pin_phrase.cpython-313.pyc`

**Type:** `pyc`

### `core/security/auth/__pycache__/ptt.cpython-313.pyc`

**Type:** `pyc`

## `core/state/`

### `core/state/__init__.py`

### `core/state/context_service.py`

### `core/state/presence.py`

### `core/state/room_resolver.py`

### `core/state/session_service.py`

## `core/state/__pycache__/`

### `core/state/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `core/state/__pycache__/context_service.cpython-313.pyc`

**Type:** `pyc`

### `core/state/__pycache__/presence.cpython-313.pyc`

**Type:** `pyc`

### `core/state/__pycache__/room_resolver.cpython-313.pyc`

**Type:** `pyc`

### `core/state/__pycache__/session_service.cpython-313.pyc`

**Type:** `pyc`