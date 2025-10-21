from django.db import models
# from django.contrib.auth import get_user_model
# User = get_user_model()
# from django.utils import timezone


# class MyWallet(models.Model):
#     user = models.ForeignKey(User,on_delete=models.CASCADE , related_name='wallet')
#     balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    
#     def __str__(self):
#         return f"{self.user.username}'s Wallet - Balance: ₹{self.balance}"

#     def credit(self, amount, description=""):
#         """Add money to wallet"""
#         self.balance += amount
#         self.save()
#         WalletTransaction.objects.create(wallet=self, amount=amount, transaction_type='CREDIT', description=description)

#     def debit(self, amount, description=""):
#         """Deduct money if balance available"""
#         if self.balance >= amount:
#             self.balance -= amount
#             self.save()
#             WalletTransaction.objects.create(wallet=self, amount=amount, transaction_type='DEBIT', description=description)
#         else:
#             raise ValueError("Insufficient wallet balance!")


# class WalletTransaction(models.Model):
#     TRANSACTION_TYPES = (
#         ('CREDIT', 'Credit'),
#         ('DEBIT', 'Debit'),
#     )

#     wallet = models.ForeignKey(MyWallet, on_delete=models.CASCADE, related_name='transactions')
#     transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     description = models.CharField(max_length=255, blank=True, null=True)
#     created_at = models.DateTimeField(default=timezone.now)

#     class Meta:
#         ordering = ['-created_at']

#     def __str__(self):
#         return f"{self.transaction_type} ₹{self.amount} ({self.created_at.date()})"