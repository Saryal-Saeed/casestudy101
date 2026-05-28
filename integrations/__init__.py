"""
Mock Integrations for People Ops Automation

These simulate external services:
- HRISClient: Human Resource Information System
- ITTasksClient: IT Task/Ticketing System  
- TicketingClient: People Team Ticketing System

By default, integrations always succeed. You can simulate flaky
services by passing a higher `failure_rate` (e.g. `HRISClient(failure_rate=0.1)`)
if you want to try the optional failure-handling stretch goal.

Example usage:
    from integrations.hris import HRISClient
    from integrations.it_tasks import ITTasksClient
    from integrations.ticketing import TicketingClient
    
    hris = HRISClient()
    result = hris.get_employee("lina@company.com")
"""

from integrations.hris import HRISClient
from integrations.it_tasks import ITTasksClient
from integrations.ticketing import TicketingClient

__all__ = ["HRISClient", "ITTasksClient", "TicketingClient"]
