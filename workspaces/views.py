from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
import uuid
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
    """Invite by email — adds user directly if they exist, sends email invite if not."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk)

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
            # Send notification email
            _send_invite_email(
                to_email=email,
                inviter=request.user.username,
                workspace_name=workspace.name,
                join_url=f"{settings.FRONTEND_URL}/dashboard",
            )
            return Response(
                WorkspaceMemberSerializer(member).data,
                status=status.HTTP_201_CREATED
            )
        except User.DoesNotExist:
            # User doesn't exist — create invitation token and send signup link
            invitation, _ = WorkspaceInvitation.objects.get_or_create(
                workspace=workspace,
                email=email,
                defaults={'role': role, 'token': uuid.uuid4(), 'status': 'pending'}
            )
            join_url = f"{settings.FRONTEND_URL}/invite/{invitation.token}"
            _send_invite_email(
                to_email=email,
                inviter=request.user.username,
                workspace_name=workspace.name,
                join_url=join_url,
                is_new_user=True,
            )
            return Response(
                {'message': f'Invitation sent to {email}.'},
                status=status.HTTP_200_OK
            )


class GenerateInviteLinkView(APIView):
    """Generate a shareable invite link for the workspace."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, id=pk)

        requester = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).first()
        if not requester or requester.role not in ['owner', 'admin']:
            return Response(
                {'error': 'Permission denied.'},
                status=status.HTTP_403_FORBIDDEN
            )

        role = request.data.get('role', 'member')

        # Create a link-based invitation (no email)
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email=None,
            role=role,
            token=uuid.uuid4(),
            status='pending',
        )

        join_url = f"{settings.FRONTEND_URL}/invite/{invitation.token}"
        return Response({'invite_link': join_url, 'token': str(invitation.token)})


class AcceptInviteView(APIView):
    """Accept an invite — works for both email invites and link invites."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token):
        invitation = get_object_or_404(WorkspaceInvitation, token=token)

        if invitation.status == 'accepted':
            # Already accepted — just redirect them in
            already = WorkspaceMember.objects.filter(
                workspace=invitation.workspace, user=request.user
            ).first()
            if already:
                return Response({
                    'message': 'Already a member.',
                    'workspace_id': str(invitation.workspace.id)
                })

        if invitation.status == 'revoked':
            return Response(
                {'error': 'This invite link has been revoked.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if WorkspaceMember.objects.filter(
            workspace=invitation.workspace, user=request.user
        ).exists():
            return Response({
                'message': 'Already a member.',
                'workspace_id': str(invitation.workspace.id)
            })

        WorkspaceMember.objects.create(
            workspace=invitation.workspace,
            user=request.user,
            role=invitation.role
        )

        # Only mark as accepted if it's an email invite (not a reusable link)
        if invitation.email:
            invitation.status = 'accepted'
            invitation.save()

        return Response({
            'message': 'Joined workspace successfully.',
            'workspace_id': str(invitation.workspace.id)
        })


class GetInviteInfoView(APIView):
    """Get workspace info from invite token — shown on the invite page before accepting."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        invitation = get_object_or_404(WorkspaceInvitation, token=token)

        if invitation.status == 'revoked':
            return Response(
                {'error': 'This invite link has been revoked.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'workspace_name': invitation.workspace.name,
            'workspace_id': str(invitation.workspace.id),
            'role': invitation.role,
            'token': str(invitation.token),
        })


class RemoveMemberView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, user_id):
        workspace = get_object_or_404(Workspace, id=pk)

        requester = WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user
        ).first()

        is_admin = requester and requester.role in ['owner', 'admin']
        is_self = request.user.id == user_id

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


# ------------------------------------
# Helper
# ------------------------------------

def _send_invite_email(to_email, inviter, workspace_name, join_url, is_new_user=False):
    """Send workspace invite email. Fails silently if email not configured."""
    try:
        if is_new_user:
            subject = f"{inviter} invited you to join {workspace_name} on SyncSpace"
            body = f"""Hi there,

{inviter} has invited you to join the workspace "{workspace_name}" on SyncSpace.

Click the link below to create your account and join:
{join_url}

If you didn't expect this invitation, you can ignore this email.

— The SyncSpace Team
"""
        else:
            subject = f"{inviter} added you to {workspace_name} on SyncSpace"
            body = f"""Hi there,

{inviter} has added you to the workspace "{workspace_name}" on SyncSpace.

Click the link below to get started:
{join_url}

— The SyncSpace Team
"""
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )
    except Exception:
        pass  # Never crash the API because of email failure