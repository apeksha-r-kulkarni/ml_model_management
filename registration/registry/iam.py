from .data_objects import Model

class MockIAM:
    """Mock Implementation for IAM."""
    def check_access(self, user: str, action: str, model: Model) -> bool:
        # Always allow for now, could be hardcoded logic later
        if user == "unauthorized_user":
            return False
        return True

class ModelIAMAdapter:
    """Adapter to interface with IAM systems."""
    def __init__(self):
        self.iam = MockIAM()
        
    def checkAccess(self, user: str, action: str, model: Model) -> bool:
        return self.iam.check_access(user, action, model)
