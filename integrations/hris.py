"""
HRIS Integration (Mock)

Human Resource Information System for employee data.
"""

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class HRISResponse:
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class HRISError(Exception):
    """Raised when HRIS operation fails."""
    pass


class HRISClient:
    """
    Mock HRIS client.
    
    Args:
        failure_rate: Probability of random failure (0.0 to 1.0)
    """
    
    def __init__(self, failure_rate: float = 0.0):
        self.failure_rate = failure_rate
        self._employees = {
            "lina.mueller@company.com": {
                "id": "emp_001",
                "first_name": "Lina",
                "last_name": "Müller",
                "email": "lina.mueller@company.com",
                "team": "Engineering",
                "role": "Software Engineer",
                "manager": "alex.schmidt@company.com",
                "location": "Berlin",
            },
            "alex.schmidt@company.com": {
                "id": "emp_002",
                "first_name": "Alex",
                "last_name": "Schmidt",
                "email": "alex.schmidt@company.com",
                "team": "Engineering",
                "role": "Engineering Manager",
                "manager": "cto@company.com",
                "location": "Berlin",
            },
            "sara.klein@company.com": {
                "id": "emp_003",
                "first_name": "Sara",
                "last_name": "Klein",
                "email": "sara.klein@company.com",
                "team": "Engineering",
                "role": "Senior Engineering Manager",
                "manager": "cto@company.com",
                "location": "Berlin",
            },
        }
    
    def _maybe_fail(self):
        if random.random() < self.failure_rate:
            raise HRISError("HRIS service temporarily unavailable")
    
    def get_employee(self, email: str) -> HRISResponse:
        """
        Get employee by email.
        
        Returns:
            HRISResponse with employee data or error
        """
        self._maybe_fail()
        
        employee = self._employees.get(email)
        if employee:
            return HRISResponse(success=True, data=employee.copy())
        return HRISResponse(success=False, error=f"Employee not found: {email}")
    
    def create_employee(self, employee_data: dict[str, Any]) -> HRISResponse:
        """
        Create a new employee record.
        
        Required fields: email, first_name, last_name, team, role, manager, location
        """
        self._maybe_fail()
        
        email = employee_data.get("email")
        if not email:
            return HRISResponse(success=False, error="Email is required")
        
        if email in self._employees:
            return HRISResponse(success=False, error=f"Employee already exists: {email}")
        
        required = ["first_name", "last_name", "team", "role", "manager", "location"]
        missing = [f for f in required if f not in employee_data]
        if missing:
            return HRISResponse(success=False, error=f"Missing required fields: {missing}")
        
        new_id = f"emp_{len(self._employees) + 1:03d}"
        new_employee = {"id": new_id, **employee_data}
        self._employees[email] = new_employee
        
        return HRISResponse(success=True, data=new_employee)
    
    def update_employee(self, email: str, updates: dict[str, Any]) -> HRISResponse:
        """
        Update an employee record.
        
        Args:
            email: Employee email
            updates: Fields to update (e.g., {"role": "Senior Engineer"})
        """
        self._maybe_fail()
        
        if email not in self._employees:
            return HRISResponse(success=False, error=f"Employee not found: {email}")
        
        self._employees[email].update(updates)
        return HRISResponse(success=True, data=self._employees[email].copy())
    
    def list_employees(self, team: str | None = None) -> HRISResponse:
        """List all employees, optionally filtered by team."""
        self._maybe_fail()
        
        employees = list(self._employees.values())
        if team:
            employees = [e for e in employees if e.get("team") == team]
        
        return HRISResponse(success=True, data=employees)
