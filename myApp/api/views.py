from rest_framework.views import APIView
from .serializers import AuthorSerializer
from myApp.models import Author
from rest_framework.response import Response
from rest_framework import status



class AuthorAPIView(APIView):
    def get(self, request):
        authors = Author.objects.all()
        serialized_authors = AuthorSerializer(authors, many=True)
        return Response(
            serialized_authors.data,
            status=status.HTTP_200_OK
        )