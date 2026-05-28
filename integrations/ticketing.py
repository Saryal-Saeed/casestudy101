"""
Ticketing Integration (Mock)

People team ticketing system for internal requests.
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Ticket:
    ticket_id: str
    subject: str
    description: str
    requester: str
    assignee: str | None
    status: str
    priority: str
    category: str | None
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TicketResponse:
    success: bool
    ticket: Ticket | None = None
    error: str | None = None


class TicketingError(Exception):
    """Raised when Ticketing operation fails."""
    pass


class TicketingClient:
    """
    Mock Ticketing client.
    
    Args:
        failure_rate: Probability of random failure (0.0 to 1.0)
    """
    
    def __init__(self, failure_rate: float = 0.0):
        self.failure_rate = failure_rate
        self._tickets: dict[str, Ticket] = {}
    
    def _maybe_fail(self):
        if random.random() < self.failure_rate:
            raise TicketingError("Ticketing service temporarily unavailable")
    
    def create_ticket(
        self,
        subject: str,
        description: str,
        requester: str,
        assignee: str | None = None,
        priority: str = "medium",
        category: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TicketResponse:
        """
        Create a new ticket.
        
        Args:
            subject: Ticket subject line
            description: Full description
            requester: Email of person who submitted
            assignee: Email of person to handle (optional)
            priority: low, medium, high, urgent
            category: Category for routing
            metadata: Additional data
        """
        self._maybe_fail()
        
        if not subject:
            return TicketResponse(success=False, error="Subject is required")
        if not requester:
            return TicketResponse(success=False, error="Requester is required")
        
        ticket_id = f"PEOPLE-{uuid.uuid4().hex[:6].upper()}"
        
        ticket = Ticket(
            ticket_id=ticket_id,
            subject=subject,
            description=description,
            requester=requester,
            assignee=assignee,
            status="open",
            priority=priority,
            category=category,
            created_at=datetime.utcnow().isoformat(),
            metadata=metadata or {},
        )
        
        self._tickets[ticket_id] = ticket
        return TicketResponse(success=True, ticket=ticket)
    
    def get_ticket(self, ticket_id: str) -> TicketResponse:
        """Get a ticket by ID."""
        self._maybe_fail()
        
        ticket = self._tickets.get(ticket_id)
        if ticket:
            return TicketResponse(success=True, ticket=ticket)
        return TicketResponse(success=False, error=f"Ticket not found: {ticket_id}")
    
    def update_ticket(self, ticket_id: str, updates: dict[str, Any]) -> TicketResponse:
        """Update a ticket."""
        self._maybe_fail()
        
        if ticket_id not in self._tickets:
            return TicketResponse(success=False, error=f"Ticket not found: {ticket_id}")
        
        ticket = self._tickets[ticket_id]
        for key, value in updates.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        
        return TicketResponse(success=True, ticket=ticket)
    
    def add_comment(
        self,
        ticket_id: str,
        author: str,
        content: str,
        is_internal: bool = False,
    ) -> TicketResponse:
        """Add a comment to a ticket."""
        self._maybe_fail()
        
        if ticket_id not in self._tickets:
            return TicketResponse(success=False, error=f"Ticket not found: {ticket_id}")
        
        ticket = self._tickets[ticket_id]
        if "comments" not in ticket.metadata:
            ticket.metadata["comments"] = []
        
        ticket.metadata["comments"].append({
            "author": author,
            "content": content,
            "is_internal": is_internal,
            "created_at": datetime.utcnow().isoformat(),
        })
        
        return TicketResponse(success=True, ticket=ticket)
    
    def find_ticket_by_metadata(self, key: str, value: Any) -> Ticket | None:
        """Find a ticket by metadata field (useful for idempotency checks)."""
        self._maybe_fail()
        
        for ticket in self._tickets.values():
            if ticket.metadata.get(key) == value:
                return ticket
        return None
