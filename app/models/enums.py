import enum


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class TaskStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    TESTING = "Testing"
    COMPLETED = "Completed"


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Store the enum *values* (e.g. "In Progress") rather than member names."""
    return [member.value for member in enum_cls]
