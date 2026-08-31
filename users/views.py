from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import logout
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
from .serializers import RegisterSerializer, LoginSerializer, UtilisateurSerializer
from .backends import EmailOrTelephoneBackend

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    """
    POST /api/auth/register/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            utilisateur = serializer.save()
            return Response(
                {
                    "message": "Compte créé avec succès.",
                    "utilisateur": UtilisateurSerializer(utilisateur).data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """
    POST /api/auth/login/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        identifiant = serializer.validated_data['identifiant']
        password = serializer.validated_data['password']

        backend = EmailOrTelephoneBackend()
        utilisateur = backend.authenticate(
            request,
            username=identifiant,
            password=password
        )

        if utilisateur is None:
            return Response(
                {"detail": "Identifiants incorrects."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Gestion manuelle de la session (évite le signal last_login)
        request.session[SESSION_KEY] = str(utilisateur.pk)
        request.session[BACKEND_SESSION_KEY] = 'users.backends.EmailOrTelephoneBackend'
        request.session[HASH_SESSION_KEY] = utilisateur.get_session_auth_hash()
        request.session.cycle_key()  # sécurité : change l'ID de session

        return Response(
            {
                "message": "Connexion réussie.",
                "utilisateur": UtilisateurSerializer(utilisateur).data
            },
            status=status.HTTP_200_OK
        )


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    """
    POST /api/auth/logout/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "Déconnexion réussie."}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class MeView(APIView):
    """
    GET /api/auth/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UtilisateurSerializer(request.user).data)