import uuid
from django.db import models

# Create your models here.

from django.contrib.auth.models import User
from django.utils import timezone


class Station(models.Model):
    name = models.CharField(max_length=20)
    address = models.CharField(max_length=200)
    code = models.CharField(
        max_length=20,
        unique=True,
        blank=False,
        null=False
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def str(self):
        return self.name


class FuelPrice(models.Model):
    price_per_litre = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )
    time = models.DateTimeField(auto_now_add=True)
    set_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fuel_prices_set'
    )

    class Meta:
        ordering = ["-time"]

    def str(self):
        return f"N {self.price_per_litre}/litre created by {self.set_by}"


class LitrePurchase(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    litres_bought = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )
    current_price_per_litre = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        editable=False
    )
    payment_reference = models.CharField(
        max_length=100,
        unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def str(self):
        return (
            f"{self.user.username} bought "
            f"{self.litres_bought}L -> "
            f"total: {self.total_amount}"
        )

    def save(self, *args, **kwargs):
        self.total_amount = (
            self.litres_bought *
            self.current_price_per_litre
        )
        super().save(*args, **kwargs)


class LitreWallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="litre_wallet"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def str(self):
        return f"{self.user.username}'s Litre wallet"

    @property
    def available_litres(self):
        lots = self.user.litrelot_set.filter(
            status="ACTIVE",
            expires_at__gt=timezone.now(),
            litres_remaining__gt=0
        )

        return sum(
            (lot.litres_remaining for lot in lots),
            0
        )


class LitreLot(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("EXHAUSTED", "Exhausted"),
        ("EXPIRED", "Expired"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    purchase = models.OneToOneField(
        LitrePurchase,
        on_delete=models.CASCADE
    )
    litres_purchased = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )
    litres_remaining = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )
    price_per_litre = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )
    expires_at = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def str(self):
        return (
            f"{self.user.username} - "
            f"{self.litres_remaining}L remaining"
        )

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class FuelRedemption(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("REDEEMED", "Redeemed"),
        ("EXPIRED", "Expired"),
        ("CANCELED", "Canceled"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="fuel_redemptions"
    )

    station = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="fuel_redemptions"
    )
    
    litres_redeemed = models.DecimalField(
        max_digits=10,
        decimal_places=3
    )

    qr_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    qr_expired_at = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    redeemed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendant_redemptions"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    redeemed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def str(self):
        return (
            f"{self.user.username} - "
            f"{self.litres_redeemed}L - "
            f"{self.status}"
        )

    @property
    def is_expired(self):
        return timezone.now() >= self.qr_expired_at

    @property
    def verification_code(self):
        """
        Generate a short 6-digit verification code
        from the QR UUID.
        """

        return str(
            int(self.qr_code.hex[:6], 16) % 1000000
        ).zfill(6)


class initializePaymentMethod(models.Model):
    STATUS_CHOICES = [
            ("PENDING", "Pending"),
            ("SUCCESS", "success"),
            ("EXPIRED", "Expired"),
            ("CANCELED", "Canceled"),
        ]
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100, unique=True)
    used = models.BooleanField(default=False)
    litre_to_purchase = models.DecimalField(max_digits=10, decimal_places=3)
    price_per_litre = models.DecimalField(max_digits=8, decimal_places=2)
    total_amount_to_pay = models.DecimalField(max_digits=10, decimal_places=3, default =0.00) 
    status = models.CharField(choices=STATUS_CHOICES, max_length=10, default="PENDING")