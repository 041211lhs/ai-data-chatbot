"""서비스 계층 전용 예외. 서비스는 HTTP를 모르고, main.py의 핸들러가 상태 코드로 바꿔 준다."""


class NotFoundError(Exception):
    pass


class DuplicateError(Exception):
    pass


class AIServiceError(Exception):
    pass
