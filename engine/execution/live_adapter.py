"""Live execution adapter: stub that blocks until quality gates are met."""

from engine.models.execution import OrderIntent, OrderResult


class LiveAdapter:
    def execute(self, intent: OrderIntent) -> OrderResult:
        """Live execution is not yet implemented.

        This raises NotImplementedError to enforce the quality gate:
        live trading requires passing Gate B checklist before
        this adapter is replaced with a real implementation.
        """
        raise NotImplementedError(
            "Live execution adapter not implemented. "
            "Complete Gate B quality checklist before enabling live trading."
        )
