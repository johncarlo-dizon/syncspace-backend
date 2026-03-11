from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Workspace, WorkspaceMember, WorkspaceInvitation
from .serializers import (
    WorkspaceSerializer,
    CreateWorkspaceSerializer,
    WorkspaceMemberSerializer,
    InviteMemberSerializer,
    UpdateMemberRoleSerializer,
)


class WorkspaceListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateWorkspaceSerializer
        return WorkspaceSerializer

    def get_queryset(self):
        return Workspace.objects.filter(
            members__user=self.request.user
        ).distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = CreateWorkspaceSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        workspace = serializer.save()
        return Response(
            WorkspaceSerializer(workspace, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = WorkspaceSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)


class WorkspaceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkspaceSerializer

    def get_queryset(self):
        return Workspace.objects.filter(
            members__user=self.request.user
        ).distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class WorkspaceMemberListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkspaceMemberSerializer

    def get_queryset(self):
        return WorkspaceMember.objects.filter(
            workspace_id=self.kwargs['pk']
        ).select_related('user').order_by('joined_at')


class InviteMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk)

        # Check requester is admin or owner
        requester = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).first()
        if not requester or requester.role not in ['owner', 'admin']:
            return Response(
                {'error': 'You do not have permission to invite members.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        role = serializer.validated_data['role']

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(email=email)
            if WorkspaceMember.objects.filter(workspace=workspace, user=user).exists():
                return Response(
                    {'error': 'User is already a member.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            member = WorkspaceMember.objects.create(
                workspace=workspace, user=user, role=role
            )
            return Response(
                WorkspaceMemberSerializer(member).data,
                status=status.HTTP_201_CREATED
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'No user found with that email.'},
                status=status.HTTP_404_NOT_FOUND
            )


class RemoveMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, user_id):
        workspace = get_object_or_404(Workspace, id=pk)

        requester = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).first()
        if not requester or requester.role not in ['owner', 'admin']:
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )

        member = get_object_or_404(
            WorkspaceMember, workspace=workspace, user_id=user_id
        )
        if member.role == 'owner':
            return Response(
                {'error': 'Cannot remove the workspace owner.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UpdateMemberRoleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk, user_id):
        workspace = get_object_or_404(Workspace, id=pk)

        requester = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).first()
        if not requester or requester.role not in ['owner', 'admin']:
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )

        member = get_object_or_404(
            WorkspaceMember, workspace=workspace, user_id=user_id
        )
        serializer = UpdateMemberRoleSerializer(
            member, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(WorkspaceMemberSerializer(member).data)


class AcceptInviteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        invitation = get_object_or_404(WorkspaceInvitation, token=token)
        if invitation.status != 'pending':
            return Response(
                {'error': 'Invitation is no longer valid.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        WorkspaceMember.objects.get_or_create(
            workspace=invitation.workspace,
            user=request.user,
            defaults={'role': invitation.role}
        )
        invitation.status = 'accepted'
        invitation.save()
        return Response({'message': 'Joined workspace successfully.'})



class RemoveMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, user_id):
        workspace = get_object_or_404(Workspace, id=pk)

        requester = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).first()

        is_admin = requester and requester.role in ['owner', 'admin']
        is_self = request.user.id == user_id  # ✅ allow self-removal (leave)

        if not is_admin and not is_self:
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )

        member = get_object_or_404(
            WorkspaceMember, workspace=workspace, user_id=user_id
        )
        if member.role == 'owner':
            return Response(
                {'error': 'Cannot remove the workspace owner.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)