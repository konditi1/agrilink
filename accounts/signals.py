import logging
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import CustomUser, FarmerProfile, ConsumerProfile

logger = logging.getLogger(__name__)

VALID_ROLES = {"farmer", "consumer"}

@receiver(pre_save, sender=CustomUser)
def switch_role(sender, instance, **kwargs):
    """Deletes the old profile if the user changes roles."""
    previous_user = None

    if instance.pk:
        try:
            previous_user = CustomUser.objects.get(pk=instance.pk)
            logger.info(f"Previous role: {previous_user.role}, New role: {instance.role}")
        except CustomUser.DoesNotExist:
            logger.warning(f"User with pk {instance.pk} not found. Assuming this is a new user.")
    
    if previous_user and previous_user.role != instance.role:
        with transaction.atomic():
            if previous_user.role == "farmer":
                FarmerProfile.objects.filter(user=instance).delete()
                logger.info(f"Deleted FarmerProfile for user {instance.email}")
            elif previous_user.role == "consumer":
                ConsumerProfile.objects.filter(user=instance).delete()
                logger.info(f"Deleted ConsumerProfile for user {instance.email}")

@receiver(post_save, sender=CustomUser)
def create_or_update_profile(sender, instance, created, **kwargs):
    """Creates or updates user profiles based on role."""
    if instance.role not in VALID_ROLES:
        logger.error(f"Invalid role '{instance.role}' for user {instance.email}. No profile created.")
        return

    with transaction.atomic():
        if created:
            if instance.role == "farmer":
                FarmerProfile.objects.create(user=instance)
                logger.info(f"Created FarmerProfile for user {instance.email}")
            elif instance.role == "consumer":
                ConsumerProfile.objects.create(user=instance)
                logger.info(f"Created ConsumerProfile for user {instance.email}")
        else:
            if instance.role == "farmer":
                FarmerProfile.objects.get_or_create(user=instance)
                logger.info(f"Updated FarmerProfile for user {instance.email}")
            elif instance.role == "consumer":
                ConsumerProfile.objects.get_or_create(user=instance)
                logger.info(f"Updated ConsumerProfile for user {instance.email}")
