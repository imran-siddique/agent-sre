"""Tests for Kubernetes operator module."""

from __future__ import annotations

import pytest

from agent_sre.k8s import (
    CRD_GROUP,
    CRD_KIND,
    CRD_PLURAL,
    CRD_VERSION,
    Condition,
    ConditionStatus,
    ConditionType,
    ReconcileAction,
    ReconcileResult,
    Reconciler,
    ResourceStatus,
    generate_crd_manifest,
)
from agent_sre.delivery.rollout import RolloutState


# ---------------------------------------------------------------------------
# CRD manifest
# ---------------------------------------------------------------------------

class TestCRDManifest:
    def test_generate_crd(self):
        crd = generate_crd_manifest()
        assert crd["apiVersion"] == "apiextensions.k8s.io/v1"
        assert crd["kind"] == "CustomResourceDefinition"
        assert crd["metadata"]["name"] == f"{CRD_PLURAL}.{CRD_GROUP}"

    def test_crd_has_versions(self):
        crd = generate_crd_manifest()
        versions = crd["spec"]["versions"]
        assert len(versions) == 1
        assert versions[0]["name"] == CRD_VERSION
        assert versions[0]["served"] is True
        assert versions[0]["storage"] is True

    def test_crd_has_schema(self):
        crd = generate_crd_manifest()
        schema = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
        assert schema["type"] == "object"
        spec_props = schema["properties"]["spec"]["properties"]
        assert "strategy" in spec_props
        assert "candidate" in spec_props
        assert "steps" in spec_props

    def test_crd_has_subresources(self):
        crd = generate_crd_manifest()
        assert "status" in crd["spec"]["versions"][0]["subresources"]

    def test_crd_printer_columns(self):
        crd = generate_crd_manifest()
        columns = crd["spec"]["versions"][0]["additionalPrinterColumns"]
        names = [c["name"] for c in columns]
        assert "Strategy" in names
        assert "Phase" in names
        assert "Weight" in names

    def test_crd_scope(self):
        crd = generate_crd_manifest()
        assert crd["spec"]["scope"] == "Namespaced"

    def test_crd_short_names(self):
        crd = generate_crd_manifest()
        assert "aroll" in crd["spec"]["names"]["shortNames"]


# ---------------------------------------------------------------------------
# ResourceStatus
# ---------------------------------------------------------------------------

class TestResourceStatus:
    def test_defaults(self):
        status = ResourceStatus()
        assert status.phase == "Pending"
        assert status.current_step == 0
        assert status.current_weight == 0.0
        assert status.conditions == []

    def test_set_condition_new(self):
        status = ResourceStatus()
        status.set_condition(ConditionType.AVAILABLE, ConditionStatus.TRUE, "Ready")
        assert len(status.conditions) == 1
        assert status.conditions[0].type == ConditionType.AVAILABLE

    def test_set_condition_update(self):
        status = ResourceStatus()
        status.set_condition(ConditionType.AVAILABLE, ConditionStatus.FALSE)
        status.set_condition(ConditionType.AVAILABLE, ConditionStatus.TRUE, "Now ready")
        assert len(status.conditions) == 1
        assert status.conditions[0].status == ConditionStatus.TRUE

    def test_get_condition(self):
        status = ResourceStatus()
        status.set_condition(ConditionType.PROGRESSING, ConditionStatus.TRUE)
        c = status.get_condition(ConditionType.PROGRESSING)
        assert c is not None
        assert c.status == ConditionStatus.TRUE

    def test_get_condition_missing(self):
        status = ResourceStatus()
        assert status.get_condition(ConditionType.DEGRADED) is None

    def test_to_dict(self):
        status = ResourceStatus(phase="canary", current_step=1, current_weight=0.25)
        d = status.to_dict()
        assert d["phase"] == "canary"
        assert d["currentStep"] == 1
        assert d["currentWeight"] == 0.25

    def test_condition_to_dict(self):
        c = Condition(ConditionType.AVAILABLE, ConditionStatus.TRUE, "Ready", "All good")
        d = c.to_dict()
        assert d["type"] == "Available"
        assert d["status"] == "True"
        assert d["reason"] == "Ready"


# ---------------------------------------------------------------------------
# Reconciler — creation
# ---------------------------------------------------------------------------

SAMPLE_SPEC = {
    "strategy": "canary",
    "current": {"name": "my-agent", "version": "v1"},
    "candidate": {"name": "my-agent", "version": "v2"},
    "steps": [
        {"name": "canary-5", "weight": 0.05, "durationSeconds": 3600},
        {"name": "canary-50", "weight": 0.50, "durationSeconds": 7200},
        {"name": "full", "weight": 1.0, "durationSeconds": 0},
    ],
    "rollbackConditions": [
        {"metric": "error_rate", "threshold": 0.05, "operator": "gte"},
    ],
}


class TestReconcilerCreation:
    def test_create_rollout(self):
        r = Reconciler()
        result = r.reconcile("test", "default", SAMPLE_SPEC)
        assert result.action == ReconcileAction.CREATED
        assert result.name == "test"
        assert result.namespace == "default"
        assert "v2" in result.message

    def test_created_rollout_is_canary(self):
        r = Reconciler()
        r.reconcile("test", "default", SAMPLE_SPEC)
        rollout = r.get_rollout("test", "default")
        assert rollout is not None
        assert rollout.state == RolloutState.CANARY

    def test_status_after_create(self):
        r = Reconciler()
        r.reconcile("test", "default", SAMPLE_SPEC)
        status = r.get_status("test", "default")
        assert status is not None
        assert status.phase == "canary"
        # Check condition
        progressing = status.get_condition(ConditionType.PROGRESSING)
        assert progressing is not None
        assert progressing.status == ConditionStatus.TRUE

    def test_invalid_spec(self):
        r = Reconciler()
        result = r.reconcile("test", "default", {"strategy": "invalid_strategy"})
        assert result.action == ReconcileAction.ERROR

    def test_generation_update_recreates(self):
        r = Reconciler()
        r.reconcile("test", "default", SAMPLE_SPEC, generation=1)
        # Update with new generation
        new_spec = dict(SAMPLE_SPEC)
        new_spec["candidate"] = {"name": "my-agent", "version": "v3"}
        result = r.reconcile("test", "default", new_spec, generation=2)
        assert result.action == ReconcileAction.CREATED
        assert "v3" in result.message


# ---------------------------------------------------------------------------
# Reconciler — advance & rollback
# ---------------------------------------------------------------------------

class TestReconcilerAdvance:
    def test_advance(self):
        r = Reconciler()
        r.reconcile("test", "default", SAMPLE_SPEC)
        result = r.advance("test", "default")
        assert result.action == ReconcileAction.ADVANCED
        assert result.status.current_weight == 0.50

    def test_advance_to_completion(self):
        r = Reconciler()
        r.reconcile("test", "default", SAMPLE_SPEC)
        r.advance("test", "default")  # → 0.50
        r.advance("test", "default")  # → 1.0
        result = r.advance("test", "default")  # → COMPLETE (advance returns False at last step)
        assert result.action == ReconcileAction.COMPLETED
        assert result.status.phase == "complete"

    def test_advance_nonexistent(self):
        r = Reconciler()
        result = r.advance("missing", "default")
        assert result.action == ReconcileAction.ERROR

    def test_rollback(self):
        r = Reconciler()
        r.reconcile("test", "default", SAMPLE_SPEC)
        result = r.rollback("test", "default", reason="SLO violation")
        assert result.action == ReconcileAction.ROLLED_BACK
        assert result.status.phase == "rolled_back"
        rb_cond = result.status.get_condition(ConditionType.ROLLED_BACK)
        assert rb_cond is not None
        assert rb_cond.status == ConditionStatus.TRUE

    def test_rollback_nonexistent(self):
        r = Reconciler()
        result = r.rollback("missing", "default")
        assert result.action == ReconcileAction.ERROR


# ---------------------------------------------------------------------------
# Reconciler — sync (idempotent reconcile)
# ---------------------------------------------------------------------------

class TestReconcilerSync:
    def test_noop_on_same_generation(self):
        r = Reconciler()
        r.reconcile("test", "default", SAMPLE_SPEC, generation=1)
        result = r.reconcile("test", "default", SAMPLE_SPEC, generation=1)
        assert result.action == ReconcileAction.NOOP

    def test_completed_stays_completed(self):
        r = Reconciler()
        r.reconcile("test", "default", SAMPLE_SPEC)
        r.advance("test", "default")
        r.advance("test", "default")
        r.advance("test", "default")  # complete
        result = r.reconcile("test", "default", SAMPLE_SPEC, generation=1)
        assert result.action == ReconcileAction.COMPLETED

    def test_rolled_back_stays_rolled_back(self):
        r = Reconciler()
        r.reconcile("test", "default", SAMPLE_SPEC)
        r.rollback("test", "default", "bad")
        result = r.reconcile("test", "default", SAMPLE_SPEC, generation=1)
        assert result.action == ReconcileAction.ROLLED_BACK


# ---------------------------------------------------------------------------
# Reconciler — queries
# ---------------------------------------------------------------------------

class TestReconcilerQueries:
    def test_list_rollouts(self):
        r = Reconciler()
        r.reconcile("a", "default", SAMPLE_SPEC)
        r.reconcile("b", "staging", SAMPLE_SPEC)
        all_rollouts = r.list_rollouts()
        assert len(all_rollouts) == 2

    def test_list_rollouts_filtered(self):
        r = Reconciler()
        r.reconcile("a", "default", SAMPLE_SPEC)
        r.reconcile("b", "staging", SAMPLE_SPEC)
        default_only = r.list_rollouts(namespace="default")
        assert len(default_only) == 1
        assert default_only[0]["name"] == "a"

    def test_active_count(self):
        r = Reconciler()
        r.reconcile("a", "default", SAMPLE_SPEC)
        r.reconcile("b", "default", SAMPLE_SPEC)
        assert r.active_count == 2
        r.advance("a", "default")
        r.advance("a", "default")
        r.advance("a", "default")  # complete
        assert r.active_count == 1

    def test_get_status_missing(self):
        r = Reconciler()
        assert r.get_status("missing", "default") is None

    def test_get_rollout_missing(self):
        r = Reconciler()
        assert r.get_rollout("missing", "default") is None

    def test_reconcile_result_to_dict(self):
        r = Reconciler()
        result = r.reconcile("test", "default", SAMPLE_SPEC)
        d = result.to_dict()
        assert d["action"] == "created"
        assert d["name"] == "test"
        assert "status" in d


# ---------------------------------------------------------------------------
# Spec parsing edge cases
# ---------------------------------------------------------------------------

class TestSpecParsing:
    def test_minimal_spec(self):
        r = Reconciler()
        spec = {
            "candidate": {"name": "agent", "version": "v1"},
        }
        result = r.reconcile("minimal", "default", spec)
        assert result.action == ReconcileAction.CREATED

    def test_shadow_strategy(self):
        r = Reconciler()
        spec = {
            "strategy": "shadow",
            "candidate": {"name": "agent", "version": "v2"},
            "steps": [{"weight": 0.0, "durationSeconds": 86400}],
        }
        result = r.reconcile("shadow", "default", spec)
        assert result.action == ReconcileAction.CREATED

    def test_spec_with_slo_requirements(self):
        r = Reconciler()
        spec = dict(SAMPLE_SPEC)
        spec["sloRequirements"] = [{"name": "accuracy", "target": 0.99}]
        result = r.reconcile("slo-test", "default", spec)
        assert result.action == ReconcileAction.CREATED

    def test_spec_with_analysis_criteria(self):
        r = Reconciler()
        spec = {
            "candidate": {"name": "agent", "version": "v2"},
            "steps": [
                {
                    "weight": 0.1,
                    "analysis": [{"metric": "accuracy", "threshold": 0.95}],
                },
                {"weight": 1.0},
            ],
        }
        result = r.reconcile("analysis", "default", spec)
        assert result.action == ReconcileAction.CREATED
