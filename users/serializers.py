from rest_framework import serializers
from django.db.models import Q
from .models import Utilisateur


class RegisterSerializer(serializers.Serializer):
    """
    Serializer d'inscription.
    Règles respectées :
    - nom + prénom obligatoires
    - au moins email OU téléphone
    - mot de passe obligatoire (min 8 caractères)
    """
    nom = serializers.CharField(max_length=100)
    prenom = serializers.CharField(max_length=100)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    telephone = serializers.CharField(max_length=30, required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    def validate(self, data):
        email = data.get('email') or None
        telephone = data.get('telephone') or None
        password = data.get('password')
        password_confirm = data.get('password_confirm')

        # Au moins un moyen de contact
        if not email and not telephone:
            raise serializers.ValidationError(
                "Vous devez fournir au moins un email ou un numéro de téléphone."
            )

        # Mot de passe confirmation
        if password != password_confirm:
            raise serializers.ValidationError({
                "password_confirm": "Les deux mots de passe ne correspondent pas."
            })

        # Unicité email (insensible à la casse)
        if email:
            if Utilisateur.objects.filter(email__iexact=email).exists():
                raise serializers.ValidationError({
                    "email": "Cet email est déjà utilisé."
                })

        # Unicité téléphone
        if telephone:
            if Utilisateur.objects.filter(telephone=telephone).exists():
                raise serializers.ValidationError({
                    "telephone": "Ce numéro de téléphone est déjà utilisé."
                })

        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        utilisateur = Utilisateur(
            nom=validated_data['nom'],
            prenom=validated_data['prenom'],
            email=validated_data.get('email') or None,
            telephone=validated_data.get('telephone') or None,
            role=Utilisateur.Role.CLIENT,
            actif=True,
        )
        utilisateur.set_password(password)
        utilisateur.save()
        return utilisateur


class LoginSerializer(serializers.Serializer):
    """
    Serializer de connexion.
    `identifiant` = email OU téléphone
    """
    identifiant = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class UtilisateurSerializer(serializers.ModelSerializer):
    """Serializer de lecture d'un utilisateur (sans le hash du mot de passe)."""
    class Meta:
        model = Utilisateur
        fields = (
            'id_utilisateur',
            'nom',
            'prenom',
            'email',
            'telephone',
            'role',
            'actif',
            'date_creation',
        )
        read_only_fields = fields