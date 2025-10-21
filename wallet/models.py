from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator
import uuid

User = get_user_model()


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallets')
    balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'
    
    def __str__(self):
        return f"{self.user.email} - ₹{self.balance}"
    
    def add_money(self, amount, transaction_type, description, reference_id=None):
        """Add money to wallet and create transaction"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        self.balance += Decimal(str(amount))
        self.save()
        
        transaction = WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference_id=reference_id
        )
        
        return transaction
    
    def deduct_money(self, amount, transaction_type, description, reference_id=None):
        """Deduct money from wallet and create transaction"""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        if self.balance < Decimal(str(amount)):
            raise ValueError("Insufficient wallet balance")
        
        self.balance -= Decimal(str(amount))
        self.save()
        
        # Create transaction record
        transaction = WalletTransaction.objects.create(
            wallet=self,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=self.balance,
            description=description,
            reference_id=reference_id
        )
        
        return transaction
    
    def has_sufficient_balance(self, amount):
        """Check if wallet has enough balance"""
        return self.balance >= Decimal(str(amount))


class WalletTransaction(models.Model):
    """Track all wallet transactions"""
    
    CREDIT_REFUND = 'credit_refund'
    CREDIT_CASHBACK = 'credit_cashback'
    CREDIT_REFERRAL = 'credit_referral'
    CREDIT_ADMIN = 'credit_admin'
    CREDIT_RETURN = 'credit_return'
    DEBIT_PURCHASE = 'debit_purchase'
    DEBIT_WITHDRAWAL = 'debit_withdrawal'
    DEBIT_ADMIN = 'debit_admin'
    
    TRANSACTION_TYPE_CHOICES = (
        (CREDIT_REFUND, 'Refund Credit'),
        (CREDIT_CASHBACK, 'Cashback Credit'),
        (CREDIT_REFERRAL, 'Referral Bonus Credit'),
        (CREDIT_ADMIN, 'Admin Credit'),
        (CREDIT_RETURN, 'Return Credit'),
        (DEBIT_PURCHASE, 'Purchase Debit'),
        (DEBIT_WITHDRAWAL, 'Withdrawal Debit'),
        (DEBIT_ADMIN, 'Admin Debit'),
    )
    
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
    )
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    reference_id = models.CharField(max_length=100, null=True, blank=True, help_text="Order ID, Refund ID, etc.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=COMPLETED)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'
    
    def __str__(self):
        return f"{self.transaction_id} - {self.get_transaction_type_display()} - ₹{self.amount}" #pylint: disable=no-member
    
    @property
    def is_credit(self):
        """Check if transaction is credit"""
        return self.transaction_type in [
            self.CREDIT_REFUND,
            self.CREDIT_CASHBACK,
            self.CREDIT_REFERRAL,
            self.CREDIT_ADMIN,
            self.CREDIT_RETURN
        ]
    
    @property
    def is_debit(self):
        """Check if transaction is debit"""
        return not self.is_credit


class WalletWithdrawalRequest(models.Model):
    """Withdrawal requests from users"""
    
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    PROCESSED = 'processed'
    
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (PROCESSED, 'Processed'),
    )
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='withdrawal_requests')
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Bank details
    account_holder_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=200)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    admin_remarks = models.TextField(null=True, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_withdrawals')
    
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Withdrawal Request'
        verbose_name_plural = 'Withdrawal Requests'
    
    def __str__(self):
        return f"{self.request_id} - {self.wallet.user.email} - ₹{self.amount}"
    
    def approve(self, admin_user, remarks=None):
        """Approve withdrawal request"""
        if self.status != self.PENDING:
            raise ValueError("Only pending requests can be approved")
        
        if not self.wallet.has_sufficient_balance(self.amount):
            raise ValueError("Insufficient wallet balance")
        
        # Deduct from wallet
        self.wallet.deduct_money(
            amount=self.amount,
            transaction_type=WalletTransaction.DEBIT_WITHDRAWAL,
            description=f"Withdrawal to bank account {self.account_number}",
            reference_id=str(self.request_id)
        )
        
        self.status = self.PROCESSED
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.admin_remarks = remarks
        self.save()
    
    def reject(self, admin_user, remarks):
        """Reject withdrawal request"""
        if self.status != self.PENDING:
            raise ValueError("Only pending requests can be rejected")
        
        self.status = self.REJECTED
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.admin_remarks = remarks
        self.save()
    
    def user_name(self):
        return self.wallet.user.full_name
    def user_email(self):
        return self.wallet.user.email