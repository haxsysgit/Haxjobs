from sqlalchemy import inspect, select

from haxjobs_api.database import Base, create_database_engine, create_session_factory
from haxjobs_api.features.applications.models import Application, ApplicationStatus
from haxjobs_api.features.contacts.models import Contact
from haxjobs_api.features.documents.models import Document, DocumentType
from haxjobs_api.features.jobs.models import Job, JobSourceSnapshot, SourcePlatform
from haxjobs_api.features.packs.models import ApplicationPack
from haxjobs_api.features.profiles.models import ProfileFact, SavedAnswer, UserProfile
from haxjobs_api.features.tasks.models import ApprovalCheckpoint, HermesTask, StatusEvent, TaskStatus, TaskType


def make_session(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'models.db'}")
    Base.metadata.create_all(engine)
    return create_session_factory(engine)()


def test_core_model_tables_are_registered():
    table_names = set(Base.metadata.tables)

    assert {
        "user_profiles",
        "profile_facts",
        "saved_answers",
        "jobs",
        "job_source_snapshots",
        "applications",
        "application_packs",
        "documents",
        "contacts",
        "outreach_messages",
        "hermes_tasks",
        "approval_checkpoints",
        "status_events",
    }.issubset(table_names)


def test_core_model_relationships_can_persist_a_job_application_pack_flow(tmp_path):
    session = make_session(tmp_path)

    profile = UserProfile(
        full_name="Arinze Elenasulu",
        email="arinze@example.com",
        preferred_roles=["Backend Engineer", "AI Engineer"],
    )
    fact = ProfileFact(
        profile=profile,
        category="skill",
        claim="Advanced pytest knowledge is confirmed.",
        confidence="confirmed",
    )
    answer = SavedAnswer(
        profile=profile,
        question_key="availability",
        question_text="When can you start?",
        answer="Available immediately.",
        sensitivity="review_before_use",
    )
    job = Job(
        company="ExampleCo",
        title="Python Backend Engineer",
        source_platform=SourcePlatform.MANUAL,
        source_url="https://example.com/jobs/1",
        job_description="Build APIs with Python.",
    )
    snapshot = JobSourceSnapshot(job=job, url=job.source_url, source_platform=SourcePlatform.MANUAL)
    application = Application(job=job, status=ApplicationStatus.SAVED, next_action="Generate pack")
    pack = ApplicationPack(application=application, company="ExampleCo", role_title="Python Backend Engineer")
    document = Document(pack=pack, document_type=DocumentType.TAILORED_CV, format="pdf", path="data/documents/cv.pdf")
    contact = Contact(job=job, name="Hiring Manager", company="ExampleCo", confidence="medium")
    task = HermesTask(task_type=TaskType.ANALYZE_JOB, status=TaskStatus.PENDING, job=job, application=application)
    approval = ApprovalCheckpoint(task=task, application=application, reason="Final submit")
    event = StatusEvent(application=application, event_type="job_saved", summary="Job saved manually")

    session.add_all([fact, answer, snapshot, document, contact, task, approval, event])
    session.commit()

    saved_job = session.scalars(select(Job).where(Job.company == "ExampleCo")).one()

    assert saved_job.application is not None
    assert saved_job.application.packs[0].documents[0].document_type == DocumentType.TAILORED_CV
    assert saved_job.snapshots[0].source_platform == SourcePlatform.MANUAL
    assert saved_job.contacts[0].name == "Hiring Manager"
    assert saved_job.hermes_tasks[0].task_type == TaskType.ANALYZE_JOB
    assert profile.facts[0].claim.startswith("Advanced pytest")
    assert profile.saved_answers[0].question_key == "availability"
    assert application.approval_checkpoints[0].reason == "Final submit"
    assert application.status_events[0].event_type == "job_saved"


def test_migration_tables_include_core_models(tmp_path):
    from alembic import command
    from alembic.config import Config

    database_path = tmp_path / "migration-models.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(config, "head")

    engine = create_database_engine(f"sqlite:///{database_path}")
    table_names = set(inspect(engine).get_table_names())

    assert "jobs" in table_names
    assert "applications" in table_names
    assert "hermes_tasks" in table_names
