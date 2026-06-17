"""Tests for BaseEntity — the root of all EIOS domain objects."""

from datetime import UTC

from domain.base_entity import BaseEntity
from domain.enums import EntityStatus


class TestBaseEntity:
    def test_instantiation_with_defaults(self) -> None:
        entity = BaseEntity()
        assert entity.id is not None
        assert len(entity.id) == 36  # UUID4 string
        assert entity.status == EntityStatus.DRAFT
        assert entity.version == 1
        assert entity.owner is None
        assert entity.created_by is None
        assert entity.updated_by is None

    def test_id_is_unique(self) -> None:
        a = BaseEntity()
        b = BaseEntity()
        assert a.id != b.id

    def test_created_at_is_utc(self) -> None:
        entity = BaseEntity()
        assert entity.created_at.tzinfo == UTC

    def test_updated_at_is_utc(self) -> None:
        entity = BaseEntity()
        assert entity.updated_at.tzinfo == UTC

    def test_explicit_id(self) -> None:
        entity = BaseEntity(id="custom-id")
        assert entity.id == "custom-id"

    def test_explicit_status(self) -> None:
        entity = BaseEntity(status=EntityStatus.ACTIVE)
        assert entity.status == EntityStatus.ACTIVE

    def test_all_nine_statuses_are_valid(self) -> None:
        for status in EntityStatus:
            entity = BaseEntity(status=status)
            assert entity.status == status

    def test_owner_can_be_set(self) -> None:
        entity = BaseEntity(owner="org-123")
        assert entity.owner == "org-123"

    def test_audit_fields_can_be_set(self) -> None:
        entity = BaseEntity(created_by="user-1", updated_by="user-2")
        assert entity.created_by == "user-1"
        assert entity.updated_by == "user-2"
