"""Import all SQLAlchemy models so Alembic sees complete metadata."""

from haxjobs_api.features.applications.models import Application
from haxjobs_api.features.contacts.models import Contact, OutreachMessage
from haxjobs_api.features.documents.models import Document
from haxjobs_api.features.jobs.models import Job, JobSourceSnapshot
from haxjobs_api.features.packs.models import ApplicationPack
from haxjobs_api.features.profiles.models import ProfileFact, SavedAnswer, UserProfile
from haxjobs_api.features.tasks.models import ApprovalCheckpoint, HermesTask, StatusEvent

__all__ = [
    "Application",
    "Contact",
    "OutreachMessage",
    "Document",
    "Job",
    "JobSourceSnapshot",
    "ApplicationPack",
    "ProfileFact",
    "SavedAnswer",
    "UserProfile",
    "ApprovalCheckpoint",
    "HermesTask",
    "StatusEvent",
]
