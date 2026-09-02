from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth import logout
from .backends import EmailOrTelephoneBackend
from .models import Utilisateur


class LoginWebView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('web-catalogue')
        return render(request, 'auth/login.html')

    def post(self, request):
        identifiant = request.POST.get('identifiant', '').strip()
        password = request.POST.get('password', '')

        backend = EmailOrTelephoneBackend()
        utilisateur = backend.authenticate(request, username=identifiant, password=password)

        if utilisateur is None:
            messages.error(request, "Identifiants incorrects.")
            return render(request, 'auth/login.html')

        # Session manuelle (même logique que l'API)
        from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
        request.session[SESSION_KEY] = str(utilisateur.pk)
        request.session[BACKEND_SESSION_KEY] = 'users.backends.EmailOrTelephoneBackend'
        request.session[HASH_SESSION_KEY] = utilisateur.get_session_auth_hash()
        request.session.cycle_key()

        messages.success(request, f"Bonjour {utilisateur.prenom} !")
        return redirect('web-catalogue')


class LogoutWebView(View):
    def get(self, request):
        logout(request)
        messages.success(request, "Vous êtes déconnecté.")
        return redirect('web-catalogue')


class RegisterWebView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('web-catalogue')
        return render(request, 'auth/register.html')

    def post(self, request):
        nom = request.POST.get('nom', '').strip()
        prenom = request.POST.get('prenom', '').strip()
        email = request.POST.get('email', '').strip() or None
        telephone = request.POST.get('telephone', '').strip() or None
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if not nom or not prenom:
            messages.error(request, "Nom et prénom obligatoires.")
            return render(request, 'auth/register.html')

        if not email and not telephone:
            messages.error(request, "Fournissez un email ou un téléphone.")
            return render(request, 'auth/register.html')

        if password != password_confirm or len(password) < 8:
            messages.error(request, "Mot de passe invalide (min. 8 caractères, confirmation identique).")
            return render(request, 'auth/register.html')

        if email and Utilisateur.objects.filter(email__iexact=email).exists():
            messages.error(request, "Cet email est déjà utilisé.")
            return render(request, 'auth/register.html')

        if telephone and Utilisateur.objects.filter(telephone=telephone).exists():
            messages.error(request, "Ce téléphone est déjà utilisé.")
            return render(request, 'auth/register.html')

        utilisateur = Utilisateur(
            nom=nom, prenom=prenom, email=email, telephone=telephone,
            role=Utilisateur.Role.CLIENT, actif=True
        )
        utilisateur.set_password(password)
        utilisateur.save()

        messages.success(request, "Compte créé. Vous pouvez vous connecter.")
        return redirect('web-login')