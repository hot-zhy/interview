"""
Memory-aware, tool-augmented agentic interview framework.

This package adds an orchestration layer on top of existing interview services.
All agentic behavior is gated behind feature flags (see backend.core.config).
When disabled, the system falls back to the original interview flow unchanged.
"""
