class AppException(Exception):
    """모든 커스텀 예외의 부모"""

class NotFoundException(AppException):
    pass

class DatabaseException(AppException):
    pass

class ValidationException(AppException):
    pass
