# `devices/` package

## Device control in JARED (Milestone 3)

`devices/` is where the “real world” gets touched — but only through a strict, auditable pipeline:

1. **Router builds an `ActionRequest`** (what the user wants).
2. **`DeviceManager.handle()` resolves the target device** (device_id/room_id/capabilities).
3. **PolicyEngine decides** allow/deny + required auth + verification + rate limiting.
4. **A driver executes** (MQTT/HTTP/GPIO).
5. **Verifier confirms** when policy requires it (or returns an explicit “not verified” result).
6. **Outcome is returned + events are emitted** (for logs, UI, future automations).

Nothing should talk to a driver directly — *drivers are “pure execution”*.


Registry + drivers + execution and verification. Policy-gated device control lives here.

## `devices/`

### `devices/__init__.py`

## `devices/__pycache__/`

### `devices/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

## `devices/drivers/`

### `devices/drivers/__init__.py`

### `devices/drivers/base.py`

**Classes:** `DriverResult`, `Driver`

**Used by:** `devices.drivers.mqtt.driver`, `devices.drivers.registry`, `devices.execution.device_manager`, `devices.execution.verifier`

### `devices/drivers/registry.py`

**Classes:** `DriverRegistry`

**Used by:** `app.main`, `devices.execution.device_manager`, `tests.test_device_manager`

## `devices/drivers/__pycache__/`

### `devices/drivers/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `devices/drivers/__pycache__/base.cpython-313.pyc`

**Type:** `pyc`

### `devices/drivers/__pycache__/registry.cpython-313.pyc`

**Type:** `pyc`

## `devices/drivers/gpio/`

### `devices/drivers/gpio/__init__.py`

### `devices/drivers/gpio/driver.py`

## `devices/drivers/http/`

### `devices/drivers/http/__init__.py`

### `devices/drivers/http/driver.py`

## `devices/drivers/mqtt/`

### `devices/drivers/mqtt/__init__.py`

### `devices/drivers/mqtt/discovery.py`

### `devices/drivers/mqtt/driver.py`

**Classes:** `MQTTDriver`

**Used by:** `app.main`, `tests.test_device_manager`

### `devices/drivers/mqtt/topics.py`

## `devices/drivers/mqtt/__pycache__/`

### `devices/drivers/mqtt/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `devices/drivers/mqtt/__pycache__/driver.cpython-313.pyc`

**Type:** `pyc`

## `devices/execution/`

### `devices/execution/__init__.py`

### `devices/execution/action_executor.py`

### `devices/execution/action_request.py`

**Classes:** `SafetyClass`, `AuthLevel`, `ActionRequest`, `PolicyDecision`, `ActionOutcome`

**Used by:** `core.security.auth.auth_window`, `core.security.policy_engine`, `devices.drivers.base`, `devices.drivers.mqtt.driver`, `devices.execution.device_manager`, `devices.execution.verifier`, `nlp.intents.router`, `tests.test_class2_policy` …

### `devices/execution/device_manager.py`

**Classes:** `DeviceManager`

**Used by:** `app.main`, `nlp.intents.router`, `tests.test_device_manager`

### `devices/execution/policy_adapter.py`

### `devices/execution/verifier.py`

**Classes:** `VerificationResult`, `Verifier`

**Used by:** `devices.execution.device_manager`

## `devices/execution/__pycache__/`

### `devices/execution/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `devices/execution/__pycache__/action_request.cpython-313.pyc`

**Type:** `pyc`

### `devices/execution/__pycache__/device_manager.cpython-313.pyc`

**Type:** `pyc`

### `devices/execution/__pycache__/verifier.cpython-313.pyc`

**Type:** `pyc`

## `devices/registry/`

### `devices/registry/__init__.py`

### `devices/registry/models.py`

**Classes:** `Room`, `DeviceTemplate`, `DeviceRecord`, `DeviceTarget`

**Used by:** `devices.drivers.base`, `devices.drivers.mqtt.driver`, `devices.execution.device_manager`, `devices.registry.store`, `nlp.intents.router`, `tests.test_device_manager`, `tools.guardrails_smoke`, `tools.seed_registry`

### `devices/registry/store.py`

**Classes:** `RegistryStore`

**Used by:** `app.main`, `devices.execution.device_manager`, `tests.test_device_manager`, `tools.seed_registry`

## `devices/registry/__pycache__/`

### `devices/registry/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `devices/registry/__pycache__/models.cpython-313.pyc`

**Type:** `pyc`

### `devices/registry/__pycache__/store.cpython-313.pyc`

**Type:** `pyc`

## `devices/registry/templates/`

### `devices/registry/templates/compressor.json`

**Type:** `json`

### `devices/registry/templates/fan.json`

**Type:** `json`

### `devices/registry/templates/garage_door.json`

**Type:** `json`

### `devices/registry/templates/heat_source.json`

**Type:** `json`

### `devices/registry/templates/light_basic.json`

**Type:** `json`

### `devices/registry/templates/outlet_general.json`

**Type:** `json`

### `devices/registry/templates/scene.json`

**Type:** `json`