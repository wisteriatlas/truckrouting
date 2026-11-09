from datetime import datetime

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import providers, service, weather


class PointSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)


class AnalyzeSerializer(serializers.Serializer):
    origin = PointSerializer()
    destination = PointSerializer()
    departure_time = serializers.DateTimeField()
    load_lb = serializers.FloatField(min_value=0, max_value=200_000)


class GeocodeView(APIView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response([])
        try:
            return Response(providers.geocode(q))
        except providers.ProviderError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class AnalyzeView(APIView):
    def post(self, request):
        s = AnalyzeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            result = service.analyze(
                (d["origin"]["lat"], d["origin"]["lon"]),
                (d["destination"]["lat"], d["destination"]["lon"]),
                d["departure_time"],
                d["load_lb"],
            )
        except (providers.ProviderError, weather.WeatherError) as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(result)


class HealthView(APIView):
    def get(self, request):
        return Response({"ok": True, "time": datetime.utcnow().isoformat()})
