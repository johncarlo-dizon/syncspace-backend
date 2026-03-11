from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Project, ProjectMember
from .serializers import ProjectSerializer, ProjectMemberSerializer
from workspaces.models import Workspace, WorkspaceMember


class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(
            workspace__id=self.kwargs['workspace_id'],
            workspace__members__user=self.request.user
        ).distinct()

    def perform_create(self, serializer):
        workspace = get_object_or_404(Workspace, id=self.kwargs['workspace_id'])
        project = serializer.save(
            workspace=workspace,
            created_by=self.request.user
        )
        # Auto-add creator as owner
        ProjectMember.objects.create(
            project=project,
            user=self.request.user,
            role='owner'
        )


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(
            workspace__members__user=self.request.user
        ).distinct()


class ProjectMemberListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectMemberSerializer

    def get_queryset(self):
        return ProjectMember.objects.filter(
            project__id=self.kwargs['project_id']
        ).select_related('user').order_by('joined_at')


class ProjectInviteMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)

        # Must be workspace member
        is_workspace_member = WorkspaceMember.objects.filter(
            workspace=project.workspace, user=request.user
        ).exists()
        if not is_workspace_member:
            return Response({'error': 'Permission denied.'}, status=403)

        from django.contrib.auth import get_user_model
        User = get_user_model()

        email = request.data.get('email', '').strip()
        role = request.data.get('role', 'member')

        if not email:
            return Response({'error': 'Email is required.'}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'No user found with that email.'}, status=404)

        if ProjectMember.objects.filter(project=project, user=user).exists():
            return Response({'error': 'User is already a project member.'}, status=400)

        # Also add to workspace if not already a member
        WorkspaceMember.objects.get_or_create(
            workspace=project.workspace, user=user,
            defaults={'role': 'member'}
        )

        member = ProjectMember.objects.create(project=project, user=user, role=role)
        return Response(ProjectMemberSerializer(member).data, status=201)


class ProjectRemoveMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, project_id, user_id):
        project = get_object_or_404(Project, id=project_id)

        # Must be workspace member to remove others
        is_workspace_member = WorkspaceMember.objects.filter(
            workspace=project.workspace, user=request.user
        ).exists()
        if not is_workspace_member:
            return Response({'error': 'Permission denied.'}, status=403)

        member = get_object_or_404(ProjectMember, project=project, user_id=user_id)

        if member.role == 'owner':
            return Response({'error': 'Cannot remove the project owner.'}, status=400)

        member.delete()
        return Response(status=204)