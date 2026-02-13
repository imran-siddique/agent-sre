"""Tests for Agent Mesh and Agent OS integrations."""

from agent_sre.incidents.detector import SignalType
from agent_sre.integrations.agent_mesh.bridge import AgentMeshBridge, MeshEvent
from agent_sre.integrations.agent_os.bridge import AgentOSBridge, AuditLogEntry


class TestAgentMeshBridge:
    def test_trust_sli(self) -> None:
        bridge = AgentMeshBridge()
        bridge.trust_sli.record_trust(850, agent_did="did:mesh:abc")
        val = bridge.trust_sli.current_value()
        assert val is not None
        assert abs(val - 0.85) < 0.01

    def test_handshake_sli(self) -> None:
        bridge = AgentMeshBridge()
        bridge.handshake_sli.record_handshake(True)
        bridge.handshake_sli.record_handshake(True)
        bridge.handshake_sli.record_handshake(False)
        val = bridge.handshake_sli.current_value()
        assert val is not None
        assert val < 1.0

    def test_process_trust_revocation(self) -> None:
        bridge = AgentMeshBridge()
        event = MeshEvent(
            event_type="trust_revocation",
            agent_did="did:mesh:bad-agent",
            details={"reason": "malicious behavior"},
        )
        signal = bridge.process_event(event)
        assert signal is not None
        assert signal.signal_type == SignalType.TRUST_REVOCATION

    def test_process_policy_violation(self) -> None:
        bridge = AgentMeshBridge()
        event = MeshEvent(event_type="policy_violation", agent_did="did:mesh:rogue")
        signal = bridge.process_event(event)
        assert signal is not None
        assert signal.signal_type == SignalType.POLICY_VIOLATION

    def test_process_irrelevant_event(self) -> None:
        bridge = AgentMeshBridge()
        event = MeshEvent(event_type="agent_registered", agent_did="did:mesh:new")
        signal = bridge.process_event(event)
        assert signal is None

    def test_slis(self) -> None:
        bridge = AgentMeshBridge()
        slis = bridge.slis()
        assert len(slis) == 2

    def test_summary(self) -> None:
        bridge = AgentMeshBridge()
        bridge.process_event(MeshEvent(event_type="trust_revocation", agent_did="x"))
        s = bridge.summary()
        assert s["events_processed"] == 1


class TestAgentOSBridge:
    def test_blocked_creates_signal(self) -> None:
        bridge = AgentOSBridge()
        entry = AuditLogEntry(
            entry_type="blocked",
            agent_id="bot-1",
            action="write_file",
            policy_name="no-write-policy",
        )
        signal = bridge.process_audit_entry(entry)
        assert signal is not None
        assert signal.signal_type == SignalType.POLICY_VIOLATION

    def test_blocked_records_compliance_failure(self) -> None:
        bridge = AgentOSBridge()
        bridge.process_audit_entry(AuditLogEntry(entry_type="blocked", agent_id="bot-1", policy_name="p1"))
        val = bridge.policy_sli.current_value()
        assert val is not None
        assert val == 0.0  # 0 out of 1 compliant

    def test_allowed_records_compliance(self) -> None:
        bridge = AgentOSBridge()
        bridge.process_audit_entry(AuditLogEntry(entry_type="allowed", agent_id="bot-1"))
        val = bridge.policy_sli.current_value()
        assert val is not None
        assert val == 1.0

    def test_warning_no_signal(self) -> None:
        bridge = AgentOSBridge()
        signal = bridge.process_audit_entry(AuditLogEntry(entry_type="warning", agent_id="bot-1"))
        assert signal is None

    def test_slis(self) -> None:
        bridge = AgentOSBridge()
        assert len(bridge.slis()) == 1

    def test_summary(self) -> None:
        bridge = AgentOSBridge()
        bridge.process_audit_entry(AuditLogEntry(entry_type="blocked", agent_id="bot-1", policy_name="p1"))
        bridge.process_audit_entry(AuditLogEntry(entry_type="warning", agent_id="bot-1"))
        s = bridge.summary()
        assert s["events_processed"] == 2
        assert s["blocked_count"] == 1
        assert s["warning_count"] == 1
