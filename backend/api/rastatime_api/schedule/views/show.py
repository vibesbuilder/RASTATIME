from django_filters import rest_framework as filters
from rest_framework import viewsets

from ..models import Show, ShowDays, ShowHost, ShowInstance, ShowRebroadcast
from ..serializers import (
    ShowDaysSerializer,
    ShowHostSerializer,
    ShowInstanceSerializer,
    ShowRebroadcastSerializer,
    ShowSerializer,
)


class ShowViewSet(viewsets.ModelViewSet):
    queryset = Show.objects.all()
    serializer_class = ShowSerializer
    model_permission_name = "show"


class ShowDaysViewSet(viewsets.ModelViewSet):
    queryset = ShowDays.objects.all()
    serializer_class = ShowDaysSerializer
    model_permission_name = "showdays"


class ShowHostViewSet(viewsets.ModelViewSet):
    queryset = ShowHost.objects.all()
    serializer_class = ShowHostSerializer
    model_permission_name = "showhost"


class ShowInstanceFilter(filters.FilterSet):
    # RASTATIME 2026-10-28 - the playout's preflight scan lists the instances
    # of the next 48 h (autoplaylist_missing); a plain list was every
    # instance ever scheduled.
    starts = filters.DateTimeFromToRangeFilter(field_name="starts_at")
    ends = filters.DateTimeFromToRangeFilter(field_name="ends_at")
    modified = filters.BooleanFilter(field_name="modified")

    class Meta:
        model = ShowInstance
        fields = ["show", "modified"]


class ShowInstanceViewSet(viewsets.ModelViewSet):
    queryset = ShowInstance.objects.all()
    serializer_class = ShowInstanceSerializer
    filterset_class = ShowInstanceFilter
    model_permission_name = "showinstance"


class ShowRebroadcastViewSet(viewsets.ModelViewSet):
    queryset = ShowRebroadcast.objects.all()
    serializer_class = ShowRebroadcastSerializer
    model_permission_name = "showrebroadcast"
