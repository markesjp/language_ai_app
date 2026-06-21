from app.models import RbacPermission, RbacProfile, User
from app.services.rbac import effective_permissions, effective_profiles


def test_effective_permissions_union_multiple_profiles():
    learner = RbacProfile(name="Learner", is_active=True)
    learner.permissions = [RbacPermission(key="chat:write", description="Chat")]
    editor = RbacProfile(name="Editor", is_active=True)
    editor.permissions = [RbacPermission(key="admin.catalog:write", description="Catalog")]
    user = User(id="user-1", email="user@example.com", display_name="User")
    user.rbac_profiles = [learner, editor]

    assert effective_permissions(user) == ["admin.catalog:write", "chat:write"]
    assert effective_profiles(user) == ["Editor", "Learner"]


def test_effective_permissions_ignores_inactive_profiles():
    inactive = RbacProfile(name="Inactive", is_active=False)
    inactive.permissions = [RbacPermission(key="admin.settings:write", description="Settings")]
    user = User(id="user-1", email="user@example.com", display_name="User")
    user.rbac_profiles = [inactive]

    assert effective_permissions(user) == []
    assert effective_profiles(user) == []
