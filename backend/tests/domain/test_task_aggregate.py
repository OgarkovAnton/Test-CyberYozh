from __future__ import annotations

import pytest

from src.shared_kernel.domain.actor import ActorContext
from src.shared_kernel.domain.errors import InvariantViolationError
from src.shared_kernel.domain.identifiers import UserId
from src.task_management.domain.aggregates.task import Task
from src.task_management.domain.errors import (
    CommentNotFoundError,
    CommentPermissionError,
    TaskDomainError,
    TaskPermissionError,
    TaskTransitionError,
)
from src.task_management.domain.events.task_events import (
    CommentAdded,
    TaskAssigned,
    TaskCompleted,
    TaskCreated,
    TaskDetailsChanged,
    TaskProgressStarted,
    TaskReopened,
    TaskReturnedToTodo,
)
from src.task_management.domain.value_objects.comment_body import CommentBody
from src.task_management.domain.value_objects.task_status import TaskStatus
from src.task_management.domain.value_objects.task_title import TaskTitle


def _actor(user: UserId | None = None, *, is_staff: bool = False) -> ActorContext:
    return ActorContext.of(user or UserId.generate(), is_staff=is_staff)


def test_create_records_task_created_event() -> None:
    creator = _actor()
    task = Task.create(
        title=TaskTitle("Ship DDD"),
        description="Build aggregate",
        creator=creator,
    )
    events = task.pull_events()
    assert task.status is TaskStatus.TODO
    assert len(events) == 1
    assert isinstance(events[0], TaskCreated)
    assert events[0].title == "Ship DDD"


def test_assign_start_and_complete_happy_path() -> None:
    creator = _actor()
    assignee = UserId.generate()
    task = Task.create(title=TaskTitle("Work"), description="", creator=creator)
    task.pull_events()

    task.assign(assignee_id=assignee, actor=creator)
    assert isinstance(task.pull_events()[0], TaskAssigned)

    assignee_actor = _actor(assignee)
    task.start_progress(actor=assignee_actor)
    assert task.status is TaskStatus.IN_PROGRESS
    assert isinstance(task.pull_events()[0], TaskProgressStarted)

    task.complete(actor=assignee_actor)
    assert task.status is TaskStatus.DONE
    assert task.completed_at is not None
    assert isinstance(task.pull_events()[0], TaskCompleted)


def test_cannot_complete_from_todo() -> None:
    creator = _actor()
    task = Task.create(title=TaskTitle("Work"), description="", creator=creator)
    task.pull_events()
    with pytest.raises(TaskTransitionError):
        task.complete(actor=creator)


def test_cannot_start_without_assignee() -> None:
    creator = _actor()
    task = Task.create(title=TaskTitle("Work"), description="", creator=creator)
    with pytest.raises(TaskDomainError):
        task.start_progress(actor=creator)


def test_assignee_is_frozen_while_in_progress() -> None:
    creator = _actor()
    assignee = UserId.generate()
    other = UserId.generate()
    task = Task.create(
        title=TaskTitle("Work"),
        description="",
        creator=creator,
        assignee_id=assignee,
    )
    task.start_progress(actor=_actor(assignee))
    with pytest.raises(TaskDomainError):
        task.assign(assignee_id=other, actor=creator)
    with pytest.raises(TaskDomainError):
        task.assign(assignee_id=None, actor=creator)


def test_return_to_todo_keeps_assignee() -> None:
    creator = _actor()
    assignee = UserId.generate()
    task = Task.create(
        title=TaskTitle("Work"),
        description="",
        creator=creator,
        assignee_id=assignee,
    )
    task.start_progress(actor=creator)
    task.return_to_todo(actor=creator)
    assert task.status is TaskStatus.TODO
    assert task.assignee_id == assignee
    assert isinstance(task.pull_events()[-1], TaskReturnedToTodo)
    task.assign(assignee_id=None, actor=creator)
    assert task.assignee_id is None


def test_observer_can_view_and_comment_including_done() -> None:
    creator = _actor()
    observer = _actor()
    task = Task.create(title=TaskTitle("Shared"), description="", creator=creator)
    task.assert_visible_to(observer)
    comment = task.add_comment(body=CommentBody("hi"), actor=observer)
    assert isinstance(task.pull_events()[-1], CommentAdded)
    task.assign(assignee_id=creator.user_id, actor=creator)
    task.start_progress(actor=creator)
    task.complete(actor=creator)
    task.add_comment(body=CommentBody("still open"), actor=observer)
    with pytest.raises(CommentPermissionError):
        task.edit_comment(
            comment_id=comment.id,
            body=CommentBody("nope"),
            actor=creator,
        )
    with pytest.raises(CommentPermissionError):
        task.remove_comment(comment_id=comment.id, actor=creator)


def test_author_can_edit_and_remove_comment() -> None:
    creator = _actor()
    task = Task.create(title=TaskTitle("Shared"), description="", creator=creator)
    comment = task.add_comment(body=CommentBody("note"), actor=creator)
    task.edit_comment(comment_id=comment.id, body=CommentBody("updated"), actor=creator)
    assert task.get_comment(comment.id).body.value == "updated"
    task.remove_comment(comment_id=comment.id, actor=creator)
    with pytest.raises(CommentNotFoundError):
        task.get_comment(comment.id)


def test_only_creator_or_pm_can_delete_and_only_from_todo() -> None:
    creator = _actor()
    assignee = UserId.generate()
    stranger = _actor()
    pm = _actor(is_staff=True)
    task = Task.create(
        title=TaskTitle("Work"),
        description="",
        creator=creator,
        assignee_id=assignee,
    )
    with pytest.raises(TaskPermissionError):
        task.assert_deletable_by(stranger)
    task.assert_deletable_by(pm)
    task.start_progress(actor=creator)
    with pytest.raises(TaskDomainError):
        task.assert_deletable_by(creator)


def test_pm_cannot_edit_someone_elses_comment() -> None:
    creator = _actor()
    pm = _actor(is_staff=True)
    task = Task.create(title=TaskTitle("Work"), description="", creator=creator)
    comment = task.add_comment(body=CommentBody("note"), actor=creator)
    with pytest.raises(CommentPermissionError):
        task.remove_comment(comment_id=comment.id, actor=pm)


def test_unchanged_details_do_not_record_an_event() -> None:
    creator = _actor()
    task = Task.create(title=TaskTitle("Work"), description="Same", creator=creator)
    task.pull_events()
    task.change_details(title=TaskTitle("Work"), description="Same", actor=creator)
    assert task.pull_events() == []


def test_description_length_is_bounded() -> None:
    creator = _actor()
    with pytest.raises(InvariantViolationError):
        Task.create(title=TaskTitle("Work"), description="x" * 4001, creator=creator)


def test_observer_cannot_change_status() -> None:
    creator = _actor()
    assignee = UserId.generate()
    task = Task.create(
        title=TaskTitle("Work"),
        description="",
        creator=creator,
        assignee_id=assignee,
    )
    with pytest.raises(TaskPermissionError):
        task.start_progress(actor=_actor())


def test_create_with_assignee_records_assignment() -> None:
    creator = _actor()
    assignee = UserId.generate()
    task = Task.create(
        title=TaskTitle("Work"),
        description="",
        creator=creator,
        assignee_id=assignee,
    )
    events = task.pull_events()
    assert isinstance(events[0], TaskCreated)
    assert isinstance(events[1], TaskAssigned)
    assert events[1].assignee_id == assignee.value
    assert events[1].previous_assignee_id is None


def test_reopen_clears_completion_and_keeps_assignee() -> None:
    creator = _actor()
    assignee = UserId.generate()
    task = Task.create(
        title=TaskTitle("Work"),
        description="",
        creator=creator,
        assignee_id=assignee,
    )
    task.start_progress(actor=creator)
    task.complete(actor=creator)
    assert task.completed_at is not None
    task.reopen(actor=creator)
    assert task.status is TaskStatus.TODO
    assert task.assignee_id == assignee
    assert task.completed_at is None
    assert isinstance(task.pull_events()[-1], TaskReopened)


def test_change_details_records_event_and_blocks_stranger_and_done() -> None:
    creator = _actor()
    task = Task.create(title=TaskTitle("Work"), description="d", creator=creator)
    task.pull_events()
    version = task.version
    task.change_details(title=TaskTitle("Renamed"), description="d", actor=creator)
    events = task.pull_events()
    assert task.version == version + 1
    assert isinstance(events[0], TaskDetailsChanged)
    assert events[0].title == "Renamed"
    with pytest.raises(TaskPermissionError):
        task.change_details(title=TaskTitle("Nope"), description="d", actor=_actor())
    task.assign(assignee_id=creator.user_id, actor=creator)
    task.start_progress(actor=creator)
    task.complete(actor=creator)
    with pytest.raises(TaskDomainError):
        task.change_details(title=TaskTitle("Later"), description="d", actor=creator)
    with pytest.raises(TaskDomainError):
        task.change_details(
            title=TaskTitle("Later"),
            description="d",
            actor=_actor(is_staff=True),
        )


def test_same_assignee_does_not_record_another_event() -> None:
    creator = _actor()
    assignee = UserId.generate()
    task = Task.create(
        title=TaskTitle("Work"),
        description="",
        creator=creator,
        assignee_id=assignee,
    )
    task.pull_events()
    version = task.version
    task.assign(assignee_id=assignee, actor=creator)
    assert task.pull_events() == []
    assert task.version == version


def test_title_and_comment_reject_blank_values() -> None:
    with pytest.raises(InvariantViolationError):
        TaskTitle("   ")
    with pytest.raises(InvariantViolationError):
        TaskTitle("x" * 201)
    with pytest.raises(InvariantViolationError):
        CommentBody("  ")


def test_return_and_reopen_require_the_right_status() -> None:
    creator = _actor()
    task = Task.create(title=TaskTitle("Work"), description="", creator=creator)
    with pytest.raises(TaskTransitionError):
        task.return_to_todo(actor=creator)
    with pytest.raises(TaskTransitionError):
        task.reopen(actor=creator)


def test_unassign_records_previous_assignee() -> None:
    creator = _actor()
    assignee = UserId.generate()
    task = Task.create(
        title=TaskTitle("Work"),
        description="",
        creator=creator,
        assignee_id=assignee,
    )
    task.pull_events()
    task.assign(assignee_id=None, actor=creator)
    event = task.pull_events()[-1]
    assert isinstance(event, TaskAssigned)
    assert event.assignee_id is None
    assert event.previous_assignee_id == assignee.value
