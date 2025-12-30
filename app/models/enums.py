import enum

class SessionStatus(str, enum.Enum):
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"

class QuestionCategory(str, enum.Enum):
    GENERAL = "GENERAL"
    JOB_FIT = "JOB_FIT"
    TECHNICAL = "TECHNICAL"
    PROJECT = "PROJECT"

class AnswerAnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"
    
class PoolCategory(str, enum.Enum):
    FIXED_INTRO = "FIXED_INTRO"
    RANDOM_BODY = "RANDOM_BODY"
    FIXED_OUTRO = "FIXED_OUTRO"