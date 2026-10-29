from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.response import Response

from ...permissions import IsAdminOrOwnUser
from ..serializers import UserSerializer

# RASTATIME 2026-10-25 (operator go) - the installation account cannot be
# deleted; the legacy user page refuses it as well
# (Application_Model_User::PROTECTED_LOGIN).
PROTECTED_USERNAME = "admin"


class UserViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrOwnUser]
    model_permission_name = "user"

    def destroy(self, request, *args, **kwargs):
        if self.get_object().username.lower() == PROTECTED_USERNAME:
            return Response(
                {"detail": "the account admin cannot be deleted"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)
