from rest_framework import serializers
from .models import Workspace, WorkspaceMember, WorkspaceInvitation
from users.serializers import UserSerializer


class WorkspaceSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    owner = UserSerializer(read_only=True)

    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'description', 'logo',
            'owner', 'my_role', 'member_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_my_role(self, obj):
        request = self.context.get('request')
        if not request:
            return 'member'
        member = obj.members.filter(user=request.user).first()
        return member.role if member else 'member'

    def get_member_count(self, obj):
        return obj.members.count()


class CreateWorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ['name', 'description']

    def create(self, validated_data):
        user = self.context['request'].user
        workspace = Workspace.objects.create(
            owner=user, **validated_data
        )
        WorkspaceMember.objects.create(
            workspace=workspace, user=user, role='owner'
        )
        return workspace


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ['id', 'user', 'role', 'joined_at']


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=['admin', 'member', 'guest'],
        default='member'
    )


class UpdateMemberRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceMember
        fields = ['role']


class WorkspaceInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceInvitation
        fields = ['id', 'email', 'role', 'status', 'expires_at', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']