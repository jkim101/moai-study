"""Tests for the dashboard CLI command."""

from __future__ import annotations

from typer.main import get_command

from claude_conversation_kg.cli import app


class TestDashboardCommand:
    """Tests for the 'dashboard' CLI command registration."""

    def test_dashboard_command_registered(self) -> None:
        """The 'dashboard' command should be registered in the Typer app."""
        # Convert the Typer app to a Click group to inspect commands.
        click_group = get_command(app)
        command_names = list(click_group.commands.keys())
        assert "dashboard" in command_names
